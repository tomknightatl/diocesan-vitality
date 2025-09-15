#!/usr/bin/env python3
"""
Test script for AI-enhanced schedule extraction.
"""

import json
from core.schedule_ai_extractor import ScheduleAIExtractor
from core.logger import get_logger

logger = get_logger(__name__)


def test_adoration_extraction():
    """Test adoration schedule extraction."""
    print("Testing Adoration Schedule Extraction")
    print("=" * 40)
    
    extractor = ScheduleAIExtractor()
    
    # Test case 1: Clear weekly adoration schedule
    test_content_1 = """
    <h2>Eucharistic Adoration</h2>
    <p>Join us for weekly Eucharistic Adoration every Wednesday evening.</p>
    <ul>
        <li>Wednesdays: 6:00 PM - 7:00 PM</li>
        <li>First Friday Holy Hour: 7:00 PM - 8:00 PM</li>
    </ul>
    <p>Come and spend time with our Lord in quiet prayer and reflection.</p>
    """
    
    result = extractor.extract_schedule_from_content(
        test_content_1, "https://test1.com", "adoration"
    )
    
    print("Test 1 - Clear Weekly Schedule:")
    print(json.dumps(result, indent=2))
    print(f"Has Weekly Schedule: {result.get('has_weekly_schedule')}")
    print()

    # Test case 2: Perpetual adoration
    test_content_2 = """
    <div class="adoration-info">
        <h3>Perpetual Adoration Chapel</h3>
        <p>Our Perpetual Adoration Chapel is open 24 hours a day, 7 days a week.</p>
        <p>Sign up for your hour at the parish office. We especially need adorers for:</p>
        <ul>
            <li>Tuesday nights 2:00 AM - 3:00 AM</li>
            <li>Thursday afternoons 2:00 PM - 3:00 PM</li>
        </ul>
    </div>
    """
    
    result = extractor.extract_schedule_from_content(
        test_content_2, "https://test2.com", "adoration"
    )
    
    print("Test 2 - Perpetual Adoration:")
    print(json.dumps(result, indent=2))
    print(f"Is Perpetual: {result.get('is_perpetual')}")
    print()


def test_reconciliation_extraction():
    """Test reconciliation schedule extraction."""
    print("Testing Reconciliation Schedule Extraction")
    print("=" * 40)
    
    extractor = ScheduleAIExtractor()
    
    # Test case 1: Standard confession schedule
    test_content_1 = """
    <h2>Sacrament of Reconciliation</h2>
    <p>Confession times:</p>
    <div class="schedule">
        <p><strong>Saturdays:</strong> 3:30 PM - 4:30 PM</p>
        <p><strong>Sundays:</strong> 30 minutes before each Mass</p>
        <p>Or by appointment - please call the parish office.</p>
    </div>
    """
    
    result = extractor.extract_schedule_from_content(
        test_content_1, "https://test3.com", "reconciliation"
    )
    
    print("Test 3 - Standard Confession Schedule:")
    print(json.dumps(result, indent=2))
    print(f"Has Weekly Schedule: {result.get('has_weekly_schedule')}")
    print(f"By Appointment: {result.get('by_appointment')}")
    print()

    # Test case 2: Appointment only
    test_content_2 = """
    <div class="sacraments">
        <h4>Reconciliation</h4>
        <p>The Sacrament of Reconciliation is available by appointment only.</p>
        <p>Please contact Fr. Smith at the parish office to schedule.</p>
    </div>
    """
    
    result = extractor.extract_schedule_from_content(
        test_content_2, "https://test4.com", "reconciliation"
    )
    
    print("Test 4 - Appointment Only:")
    print(json.dumps(result, indent=2))
    print(f"Has Weekly Schedule: {result.get('has_weekly_schedule')}")
    print(f"By Appointment: {result.get('by_appointment')}")
    print()


def test_no_schedule_content():
    """Test content with no schedule information."""
    print("Testing Content With No Schedule")
    print("=" * 40)
    
    extractor = ScheduleAIExtractor()
    
    test_content = """
    <h1>Welcome to St. Mary's Parish</h1>
    <p>We are a vibrant Catholic community located in downtown Springfield.</p>
    <p>Our parish was founded in 1892 and serves over 1,200 families.</p>
    <h2>Ministries</h2>
    <ul>
        <li>Youth Ministry</li>
        <li>Food Pantry</li>
        <li>Adult Education</li>
    </ul>
    """
    
    result = extractor.extract_schedule_from_content(
        test_content, "https://test5.com", "adoration"
    )
    
    print("Test 5 - No Schedule Content:")
    print(json.dumps(result, indent=2))
    print(f"Schedule Found: {result.get('schedule_found')}")
    print()


if __name__ == "__main__":
    test_adoration_extraction()
    print("\n" + "="*60 + "\n")
    test_reconciliation_extraction()
    print("\n" + "="*60 + "\n")
    test_no_schedule_content()