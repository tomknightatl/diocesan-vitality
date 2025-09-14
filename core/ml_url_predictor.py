#!/usr/bin/env python3
"""
ML-based URL Prediction System for Enhanced Discovery Precision

This module implements machine learning-based URL prediction to dramatically
reduce 404 errors by learning from successful extraction patterns and
predicting the most likely schedule URLs for each domain.
"""

import re
import json
import pickle
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from supabase import Client
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class URLPattern:
    """Represents a learned URL pattern with success metrics."""
    pattern: str
    domain_pattern: str
    success_count: int = 0
    attempt_count: int = 0
    last_success: Optional[str] = None
    confidence_score: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.attempt_count == 0:
            return 0.0
        return self.success_count / self.attempt_count


@dataclass
class DomainProfile:
    """Domain-specific URL patterns and characteristics."""
    domain: str
    successful_patterns: List[str] = field(default_factory=list)
    failed_patterns: List[str] = field(default_factory=list)
    path_structures: Set[str] = field(default_factory=set)
    cms_type: Optional[str] = None
    complexity_score: float = 1.0
    last_updated: Optional[str] = None


class MLURLPredictor:
    """
    Machine Learning-based URL predictor that learns from extraction history
    to predict the most likely schedule URLs for each domain.
    """

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.logger = logger

        # ML Models
        self.url_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=1000,
            analyzer='char_wb'
        )

        # Pattern databases
        self.url_patterns: Dict[str, URLPattern] = {}
        self.domain_profiles: Dict[str, DomainProfile] = {}
        self.success_patterns: Dict[str, Counter] = defaultdict(Counter)

        # Model state
        self.is_trained = False
        self.last_training = None
        self.model_version = "1.0.0"

        logger.info("🧠 ML URL Predictor initialized")

    def load_training_data(self) -> Tuple[List[str], List[int]]:
        """Load training data from successful and failed extractions."""
        try:
            # Get successful URLs from ParishData
            success_response = self.supabase.table('ParishData').select(
                'fact_source_url, parish_id'
            ).in_(
                'fact_type', ['ReconciliationSchedule', 'AdorationSchedule', 'MassSchedule']
            ).is_('fact_source_url', 'not.null').execute()

            # Get attempted URLs from DiscoveredUrls (including failures)
            discovered_response = self.supabase.table('DiscoveredUrls').select(
                'url, parish_id, status_code'
            ).execute()

            urls = []
            labels = []

            # Successful URLs (label = 1)
            successful_urls = set()
            for record in success_response.data:
                url = record['fact_source_url']
                if url and self._is_schedule_relevant(url):
                    urls.append(url)
                    labels.append(1)
                    successful_urls.add(url)

            # Failed URLs (label = 0) - but only schedule-relevant ones
            for record in discovered_response.data:
                url = record['url']
                status = record.get('status_code', 404)
                if (url and url not in successful_urls and
                    self._is_schedule_relevant(url) and
                    status >= 400):
                    urls.append(url)
                    labels.append(0)

            logger.info(f"🧠 Loaded {len(urls)} URLs for training ({sum(labels)} successful, {len(labels) - sum(labels)} failed)")
            return urls, labels

        except Exception as e:
            logger.error(f"🧠 Error loading training data: {e}")
            return [], []

    def extract_url_features(self, url: str) -> Dict[str, float]:
        """Extract features from URL for ML prediction."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        features = {
            # Path-based features
            'has_reconciliation': float('reconciliation' in path or 'confession' in path),
            'has_adoration': float('adoration' in path or 'eucharist' in path),
            'has_mass': float('mass' in path),
            'has_schedule': float('schedule' in path or 'times' in path),
            'has_hours': float('hours' in path),
            'has_sacrament': float('sacrament' in path),
            'has_worship': float('worship' in path or 'liturgy' in path),

            # Structure features
            'path_depth': float(len([p for p in path.split('/') if p])),
            'path_length': float(len(path)),
            'has_hyphen': float('-' in path),
            'has_underscore': float('_' in path),

            # Domain features
            'domain_length': float(len(parsed.netloc)),
            'has_subdomain': float(len(parsed.netloc.split('.')) > 2),

            # Pattern matching
            'ends_with_schedule': float(path.endswith('schedule') or path.endswith('schedules')),
            'contains_time_words': float(any(word in path for word in ['time', 'hour', 'when'])),

            # Negative indicators
            'has_negative_words': float(any(word in path for word in ['donate', 'giving', 'about', 'contact', 'news'])),
        }

        return features

    def train_model(self, retrain: bool = False) -> bool:
        """Train the ML model using historical data."""
        try:
            if self.is_trained and not retrain:
                logger.info("🧠 Model already trained, skipping training")
                return True

            logger.info("🧠 Training ML URL prediction model...")

            urls, labels = self.load_training_data()
            if len(urls) < 10:
                logger.warning("🧠 Insufficient training data, using pattern-based fallback")
                return False

            # Extract features
            X = []
            for url in urls:
                features = self.extract_url_features(url)
                X.append(list(features.values()))

            X = np.array(X)
            y = np.array(labels)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Train model
            self.url_classifier.fit(X_train, y_train)

            # Evaluate
            accuracy = self.url_classifier.score(X_test, y_test)
            logger.info(f"🧠 Model trained with accuracy: {accuracy:.3f}")

            # Train text vectorizer for pattern matching
            self.vectorizer.fit(urls)

            self.is_trained = True
            self.last_training = datetime.now().isoformat()

            # Build pattern database
            self._build_pattern_database(urls, labels)

            logger.info("🧠 ✅ ML URL Predictor training completed successfully")
            return True

        except Exception as e:
            logger.error(f"🧠 Error training model: {e}")
            return False

    def _build_pattern_database(self, urls: List[str], labels: List[int]):
        """Build pattern database from training data."""
        for url, label in zip(urls, labels):
            domain = urlparse(url).netloc
            path = urlparse(url).path

            # Extract patterns
            pattern = self._extract_pattern(path)

            # Update pattern statistics
            pattern_key = f"{domain}:{pattern}"
            if pattern_key not in self.url_patterns:
                self.url_patterns[pattern_key] = URLPattern(
                    pattern=pattern,
                    domain_pattern=domain
                )

            self.url_patterns[pattern_key].attempt_count += 1
            if label == 1:
                self.url_patterns[pattern_key].success_count += 1
                self.url_patterns[pattern_key].last_success = datetime.now().isoformat()

            # Update domain profile
            if domain not in self.domain_profiles:
                self.domain_profiles[domain] = DomainProfile(domain=domain)

            if label == 1:
                self.domain_profiles[domain].successful_patterns.append(pattern)
            else:
                self.domain_profiles[domain].failed_patterns.append(pattern)

            self.domain_profiles[domain].path_structures.add(
                '/'.join(p for p in path.split('/') if p)[:2]  # First 2 path segments
            )

    def _extract_pattern(self, path: str) -> str:
        """Extract generalized pattern from URL path."""
        # Remove specific identifiers and numbers
        pattern = re.sub(r'/\d+', '/NUM', path)
        pattern = re.sub(r'[0-9]+', 'N', pattern)
        pattern = re.sub(r'[a-f0-9]{8,}', 'ID', pattern.lower())
        return pattern

    def predict_successful_urls(self, domain: str, base_patterns: List[str] = None) -> List[Tuple[str, float]]:
        """
        Predict URLs most likely to contain schedule information for a domain.

        Returns:
            List of (url, confidence_score) tuples, sorted by confidence
        """
        try:
            predicted_urls = []

            if not self.is_trained:
                logger.info("🧠 Model not trained, attempting to train...")
                if not self.train_model():
                    return self._fallback_url_prediction(domain, base_patterns)

            # Get domain profile
            domain_profile = self.domain_profiles.get(domain)

            # Generate candidate URLs
            candidates = self._generate_candidate_urls(domain, domain_profile, base_patterns)

            # Score each candidate
            for url in candidates:
                confidence = self._calculate_url_confidence(url, domain_profile)
                if confidence > 0.1:  # Filter very low confidence URLs
                    predicted_urls.append((url, confidence))

            # Sort by confidence and return top predictions
            predicted_urls.sort(key=lambda x: x[1], reverse=True)

            logger.info(f"🧠 Predicted {len(predicted_urls)} URLs for {domain}")
            return predicted_urls[:50]  # Return top 50

        except Exception as e:
            logger.error(f"🧠 Error predicting URLs for {domain}: {e}")
            return self._fallback_url_prediction(domain, base_patterns)

    def _generate_candidate_urls(self, domain: str, profile: Optional[DomainProfile],
                                base_patterns: List[str] = None) -> Set[str]:
        """Generate candidate URLs for testing."""
        candidates = set()

        # Base patterns from successful extractions
        if base_patterns:
            for pattern in base_patterns:
                candidates.add(f"https://{domain}{pattern}")
                candidates.add(f"http://{domain}{pattern}")

        # Domain-specific successful patterns
        if profile and profile.successful_patterns:
            for pattern in profile.successful_patterns[:20]:  # Top 20 successful patterns
                candidates.add(f"https://{domain}{pattern}")
                candidates.add(f"http://{domain}{pattern}")

        # High-confidence general patterns
        high_confidence_patterns = [
            '/reconciliation', '/confession', '/confessions',
            '/adoration', '/eucharistic-adoration',
            '/mass-times', '/mass-schedule',
            '/schedule', '/schedules',
            '/worship', '/liturgy',
            '/sacraments'
        ]

        for pattern in high_confidence_patterns:
            candidates.add(f"https://{domain}{pattern}")
            candidates.add(f"http://{domain}{pattern}")

        return candidates

    def _calculate_url_confidence(self, url: str, profile: Optional[DomainProfile]) -> float:
        """Calculate confidence score for a URL."""
        try:
            # ML model prediction
            features = self.extract_url_features(url)
            feature_vector = np.array([list(features.values())]).reshape(1, -1)

            if self.is_trained:
                try:
                    ml_confidence = self.url_classifier.predict_proba(feature_vector)[0][1]
                except:
                    ml_confidence = 0.5
            else:
                ml_confidence = 0.5

            # Pattern-based confidence
            domain = urlparse(url).netloc
            path = urlparse(url).path
            pattern = self._extract_pattern(path)

            pattern_confidence = 0.5
            pattern_key = f"{domain}:{pattern}"
            if pattern_key in self.url_patterns:
                pattern_obj = self.url_patterns[pattern_key]
                pattern_confidence = max(pattern_obj.success_rate, 0.1)

            # Domain profile boost
            domain_boost = 1.0
            if profile:
                if any(p in path for p in profile.successful_patterns[:5]):
                    domain_boost = 1.2
                elif path in profile.failed_patterns:
                    domain_boost = 0.3

            # Combine scores
            final_confidence = (ml_confidence * 0.6 + pattern_confidence * 0.4) * domain_boost

            return min(final_confidence, 1.0)

        except Exception as e:
            logger.debug(f"🧠 Error calculating confidence for {url}: {e}")
            return 0.5

    def _fallback_url_prediction(self, domain: str, base_patterns: List[str] = None) -> List[Tuple[str, float]]:
        """Fallback URL prediction using pattern-based approach."""
        predictions = []

        patterns = base_patterns or [
            '/reconciliation', '/confession', '/adoration',
            '/mass-times', '/schedule', '/worship'
        ]

        for pattern in patterns:
            for scheme in ['https', 'http']:
                url = f"{scheme}://{domain}{pattern}"
                confidence = 0.5 + (0.3 if 'reconciliation' in pattern or 'adoration' in pattern else 0)
                predictions.append((url, confidence))

        return sorted(predictions, key=lambda x: x[1], reverse=True)

    def _is_schedule_relevant(self, url: str) -> bool:
        """Check if URL is relevant for schedule extraction."""
        url_lower = url.lower()
        relevant_terms = [
            'reconciliation', 'confession', 'adoration', 'eucharistic',
            'mass', 'times', 'schedule', 'hours', 'worship', 'liturgy',
            'sacrament', 'service'
        ]
        return any(term in url_lower for term in relevant_terms)

    def update_prediction_feedback(self, url: str, success: bool, schedule_found: bool = False):
        """Update model with feedback from extraction attempts."""
        try:
            domain = urlparse(url).netloc
            path = urlparse(url).path
            pattern = self._extract_pattern(path)
            pattern_key = f"{domain}:{pattern}"

            # Update pattern statistics
            if pattern_key not in self.url_patterns:
                self.url_patterns[pattern_key] = URLPattern(
                    pattern=pattern,
                    domain_pattern=domain
                )

            self.url_patterns[pattern_key].attempt_count += 1
            if success and schedule_found:
                self.url_patterns[pattern_key].success_count += 1
                self.url_patterns[pattern_key].last_success = datetime.now().isoformat()

            # Update domain profile
            if domain not in self.domain_profiles:
                self.domain_profiles[domain] = DomainProfile(domain=domain)

            if success and schedule_found:
                if pattern not in self.domain_profiles[domain].successful_patterns:
                    self.domain_profiles[domain].successful_patterns.append(pattern)
            elif not success:
                if pattern not in self.domain_profiles[domain].failed_patterns:
                    self.domain_profiles[domain].failed_patterns.append(pattern)

            self.domain_profiles[domain].last_updated = datetime.now().isoformat()

        except Exception as e:
            logger.debug(f"🧠 Error updating feedback for {url}: {e}")

    def save_model(self, filepath: str):
        """Save trained model and patterns to disk."""
        try:
            model_data = {
                'classifier': self.url_classifier,
                'vectorizer': self.vectorizer,
                'url_patterns': self.url_patterns,
                'domain_profiles': self.domain_profiles,
                'is_trained': self.is_trained,
                'last_training': self.last_training,
                'model_version': self.model_version
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"🧠 Model saved to {filepath}")

        except Exception as e:
            logger.error(f"🧠 Error saving model: {e}")

    def load_model(self, filepath: str) -> bool:
        """Load trained model and patterns from disk."""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)

            self.url_classifier = model_data.get('classifier', self.url_classifier)
            self.vectorizer = model_data.get('vectorizer', self.vectorizer)
            self.url_patterns = model_data.get('url_patterns', {})
            self.domain_profiles = model_data.get('domain_profiles', {})
            self.is_trained = model_data.get('is_trained', False)
            self.last_training = model_data.get('last_training')
            self.model_version = model_data.get('model_version', "1.0.0")

            logger.info(f"🧠 Model loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"🧠 Error loading model: {e}")
            return False


def get_ml_url_predictor(supabase: Client) -> MLURLPredictor:
    """Factory function to create ML URL predictor."""
    return MLURLPredictor(supabase)