#!/usr/bin/env python3
"""
Parish Website Finder

This script specifically focuses on finding websites for validated parishes
by using multiple search strategies and AI-powered validation.
"""

import re
import time
import argparse
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

import config
from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

class ParishWebsiteFinder:
    """Advanced parish website discovery system."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Parish Website Finder)'
        })

        # Initialize AI if available
        if config.GENAI_API_KEY:
            try:
                genai.configure(api_key=config.GENAI_API_KEY)
                self.use_ai = True
                logger.info("🤖 AI-powered website validation enabled")
            except Exception as e:
                logger.warning(f"AI initialization failed: {e}")
                self.use_ai = False
        else:
            self.use_ai = False

    def extract_location_info(self, parish_name: str, address: str = None) -> Dict:
        """Extract city and state from parish name and address."""
        location_info = {'city': None, 'state': None}

        # Common state abbreviations and full names
        states = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
        }

        # Try to extract from parish name (e.g., "St. Mary, Boston, MA")
        name_parts = [part.strip() for part in parish_name.split(',')]
        if len(name_parts) >= 2:
            location_info['city'] = name_parts[-2]
            if len(name_parts) >= 3:
                state_candidate = name_parts[-1].upper()
                if state_candidate in states:
                    location_info['state'] = state_candidate

        # Try to extract from address if available
        if address and not location_info['state']:
            for abbrev, full_name in states.items():
                if abbrev in address.upper() or full_name.lower() in address.lower():
                    location_info['state'] = abbrev
                    break

        return location_info

    def generate_parish_search_terms(self, parish_name: str, location_info: Dict) -> List[str]:
        """Generate multiple search terms for finding parish websites."""
        search_terms = []

        # Clean parish name
        clean_name = parish_name.replace('Catholic Church', '').replace('Parish', '').strip()

        # Base search terms
        base_terms = [
            f'"{parish_name}" catholic church',
            f'"{clean_name}" catholic parish',
            f'"{parish_name}" website',
        ]

        # Add location-specific terms
        if location_info.get('city'):
            city = location_info['city']
            base_terms.extend([
                f'"{clean_name}" {city} catholic',
                f'"{parish_name}" {city}',
            ])

        if location_info.get('state'):
            state = location_info['state']
            base_terms.extend([
                f'"{clean_name}" {state} catholic church',
                f'"{parish_name}" {state}',
            ])

        # Add diocese-specific terms
        if location_info.get('city') and location_info.get('state'):
            base_terms.append(f'{clean_name} diocese {location_info["city"]} {location_info["state"]}')

        return base_terms[:5]  # Limit to top 5 search terms

    def validate_parish_website_with_ai(self, url: str, parish_name: str) -> Dict:
        """Use AI to validate if a URL is the correct parish website."""
        if not self.use_ai:
            return {'is_correct': True, 'confidence': 0.7, 'reason': 'basic validation'}

        try:
            # Get website content
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()

            page_text = soup.get_text()[:2000]  # First 2000 characters

            prompt = f"""
            Analyze this website to determine if it's the official website for "{parish_name}":

            URL: {url}
            Website content (first 2000 chars): {page_text}

            Consider:
            1. Does the website mention the parish name or a similar variant?
            2. Does it have Catholic church content (Mass times, sacraments, etc.)?
            3. Is it clearly a parish website vs. a business or other organization?
            4. Does the domain name suggest it's a parish website?

            Respond with:
            Score: [0-100] (confidence this is the correct parish website)
            Reason: [brief explanation]
            """

            model = genai.GenerativeModel("gemini-1.5-flash")
            ai_response = model.generate_content(prompt)
            response_text = ai_response.text

            score_match = re.search(r"Score: (\d+)", response_text)
            score = int(score_match.group(1)) if score_match else 50

            reason_match = re.search(r"Reason: (.+)", response_text)
            reason = reason_match.group(1).strip() if reason_match else "AI validation"

            return {
                'is_correct': score >= 70,
                'confidence': score / 100,
                'reason': reason
            }

        except Exception as e:
            logger.warning(f"AI website validation failed for {url}: {e}")
            return {'is_correct': False, 'confidence': 0.3, 'reason': f'validation error: {e}'}

    def search_google_for_parish(self, search_terms: List[str]) -> List[str]:
        """Mock Google search - in production would use Google Custom Search API."""
        # For demonstration, return mock results based on search terms
        potential_urls = []

        for term in search_terms:
            # Generate plausible parish website URLs based on search terms
            if 'st.' in term.lower() or 'saint' in term.lower():
                # Extract saint name
                saint_match = re.search(r'(st\.?\s+\w+|saint\s+\w+)', term.lower())
                if saint_match:
                    saint_name = saint_match.group(1).replace('st.', 'st').replace(' ', '')
                    potential_urls.append(f"https://www.{saint_name}parish.org")
                    potential_urls.append(f"https://{saint_name}catholic.com")

            # Generic patterns
            parish_words = term.lower().replace('"', '').split()
            if 'catholic' in parish_words:
                parish_words.remove('catholic')
            if 'church' in parish_words:
                parish_words.remove('church')
            if 'parish' in parish_words:
                parish_words.remove('parish')

            if parish_words:
                domain_name = ''.join(parish_words[:2])  # First two meaningful words
                potential_urls.extend([
                    f"https://www.{domain_name}parish.org",
                    f"https://{domain_name}catholic.org",
                    f"https://www.{domain_name}church.com",
                ])

        # Return unique URLs
        return list(set(potential_urls))[:5]

    def check_url_exists_and_is_parish(self, url: str) -> Optional[str]:
        """Check if URL exists and appears to be a parish website."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Basic content check
                content = response.text.lower()
                parish_indicators = [
                    'mass times', 'mass schedule', 'catholic', 'parish',
                    'sacrament', 'confession', 'baptism', 'eucharist',
                    'sunday mass', 'holy mass', 'liturgy'
                ]

                if any(indicator in content for indicator in parish_indicators):
                    return url
        except:
            pass

        return None

    def find_website_for_parish(self, parish_info: Dict) -> Optional[str]:
        """Main method to find a website for a specific parish."""
        parish_name = parish_info['Name']
        address = parish_info.get('Street Address', '')

        logger.info(f"  🔍 Searching for website: {parish_name}")

        # Extract location information
        location_info = self.extract_location_info(parish_name, address)

        # Generate search terms
        search_terms = self.generate_parish_search_terms(parish_name, location_info)
        logger.info(f"    📝 Using search terms: {search_terms[:2]}")

        # Search for potential websites
        potential_urls = self.search_google_for_parish(search_terms)

        # Test each potential URL
        for url in potential_urls:
            existing_url = self.check_url_exists_and_is_parish(url)
            if existing_url:
                # Validate with AI if available
                validation = self.validate_parish_website_with_ai(existing_url, parish_name)
                if validation['is_correct']:
                    logger.info(f"    ✅ Found website: {existing_url} (confidence: {validation['confidence']:.2f})")
                    return existing_url
                else:
                    logger.info(f"    ❌ Rejected: {existing_url} - {validation['reason']}")

        logger.info(f"    ⚠️ No website found for {parish_name}")
        return None

    def find_websites_for_parishes(self, limit: int = 10, diocese_id: int = None) -> Dict:
        """Find websites for parishes that don't have them."""
        try:
            # Get legitimate parishes without websites
            query = self.supabase.table('Parishes').select('id, Name, "Street Address", diocese_id')
            query = query.eq('Status', 'Parish').is_('Web', 'null')

            if diocese_id:
                query = query.eq('diocese_id', diocese_id)

            query = query.limit(limit)
            response = query.execute()

            parishes = response.data
            logger.info(f"🔍 Searching websites for {len(parishes)} parishes")

            results = {
                'processed': 0,
                'websites_found': 0,
                'websites_added': 0,
                'failed_searches': 0
            }

            for parish in parishes:
                results['processed'] += 1

                website = self.find_website_for_parish(parish)

                if website:
                    results['websites_found'] += 1

                    # Update parish with website
                    update_result = self.supabase.table('Parishes').update({
                        'Web': website
                    }).eq('id', parish['id']).execute()

                    if update_result:
                        results['websites_added'] += 1
                        logger.info(f"  ✅ Updated: {parish['Name']} → {website}")
                else:
                    results['failed_searches'] += 1

                # Rate limiting
                time.sleep(1)

            return results

        except Exception as e:
            logger.error(f"Error in find_websites_for_parishes: {e}")
            return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description="Find websites for parishes")
    parser.add_argument("--limit", type=int, default=5, help="Number of parishes to process")
    parser.add_argument("--diocese_id", type=int, help="Process specific diocese only")

    args = parser.parse_args()

    if not config.validate_config():
        logger.error("Configuration validation failed")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    finder = ParishWebsiteFinder(supabase)

    logger.info(f"🚀 Starting parish website search (limit: {args.limit})")
    if args.diocese_id:
        logger.info(f"   Targeting diocese ID: {args.diocese_id}")

    results = finder.find_websites_for_parishes(args.limit, args.diocese_id)

    if 'error' in results:
        logger.error(f"❌ Website search failed: {results['error']}")
        return

    logger.info("📊 Website Search Results:")
    logger.info(f"   Processed: {results['processed']} parishes")
    logger.info(f"   Websites found: {results['websites_found']}")
    logger.info(f"   Websites added: {results['websites_added']}")
    logger.info(f"   Failed searches: {results['failed_searches']}")

    if results['processed'] > 0:
        success_rate = results['websites_found'] / results['processed'] * 100
        logger.info(f"   📈 Success rate: {success_rate:.1f}%")


if __name__ == '__main__':
    main()