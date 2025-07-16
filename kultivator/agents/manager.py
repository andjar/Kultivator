"""
Agent Manager for Kultivator.

This module provides the AgentManager class that handles loading agents from
configuration, managing agent templates, and providing a unified interface
for agent operations.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .registry import AgentConfig, AgentRegistry
from ..config import config


@dataclass
class AgentDefinition:
    """
    Configuration-based agent definition loaded from YAML.
    """
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    available_tools: List[str] = field(default_factory=list)
    requires_database: bool = True
    timeout: float = 30.0
    
    def to_agent_config(self) -> AgentConfig:
        """Convert to AgentConfig for backward compatibility."""
        return AgentConfig(
            name=self.name,
            description=self.description,
            system_prompt=self.system_prompt,
            available_tools=self.available_tools,
            requires_database=self.requires_database,
            timeout=self.timeout
        )


class AgentManager:
    """
    Manages AI agents with configuration-based definitions and template support.
    """
    
    def __init__(self, agent_registry: Optional[AgentRegistry] = None):
        """
        Initialize the agent manager.
        
        Args:
            agent_registry: Optional agent registry to use
        """
        self.agent_registry = agent_registry or AgentRegistry()
        self.agent_definitions: Dict[str, AgentDefinition] = {}
        self._load_agent_definitions()
        
    def _load_agent_definitions(self):
        """Load agent definitions from configuration."""
        try:
            agent_defs = config.agent_definitions
            
            for agent_name, agent_config in agent_defs.items():
                try:
                    # Validate required fields
                    required_fields = ['description', 'system_prompt', 'user_prompt_template']
                    for field in required_fields:
                        if field not in agent_config:
                            raise ValueError(f"Missing required field '{field}' in agent '{agent_name}'")
                    
                    # Create agent definition
                    agent_def = AgentDefinition(
                        name=agent_name,
                        description=agent_config['description'],
                        system_prompt=agent_config['system_prompt'],
                        user_prompt_template=agent_config['user_prompt_template'],
                        available_tools=agent_config.get('available_tools', []),
                        requires_database=agent_config.get('requires_database', True),
                        timeout=agent_config.get('timeout', 30.0)
                    )
                    
                    self.agent_definitions[agent_name] = agent_def
                    
                    # Also register in the legacy registry for backward compatibility
                    self.agent_registry.register_agent(agent_def.to_agent_config())
                    
                    logging.info(f"Loaded agent definition: {agent_name}")
                    
                except Exception as e:
                    logging.error(f"Failed to load agent definition '{agent_name}': {e}")
                    
        except Exception as e:
            logging.error(f"Failed to load agent definitions: {e}")
    
    def get_agent_definition(self, agent_name: str) -> Optional[AgentDefinition]:
        """
        Get an agent definition by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent definition or None if not found
        """
        return self.agent_definitions.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """
        Get a list of all available agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agent_definitions.keys())
    
    def get_agents_by_tool(self, tool_name: str) -> List[str]:
        """
        Get agents that have access to a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            List of agent names that can use the tool
        """
        return [
            name for name, agent_def in self.agent_definitions.items()
            if tool_name in agent_def.available_tools
        ]
    
    def render_user_prompt(self, agent_name: str, **kwargs) -> str:
        """
        Render a user prompt for an agent using its template.
        
        Args:
            agent_name: Name of the agent
            **kwargs: Template variables
            
        Returns:
            Rendered user prompt
            
        Raises:
            ValueError: If agent not found or template rendering fails
        """
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        try:
            # Use string format method for {variable} syntax
            return agent_def.user_prompt_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable {e} for agent '{agent_name}'")
        except Exception as e:
            raise ValueError(f"Failed to render template for agent '{agent_name}': {e}")
    
    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get the system prompt for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            System prompt
            
        Raises:
            ValueError: If agent not found
        """
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        return agent_def.system_prompt
    
    def validate_agent_definition(self, agent_name: str) -> Dict[str, Any]:
        """
        Validate an agent definition and return validation results.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            results['valid'] = False
            results['errors'].append(f"Agent '{agent_name}' not found")
            return results
        
        # Validate system prompt
        if not agent_def.system_prompt.strip():
            results['valid'] = False
            results['errors'].append("System prompt cannot be empty")
        
        # Validate user prompt template
        if not agent_def.user_prompt_template.strip():
            results['valid'] = False
            results['errors'].append("User prompt template cannot be empty")
        
        # Check for common template variables
        template_vars = self._extract_template_variables(agent_def.user_prompt_template)
        recommended_vars = {
            'triage': ['current_time', 'source_ref', 'content', 'created_at', 'updated_at'],
            'synthesizer_create': ['entity_name', 'entity_type', 'context_info', 'summary', 'content'],
            'synthesizer_merge': ['entity_name', 'entity_type', 'context_info', 'existing_content', 'summary'],
            'task_manager': ['content', 'source_ref', 'entity_name', 'entity_type', 'context_info'],
            'travel_planner': ['content', 'source_ref', 'entity_name', 'entity_type', 'context_info']
        }
        
        if agent_name in recommended_vars:
            missing_vars = set(recommended_vars[agent_name]) - set(template_vars)
            if missing_vars:
                results['warnings'].append(f"Missing recommended template variables: {', '.join(missing_vars)}")
        
        # Validate tools
        known_tools = ['list_entities', 'get_entity_context']
        unknown_tools = set(agent_def.available_tools) - set(known_tools)
        if unknown_tools:
            results['warnings'].append(f"Unknown tools specified: {', '.join(unknown_tools)}")
        
        # Validate timeout
        if agent_def.timeout <= 0:
            results['valid'] = False
            results['errors'].append("Timeout must be positive")
        
        return results
    
    def _extract_template_variables(self, template: str) -> List[str]:
        """
        Extract template variables from a template string.
        
        Args:
            template: Template string
            
        Returns:
            List of variable names
        """
        import re
        
        # Find all {variable} patterns
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)
        
        return list(set(matches))
    
    def reload_definitions(self):
        """Reload agent definitions from configuration."""
        self.agent_definitions.clear()
        config.reload()
        self._load_agent_definitions()
        logging.info("Agent definitions reloaded")


# Global agent manager instance
agent_manager = AgentManager()