#!/usr/bin/env python3
"""
AI Configuration Management Module.

This module provides comprehensive configuration management for AI services,
including Google Gemini models and authentication strategies. It supports
YAML configuration files, environment variable overrides, and validation.

Features:
- Load from YAML configuration files
- Parse environment variables for AI authentication
- Validate configuration values
- Support configuration overrides
- Handle default values and fallback configurations
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from core.logger import get_logger

logger = get_logger(__name__)


class AIConfig:
    """
    Configuration manager for AI services.

    This class handles loading, validating, and providing access to AI configuration
    settings, including authentication methods, model configurations, and component-specific
    settings.
    """

    # Default configuration values
    DEFAULT_CONFIG = {
        "authentication": {
            "method": "auto_detect",  # api_key, oauth, service_account, auto_detect
            "enable_web_auth": False,
            "force_model": None,
        },
        "models": {
            "default": "gemini-1.5-flash",
            "components": {
                "content_analyzer": "gemini-2.5-pro",
                "schedule_extractor": "gemini-3.1-flash-preview",
                "fallback_extractor": "gemini-2.5-pro",
                "url_filter": "gemini-2.5-flash-lite",
                "parish_prioritizer": "gemini-3.1-flash-preview",
            },
        },
        "component_parameters": {
            "content_analyzer": {
                "temperature": 0.7,
                "max_tokens": 8192,
                "thinking_enabled": True,
                "thinking_budget": 8192,
            },
            "schedule_extractor": {
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            "fallback_extractor": {
                "temperature": 0.7,
                "max_tokens": 8192,
                "thinking_enabled": True,
                "thinking_budget": 16384,
            },
            "url_filter": {
                "temperature": 0.1,
                "max_tokens": 2048,
            },
            "parish_prioritizer": {
                "temperature": 0.5,
                "max_tokens": 4096,
            },
        },
        "model_parameters": {
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 0.9,
            "top_k": 40,
        },
        "performance": {
            "enable_caching": True,
            "cache_ttl": 3600,  # 1 hour
            "max_retries": 3,
            "timeout": 30,
        },
        "logging": {
            "level": "INFO",
            "log_requests": False,
            "log_responses": False,
        },
        "cost_optimization": {
            "enabled": True,
            "budget_limit_usd": 100.0,
            "daily_quota_tokens": 1000000,
            "prefer_cheaper_models": True,
            "enable_smart_routing": True,
        },
    }

    # Valid authentication methods
    VALID_AUTH_METHODS = ["api_key", "oauth", "service_account", "auto_detect"]

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AI configuration manager.

        Args:
            config_path: Path to YAML configuration file. If None, uses default path.
        """
        self._config: Dict[str, Any] = {}
        self._config_path = self._resolve_config_path(config_path)
        self._load_config()
        self._apply_environment_overrides()
        self._validate_config()

        logger.info(f"AI Configuration loaded from {self._config_path}")
        logger.debug(f"Authentication method: {self.auth_method}")

    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """
        Resolve the configuration file path.

        Args:
            config_path: User-provided config path or None

        Returns:
            Resolved absolute path to config file
        """
        if config_path:
            # Use user-provided path
            path = Path(config_path)
            if path.exists():
                return str(path.absolute())
            logger.warning(f"Config file not found at {config_path}, using defaults")

        # Try default locations
        default_paths = [
            "config/ai_config.yaml",
            "config/ai_config.yml",
            "../config/ai_config.yaml",
            "../config/ai_config.yml",
        ]

        for default_path in default_paths:
            path = Path(default_path)
            if path.exists():
                return str(path.absolute())

        # Return first default path (will use defaults if file doesn't exist)
        return str(Path("config/ai_config.yaml").absolute())

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            config_file = Path(self._config_path)
            if config_file.exists():
                with open(config_file, "r") as f:
                    loaded_config = yaml.safe_load(f) or {}
                self._config = self._deep_merge(self.DEFAULT_CONFIG, loaded_config)
                logger.info(f"Loaded configuration from {self._config_path}")
            else:
                self._config = self.DEFAULT_CONFIG.copy()
                logger.info("Using default configuration (no config file found)")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}, using defaults")
            self._config = self.DEFAULT_CONFIG.copy()

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_overrides = {
            "GOOGLE_AI_AUTH_METHOD": ("authentication", "method"),
            "GOOGLE_AI_FORCE_MODEL": ("authentication", "force_model"),
            "GOOGLE_AI_ENABLE_WEB_AUTH": ("authentication", "enable_web_auth"),
            "GOOGLE_AI_DEFAULT_MODEL": ("models", "default"),
            "GOOGLE_AI_TEMPERATURE": ("model_parameters", "temperature"),
            "GOOGLE_AI_MAX_TOKENS": ("model_parameters", "max_tokens"),
            "GOOGLE_AI_TOP_P": ("model_parameters", "top_p"),
            "GOOGLE_AI_TOP_K": ("model_parameters", "top_k"),
            "GOOGLE_AI_ENABLE_CACHING": ("performance", "enable_caching"),
            "GOOGLE_AI_CACHE_TTL": ("performance", "cache_ttl"),
            "GOOGLE_AI_MAX_RETRIES": ("performance", "max_retries"),
            "GOOGLE_AI_TIMEOUT": ("performance", "timeout"),
            "GOOGLE_AI_LOG_LEVEL": ("logging", "level"),
            "GOOGLE_AI_LOG_REQUESTS": ("logging", "log_requests"),
            "GOOGLE_AI_LOG_RESPONSES": ("logging", "log_responses"),
        }

        for env_var, (section, key) in env_overrides.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value, key)
                self._config[section][key] = converted_value
                logger.debug(f"Applied env override: {env_var} = {converted_value}")

    def _convert_env_value(self, value: str, key: str) -> Any:
        """
        Convert environment variable string to appropriate type.

        Args:
            value: String value from environment
            key: Configuration key for type inference

        Returns:
            Converted value (bool, int, float, or str)
        """
        # Boolean conversion
        if key in ["enable_web_auth", "enable_caching", "log_requests", "log_responses"]:
            return value.lower() in ("true", "1", "yes", "on")

        # Numeric conversion
        if key in ["temperature", "max_tokens", "top_p", "top_k", "cache_ttl", "max_retries", "timeout"]:
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                logger.warning(f"Failed to convert {value} to number for {key}, using string")
                return value

        # Default: return as string
        return value

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate authentication method
        auth_method = self._config["authentication"]["method"]
        if auth_method not in self.VALID_AUTH_METHODS:
            logger.warning(
                f"Invalid auth method '{auth_method}', must be one of {self.VALID_AUTH_METHODS}. "
                f"Using 'auto_detect' instead."
            )
            self._config["authentication"]["method"] = "auto_detect"

        # Validate model parameters
        temp = self._config["model_parameters"]["temperature"]
        if not 0.0 <= temp <= 2.0:
            logger.warning(f"Temperature {temp} out of range [0.0, 2.0], clamping to 0.7")
            self._config["model_parameters"]["temperature"] = 0.7

        max_tokens = self._config["model_parameters"]["max_tokens"]
        if max_tokens < 1 or max_tokens > 32768:
            logger.warning(f"max_tokens {max_tokens} out of range [1, 32768], clamping to 4096")
            self._config["model_parameters"]["max_tokens"] = 4096

        # Validate performance settings
        if self._config["performance"]["max_retries"] < 0:
            logger.warning("max_retries cannot be negative, setting to 3")
            self._config["performance"]["max_retries"] = 3

        if self._config["performance"]["timeout"] < 1:
            logger.warning("timeout cannot be less than 1 second, setting to 30")
            self._config["performance"]["timeout"] = 30

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # Property accessors

    @property
    def auth_method(self) -> str:
        """Get the authentication method."""
        return self._config["authentication"]["method"]

    @property
    def enable_web_auth(self) -> bool:
        """Get whether web authentication is enabled."""
        return self._config["authentication"]["enable_web_auth"]

    @property
    def force_model(self) -> Optional[str]:
        """Get the forced model name (if any)."""
        return self._config["authentication"]["force_model"]

    @property
    def default_model(self) -> str:
        """Get the default model name."""
        return self._config["models"]["default"]

    @property
    def model_parameters(self) -> Dict[str, Any]:
        """Get model parameters."""
        return self._config["model_parameters"].copy()

    @property
    def enable_caching(self) -> bool:
        """Get whether model caching is enabled."""
        return self._config["performance"]["enable_caching"]

    @property
    def cache_ttl(self) -> int:
        """Get cache time-to-live in seconds."""
        return self._config["performance"]["cache_ttl"]

    @property
    def max_retries(self) -> int:
        """Get maximum number of retries."""
        return self._config["performance"]["max_retries"]

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        return self._config["performance"]["timeout"]

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config["logging"]["level"]

    @property
    def log_requests(self) -> bool:
        """Get whether to log API requests."""
        return self._config["logging"]["log_requests"]

    @property
    def log_responses(self) -> bool:
        """Get whether to log API responses."""
        return self._config["logging"]["log_responses"]

    @property
    def cost_optimization_enabled(self) -> bool:
        """Get whether cost optimization is enabled."""
        return self._config.get("cost_optimization", {}).get("enabled", False)

    @property
    def budget_limit_usd(self) -> float:
        """Get the budget limit in USD."""
        return self._config.get("cost_optimization", {}).get("budget_limit_usd", 100.0)

    @property
    def daily_quota_tokens(self) -> int:
        """Get the daily quota in tokens."""
        return self._config.get("cost_optimization", {}).get("daily_quota_tokens", 1000000)

    @property
    def prefer_cheaper_models(self) -> bool:
        """Get whether to prefer cheaper models."""
        return self._config.get("cost_optimization", {}).get("prefer_cheaper_models", True)

    @property
    def enable_smart_routing(self) -> bool:
        """Get whether smart routing is enabled."""
        return self._config.get("cost_optimization", {}).get("enable_smart_routing", True)

    # Component-specific methods

    def get_model_for_component(self, component_name: str) -> str:
        """
        Get the model name for a specific component.

        Args:
            component_name: Name of the component (e.g., 'content_analyzer')

        Returns:
            Model name to use for the component
        """
        # Check for forced model override
        if self.force_model:
            logger.debug(f"Using forced model {self.force_model} for {component_name}")
            return self.force_model

        # Check for component-specific model
        component_models = self._config["models"].get("components", {})
        if component_name in component_models:
            return component_models[component_name]

        # Fall back to default model
        logger.debug(f"No specific model for {component_name}, using default {self.default_model}")
        return self.default_model

    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """
        Get full configuration for a specific component.

        Args:
            component_name: Name of the component

        Returns:
            Component-specific configuration dictionary
        """
        # Get component-specific parameters if available, otherwise use global parameters
        component_params = self.get_component_parameters(component_name)

        return {
            "model": self.get_model_for_component(component_name),
            "parameters": component_params,
            "performance": {
                "enable_caching": self.enable_caching,
                "cache_ttl": self.cache_ttl,
                "max_retries": self.max_retries,
                "timeout": self.timeout,
            },
            "logging": {
                "level": self.log_level,
                "log_requests": self.log_requests,
                "log_responses": self.log_responses,
            },
        }

    def get_component_parameters(self, component_name: str) -> Dict[str, Any]:
        """
        Get parameters for a specific component.

        Args:
            component_name: Name of the component

        Returns:
            Component-specific parameters dictionary
        """
        # Check for component-specific parameters
        component_params = self._config.get("component_parameters", {}).get(component_name, {})

        # Merge with global parameters (component-specific takes precedence)
        merged_params = self.model_parameters.copy()
        merged_params.update(component_params)

        return merged_params

    def get_all_component_models(self) -> Dict[str, str]:
        """
        Get all component-to-model mappings.

        Returns:
            Dictionary mapping component names to model names
        """
        models = {}
        component_models = self._config["models"].get("components", {})
        for component, model in component_models.items():
            models[component] = model
        return models

    def get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.

        Args:
            section: Configuration section name
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(section, {}).get(key, default)

    def reload(self) -> None:
        """Reload configuration from file and environment."""
        logger.info("Reloading AI configuration...")
        self._load_config()
        self._apply_environment_overrides()
        self._validate_config()
        logger.info("AI configuration reloaded successfully")


# Global configuration instance
_global_config: Optional[AIConfig] = None


def get_ai_config(config_path: Optional[str] = None) -> AIConfig:
    """
    Get the global AI configuration instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        AIConfig instance
    """
    global _global_config
    if _global_config is None:
        _global_config = AIConfig(config_path)
    return _global_config


def reset_ai_config() -> None:
    """Reset the global AI configuration instance."""
    global _global_config
    _global_config = None
    logger.info("Global AI configuration reset")