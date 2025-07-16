"""
Configuration management for Kultivator.

This module handles loading and accessing configuration values from config.yaml.
It provides a centralized way to manage all settings and makes it easy to 
modify behavior without changing code.
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging


class ConfigManager:
    """
    Manages configuration loading and access for Kultivator.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
                
            logging.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            # Fall back to default configuration
            self._config = self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values as fallback."""
        return {
            "ai": {
                "ollama_host": "http://localhost:11434",
                "model": "gemma3",
                "timeout": 30.0
            },
            "database": {
                "filename": "kultivator.db",
                "timeout": 30.0
            },
            "paths": {
                "wiki_dir": "wiki",
                "state_file": "logseq_last_state.json",
                "log_file": "kultivator.log"
            },
            "git": {
                "auto_commit": True,
                "commit_messages": {
                    "bootstrap": "AI: Bootstrap knowledge base with {entity_count} entities from {block_count} blocks",
                    "incremental": "AI: {action} {entity_name}\\n\\nUpdated by Kultivator AI on {timestamp}\\nSource block: {block_id}\\n\\nThis commit represents an incremental update to the knowledge base\\nbased on changes detected in the source data."
                }
            },
            "wiki": {
                "file_extension": ".md",
                "entity_directories": {
                    "person": "People",
                    "project": "Projects", 
                    "place": "Places",
                    "company": "Companies",
                    "book": "Books",
                    "other": "Other"
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "import": {
                "default_logseq_path": "./sample_logseq_data",
                "supported_formats": ["edn", "json"]
            },
            "agents": {
                "max_retries": 3,
                "enable_tools": True,
                "context_limit": 5,
                "definitions": {}
            },
            "performance": {
                "batch_size": 100,
                "max_concurrent_agents": 1
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., "ai.model")
            default: Default value if key is not found
            
        Returns:
            The configuration value
            
        Examples:
            config.get("ai.model")  # Returns "gemma3"
            config.get("wiki.entity_directories.person")  # Returns "People"
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Name of the configuration section
            
        Returns:
            Dictionary containing the section configuration
        """
        return self._config.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    # Convenience properties for commonly used values
    
    @property
    def ollama_host(self) -> str:
        """Get Ollama host URL."""
        return self.get("ai.ollama_host", "http://localhost:11434")
    
    @property
    def model_name(self) -> str:
        """Get AI model name."""
        return self.get("ai.model", "gemma3")
    
    @property
    def ollama_timeout(self) -> float:
        """Get Ollama timeout."""
        return self.get("ai.timeout", 30.0)
    
    @property
    def database_filename(self) -> str:
        """Get database filename."""
        return self.get("database.filename", "kultivator.db")
    
    @property
    def wiki_directory(self) -> str:
        """Get wiki directory path."""
        return self.get("paths.wiki_dir", "wiki")
    
    @property
    def state_filename(self) -> str:
        """Get state file name."""
        return self.get("paths.state_file", "logseq_last_state.json")
    
    @property
    def log_filename(self) -> str:
        """Get log file name."""
        return self.get("paths.log_file", "kultivator.log")
    
    @property
    def entity_directories(self) -> Dict[str, str]:
        """Get entity type to directory mapping."""
        return self.get("wiki.entity_directories", {
            "person": "People",
            "project": "Projects", 
            "place": "Places",
            "company": "Companies",
            "book": "Books",
            "other": "Other"
        })
    
    @property
    def context_limit(self) -> int:
        """Get agent context limit."""
        return self.get("agents.context_limit", 5)

    @property
    def agent_definitions(self) -> Dict[str, Any]:
        """Get agent definitions from configuration."""
        return self.get("agents.definitions", {})

    def get_agent_definition(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific agent definition by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent definition dictionary or None if not found
        """
        return self.agent_definitions.get(agent_name)


# Global configuration instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """
    Get the global configuration instance.
    
    Returns:
        The global ConfigManager instance
    """
    return config 