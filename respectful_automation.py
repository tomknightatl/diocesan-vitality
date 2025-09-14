#!/usr/bin/env python3
"""
Respectful Automation Module

Implements respectful web scraping practices including:
- Bot detection and tracking
- Rate limiting
- Robots.txt compliance
- User-Agent identification
- Blocking detection and reporting
"""

import time
import random
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional, Tuple
import json

from core.logger import get_logger

logger = get_logger(__name__)

class RespectfulAutomation:
    """Implements respectful automation practices for web scraping."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Parish Directory Research;)'
        })

        # Rate limiting: minimum time between requests per domain
        self.domain_last_request = {}
        self.min_delay_seconds = 2.0  # 2 second minimum between requests
        self.random_delay_max = 3.0   # Up to 3 additional random seconds

        # Robots.txt cache
        self.robots_cache = {}

    def can_fetch_url(self, url: str, user_agent: str = '*') -> Dict:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = urljoin(base_url, '/robots.txt')

            # Check cache first
            if base_url in self.robots_cache:
                rp = self.robots_cache[base_url]
            else:
                # Fetch and parse robots.txt
                rp = RobotFileParser()
                rp.set_url(robots_url)

                try:
                    rp.read()
                    self.robots_cache[base_url] = rp
                    logger.debug(f"Loaded robots.txt from {robots_url}")
                except Exception as e:
                    logger.debug(f"Could not load robots.txt from {robots_url}: {e}")
                    # Create permissive default
                    rp = None
                    self.robots_cache[base_url] = None

            # Check if fetch is allowed
            if rp:
                can_fetch = rp.can_fetch(user_agent, url)
                crawl_delay = rp.crawl_delay(user_agent)
                return {
                    'allowed': can_fetch,
                    'crawl_delay': crawl_delay,
                    'robots_url': robots_url,
                    'has_robots_txt': True
                }
            else:
                return {
                    'allowed': True,  # Assume allowed if no robots.txt
                    'crawl_delay': None,
                    'robots_url': robots_url,
                    'has_robots_txt': False
                }

        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return {
                'allowed': True,  # Default to allowed on error
                'crawl_delay': None,
                'robots_url': None,
                'has_robots_txt': False,
                'error': str(e)
            }

    def respectful_delay(self, domain: str, crawl_delay: Optional[float] = None):
        """Implement respectful delays between requests."""
        current_time = time.time()

        # Use crawl delay from robots.txt if specified
        if crawl_delay:
            delay = max(crawl_delay, self.min_delay_seconds)
        else:
            delay = self.min_delay_seconds

        # Add random component to avoid predictable patterns
        total_delay = delay + random.uniform(0, self.random_delay_max)

        # Check last request time for this domain
        if domain in self.domain_last_request:
            time_since_last = current_time - self.domain_last_request[domain]
            if time_since_last < total_delay:
                sleep_time = total_delay - time_since_last
                logger.debug(f"Respectful delay: sleeping {sleep_time:.1f}s for {domain}")
                time.sleep(sleep_time)

        # Update last request time
        self.domain_last_request[domain] = time.time()

    def detect_blocking_mechanisms(self, response: requests.Response, url: str) -> Dict:
        """Detect various blocking mechanisms from HTTP response."""
        blocking_info = {
            'is_blocked': False,
            'blocking_type': None,
            'evidence': [],
            'status_code': response.status_code,
            'headers': dict(response.headers)
        }

        # Check status codes that indicate blocking
        if response.status_code == 403:
            blocking_info.update({
                'is_blocked': True,
                'blocking_type': '403_forbidden',
                'evidence': ['HTTP 403 Forbidden status']
            })
        elif response.status_code == 429:
            blocking_info.update({
                'is_blocked': True,
                'blocking_type': 'rate_limited',
                'evidence': ['HTTP 429 Too Many Requests']
            })
        elif response.status_code == 503:
            blocking_info.update({
                'is_blocked': True,
                'blocking_type': 'service_unavailable',
                'evidence': ['HTTP 503 Service Unavailable']
            })

        # Check headers for bot detection services
        suspicious_headers = {
            'cf-ray': 'cloudflare_protection',
            'server': 'cloudflare',
            'x-sucuri-id': 'sucuri_firewall',
            'x-served-by': 'cdn_blocking'
        }

        for header, service in suspicious_headers.items():
            if header in response.headers:
                blocking_info['evidence'].append(f'{service}: {response.headers[header]}')

        # Check response content for blocking indicators
        try:
            content = response.text.lower()
            blocking_patterns = [
                ('cloudflare', 'attention required'),
                ('cloudflare', 'checking your browser'),
                ('bot_detection', 'access denied'),
                ('captcha', 'prove you are human'),
                ('firewall', 'blocked by security policy'),
                ('ddos_protection', 'ddos protection by'),
            ]

            for pattern_type, pattern in blocking_patterns:
                if pattern in content:
                    if not blocking_info['is_blocked']:
                        blocking_info.update({
                            'is_blocked': True,
                            'blocking_type': pattern_type
                        })
                    blocking_info['evidence'].append(f'Content pattern: {pattern}')

        except Exception as e:
            logger.debug(f"Error analyzing content for blocking patterns: {e}")

        return blocking_info

    def respectful_get(self, url: str, timeout: int = 30) -> Tuple[Optional[requests.Response], Dict]:
        """Make a respectful HTTP GET request with blocking detection."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Check robots.txt compliance
        robots_check = self.can_fetch_url(url)
        if not robots_check['allowed']:
            return None, {
                'error': 'robots_txt_disallowed',
                'message': f'Access disallowed by robots.txt',
                'robots_info': robots_check
            }

        # Implement respectful delay
        self.respectful_delay(domain, robots_check.get('crawl_delay'))

        try:
            # Make the request
            response = self.session.get(url, timeout=timeout)

            # Detect blocking mechanisms
            blocking_info = self.detect_blocking_mechanisms(response, url)

            return response, {
                'success': True,
                'blocking_info': blocking_info,
                'robots_info': robots_check,
                'domain': domain
            }

        except requests.exceptions.RequestException as e:
            return None, {
                'error': 'request_failed',
                'message': str(e),
                'robots_info': robots_check,
                'domain': domain
            }


def create_blocking_report(blocking_info: Dict, url: str, diocese_name: str) -> Dict:
    """Create a standardized blocking report for database storage."""
    report = {
        'diocese_name': diocese_name,
        'url': url,
        'timestamp': time.time(),
        'is_blocked': blocking_info.get('is_blocked', False),
        'blocking_type': blocking_info.get('blocking_type'),
        'status_code': blocking_info.get('status_code'),
        'evidence': blocking_info.get('evidence', []),
        'user_agent': 'USCCB Parish Directory Research'
    }

    # Add human-readable status
    if report['is_blocked']:
        if report['blocking_type'] == '403_forbidden':
            report['status_description'] = 'Diocese website actively blocking automated access (403 Forbidden)'
        elif report['blocking_type'] == 'rate_limited':
            report['status_description'] = 'Diocese website rate limiting requests (429 Too Many Requests)'
        elif report['blocking_type'] == 'cloudflare_protection':
            report['status_description'] = 'Diocese website using Cloudflare bot protection'
        elif report['blocking_type'] == 'captcha':
            report['status_description'] = 'Diocese website requiring CAPTCHA verification'
        else:
            report['status_description'] = f'Diocese website blocking access ({report["blocking_type"]})'
    else:
        report['status_description'] = 'Diocese website accessible to automated requests'

    return report


def test_respectful_automation():
    """Test the respectful automation system."""
    automation = RespectfulAutomation()

    test_urls = [
        'https://usccb.org/',  # Should be accessible
        'https://dioceseoflaredo.org/',  # Known to block
        'https://nonexistent-diocese-test.org/'  # Should fail
    ]

    print("🔍 Testing Respectful Automation:")
    print("=" * 50)

    for url in test_urls:
        print(f"\nTesting: {url}")

        response, info = automation.respectful_get(url, timeout=10)

        if response:
            print(f"✅ Success: {response.status_code}")
            if info['blocking_info']['is_blocked']:
                print(f"⚠️ Blocking detected: {info['blocking_info']['blocking_type']}")
                print(f"   Evidence: {info['blocking_info']['evidence']}")
            else:
                print("✅ No blocking detected")
        else:
            print(f"❌ Failed: {info['error']}")
            print(f"   Message: {info['message']}")


if __name__ == '__main__':
    test_respectful_automation()