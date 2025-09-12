#!/usr/bin/env python3
"""
Simple accuracy check for Diocese ID 2002 parish extraction.
Compares extracted parishes against expected parishes list using direct database queries.
"""

import sys
import os
from datetime import datetime
from difflib import SequenceMatcher

# Add the project root to Python path
sys.path.append('/home/tomk/USCCB')

from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

def get_expected_parishes():
    """Hardcoded list of expected parishes for Diocese 2002"""
    return [
        ('Saint Thomas Syro-Malabar Forane Catholic Church', 'Orange'),
        ('Saint John Maron Catholic Church', 'Orange'),
        ('Saint John Henry Newman Catholic Church', 'Irvine'),
        ('Saint George Chaldean Catholic Church', 'Santa Ana'),
        ('Holy Cross Melkite Catholic Church', 'Placentia'),
        ('Annunciation Byzantine Catholic Church', 'Anaheim'),
        ('Vietnamese Catholic Center', 'Santa Ana'),
        ('Saint Vincent de Paul Catholic Church', 'Huntington Beach'),
        ('Saint Timothy Catholic Church', 'Laguna Niguel'),
        ('Saint Thomas Korean Catholic Center', 'Anaheim'),
        ('Saints Simon and Jude Catholic Church', 'Huntington Beach'),
        ('Saint Polycarp Catholic Church', 'Stanton'),
        ('Saint Pius V Catholic Church', 'Buena Park'),
        ('Saint Philip Benizi Catholic Church', 'Fullerton'),
        ('Saint Norbert Catholic Church', 'Orange'),
        ('Saint Nicholas Catholic Churh', 'Laguna Woods'),
        ('Saint Mary\'s by The Sea Catholic Church', 'Huntington Beach'),
        ('Saint Mary Catholic Church', 'Fullerton'),
        ('Saint Martin de Porres Catholic Church', 'Yorba Linda'),
        ('Saint Kilian Catholic Church', 'Mission Viejo'),
        ('Saint Justin Martyr Catholic Church', 'Anaheim'),
        ('Saint Juliana Falconieri Catholic Church', 'Fullerton'),
        ('Saint Joseph Catholic Church, Santa Ana', 'Santa Ana'),
        ('Saint Joseph Catholic Church, Placentia', 'Placentia'),
        ('Saint John Vianney Chapel', 'Newport Beach'),
        ('Saint John The Baptist Catholic Chuch', 'Costa Mesa'),
        ('Saint John Neumann Catholic Church', 'Irvine'),
        ('Saint Joachim Catholic Church', 'Costa Mesa'),
        ('Saint Irenaeus Catholic Church', 'Cypress'),
        ('Saint Hedwig Catholic Church', 'Los Alamitos'),
        ('Saint Elizabeth Ann Seton Catholic Church', 'Irvine'),
        ('Saint Edward The Confessor Catholic Church', 'Dana Point'),
        ('Saint Columban Catholic Church', 'Garden Grove'),
        ('Saint Cecilia Catholic Church', 'Tustin'),
        ('Saint Catherine of Siena Catholic Church', 'Laguna Beach'),
        ('Saint Boniface Catholic Church', 'Anaheim'),
        ('Saint Bonaventure Catholic Church', 'Huntington Beach'),
        ('Saint Barbara Catholic Church', 'Santa Ana'),
        ('Saint Anthony Claret Catholic Church', 'Anaheim'),
        ('Saint Anne Catholic Church, Seal Beach', 'Seal Beach'),
        ('Saint Anne Catholic Church, Santa Ana', 'Santa Ana'),
        ('Saint Angela Merici Catholic Church', 'Brea'),
        ('Santiago de Compostela Catholic Church', 'Lake Forest'),
        ('Santa Clara de Asis Catholic Church', 'Yorba Linda'),
        ('San Francisco Solano Catholic Church', 'Rancho Santa Margarita'),
        ('San Antonio de Padua Catholic Church', 'Anaheim Hills'),
        ('Our Lady Queen of Angels Catholic Church', 'Newport Beach'),
        ('Our Lady of The Pillar Catholic Church', 'Santa Ana'),
        ('Our Lady of Mount Carmel Catholic Church', 'Newport Beach'),
        ('Our Lady of La Vang Catholic Church', 'Santa Ana'),
        ('Our Lady of Guadalupe, La Habra', 'La Habra'),
        ('Our Lady of Guadalupe, Delhi', 'Santa Ana'),
        ('Our Lady of Guadalupe, Santa Ana', 'Santa Ana'),
        ('Our Lady of Fatima Catholic Church', 'San Clemente'),
        ('Our Lady of Peace Korean Catholic Center', 'Irvine'),
        ('Mission Basilica', 'San Juan Capistrano'),
        ('La Purisima Catholic Church', 'Orange'),
        ('Korean Martyrs Catholic Center', 'Westminster'),
        ('Saint John Paul II Catholic Polish Center', 'Yorba Linda'),
        ('Immaculate Heart of Mary Catholic Church', 'Santa Ana'),
        ('Holy Spirit Catholic Church', 'Fountain Valley'),
        ('Holy Family Catholic Church, Seal Beach', 'Seal Beach'),
        ('Holy Family Catholic Church, Orange', 'Orange'),
        ('Corpus Christi Catholic Church', 'Aliso Viejo'),
        ('Christ Our Savior Catholic Parish', 'Santa Ana'),
        ('Christ Cathedral Parish', 'Garden Grove'),
        ('Blessed Sacrament Catholic Church', 'Westminster'),
        ('Holy Trinity Catholic Church', 'Ladera Ranch'),
        ('Saint Thomas More Catholic Church', 'Irvine')
    ]

def get_extracted_parishes():
    """Get parishes extracted by the pipeline for Diocese ID 2002"""
    logger.info("🔍 Getting extracted parishes from database...")
    
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('Parishes').select('Name, City, "Street Address"').eq('diocese_id', 2002).execute()
        
        extracted_parishes = []
        for parish in response.data:
            name = parish['Name'].strip() if parish['Name'] else ''
            city = parish['City'].strip() if parish['City'] else ''
            address = parish['Street Address'] if parish['Street Address'] else ''
            extracted_parishes.append((name, city, address))
        
        logger.info(f"🔍 Found {len(extracted_parishes)} extracted parishes for Diocese ID 2002")
        return extracted_parishes
        
    except Exception as e:
        logger.error(f"❌ Failed to get extracted parishes: {str(e)}")
        return []

def normalize_name(name):
    """Normalize parish name for comparison"""
    if not name:
        return ""
    
    # Basic normalization
    normalized = name.lower().strip()
    
    # Common variations
    replacements = [
        ("saint", "st"),
        ("st.", "st"),
        (" catholic church", ""),
        (" catholic parish", ""),
        (" church", ""),
        (" parish", ""),
        (" the ", " "),
        ("  ", " "),
        ("'", "")
    ]
    
    for old, new in replacements:
        normalized = normalized.replace(old, new)
    
    return normalized.strip()

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def find_best_match(target_name, target_city, extracted_list):
    """Find the best matching parish in the extracted list"""
    target_norm = normalize_name(target_name)
    target_city_norm = target_city.lower().strip()
    
    best_match = None
    best_score = 0
    
    for extracted_name, extracted_city, extracted_address in extracted_list:
        extracted_norm = normalize_name(extracted_name)
        extracted_city_norm = extracted_city.lower().strip()
        
        # Calculate name similarity
        name_sim = similarity(target_norm, extracted_norm)
        
        # Calculate city similarity
        city_sim = similarity(target_city_norm, extracted_city_norm)
        
        # Combined score (weighted towards name matching)
        combined_score = (name_sim * 0.7) + (city_sim * 0.3)
        
        if combined_score > best_score and combined_score > 0.6:  # Minimum threshold
            best_score = combined_score
            best_match = (extracted_name, extracted_city, extracted_address, combined_score)
    
    return best_match

def calculate_accuracy():
    """Calculate accuracy metrics"""
    logger.info("📊 Calculating accuracy metrics...")
    
    expected_parishes = get_expected_parishes()
    extracted_parishes = get_extracted_parishes()
    
    if not extracted_parishes:
        logger.warning("⚠️ No extracted parishes found. The extraction may not have completed yet.")
        return None
    
    total_expected = len(expected_parishes)
    total_extracted = len(extracted_parishes)
    
    matches = []
    missing = []
    used_extracted = set()
    
    # Find matches
    for expected_name, expected_city in expected_parishes:
        match = find_best_match(expected_name, expected_city, extracted_parishes)
        if match:
            matches.append({
                'expected': (expected_name, expected_city),
                'found': (match[0], match[1], match[2]),
                'score': match[3]
            })
            used_extracted.add((match[0], match[1], match[2]))
        else:
            missing.append((expected_name, expected_city))
    
    # Find extra parishes (in extracted but not matched)
    extra = []
    for parish in extracted_parishes:
        if parish not in used_extracted:
            extra.append(parish)
    
    # Calculate metrics
    true_positives = len(matches)
    false_negatives = len(missing)
    false_positives = len(extra)
    
    precision = true_positives / total_extracted if total_extracted > 0 else 0
    recall = true_positives / total_expected if total_expected > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = true_positives / total_expected if total_expected > 0 else 0
    
    return {
        'total_expected': total_expected,
        'total_extracted': total_extracted,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'accuracy': accuracy,
        'matches': matches,
        'missing': missing,
        'extra': extra
    }

def generate_report(metrics):
    """Generate accuracy report"""
    if not metrics:
        return "❌ No accuracy metrics available - extraction may not have completed yet."
    
    report = []
    report.append("=" * 80)
    report.append("DIOCESE 2002 (DIOCESE OF ORANGE) PARISH EXTRACTION ACCURACY REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    report.append("📊 SUMMARY METRICS:")
    report.append("-" * 40)
    report.append(f"Expected Parishes: {metrics['total_expected']}")
    report.append(f"Extracted Parishes: {metrics['total_extracted']}")
    report.append(f"Correctly Found (True Positives): {metrics['true_positives']}")
    report.append(f"Missing (False Negatives): {metrics['false_negatives']}")
    report.append(f"Extra (False Positives): {metrics['false_positives']}")
    report.append("")
    report.append(f"🎯 Accuracy: {metrics['accuracy']:.1%}")
    report.append(f"🎯 Precision: {metrics['precision']:.1%}")
    report.append(f"🎯 Recall: {metrics['recall']:.1%}")
    report.append(f"🎯 F1-Score: {metrics['f1_score']:.1%}")
    report.append("")
    
    if metrics['matches']:
        report.append("✅ CORRECTLY FOUND PARISHES:")
        report.append("-" * 40)
        for match in sorted(metrics['matches'], key=lambda x: x['score'], reverse=True):
            expected_name, expected_city = match['expected']
            found_name, found_city, found_address = match['found']
            score = match['score']
            report.append(f"• {expected_name} ({expected_city})")
            if score < 0.95:  # Show details for imperfect matches
                report.append(f"  ↳ Found as: {found_name} ({found_city}) [Match: {score:.1%}]")
        report.append("")
    
    if metrics['missing']:
        report.append("❌ MISSING PARISHES (False Negatives):")
        report.append("-" * 40)
        for name, city in sorted(metrics['missing']):
            report.append(f"• {name} - {city}")
        report.append("")
    
    if metrics['extra']:
        report.append("❓ EXTRA PARISHES (False Positives):")
        report.append("-" * 40)
        for name, city, address in sorted(metrics['extra']):
            report.append(f"• {name} - {city}")
            if address:
                report.append(f"  Address: {address}")
        report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """Main function"""
    logger.info("🧪 Starting Diocese 2002 accuracy check...")
    
    # Calculate accuracy
    metrics = calculate_accuracy()
    
    # Generate report
    report = generate_report(metrics)
    
    # Display results
    print(report)
    
    if metrics:
        # Save report
        report_file = f"/home/tomk/USCCB/diocese_2002_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Report saved to: {report_file}")
        logger.info(f"🎯 Final Accuracy: {metrics['accuracy']:.1%}")

if __name__ == "__main__":
    main()