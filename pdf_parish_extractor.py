"""
PDF Parish Directory Extractor for dioceses that publish parish directories as PDF files.
Handles downloading, parsing, and extracting parish information from PDF documents.
"""

import re
import requests
import tempfile
import os
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import PyPDF2
import pdfplumber
from core.logger import get_logger
from core.db import get_supabase_client
from dataclasses import dataclass

logger = get_logger(__name__)

@dataclass
class ParishData:
    """Data class for parish information"""
    name: str
    city: str = ""
    state: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    pastor: str = ""
    confidence: float = 0.8  # Default confidence for PDF extraction

class PDFParishExtractor:
    """
    Extractor for parish directories published as PDF files.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def can_handle(self, url: str, page_source: str = None) -> float:
        """
        Determine if this extractor can handle the given URL.
        Returns confidence score between 0.0 and 1.0.
        """
        confidence = 0.0
        
        # Check for PDF in URL
        if '.pdf' in url.lower():
            confidence += 0.7
        
        # Check for PDF-related keywords in page source
        if page_source:
            pdf_indicators = [
                'parish directory.pdf',
                'parish list.pdf',
                'church directory.pdf',
                'parish guide.pdf',
                '.pdf',
                'download parish directory',
                'parish directory download'
            ]
            
            page_lower = page_source.lower()
            for indicator in pdf_indicators:
                if indicator in page_lower:
                    confidence += 0.1
                    
        return min(confidence, 1.0)
    
    def find_pdf_urls(self, base_url: str, page_content: str) -> List[str]:
        """Find PDF URLs in the page content that might contain parish directories."""
        pdf_urls = []
        
        # Common patterns for PDF links
        pdf_patterns = [
            r'href=["\']([^"\']*\.pdf)["\']',
            r'src=["\']([^"\']*\.pdf)["\']',
            r'url\(["\']?([^"\']*\.pdf)["\']?\)',
        ]
        
        for pattern in pdf_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                # Convert relative URLs to absolute
                if match.startswith('http'):
                    pdf_urls.append(match)
                else:
                    pdf_urls.append(urljoin(base_url, match))
        
        # Filter for likely parish directory PDFs
        parish_keywords = [
            'parish', 'church', 'directory', 'guide', 'list', 'contact'
        ]
        
        filtered_urls = []
        for url in pdf_urls:
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in parish_keywords):
                filtered_urls.append(url)
        
        return filtered_urls
    
    def download_pdf(self, pdf_url: str) -> Optional[str]:
        """Download PDF file and return path to temporary file."""
        try:
            logger.info(f"📥 Downloading PDF from: {pdf_url}")
            response = self.session.get(pdf_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            logger.info(f"✅ PDF downloaded to: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"❌ Failed to download PDF {pdf_url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods."""
        text = ""
        
        # Method 1: Try pdfplumber first (better for structured documents)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            
            if text.strip():
                logger.info(f"✅ Text extracted using pdfplumber ({len(text)} chars)")
                return text
                
        except Exception as e:
            logger.warning(f"⚠️ pdfplumber failed: {e}")
        
        # Method 2: Fall back to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
            
            if text.strip():
                logger.info(f"✅ Text extracted using PyPDF2 ({len(text)} chars)")
                return text
                
        except Exception as e:
            logger.error(f"❌ PyPDF2 also failed: {e}")
        
        return text
    
    def parse_parishes_from_text(self, text: str) -> List[ParishData]:
        """Parse parish information from extracted PDF text."""
        parishes = []
        
        # Common parish name patterns
        parish_patterns = [
            # "St. Mary Catholic Church - City, State"
            r'((?:St\.|Saint)\s+[^-\n]+?Catholic\s+Church)\s*[-–]\s*([^,\n]+),?\s*([A-Z]{2})?',
            # "Holy Family Parish - Address"
            r'((?:Holy|Blessed|Our Lady|Sacred)\s+[^-\n]+?(?:Parish|Church))\s*[-–]\s*([^,\n]+)',
            # "Saint Name Church, City"
            r'((?:St\.|Saint)\s+[^,\n]+?Church),\s*([^,\n]+)',
            # "Parish Name - Phone: (xxx) xxx-xxxx"
            r'([^-\n]+?(?:Parish|Church|Cathedral))\s*[-–]\s*(?:Phone:?\s*)?(\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4})',
        ]
        
        for pattern in parish_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    name = match[0].strip()
                    location_or_phone = match[1].strip()
                    
                    # Skip if name is too short or contains unwanted text
                    if len(name) < 5 or any(skip in name.lower() for skip in ['page', 'directory', 'index']):
                        continue
                    
                    parish = ParishData(name=name)
                    
                    # Determine if second match is location or phone
                    if re.match(r'\([0-9]{3}\)', location_or_phone):
                        parish.phone = location_or_phone
                    else:
                        parish.city = location_or_phone
                        if len(match) > 2 and match[2]:
                            parish.state = match[2]
                    
                    parishes.append(parish)
        
        # Remove duplicates based on parish name
        unique_parishes = []
        seen_names = set()
        
        for parish in parishes:
            normalized_name = self._normalize_parish_name(parish.name)
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_parishes.append(parish)
        
        return unique_parishes
    
    def _normalize_parish_name(self, name: str) -> str:
        """Normalize parish name for duplicate detection."""
        # Remove common variations
        normalized = name.lower().strip()
        normalized = re.sub(r'\bcatholic\b', '', normalized)
        normalized = re.sub(r'\bchurch\b', '', normalized)
        normalized = re.sub(r'\bparish\b', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()
    
    def extract_parishes(self, url: str) -> List[ParishData]:
        """
        Main extraction method for PDF-based parish directories.
        """
        logger.info(f"🎯 PDF Extractor processing: {url}")
        
        parishes = []
        temp_files = []
        
        try:
            # If URL is directly a PDF
            if url.lower().endswith('.pdf'):
                pdf_urls = [url]
            else:
                # Get page content to find PDF links
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                pdf_urls = self.find_pdf_urls(url, response.text)
            
            if not pdf_urls:
                logger.warning("⚠️ No PDF URLs found")
                return parishes
            
            logger.info(f"📋 Found {len(pdf_urls)} potential PDF(s)")
            
            # Process each PDF
            for pdf_url in pdf_urls[:3]:  # Limit to first 3 PDFs
                temp_file = self.download_pdf(pdf_url)
                if temp_file:
                    temp_files.append(temp_file)
                    
                    # Extract text from PDF
                    text = self.extract_text_from_pdf(temp_file)
                    if text.strip():
                        # Parse parishes from text
                        pdf_parishes = self.parse_parishes_from_text(text)
                        parishes.extend(pdf_parishes)
                        
                        logger.info(f"✅ Extracted {len(pdf_parishes)} parishes from PDF")
                    else:
                        logger.warning("⚠️ No text could be extracted from PDF")
            
            logger.info(f"📊 Total parishes extracted: {len(parishes)}")
            
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
        
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete temp file {temp_file}: {e}")
        
        return parishes


def create_pdf_parish_extractor(timeout: int = 30) -> PDFParishExtractor:
    """Factory function to create a PDF parish extractor."""
    return PDFParishExtractor(timeout)


# Test function
def test_pdf_extractor():
    """Test the PDF extractor with a known PDF URL."""
    extractor = PDFParishExtractor()
    
    # Test with San Francisco Archdiocese PDF (observed in pipeline output)
    test_url = "https://www.sfarchdiocese.org/wp-content/uploads/2022/02/2020-2021-PCL-DIRECTORY-almost-final.pub_.pdf"
    
    parishes = extractor.extract_parishes(test_url)
    
    print(f"\n📊 PDF Extraction Test Results:")
    print(f"Total parishes found: {len(parishes)}")
    
    for i, parish in enumerate(parishes[:10], 1):  # Show first 10
        print(f"{i:2d}. {parish.name}")
        if parish.city:
            print(f"    City: {parish.city}")
        if parish.phone:
            print(f"    Phone: {parish.phone}")


if __name__ == "__main__":
    test_pdf_extractor()