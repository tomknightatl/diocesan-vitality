#!/usr/bin/env python3
"""
AI Authentication Manager Module.

This module provides authentication abstraction for Google AI services,
supporting multiple authentication strategies including API keys, OAuth,
service accounts, and automatic detection.

Features:
- Abstract base class for authentication strategies
- Multiple authentication strategy implementations
- Credential caching and refresh
- Graceful fallback between authentication methods
- Error handling and logging
- Integration with google.generativeai SDK
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

import google.auth
from google.auth.credentials import Credentials
from google.oauth2 import service_account
import google.generativeai as genai

from core.logger import get_logger

logger = get_logger(__name__)


class AuthStrategyError(Exception):
    """Base exception for authentication strategy errors."""
    pass


class AuthenticationFailedError(AuthStrategyError):
    """Exception raised when authentication fails."""
    pass


class CredentialsNotFoundError(AuthStrategyError):
    """Exception raised when required credentials are not found."""
    pass


class AuthStrategy(ABC):
    """
    Abstract base class for authentication strategies.

    All authentication strategies must implement this interface.
    """

    def __init__(self):
        """Initialize the authentication strategy."""
        self._credentials: Optional[Credentials] = None
        self._is_authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate using this strategy.

        Returns:
            True if authentication succeeded, False otherwise
        """
        pass

    @abstractmethod
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get the credentials object.

        Returns:
            Credentials object or None if not authenticated
        """
        pass

    @abstractmethod
    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with this authentication.

        Returns:
            True if configuration succeeded, False otherwise
        """
        pass

    @property
    def is_authenticated(self) -> bool:
        """Check if authentication was successful."""
        return self._is_authenticated

    def refresh(self) -> bool:
        """
        Refresh credentials if possible.

        Returns:
            True if refresh succeeded, False otherwise
        """
        logger.debug(f"Attempting to refresh {self.__class__.__name__} credentials")
        return self.authenticate()


class APIKeyAuthStrategy(AuthStrategy):
    """
    Authentication strategy using GENAI_API_KEY environment variable.

    This is the simplest authentication method, suitable for development
    and testing environments.
    """

    ENV_VAR_NAME = "GENAI_API_KEY"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API key authentication strategy.

        Args:
            api_key: API key string. If None, reads from environment variable.
        """
        super().__init__()
        self._api_key = api_key or os.getenv(self.ENV_VAR_NAME)

    def authenticate(self) -> bool:
        """
        Authenticate using API key.

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self._api_key:
            logger.error(f"API key not found in environment variable {self.ENV_VAR_NAME}")
            raise CredentialsNotFoundError(
                f"API key not found. Set {self.ENV_VAR_NAME} environment variable."
            )

        try:
            # Validate API key format (basic check)
            if len(self._api_key) < 10:
                logger.error("API key appears to be invalid (too short)")
                return False

            self._is_authenticated = True
            logger.info("API key authentication successful")
            return True

        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return False

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get credentials object.

        Note: API key strategy doesn't use Google Credentials object.
        Returns None as this strategy uses direct API key configuration.

        Returns:
            None (API key strategy doesn't use Credentials)
        """
        return None

    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with API key.

        Returns:
            True if configuration succeeded, False otherwise
        """
        if not self._is_authenticated and not self.authenticate():
            return False

        try:
            genai.configure(api_key=self._api_key)
            logger.info("Configured google.generativeai with API key")
            return True
        except Exception as e:
            logger.error(f"Failed to configure genai with API key: {e}")
            return False

    @property
    def api_key(self) -> Optional[str]:
        """Get the API key."""
        return self._api_key


class OAuthAuthStrategy(AuthStrategy):
    """
    Authentication strategy using Google Cloud OAuth credentials.

    This strategy uses Application Default Credentials (ADC) and is
    suitable for production environments with proper Google Cloud setup.
    """

    def __init__(self, scopes: Optional[list] = None):
        """
        Initialize OAuth authentication strategy.

        Args:
            scopes: OAuth scopes to request. If None, uses default scopes.
        """
        super().__init__()
        self._scopes = scopes or [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/generative-language.retriever",
        ]

    def authenticate(self) -> bool:
        """
        Authenticate using OAuth credentials.

        Returns:
            True if authentication succeeded, False otherwise
        """
        try:
            # Use Application Default Credentials
            self._credentials, project_id = google.auth.default(scopes=self._scopes)

            if not self._credentials:
                logger.error("No OAuth credentials found via Application Default Credentials")
                return False

            self._is_authenticated = True
            logger.info(f"OAuth authentication successful (project: {project_id})")
            return True

        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return False

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get the credentials object.

        Returns:
            Credentials object or None if not authenticated
        """
        return self._credentials

    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with OAuth credentials.

        Returns:
            True if configuration succeeded, False otherwise
        """
        if not self._is_authenticated and not self.authenticate():
            return False

        try:
            genai.configure(credentials=self._credentials)
            logger.info("Configured google.generativeai with OAuth credentials")
            return True
        except Exception as e:
            logger.error(f"Failed to configure genai with OAuth credentials: {e}")
            return False

    def refresh(self) -> bool:
        """
        Refresh OAuth credentials.

        Returns:
            True if refresh succeeded, False otherwise
        """
        if self._credentials and hasattr(self._credentials, "refresh"):
            try:
                self._credentials.refresh(google.auth.transport.requests.Request())
                logger.info("OAuth credentials refreshed successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh OAuth credentials: {e}")
                return False
        return super().refresh()


class ServiceAccountAuthStrategy(AuthStrategy):
    """
    Authentication strategy using Google Cloud service account.

    This strategy uses a service account JSON file and is suitable for
    server-to-server authentication in production environments.
    """

    ENV_VAR_NAME = "GOOGLE_APPLICATION_CREDENTIALS"

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        scopes: Optional[list] = None,
    ):
        """
        Initialize service account authentication strategy.

        Args:
            credentials_path: Path to service account JSON file.
                            If None, reads from GOOGLE_APPLICATION_CREDENTIALS env var.
            scopes: OAuth scopes to request. If None, uses default scopes.
        """
        super().__init__()
        self._credentials_path = credentials_path or os.getenv(self.ENV_VAR_NAME)
        self._scopes = scopes or [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/generative-language.retriever",
        ]

    def authenticate(self) -> bool:
        """
        Authenticate using service account credentials.

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self._credentials_path:
            logger.error(
                f"Service account credentials path not found. "
                f"Set {self.ENV_VAR_NAME} environment variable or provide credentials_path."
            )
            raise CredentialsNotFoundError(
                f"Service account credentials not found. Set {self.ENV_VAR_NAME} "
                f"environment variable or provide credentials_path."
            )

        try:
            # Validate file exists
            cred_path = Path(self._credentials_path)
            if not cred_path.exists():
                logger.error(f"Service account file not found: {self._credentials_path}")
                return False

            # Load service account credentials
            self._credentials = service_account.Credentials.from_service_account_file(
                self._credentials_path,
                scopes=self._scopes,
            )

            self._is_authenticated = True
            logger.info(f"Service account authentication successful (file: {self._credentials_path})")
            return True

        except Exception as e:
            logger.error(f"Service account authentication failed: {e}")
            return False

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get the credentials object.

        Returns:
            Credentials object or None if not authenticated
        """
        return self._credentials

    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with service account credentials.

        Returns:
            True if configuration succeeded, False otherwise
        """
        if not self._is_authenticated and not self.authenticate():
            return False

        try:
            genai.configure(credentials=self._credentials)
            logger.info("Configured google.generativeai with service account credentials")
            return True
        except Exception as e:
            logger.error(f"Failed to configure genai with service account credentials: {e}")
            return False

    def refresh(self) -> bool:
        """
        Refresh service account credentials.

        Returns:
            True if refresh succeeded, False otherwise
        """
        if self._credentials and hasattr(self._credentials, "refresh"):
            try:
                self._credentials.refresh(google.auth.transport.requests.Request())
                logger.info("Service account credentials refreshed successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to refresh service account credentials: {e}")
                return False
        return super().refresh()


class AutoDetectAuthStrategy(AuthStrategy):
    """
    Authentication strategy that automatically detects available authentication.

    This strategy tries multiple authentication methods in order of preference:
    1. Service account (if GOOGLE_APPLICATION_CREDENTIALS is set)
    2. OAuth (if Application Default Credentials are available)
    3. API key (if GENAI_API_KEY is set)

    This is the recommended strategy for most applications.
    """

    def __init__(self, enable_web_auth: bool = False):
        """
        Initialize auto-detect authentication strategy.

        Args:
            enable_web_auth: Whether to enable web-based OAuth flow
                           (not implemented in this version)
        """
        super().__init__()
        self._enable_web_auth = enable_web_auth
        self._active_strategy: Optional[AuthStrategy] = None
        self._strategy_priority = [
            ServiceAccountAuthStrategy,
            OAuthAuthStrategy,
            APIKeyAuthStrategy,
        ]

    def authenticate(self) -> bool:
        """
        Authenticate by auto-detecting the best available method.

        Returns:
            True if authentication succeeded, False otherwise
        """
        logger.info("Starting auto-detection of authentication method...")

        for strategy_class in self._strategy_priority:
            try:
                logger.debug(f"Trying {strategy_class.__name__}...")

                if strategy_class == ServiceAccountAuthStrategy:
                    strategy = strategy_class()
                elif strategy_class == OAuthAuthStrategy:
                    strategy = strategy_class()
                elif strategy_class == APIKeyAuthStrategy:
                    strategy = strategy_class()
                else:
                    continue

                if strategy.authenticate():
                    self._active_strategy = strategy
                    self._is_authenticated = True
                    logger.info(f"Auto-detected and authenticated using {strategy_class.__name__}")
                    return True

            except CredentialsNotFoundError:
                # This strategy doesn't have credentials, try next
                logger.debug(f"{strategy_class.__name__} credentials not found, trying next...")
                continue
            except Exception as e:
                # Unexpected error, log and try next
                logger.warning(f"{strategy_class.__name__} failed with error: {e}, trying next...")
                continue

        logger.error("All authentication methods failed")
        return False

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get the credentials object from the active strategy.

        Returns:
            Credentials object or None if not authenticated
        """
        if self._active_strategy:
            return self._active_strategy.get_credentials()
        return None

    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with the active strategy.

        Returns:
            True if configuration succeeded, False otherwise
        """
        if not self._is_authenticated and not self.authenticate():
            return False

        if self._active_strategy:
            return self._active_strategy.configure_genai()

        logger.error("No active authentication strategy to configure")
        return False

    def refresh(self) -> bool:
        """
        Refresh credentials using the active strategy.

        Returns:
            True if refresh succeeded, False otherwise
        """
        if self._active_strategy:
            return self._active_strategy.refresh()
        return super().refresh()

    @property
    def active_strategy(self) -> Optional[AuthStrategy]:
        """Get the active authentication strategy."""
        return self._active_strategy

    @property
    def active_strategy_name(self) -> Optional[str]:
        """Get the name of the active authentication strategy."""
        if self._active_strategy:
            return self._active_strategy.__class__.__name__
        return None


class AIAuthManager:
    """
    Authentication manager for AI services.

    This class provides a unified interface for authentication management,
    supporting multiple strategies and automatic fallback.
    """

    def __init__(
        self,
        auth_method: str = "auto_detect",
        enable_web_auth: bool = False,
        api_key: Optional[str] = None,
        credentials_path: Optional[str] = None,
        scopes: Optional[list] = None,
    ):
        """
        Initialize AI authentication manager.

        Args:
            auth_method: Authentication method to use
                        ('api_key', 'oauth', 'service_account', 'auto_detect')
            enable_web_auth: Whether to enable web-based OAuth flow
            api_key: API key (for api_key method)
            credentials_path: Path to service account JSON (for service_account method)
            scopes: OAuth scopes (for oauth and service_account methods)
        """
        self._auth_method = auth_method
        self._enable_web_auth = enable_web_auth
        self._strategy = self._create_strategy(
            auth_method, enable_web_auth, api_key, credentials_path, scopes
        )
        self._is_configured = False

    def _create_strategy(
        self,
        auth_method: str,
        enable_web_auth: bool,
        api_key: Optional[str],
        credentials_path: Optional[str],
        scopes: Optional[list],
    ) -> AuthStrategy:
        """
        Create the appropriate authentication strategy.

        Args:
            auth_method: Authentication method name
            enable_web_auth: Whether to enable web auth
            api_key: API key
            credentials_path: Service account credentials path
            scopes: OAuth scopes

        Returns:
            AuthStrategy instance
        """
        if auth_method == "api_key":
            return APIKeyAuthStrategy(api_key)
        elif auth_method == "oauth":
            return OAuthAuthStrategy(scopes)
        elif auth_method == "service_account":
            return ServiceAccountAuthStrategy(credentials_path, scopes)
        elif auth_method == "auto_detect":
            return AutoDetectAuthStrategy(enable_web_auth)
        else:
            logger.warning(f"Unknown auth method '{auth_method}', using auto_detect")
            return AutoDetectAuthStrategy(enable_web_auth)

    def authenticate(self) -> bool:
        """
        Authenticate using the configured strategy.

        Returns:
            True if authentication succeeded, False otherwise
        """
        try:
            if self._strategy.authenticate():
                logger.info(f"Authentication successful using {self._auth_method} method")
                return True
            else:
                logger.error(f"Authentication failed using {self._auth_method} method")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def configure_genai(self) -> bool:
        """
        Configure google.generativeai with authentication.

        Returns:
            True if configuration succeeded, False otherwise
        """
        if self._is_configured:
            logger.debug("genai already configured")
            return True

        if self._strategy.configure_genai():
            self._is_configured = True
            logger.info("google.generativeai configured successfully")
            return True
        else:
            logger.error("Failed to configure google.generativeai")
            return False

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get the credentials object.

        Returns:
            Credentials object or None if not authenticated
        """
        return self._strategy.get_credentials()

    def refresh_credentials(self) -> bool:
        """
        Refresh credentials if possible.

        Returns:
            True if refresh succeeded, False otherwise
        """
        return self._strategy.refresh()

    @property
    def is_authenticated(self) -> bool:
        """Check if authentication was successful."""
        return self._strategy.is_authenticated

    @property
    def is_configured(self) -> bool:
        """Check if genai is configured."""
        return self._is_configured

    @property
    def auth_method(self) -> str:
        """Get the authentication method."""
        return self._auth_method

    @property
    def active_strategy(self) -> Optional[AuthStrategy]:
        """Get the active authentication strategy."""
        if isinstance(self._strategy, AutoDetectAuthStrategy):
            return self._strategy.active_strategy
        return self._strategy

    @property
    def active_strategy_name(self) -> Optional[str]:
        """Get the name of the active authentication strategy."""
        if isinstance(self._strategy, AutoDetectAuthStrategy):
            return self._strategy.active_strategy_name
        return self._strategy.__class__.__name__


# Global authentication manager instance
_global_auth_manager: Optional[AIAuthManager] = None


def get_ai_auth_manager(
    auth_method: str = "auto_detect",
    enable_web_auth: bool = False,
    api_key: Optional[str] = None,
    credentials_path: Optional[str] = None,
    scopes: Optional[list] = None,
) -> AIAuthManager:
    """
    Get the global AI authentication manager instance.

    Args:
        auth_method: Authentication method to use
        enable_web_auth: Whether to enable web-based OAuth flow
        api_key: API key (for api_key method)
        credentials_path: Path to service account JSON (for service_account method)
        scopes: OAuth scopes (for oauth and service_account methods)

    Returns:
        AIAuthManager instance
    """
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = AIAuthManager(
            auth_method, enable_web_auth, api_key, credentials_path, scopes
        )
    return _global_auth_manager


def reset_ai_auth_manager() -> None:
    """Reset the global AI authentication manager instance."""
    global _global_auth_manager
    _global_auth_manager = None
    logger.info("Global AI authentication manager reset")