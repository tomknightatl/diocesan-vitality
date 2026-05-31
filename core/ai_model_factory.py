#!/usr/bin/env python3
"""
AI Model Factory Module.

This module provides a factory pattern for creating and managing Google GenerativeAI
model instances, supporting per-component model selection, authentication injection,
and model-specific parameters.

Features:
- Factory method for model instantiation
- Per-component model selection
- Authentication strategy injection
- Model-specific parameter handling
- Model caching for performance
- Model availability checking
- Model metadata and capabilities
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from core.ai_config import get_ai_config, AIConfig
from core.ai_auth_manager import get_ai_auth_manager, AIAuthManager
from core.logger import get_logger

logger = get_logger(__name__)


class ModelCacheEntry:
    """Cache entry for a model instance."""

    def __init__(self, model: genai.GenerativeModel, created_at: datetime, ttl: int):
        """
        Initialize model cache entry.

        Args:
            model: The cached GenerativeModel instance
            created_at: When the model was created
            ttl: Time-to-live in seconds
        """
        self.model = model
        self.created_at = created_at
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    def age(self) -> timedelta:
        """Get the age of the cache entry."""
        return datetime.now() - self.created_at


class AIModelFactory:
    """
    Factory for creating and managing Google GenerativeAI model instances.

    This factory handles model instantiation, authentication injection,
    parameter configuration, and caching for optimal performance.
    """

    # Known model capabilities
    MODEL_CAPABILITIES = {
        "gemini-1.5-flash": {
            "max_tokens": 1048576,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 1000000,
        },
        "gemini-1.5-pro": {
            "max_tokens": 2097152,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 2000000,
        },
        "gemini-2.5-flash": {
            "max_tokens": 1048576,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 1000000,
        },
        "gemini-2.5-pro": {
            "max_tokens": 2097152,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 2000000,
        },
        "gemini-2.5-flash-lite": {
            "max_tokens": 524288,
            "supports_vision": True,
            "supports_audio": False,
            "supports_video": False,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 500000,
        },
        "gemini-3.1-flash-preview": {
            "max_tokens": 1048576,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "supports_function_calling": True,
            "supports_system_instruction": True,
            "supports_json_mode": True,
            "context_window": 1000000,
        },
    }

    def __init__(
        self,
        config: Optional[AIConfig] = None,
        auth_manager: Optional[AIAuthManager] = None,
    ):
        """
        Initialize AI model factory.

        Args:
            config: AI configuration instance. If None, uses global config.
            auth_manager: Authentication manager instance. If None, uses global auth manager.
        """
        self._config = config or get_ai_config()
        self._auth_manager = auth_manager or get_ai_auth_manager()
        self._model_cache: Dict[str, ModelCacheEntry] = {}
        self._ensure_genai_configured()

        logger.info("AI Model Factory initialized")

    def _ensure_genai_configured(self) -> None:
        """Ensure google.generativeai is configured with authentication."""
        if not self._auth_manager.is_configured:
            logger.info("Configuring google.generativeai...")
            if not self._auth_manager.configure_genai():
                logger.error("Failed to configure google.generativeai")
                raise RuntimeError("Failed to configure google.generativeai authentication")

    def _generate_cache_key(
        self,
        model_name: str,
        component_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a cache key for a model instance.

        Args:
            model_name: Name of the model
            component_name: Name of the component requesting the model
            parameters: Model parameters

        Returns:
            Cache key string
        """
        key_parts = [model_name, component_name]

        if parameters:
            # Sort parameters for consistent hashing
            param_str = "&".join(f"{k}={v}" for k, v in sorted(parameters.items()))
            key_parts.append(param_str)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _create_generation_config(self, parameters: Dict[str, Any]) -> GenerationConfig:
        """
        Create a GenerationConfig from parameters.

        Args:
            parameters: Model parameters dictionary

        Returns:
            GenerationConfig instance
        """
        return GenerationConfig(
            temperature=parameters.get("temperature", 0.7),
            max_output_tokens=parameters.get("max_tokens", 4096),
            top_p=parameters.get("top_p", 0.9),
            top_k=parameters.get("top_k", 40),
        )

    def _validate_model_name(self, model_name: str) -> bool:
        """
        Validate that a model name is known and supported.

        Args:
            model_name: Name of the model to validate

        Returns:
            True if model is known, False otherwise
        """
        # Check if it's in our known capabilities
        if model_name in self.MODEL_CAPABILITIES:
            return True

        # Try to check if model exists by attempting to list models
        # (this is a lightweight check)
        try:
            # Note: This requires genai to be configured
            models = genai.list_models()
            model_names = [m.name for m in models]
            # Remove "models/" prefix if present
            model_names = [name.replace("models/", "") for name in model_names]
            return model_name in model_names
        except Exception as e:
            logger.warning(f"Could not validate model {model_name}: {e}")
            # Assume it's valid if we can't check
            return True

    def get_model(
        self,
        component_name: str,
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        use_cache: Optional[bool] = None,
    ) -> genai.GenerativeModel:
        """
        Get a GenerativeAI model instance for a component.

        Args:
            component_name: Name of the component requesting the model
            model_name: Specific model name to use. If None, uses config default.
            parameters: Model-specific parameters. If None, uses config defaults.
            system_instruction: System instruction for the model
            use_cache: Whether to use model caching. If None, uses config default.

        Returns:
            GenerativeModel instance

        Raises:
            ValueError: If model name is invalid
            RuntimeError: If model creation fails
        """
        # Determine model name
        if model_name is None:
            model_name = self._config.get_model_for_component(component_name)

        # Validate model name
        if not self._validate_model_name(model_name):
            logger.warning(f"Model {model_name} may not be valid, attempting to use anyway")

        # Determine parameters
        if parameters is None:
            parameters = self._config.get_component_parameters(component_name)

        # Determine cache usage
        if use_cache is None:
            use_cache = self._config.enable_caching

        # Check cache first
        cache_key = self._generate_cache_key(model_name, component_name, parameters)
        if use_cache and cache_key in self._model_cache:
            cache_entry = self._model_cache[cache_key]
            if not cache_entry.is_expired():
                logger.debug(f"Using cached model for {component_name} (age: {cache_entry.age()})")
                return cache_entry.model
            else:
                # Remove expired entry
                logger.debug(f"Removing expired cache entry for {component_name}")
                del self._model_cache[cache_key]

        # Create new model instance
        try:
            logger.info(f"Creating new model instance: {model_name} for {component_name}")

            # Create generation config
            generation_config = self._create_generation_config(parameters)

            # Create model with optional system instruction
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    system_instruction=system_instruction,
                )
            else:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                )

            # Cache the model if caching is enabled
            if use_cache:
                cache_entry = ModelCacheEntry(
                    model=model,
                    created_at=datetime.now(),
                    ttl=self._config.cache_ttl,
                )
                self._model_cache[cache_key] = cache_entry
                logger.debug(f"Cached model for {component_name} (TTL: {self._config.cache_ttl}s)")

            return model

        except Exception as e:
            logger.error(f"Failed to create model {model_name} for {component_name}: {e}")
            raise RuntimeError(f"Model creation failed: {e}") from e

    def get_model_with_config(
        self,
        component_name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> genai.GenerativeModel:
        """
        Get a model instance with configuration overrides.

        Args:
            component_name: Name of the component requesting the model
            config_overrides: Dictionary of configuration overrides

        Returns:
            GenerativeModel instance
        """
        # Get component config
        component_config = self._config.get_component_config(component_name)

        # Apply overrides
        if config_overrides:
            if "model" in config_overrides:
                component_config["model"] = config_overrides["model"]
            if "parameters" in config_overrides:
                component_config["parameters"].update(config_overrides["parameters"])

        # Get model
        return self.get_model(
            component_name=component_name,
            model_name=component_config["model"],
            parameters=component_config["parameters"],
        )

    def get_model_capabilities(self, model_name: str) -> Dict[str, Any]:
        """
        Get capabilities for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary of model capabilities
        """
        if model_name in self.MODEL_CAPABILITIES:
            return self.MODEL_CAPABILITIES[model_name].copy()

        # Try to get capabilities from genai
        try:
            models = genai.list_models()
            for model in models:
                if model.name.replace("models/", "") == model_name:
                    # Extract basic capabilities from model metadata
                    return {
                        "max_tokens": getattr(model, "max_output_tokens", 8192),
                        "supports_vision": True,  # Assume support for newer models
                        "supports_audio": True,
                        "supports_video": True,
                        "supports_function_calling": True,
                        "supports_system_instruction": True,
                        "supports_json_mode": True,
                        "context_window": getattr(model, "input_token_limit", 128000),
                    }
        except Exception as e:
            logger.warning(f"Could not get capabilities for {model_name}: {e}")

        # Return default capabilities
        return {
            "max_tokens": 8192,
            "supports_vision": False,
            "supports_audio": False,
            "supports_video": False,
            "supports_function_calling": False,
            "supports_system_instruction": False,
            "supports_json_mode": False,
            "context_window": 128000,
        }

    def list_available_models(self) -> List[str]:
        """
        List all available models.

        Returns:
            List of model names
        """
        try:
            models = genai.list_models()
            # Remove "models/" prefix and return as list
            return [m.name.replace("models/", "") for m in models]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            # Return known models as fallback
            return list(self.MODEL_CAPABILITIES.keys())

    def clear_cache(self, component_name: Optional[str] = None) -> int:
        """
        Clear model cache.

        Args:
            component_name: If specified, only clears cache for this component.
                           If None, clears all cache.

        Returns:
            Number of cache entries cleared
        """
        if component_name is None:
            count = len(self._model_cache)
            self._model_cache.clear()
            logger.info(f"Cleared all model cache entries ({count} total)")
            return count
        else:
            # Clear only entries for this component
            keys_to_remove = [
                key for key in self._model_cache
                if component_name in str(self._model_cache[key].model)
            ]
            for key in keys_to_remove:
                del self._model_cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries for {component_name}")
            return len(keys_to_remove)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self._model_cache)
        expired_entries = sum(1 for entry in self._model_cache.values() if entry.is_expired())

        # Calculate average age
        if self._model_cache:
            total_age = sum(entry.age().total_seconds() for entry in self._model_cache.values())
            avg_age = total_age / len(self._model_cache)
        else:
            avg_age = 0

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "average_age_seconds": avg_age,
            "cache_enabled": self._config.enable_caching,
            "cache_ttl": self._config.cache_ttl,
        }

    def test_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Test if a model is available and working.

        Args:
            model_name: Name of the model to test

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info(f"Testing model {model_name}...")

            # Create a simple test model
            model = genai.GenerativeModel(model_name)

            # Try a simple generation
            response = model.generate_content("Test")

            if response and response.text:
                logger.info(f"Model {model_name} test successful")
                return True, f"Model {model_name} is available and working"
            else:
                logger.warning(f"Model {model_name} returned empty response")
                return False, f"Model {model_name} returned empty response"

        except Exception as e:
            logger.error(f"Model {model_name} test failed: {e}")
            return False, f"Model {model_name} test failed: {str(e)}"

    def get_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata for a model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model metadata
        """
        capabilities = self.get_model_capabilities(model_name)

        return {
            "name": model_name,
            "capabilities": capabilities,
            "is_known": model_name in self.MODEL_CAPABILITIES,
            "config": {
                "temperature": self._config.model_parameters.get("temperature"),
                "max_tokens": self._config.model_parameters.get("max_tokens"),
                "top_p": self._config.model_parameters.get("top_p"),
                "top_k": self._config.model_parameters.get("top_k"),
            },
        }


# Global model factory instance
_global_model_factory: Optional[AIModelFactory] = None


def get_ai_model_factory(
    config: Optional[AIConfig] = None,
    auth_manager: Optional[AIAuthManager] = None,
) -> AIModelFactory:
    """
    Get the global AI model factory instance.

    Args:
        config: AI configuration instance. If None, uses global config.
        auth_manager: Authentication manager instance. If None, uses global auth manager.

    Returns:
        AIModelFactory instance
    """
    global _global_model_factory
    if _global_model_factory is None:
        _global_model_factory = AIModelFactory(config, auth_manager)
    return _global_model_factory


def reset_ai_model_factory() -> None:
    """Reset the global AI model factory instance."""
    global _global_model_factory
    _global_model_factory = None
    logger.info("Global AI model factory reset")


# Convenience functions for common use cases

def get_model_for_component(component_name: str) -> genai.GenerativeModel:
    """
    Convenience function to get a model for a component.

    Args:
        component_name: Name of the component

    Returns:
        GenerativeModel instance
    """
    factory = get_ai_model_factory()
    return factory.get_model(component_name)


def get_model_with_system_instruction(
    component_name: str,
    system_instruction: str,
) -> genai.GenerativeModel:
    """
    Convenience function to get a model with a system instruction.

    Args:
        component_name: Name of the component
        system_instruction: System instruction for the model

    Returns:
        GenerativeModel instance
    """
    factory = get_ai_model_factory()
    return factory.get_model(component_name, system_instruction=system_instruction)