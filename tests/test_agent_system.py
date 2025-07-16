"""
Tests for the enhanced AI agent system.

This module tests the new configuration-based agents, template system,
and specialized agents like task_manager and travel_planner.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from kultivator.agents.manager import AgentManager, AgentDefinition
from kultivator.agents.registry import AgentRegistry, AgentConfig
from kultivator.agents.runner import AgentRunner
from kultivator.config import ConfigManager
from kultivator.models import Entity, CanonicalBlock


class TestAgentManager(unittest.TestCase):
    """Test the AgentManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create test configuration with agent definitions
        test_config = """
agents:
  max_retries: 3
  enable_tools: true
  context_limit: 5
  definitions:
    test_agent:
      description: "Test agent for unit testing"
      system_prompt: "You are a test agent."
      user_prompt_template: "Process this: {content} for entity {entity_name}"
      available_tools: ["list_entities"]
      requires_database: true
      timeout: 30.0
    
    simple_agent:
      description: "Simple agent with minimal configuration"
      system_prompt: "You are simple."
      user_prompt_template: "Simple task: {task}"
      available_tools: []
      requires_database: false
"""
        
        with open(self.config_path, 'w') as f:
            f.write(test_config)
            
        # Create config manager with test config
        self.config_manager = ConfigManager(str(self.config_path))
        
    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_agent_definition_creation(self):
        """Test creating AgentDefinition objects."""
        agent_def = AgentDefinition(
            name="test",
            description="Test agent",
            system_prompt="You are a test agent.",
            user_prompt_template="Process: {content}",
            available_tools=["list_entities"],
            requires_database=True,
            timeout=30.0
        )
        
        self.assertEqual(agent_def.name, "test")
        self.assertEqual(agent_def.description, "Test agent")
        self.assertEqual(agent_def.system_prompt, "You are a test agent.")
        self.assertEqual(agent_def.user_prompt_template, "Process: {content}")
        self.assertEqual(agent_def.available_tools, ["list_entities"])
        self.assertTrue(agent_def.requires_database)
        self.assertEqual(agent_def.timeout, 30.0)
    
    def test_agent_definition_to_config(self):
        """Test converting AgentDefinition to AgentConfig."""
        agent_def = AgentDefinition(
            name="test",
            description="Test agent",
            system_prompt="You are a test agent.",
            user_prompt_template="Process: {content}",
            available_tools=["list_entities"],
            requires_database=True,
            timeout=30.0
        )
        
        config = agent_def.to_agent_config()
        
        self.assertIsInstance(config, AgentConfig)
        self.assertEqual(config.name, "test")
        self.assertEqual(config.description, "Test agent")
        self.assertEqual(config.system_prompt, "You are a test agent.")
        self.assertEqual(config.available_tools, ["list_entities"])
        self.assertTrue(config.requires_database)
        self.assertEqual(config.timeout, 30.0)
    
    @patch('kultivator.agents.manager.config')
    def test_agent_manager_initialization(self, mock_config):
        """Test AgentManager initialization."""
        mock_config.agent_definitions = {
            "test_agent": {
                "description": "Test agent",
                "system_prompt": "You are a test agent.",
                "user_prompt_template": "Process: {content}",
                "available_tools": ["list_entities"],
                "requires_database": True,
                "timeout": 30.0
            }
        }
        
        agent_manager = AgentManager()
        
        self.assertIn("test_agent", agent_manager.agent_definitions)
        agent_def = agent_manager.get_agent_definition("test_agent")
        self.assertIsNotNone(agent_def)
        self.assertEqual(agent_def.name, "test_agent")
        self.assertEqual(agent_def.description, "Test agent")
    
    @patch('kultivator.agents.manager.config')
    def test_agent_manager_list_agents(self, mock_config):
        """Test listing agents."""
        mock_config.agent_definitions = {
            "agent1": {
                "description": "Agent 1",
                "system_prompt": "You are agent 1.",
                "user_prompt_template": "Process: {content}",
            },
            "agent2": {
                "description": "Agent 2",
                "system_prompt": "You are agent 2.",
                "user_prompt_template": "Process: {content}",
            }
        }
        
        agent_manager = AgentManager()
        agents = agent_manager.list_agents()
        
        self.assertEqual(len(agents), 2)
        self.assertIn("agent1", agents)
        self.assertIn("agent2", agents)
    
    @patch('kultivator.agents.manager.config')
    def test_agent_manager_get_agents_by_tool(self, mock_config):
        """Test getting agents by tool."""
        mock_config.agent_definitions = {
            "agent1": {
                "description": "Agent 1",
                "system_prompt": "You are agent 1.",
                "user_prompt_template": "Process: {content}",
                "available_tools": ["list_entities", "get_entity_context"]
            },
            "agent2": {
                "description": "Agent 2",
                "system_prompt": "You are agent 2.",
                "user_prompt_template": "Process: {content}",
                "available_tools": ["list_entities"]
            },
            "agent3": {
                "description": "Agent 3",
                "system_prompt": "You are agent 3.",
                "user_prompt_template": "Process: {content}",
                "available_tools": []
            }
        }
        
        agent_manager = AgentManager()
        
        # Test getting agents with list_entities tool
        agents_with_list = agent_manager.get_agents_by_tool("list_entities")
        self.assertEqual(len(agents_with_list), 2)
        self.assertIn("agent1", agents_with_list)
        self.assertIn("agent2", agents_with_list)
        
        # Test getting agents with get_entity_context tool
        agents_with_context = agent_manager.get_agents_by_tool("get_entity_context")
        self.assertEqual(len(agents_with_context), 1)
        self.assertIn("agent1", agents_with_context)
        
        # Test getting agents with non-existent tool
        agents_with_unknown = agent_manager.get_agents_by_tool("unknown_tool")
        self.assertEqual(len(agents_with_unknown), 0)
    
    @patch('kultivator.agents.manager.config')
    def test_render_user_prompt(self, mock_config):
        """Test rendering user prompts with templates."""
        mock_config.agent_definitions = {
            "test_agent": {
                "description": "Test agent",
                "system_prompt": "You are a test agent.",
                "user_prompt_template": "Process this content: {content} for entity {entity_name} of type {entity_type}",
                "available_tools": [],
                "requires_database": False
            }
        }
        
        agent_manager = AgentManager()
        
        # Test successful rendering
        rendered = agent_manager.render_user_prompt(
            "test_agent",
            content="Test content",
            entity_name="Test Entity",
            entity_type="person"
        )
        
        expected = "Process this content: Test content for entity Test Entity of type person"
        self.assertEqual(rendered, expected)
        
        # Test missing variable
        with self.assertRaises(ValueError):
            agent_manager.render_user_prompt(
                "test_agent",
                content="Test content"
                # Missing entity_name and entity_type
            )
        
        # Test non-existent agent
        with self.assertRaises(ValueError):
            agent_manager.render_user_prompt(
                "non_existent_agent",
                content="Test content"
            )
    
    @patch('kultivator.agents.manager.config')
    def test_get_system_prompt(self, mock_config):
        """Test getting system prompts."""
        mock_config.agent_definitions = {
            "test_agent": {
                "description": "Test agent",
                "system_prompt": "You are a test agent with special instructions.",
                "user_prompt_template": "Process: {content}",
                "available_tools": [],
                "requires_database": False
            }
        }
        
        agent_manager = AgentManager()
        
        # Test getting system prompt
        system_prompt = agent_manager.get_system_prompt("test_agent")
        self.assertEqual(system_prompt, "You are a test agent with special instructions.")
        
        # Test non-existent agent
        with self.assertRaises(ValueError):
            agent_manager.get_system_prompt("non_existent_agent")
    
    @patch('kultivator.agents.manager.config')
    def test_validate_agent_definition(self, mock_config):
        """Test agent definition validation."""
        mock_config.agent_definitions = {
            "valid_agent": {
                "description": "Valid agent",
                "system_prompt": "You are a valid agent.",
                "user_prompt_template": "Process: {content}",
                "available_tools": ["list_entities"],
                "requires_database": True,
                "timeout": 30.0
            },
            "invalid_agent": {
                "description": "Invalid agent",
                "system_prompt": "",  # Empty system prompt
                "user_prompt_template": "Process: {content}",
                "available_tools": ["unknown_tool"],  # Unknown tool
                "requires_database": True,
                "timeout": -5.0  # Invalid timeout
            }
        }
        
        agent_manager = AgentManager()
        
        # Test valid agent
        valid_results = agent_manager.validate_agent_definition("valid_agent")
        self.assertTrue(valid_results['valid'])
        self.assertEqual(len(valid_results['errors']), 0)
        
        # Test invalid agent
        invalid_results = agent_manager.validate_agent_definition("invalid_agent")
        self.assertFalse(invalid_results['valid'])
        self.assertGreater(len(invalid_results['errors']), 0)
        
        # Test non-existent agent
        nonexistent_results = agent_manager.validate_agent_definition("non_existent_agent")
        self.assertFalse(nonexistent_results['valid'])
        self.assertIn("not found", nonexistent_results['errors'][0])


class TestAgentRunnerWithNewSystem(unittest.TestCase):
    """Test AgentRunner with the new agent system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_agent_manager = Mock()
        
        # Create test entity and block
        self.test_entity = Entity(
            name="Test Entity",
            entity_type="person",
            wiki_path="wiki/People/Test_Entity.md"
        )
        
        self.test_block = CanonicalBlock(
            block_id="test-block-1",
            content="Test block content about Test Entity",
            source_ref="test-source",
            created_at=1234567890,
            updated_at=1234567890
        )
    
    @patch('kultivator.agents.runner.httpx.Client')
    def test_run_triage_agent_with_templates(self, mock_client):
        """Test running triage agent with template system."""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": '{"entities": [{"name": "Test Entity", "type": "person"}], "summary": "Test summary"}'
        }
        mock_client.return_value.post.return_value = mock_response
        
        # Mock agent manager
        self.mock_agent_manager.get_system_prompt.return_value = "You are a test triage agent."
        self.mock_agent_manager.render_user_prompt.return_value = "Analyze this: Test block content"
        
        # Create agent runner
        runner = AgentRunner(
            database_manager=self.mock_db,
            agent_manager=self.mock_agent_manager
        )
        
        # Run triage agent
        result = runner.run_triage_agent(self.test_block)
        
        # Verify results
        self.assertEqual(len(result.entities), 1)
        self.assertEqual(result.entities[0].name, "Test Entity")
        self.assertEqual(result.entities[0].entity_type, "person")
        self.assertEqual(result.summary, "Test summary")
        
        # Verify agent manager was called
        self.mock_agent_manager.get_system_prompt.assert_called_with("triage")
        self.mock_agent_manager.render_user_prompt.assert_called_once()
    
    @patch('kultivator.agents.runner.httpx.Client')
    def test_run_specialized_agent(self, mock_client):
        """Test running specialized agents."""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "# Test Entity\n\nSpecialized content for task management."
        }
        mock_client.return_value.post.return_value = mock_response
        
        # Mock agent manager
        self.mock_agent_manager.get_system_prompt.return_value = "You are a task management agent."
        self.mock_agent_manager.render_user_prompt.return_value = "Organize tasks for: Test Entity"
        
        # Create agent runner
        runner = AgentRunner(
            database_manager=self.mock_db,
            agent_manager=self.mock_agent_manager
        )
        
        # Run specialized agent
        result = runner.run_specialized_agent(
            "task_manager",
            self.test_entity,
            "Test summary",
            self.test_block
        )
        
        # Verify results
        self.assertIn("Test Entity", result)
        self.assertIn("Specialized content for task management", result)
        
        # Verify agent manager was called
        self.mock_agent_manager.get_system_prompt.assert_called_with("task_manager")
        self.mock_agent_manager.render_user_prompt.assert_called_once()
    
    def test_run_specialized_agent_not_found(self):
        """Test running non-existent specialized agent."""
        # Mock agent manager to raise error
        self.mock_agent_manager.get_system_prompt.side_effect = ValueError("Agent not found")
        
        # Create agent runner
        runner = AgentRunner(
            database_manager=self.mock_db,
            agent_manager=self.mock_agent_manager
        )
        
        # Run specialized agent - should raise error
        with self.assertRaises(ValueError):
            runner.run_specialized_agent(
                "non_existent_agent",
                self.test_entity,
                "Test summary",
                self.test_block
            )


class TestConfigurationBasedAgents(unittest.TestCase):
    """Test the configuration-based agent system integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create test configuration with specialized agents
        test_config = """
agents:
  max_retries: 3
  enable_tools: true
  context_limit: 5
  definitions:
    task_manager:
      description: "Manages and organizes task-related information"
      system_prompt: |
        You are an expert task management assistant. Your role is to help organize, track, and manage tasks and project information from notes and blocks.
        
        Your capabilities:
        1. Extract tasks, deadlines, and priorities from content
        2. Identify project dependencies and relationships
        3. Create structured task lists and project overviews
        4. Track task status and progress
        5. Suggest task categorization and prioritization
        
        Always provide clear, actionable information formatted in Markdown.
      user_prompt_template: |
        Analyze this content for task management information:
        
        Content: {content}
        Source: {source_ref}
        Entity Name: {entity_name}
        Entity Type: {entity_type}
        
        Create a structured task management page with priorities, deadlines, and next actions.
      available_tools: ["list_entities", "get_entity_context"]
      requires_database: true
      timeout: 30.0
    
    travel_planner:
      description: "Organizes and plans travel-related information"
      system_prompt: |
        You are a travel planning expert. Your role is to organize travel information, create itineraries, and manage travel-related entities from notes and blocks.
        
        Your capabilities:
        1. Extract travel dates, destinations, and activities
        2. Create structured itineraries and travel plans
        3. Identify travel-related entities (places, accommodations, activities)
        4. Organize travel information by trip or destination
        5. Track travel expenses and bookings
        
        Always provide well-structured travel information in Markdown format.
      user_prompt_template: |
        Organize this travel-related content:
        
        Content: {content}
        Source: {source_ref}
        Entity Name: {entity_name}
        Entity Type: {entity_type}
        
        Create a comprehensive travel information page with itinerary, destinations, and activities.
      available_tools: ["list_entities", "get_entity_context"]
      requires_database: true
      timeout: 30.0
"""
        
        with open(self.config_path, 'w') as f:
            f.write(test_config)
            
    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)
    
    @patch('kultivator.agents.manager.config')
    def test_specialized_agents_loaded(self, mock_config):
        """Test that specialized agents are loaded from configuration."""
        mock_config.agent_definitions = {
            "task_manager": {
                "description": "Manages and organizes task-related information",
                "system_prompt": "You are an expert task management assistant.",
                "user_prompt_template": "Analyze this content for task management: {content}",
                "available_tools": ["list_entities", "get_entity_context"],
                "requires_database": True,
                "timeout": 30.0
            },
            "travel_planner": {
                "description": "Organizes and plans travel-related information",
                "system_prompt": "You are a travel planning expert.",
                "user_prompt_template": "Organize this travel content: {content}",
                "available_tools": ["list_entities", "get_entity_context"],
                "requires_database": True,
                "timeout": 30.0
            }
        }
        
        agent_manager = AgentManager()
        
        # Verify specialized agents are loaded
        self.assertIn("task_manager", agent_manager.agent_definitions)
        self.assertIn("travel_planner", agent_manager.agent_definitions)
        
        # Verify agent properties
        task_agent = agent_manager.get_agent_definition("task_manager")
        self.assertIsNotNone(task_agent)
        self.assertEqual(task_agent.description, "Manages and organizes task-related information")
        self.assertIn("list_entities", task_agent.available_tools)
        self.assertTrue(task_agent.requires_database)
        
        travel_agent = agent_manager.get_agent_definition("travel_planner")
        self.assertIsNotNone(travel_agent)
        self.assertEqual(travel_agent.description, "Organizes and plans travel-related information")
        self.assertIn("get_entity_context", travel_agent.available_tools)
        self.assertTrue(travel_agent.requires_database)
    
    @patch('kultivator.agents.manager.config')
    def test_agent_validation(self, mock_config):
        """Test validation of agent definitions."""
        mock_config.agent_definitions = {
            "task_manager": {
                "description": "Manages and organizes task-related information",
                "system_prompt": "You are an expert task management assistant.",
                "user_prompt_template": "Analyze this content for task management: {content} for {entity_name}",
                "available_tools": ["list_entities", "get_entity_context"],
                "requires_database": True,
                "timeout": 30.0
            }
        }
        
        agent_manager = AgentManager()
        
        # Test validation
        validation_results = agent_manager.validate_agent_definition("task_manager")
        self.assertTrue(validation_results['valid'])
        self.assertEqual(len(validation_results['errors']), 0)


if __name__ == '__main__':
    unittest.main()