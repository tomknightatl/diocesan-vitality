#!/usr/bin/env python3
"""
Parish Extraction Optimizer

This module implements performance optimizations for parish extraction:
1. Fast-Fail Interactive Map Extractor with DOM pre-analysis
2. Intelligent Extractor Pre-Selection based on page content analysis
3. Extractor-Level Circuit Breaker system
4. Progressive Timeout Strategy for different extractor types
"""

import re
import time
from typing import Dict, List, Tuple, Optional, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.circuit_breaker import circuit_manager, CircuitBreakerConfig, CircuitState
from core.logger import get_logger

logger = get_logger(__name__)


class ExtractorOptimizer:
    """
    Centralized optimization system for parish extractors
    """

    # Progressive timeout configuration based on extractor complexity
    EXTRACTOR_TIMEOUTS = {
        'NavigationExtractor': 5,               # Fast - just clicks links
        'PDFDirectoryExtractor': 3,             # Fast - checks for PDF links
        'IframeExtractor': 8,                   # Medium - checks for iframes
        'ParishFinderExtractor': 12,            # Medium - JavaScript interactions
        'EnhancedDiocesesCardExtractor': 15,    # Medium-Slow - detail page navigation
        'TableExtractor': 8,                    # Medium - HTML parsing
        'ImprovedInteractiveMapExtractor': 15,  # Slow - JavaScript/map loading
        'ImprovedGenericExtractor': 20,         # Slower - comprehensive parsing
        'EnhancedAIFallbackExtractor': 30       # Slowest - AI analysis
    }

    # Map indicator keywords for fast-fail detection
    MAP_KEYWORDS = {
        'javascript_libs': ['leaflet', 'mapbox', 'google.maps', 'arcgis', 'openlayers', 'esri'],
        'css_classes': ['leaflet-', 'mapbox-', 'gm-', 'esri-'],
        'map_elements': ['#map', '.map', '.parish-map', '.church-map', '[id*="map"]'],
        'container_patterns': ['map-container', 'map-wrapper', 'parish-locator']
    }

    def __init__(self):
        self.extractor_circuits = {}
        self._initialize_circuits()

    def _initialize_circuits(self):
        """Initialize per-extractor circuit breakers"""
        for extractor_name in self.EXTRACTOR_TIMEOUTS.keys():
            circuit_config = CircuitBreakerConfig(
                failure_threshold=3,    # Fast-fail after 3 failures
                recovery_timeout=30,    # 30 second recovery window
                request_timeout=self.EXTRACTOR_TIMEOUTS[extractor_name]
            )

            circuit_id = f'extractor_{extractor_name.lower()}'
            self.extractor_circuits[extractor_name] = circuit_manager.get_circuit_breaker(
                circuit_id, config=circuit_config
            )

            logger.debug(f"🔌 Initialized circuit breaker for {extractor_name} "
                        f"(timeout: {circuit_config.request_timeout}s)")

    def analyze_page_content(self, driver, html_content: str) -> Dict[str, any]:
        """
        Analyze page content to determine optimal extractors and detect features

        Returns:
            Dict with analysis results including:
            - has_map_features: bool
            - suitable_extractors: List[str]
            - skip_extractors: List[str]
            - estimated_complexity: str
        """
        analysis = {
            'has_map_features': False,
            'suitable_extractors': [],
            'skip_extractors': [],
            'estimated_complexity': 'medium',
            'content_indicators': {
                'has_iframe': False,
                'has_tables': False,
                'has_parish_finder': False,
                'has_navigation_menus': False,
                'has_card_layout': False,
                'has_pdf_links': False
            }
        }

        lower_content = html_content.lower()

        # Fast-fail map detection
        analysis['has_map_features'] = self._detect_map_features(lower_content)

        # Detect content patterns
        indicators = analysis['content_indicators']

        # Iframe detection
        indicators['has_iframe'] = bool(re.search(r'<iframe[^>]*>', lower_content))

        # Table detection
        indicators['has_tables'] = bool(re.search(r'<table[^>]*>.*parish.*</table>', lower_content, re.DOTALL))

        # Parish finder detection
        parish_finder_patterns = ['parish-finder', 'find.*parish', 'parish.*locator', 'parish.*search']
        indicators['has_parish_finder'] = any(pattern in lower_content for pattern in parish_finder_patterns)

        # Navigation menu detection
        nav_patterns = ['<nav', 'menu', 'dropdown', 'hover.*parish']
        indicators['has_navigation_menus'] = any(pattern in lower_content for pattern in nav_patterns)

        # Card layout detection
        card_patterns = ['card-', 'col-lg.*location', 'parish.*card', 'church.*card']
        indicators['has_card_layout'] = any(pattern in lower_content for pattern in card_patterns)

        # PDF link detection
        indicators['has_pdf_links'] = bool(re.search(r'href=["\'][^"\']*\.pdf["\']', lower_content))

        # Determine suitable extractors based on content analysis
        analysis['suitable_extractors'] = self._determine_suitable_extractors(indicators, analysis['has_map_features'])

        # Determine extractors to skip
        analysis['skip_extractors'] = self._determine_skip_extractors(indicators, analysis['has_map_features'])

        # Estimate page complexity
        analysis['estimated_complexity'] = self._estimate_complexity(indicators, lower_content)

        logger.info(f"  📊 Page Analysis Complete:")
        logger.info(f"    🗺️ Map features: {analysis['has_map_features']}")
        logger.info(f"    ✅ Suitable: {analysis['suitable_extractors'][:3]}{'...' if len(analysis['suitable_extractors']) > 3 else ''}")
        logger.info(f"    ❌ Skip: {analysis['skip_extractors']}")
        logger.info(f"    📈 Complexity: {analysis['estimated_complexity']}")

        return analysis

    def _detect_map_features(self, lower_content: str) -> bool:
        """Fast detection of map-related features in page content"""

        # Check for JavaScript map libraries
        for lib in self.MAP_KEYWORDS['javascript_libs']:
            if lib in lower_content:
                logger.debug(f"    🗺️ Found map library: {lib}")
                return True

        # Check for map-specific CSS classes
        for css_class in self.MAP_KEYWORDS['css_classes']:
            if css_class in lower_content:
                logger.debug(f"    🎨 Found map CSS: {css_class}")
                return True

        # Check for map container patterns
        for container in self.MAP_KEYWORDS['container_patterns']:
            if container in lower_content:
                logger.debug(f"    📦 Found map container: {container}")
                return True

        return False

    def _determine_suitable_extractors(self, indicators: Dict, has_map: bool) -> List[str]:
        """Determine which extractors are suitable for this page"""
        suitable = []

        # High confidence extractors based on specific indicators
        if indicators['has_iframe']:
            suitable.append('IframeExtractor')

        if indicators['has_parish_finder']:
            suitable.append('ParishFinderExtractor')

        if indicators['has_card_layout']:
            suitable.append('EnhancedDiocesesCardExtractor')

        if indicators['has_tables']:
            suitable.append('TableExtractor')

        if indicators['has_pdf_links']:
            suitable.append('PDFDirectoryExtractor')

        if indicators['has_navigation_menus']:
            suitable.append('NavigationExtractor')

        if has_map:
            suitable.append('ImprovedInteractiveMapExtractor')

        # Always include generic and AI fallback as last resorts
        suitable.extend(['ImprovedGenericExtractor', 'EnhancedAIFallbackExtractor'])

        return suitable

    def _determine_skip_extractors(self, indicators: Dict, has_map: bool) -> List[str]:
        """Determine which extractors should be skipped"""
        skip = []

        # Skip interactive map extractor if no map features detected
        if not has_map:
            skip.append('ImprovedInteractiveMapExtractor')

        # Skip PDF extractor if no PDF links
        if not indicators['has_pdf_links']:
            skip.append('PDFDirectoryExtractor')

        # Skip iframe extractor if no iframes
        if not indicators['has_iframe']:
            skip.append('IframeExtractor')

        return skip

    def _estimate_complexity(self, indicators: Dict, content: str) -> str:
        """Estimate page complexity to adjust timeouts"""
        complexity_score = 0

        # JavaScript complexity indicators
        if 'angular' in content or 'react' in content or 'vue' in content:
            complexity_score += 3

        if 'ajax' in content or 'xhr' in content or 'fetch(' in content:
            complexity_score += 2

        # Content complexity indicators
        if indicators['has_parish_finder']:
            complexity_score += 2

        if indicators['has_iframe']:
            complexity_score += 2

        if len(content) > 500000:  # Large pages
            complexity_score += 1

        if complexity_score >= 5:
            return 'high'
        elif complexity_score >= 2:
            return 'medium'
        else:
            return 'low'

    def should_skip_extractor(self, extractor_name: str, page_analysis: Dict) -> bool:
        """
        Determine if an extractor should be skipped based on analysis and circuit breaker
        """
        # Check circuit breaker status
        circuit = self.extractor_circuits.get(extractor_name)
        if circuit and circuit.state == CircuitState.OPEN:
            logger.info(f"  ⚡ Skipping {extractor_name} - circuit breaker OPEN")
            return True

        # Check page analysis recommendations
        if extractor_name in page_analysis.get('skip_extractors', []):
            logger.info(f"  🚫 Skipping {extractor_name} - not suitable for page content")
            return True

        return False

    def get_extractor_timeout(self, extractor_name: str, page_analysis: Dict) -> int:
        """Get optimized timeout for extractor based on page complexity"""
        base_timeout = self.EXTRACTOR_TIMEOUTS.get(extractor_name, 15)

        complexity = page_analysis.get('estimated_complexity', 'medium')

        # Adjust timeout based on complexity
        if complexity == 'high':
            return int(base_timeout * 1.5)
        elif complexity == 'low':
            return max(3, int(base_timeout * 0.7))
        else:
            return base_timeout

    def fast_fail_map_check(self, driver, timeout: int = 2) -> bool:
        """
        Quick check if page contains interactive map elements
        Returns True if map detected, False otherwise
        """
        try:
            # Check page source first (fastest)
            page_source = driver.page_source.lower()
            if not self._detect_map_features(page_source):
                logger.debug("  🚫 Fast-fail: No map indicators in page source")
                return False

            # Quick DOM check for map containers
            map_selectors = ["#map", ".map", ".parish-map", ".church-map"]

            for selector in map_selectors:
                try:
                    WebDriverWait(driver, 0.5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.debug(f"  ✅ Fast-fail: Found map element {selector}")
                    return True
                except TimeoutException:
                    continue

            logger.debug("  🚫 Fast-fail: No map elements found in DOM")
            return False

        except Exception as e:
            logger.debug(f"  ⚠️ Fast-fail map check error: {str(e)[:50]}")
            return False  # Fail closed - don't attempt map extraction

    def execute_with_circuit_breaker(self, extractor_name: str, extractor_func, *args, **kwargs):
        """
        Execute extractor with circuit breaker protection
        """
        circuit = self.extractor_circuits.get(extractor_name)
        if not circuit:
            # Fallback execution without circuit breaker
            logger.warning(f"  ⚠️ No circuit breaker for {extractor_name}, executing directly")
            return extractor_func(*args, **kwargs)

        try:
            # Execute with circuit breaker protection
            start_time = time.time()
            result = circuit.call(extractor_func, *args, **kwargs)
            execution_time = time.time() - start_time

            logger.debug(f"  ✅ {extractor_name} completed in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.warning(f"  ❌ {extractor_name} failed via circuit breaker: {str(e)[:100]}")
            raise

    def optimize_extractor_sequence(self, extractors_to_try: List[Tuple[str, any]], page_analysis: Dict) -> List[Tuple[str, any]]:
        """
        Optimize the sequence of extractors based on page analysis
        """
        suitable_extractors = page_analysis.get('suitable_extractors', [])
        skip_extractors = page_analysis.get('skip_extractors', [])

        # Filter out extractors that should be skipped
        filtered_extractors = []
        for name, extractor in extractors_to_try:
            if name not in skip_extractors and not self.should_skip_extractor(name, page_analysis):
                filtered_extractors.append((name, extractor))

        # Reorder based on suitability analysis
        prioritized_extractors = []
        remaining_extractors = []

        for name, extractor in filtered_extractors:
            if name in suitable_extractors:
                prioritized_extractors.append((name, extractor))
            else:
                remaining_extractors.append((name, extractor))

        # Sort prioritized extractors by their order in suitable_extractors
        prioritized_extractors.sort(key=lambda x: suitable_extractors.index(x[0]) if x[0] in suitable_extractors else 999)

        optimized_sequence = prioritized_extractors + remaining_extractors

        logger.info(f"  🎯 Optimized extractor sequence ({len(optimized_sequence)} of {len(extractors_to_try)} extractors):")
        for i, (name, _) in enumerate(optimized_sequence[:5], 1):
            timeout = self.get_extractor_timeout(name, page_analysis)
            logger.info(f"    {i}. {name} (timeout: {timeout}s)")

        if len(optimized_sequence) > 5:
            logger.info(f"    ... and {len(optimized_sequence) - 5} more")

        return optimized_sequence

    def get_optimization_stats(self) -> Dict:
        """Get statistics about optimization performance"""
        stats = {
            'circuit_breakers': {},
            'total_skipped_extractors': 0,
            'total_optimized_timeouts': 0
        }

        for extractor_name, circuit in self.extractor_circuits.items():
            stats['circuit_breakers'][extractor_name] = {
                'state': circuit.state.value,
                'failure_count': circuit.failure_count,
                'last_failure_time': getattr(circuit, 'last_failure_time', None)
            }

        return stats


# Global optimizer instance
_extractor_optimizer = None

def get_extractor_optimizer() -> ExtractorOptimizer:
    """Get the global extractor optimizer instance"""
    global _extractor_optimizer
    if _extractor_optimizer is None:
        _extractor_optimizer = ExtractorOptimizer()
        logger.info("🚀 Extractor Optimizer initialized with all performance improvements")
    return _extractor_optimizer