"""
Agent Registry for Kultivator.

This module defines the registry of all available AI agents, their configurations,
prompts, and available tools. This centralized registry makes it easy to add
new agents and modify existing ones.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """
    Configuration for an AI agent.
    """
    name: str
    description: str
    system_prompt: str
    available_tools: List[str]
    requires_database: bool = True
    timeout: float = 30.0


class AgentRegistry:
    """
    Registry of all available AI agents and their configurations.
    """
    
    def __init__(self):
        """Initialize the agent registry with default agents."""
        self._agents: Dict[str, AgentConfig] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register the default agents used by Kultivator."""
        
        # Triage Agent - extracts entities and summarizes content
        self.register_agent(AgentConfig(
            name="triage",
            description="Extracts entities and summarizes content from blocks",
            system_prompt="""You are an information clerk. Read this data block and identify all key entities (people, projects, etc.) and summarize the core fact. Output only valid JSON.

Your task:
1. Identify entities mentioned in the content (look for [[Entity Name]] patterns and other clear references)
2. Classify each entity type as one of: person, project, place, company, book, other
3. Provide a concise summary of the key information

Output format (JSON only, no explanations):
{
  "entities": [
    {"name": "Entity Name", "type": "person|project|place|company|book|other"}
  ],
  "summary": "Brief summary of the core information"
}""",
            available_tools=[],
            requires_database=False
        ))
        
        # Synthesizer Agent - generates and updates wiki content
        self.register_agent(AgentConfig(
            name="synthesizer_create",
            description="Creates new wiki content for entities",
            system_prompt="""You are a meticulous archivist with access to a rich knowledge base. Your task is to create a comprehensive wiki page for an entity based on the provided information. 

Write a complete, well-structured Markdown page that includes:
1. A clear title using the entity name
2. Basic information about the entity type
3. A summary section with key details
4. A details section for additional information
5. Proper Markdown formatting
6. Cross-references to related entities where appropriate

Keep the content informative but concise. Use proper Markdown headers, lists, and formatting. 
Write in a neutral, encyclopedic tone suitable for a personal knowledge base.
Use the knowledge base context to identify potential relationships and cross-references.

Do not include any metadata or front matter - just the Markdown content.""",
            available_tools=["list_entities", "get_entity_context"],
            requires_database=True
        ))
        
        # Synthesizer Agent (Merge mode) - updates existing wiki content
        self.register_agent(AgentConfig(
            name="synthesizer_merge",
            description="Updates existing wiki content with new information",
            system_prompt="""You are a meticulous archivist with access to a rich knowledge base. Your task is to update an existing wiki page with new information while preserving the existing structure and content.

Guidelines for content merging:
1. Preserve the existing title and overall structure
2. Add new information to appropriate sections
3. If new information contradicts existing content, note both versions
4. Add specific details (dates, names, numbers) to a "Details" section
5. Maintain consistent Markdown formatting
6. Keep a neutral, encyclopedic tone
7. Add an "Updates" section if significant new information is added
8. Use context about related entities to create meaningful cross-references

Do not duplicate existing information. Focus on integrating new details seamlessly.
Do not include any metadata or front matter - just the updated Markdown content.""",
            available_tools=["list_entities", "get_entity_context"],
            requires_database=True
        ))
    
    def register_agent(self, config: AgentConfig) -> None:
        """
        Register a new agent configuration.
        
        Args:
            config: The agent configuration to register
        """
        self._agents[config.name] = config
    
    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """
        Get an agent configuration by name.
        
        Args:
            name: The name of the agent
            
        Returns:
            The agent configuration, or None if not found
        """
        return self._agents.get(name)
    
    def list_agents(self) -> List[str]:
        """
        Get a list of all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self._agents.keys())
    
    def get_agents_by_tool(self, tool_name: str) -> List[str]:
        """
        Get agents that have access to a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            List of agent names that can use the tool
        """
        return [
            name for name, config in self._agents.items()
            if tool_name in config.available_tools
        ]


# Global agent registry instance
agent_registry = AgentRegistry() 