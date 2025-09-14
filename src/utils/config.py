"""
Configuration Management Utility

This module provides configuration management for the Openflow with LLM project.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or self._find_config_file()
        self._config = None
        self._load_config()
    
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config/nifi_config.yaml",
            "config/config.yaml",
            "nifi_config.yaml",
            "config.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_config(self):
        """Load configuration from file."""
        if not self.config_path or not os.path.exists(self.config_path):
            logger.warning(f"Configuration file not found: {self.config_path}")
            self._config = {}
            return
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    self._config = yaml.safe_load(f) or {}
                elif self.config_path.endswith('.json'):
                    self._config = json.load(f) or {}
                else:
                    logger.error(f"Unsupported config file format: {self.config_path}")
                    self._config = {}
                    
            logger.info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._config.copy()
    
    def set(self, key: str, value: Any):
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> Dict[str, Any]:
    """Get all configuration."""
    return get_config_manager().get_all()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value by key."""
    return get_config_manager().get(key, default)


def set_config_value(key: str, value: Any):
    """Set configuration value."""
    get_config_manager().set(key, value)


def reload_config():
    """Reload configuration from file."""
    get_config_manager().reload()


# Environment variable helpers
def get_env_config() -> Dict[str, Any]:
    """Get configuration from environment variables."""
    return {
        "nifi": {
            "home": os.getenv("NIFI_HOME", "/Users/kikim/Downloads/nifi-2.4.0"),
            "api": {
                "base_url": os.getenv("NIFI_BASE_URL", "http://localhost:8080/nifi-api"),
                "timeout": int(os.getenv("NIFI_TIMEOUT", "30")),
                "verify_ssl": os.getenv("NIFI_VERIFY_SSL", "false").lower() == "true"
            },
            "auth": {
                "username": os.getenv("NIFI_USERNAME"),
                "password": os.getenv("NIFI_PASSWORD")
            },
            "web": {
                "http": {
                    "host": os.getenv("NIFI_WEB_HTTP_HOST", "localhost"),
                    "port": int(os.getenv("NIFI_WEB_HTTP_PORT", "8080"))
                }
            },
            "jvm": {
                "heap_init": os.getenv("NIFI_JVM_HEAP_INIT", "512m"),
                "heap_max": os.getenv("NIFI_JVM_HEAP_MAX", "2g")
            }
        },
        "llm": {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "4000"))
            },
            "google": {
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "model": os.getenv("GOOGLE_MODEL", "gemini-pro")
            },
            "ollama": {
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": os.getenv("OLLAMA_MODEL", "llama2")
            }
        },
        "database": {
            "url": os.getenv("DATABASE_URL", "postgresql://username:password@localhost:5432/openflow_llm"),
            "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        },
        "redis": {
            "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "password": os.getenv("REDIS_PASSWORD"),
            "db": int(os.getenv("REDIS_DB", "0"))
        },
        "app": {
            "name": os.getenv("APP_NAME", "Openflow_with_LLM"),
            "version": os.getenv("APP_VERSION", "0.1.0"),
            "debug": os.getenv("DEBUG", "true").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO")
        },
        "server": {
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            "workers": int(os.getenv("WORKERS", "1"))
        }
    }


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple configuration dictionaries.
    
    Args:
        *configs: Configuration dictionaries to merge
        
    Returns:
        Merged configuration dictionary
    """
    result = {}
    
    for config in configs:
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value
    
    return result


def get_merged_config() -> Dict[str, Any]:
    """Get merged configuration from file and environment variables."""
    file_config = get_config()
    env_config = get_env_config()
    
    return merge_configs(env_config, file_config)
