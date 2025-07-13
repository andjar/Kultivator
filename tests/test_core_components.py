"""
Unit tests for core Kultivator components.

Tests non-AI components like configuration management, database operations,
data models, and utility functions.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from kultivator.config import ConfigManager
from kultivator.database import DatabaseManager
from kultivator.models import CanonicalBlock, Entity, TriageResult
from kultivator.agents.registry import AgentRegistry, AgentConfig
from kultivator.importers.logseq_edn import LogseqEDNImporter


class TestConfigManager(unittest.TestCase):
    """Test configuration management functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_config_creation_with_defaults(self):
        """Test config manager falls back to defaults when file missing."""
        config = ConfigManager(str(self.config_path))
        
        # Should use default values
        self.assertEqual(config.ollama_host, "http://localhost:11434")
        self.assertEqual(config.model_name, "gemma3")
        self.assertEqual(config.wiki_directory, "wiki")
        self.assertIsInstance(config.entity_directories, dict)
    
    def test_config_loading_from_file(self):
        """Test loading configuration from YAML file."""
        # Create test config file
        test_config = """
ai:
  ollama_host: "http://test:11434"
  model: "test-model"
  timeout: 60.0

paths:
  wiki_dir: "test-wiki"
  
wiki:
  entity_directories:
    person: "TestPeople"
    project: "TestProjects"
"""
        with open(self.config_path, 'w') as f:
            f.write(test_config)
        
        config = ConfigManager(str(self.config_path))
        
        # Should load values from file
        self.assertEqual(config.ollama_host, "http://test:11434")
        self.assertEqual(config.model_name, "test-model")
        self.assertEqual(config.get("ai.timeout"), 60.0)
        self.assertEqual(config.wiki_directory, "test-wiki")
        self.assertEqual(config.entity_directories["person"], "TestPeople")
    
    def test_dot_notation_access(self):
        """Test accessing config values with dot notation."""
        config = ConfigManager(str(self.config_path))  # Uses defaults
        
        # Test nested access
        self.assertEqual(config.get("ai.model"), "gemma3")
        self.assertEqual(config.get("paths.wiki_dir"), "wiki")
        self.assertEqual(config.get("nonexistent.key", "default"), "default")
    
    def test_config_reload(self):
        """Test configuration reloading."""
        # Create initial config
        with open(self.config_path, 'w') as f:
            f.write("ai:\n  model: 'model1'")
        
        config = ConfigManager(str(self.config_path))
        self.assertEqual(config.model_name, "model1")
        
        # Update config file
        with open(self.config_path, 'w') as f:
            f.write("ai:\n  model: 'model2'")
        
        config.reload()
        self.assertEqual(config.model_name, "model2")


class TestDataModels(unittest.TestCase):
    """Test data model validation and functionality."""
    
    def test_canonical_block_creation(self):
        """Test CanonicalBlock model creation and validation."""
        block = CanonicalBlock(
            block_id="test-123",
            source_ref="test.md",
            content="Test content",
            children=[]
        )
        
        self.assertEqual(block.block_id, "test-123")
        self.assertEqual(block.source_ref, "test.md")
        self.assertEqual(block.content, "Test content")
        self.assertEqual(len(block.children), 0)
    
    def test_canonical_block_with_children(self):
        """Test CanonicalBlock with nested children."""
        child_block = CanonicalBlock(
            block_id="child-456",
            source_ref="test.md", 
            content="Child content",
            children=[]
        )
        
        parent_block = CanonicalBlock(
            block_id="parent-123",
            source_ref="test.md",
            content="Parent content", 
            children=[child_block]
        )
        
        self.assertEqual(len(parent_block.children), 1)
        self.assertEqual(parent_block.children[0].block_id, "child-456")
    
    def test_entity_creation(self):
        """Test Entity model creation."""
        entity = Entity(
            name="Test Entity",
            entity_type="person",
            wiki_path="wiki/People/Test_Entity.md"
        )
        
        self.assertEqual(entity.name, "Test Entity")
        self.assertEqual(entity.entity_type, "person")
        self.assertEqual(entity.wiki_path, "wiki/People/Test_Entity.md")
    
    def test_triage_result_creation(self):
        """Test TriageResult model creation."""
        entities = [
            Entity(name="John Doe", entity_type="person", wiki_path=None),
            Entity(name="Project X", entity_type="project", wiki_path=None)
        ]
        
        result = TriageResult(
            entities=entities,
            summary="Test summary"
        )
        
        self.assertEqual(len(result.entities), 2)
        self.assertEqual(result.summary, "Test summary")
        self.assertEqual(result.entities[0].name, "John Doe")


class TestAgentRegistry(unittest.TestCase):
    """Test agent registry functionality."""
    
    def setUp(self):
        """Set up test registry."""
        self.registry = AgentRegistry()
    
    def test_default_agents_registered(self):
        """Test that default agents are registered."""
        agents = self.registry.list_agents()
        
        self.assertIn("triage", agents)
        self.assertIn("synthesizer_create", agents)
        self.assertIn("synthesizer_merge", agents)
    
    def test_agent_retrieval(self):
        """Test retrieving agent configurations."""
        triage_config = self.registry.get_agent("triage")
        
        self.assertIsNotNone(triage_config)
        if triage_config:  # Type guard for linter
            self.assertEqual(triage_config.name, "triage")
            self.assertIn("information clerk", triage_config.system_prompt.lower())
            self.assertEqual(len(triage_config.available_tools), 0)
            self.assertFalse(triage_config.requires_database)
    
    def test_custom_agent_registration(self):
        """Test registering custom agents."""
        custom_config = AgentConfig(
            name="test_agent",
            description="Test agent",
            system_prompt="Test prompt",
            available_tools=["test_tool"],
            requires_database=True
        )
        
        self.registry.register_agent(custom_config)
        
        retrieved = self.registry.get_agent("test_agent")
        self.assertIsNotNone(retrieved)
        if retrieved:  # Type guard for linter
            self.assertEqual(retrieved.name, "test_agent")
            self.assertEqual(retrieved.description, "Test agent")
            self.assertIn("test_tool", retrieved.available_tools)
    
    def test_agents_by_tool(self):
        """Test finding agents by tool."""
        # Synthesizer agents should have database tools
        agents_with_list_entities = self.registry.get_agents_by_tool("list_entities")
        
        self.assertIn("synthesizer_create", agents_with_list_entities)
        self.assertIn("synthesizer_merge", agents_with_list_entities)
        self.assertNotIn("triage", agents_with_list_entities)


class TestDatabaseManager(unittest.TestCase):
    """Test database management functionality."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        
    def tearDown(self):
        """Clean up test database."""
        if self.db_path.exists():
            self.db_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database creation and table initialization."""
        with DatabaseManager(str(self.db_path)) as db:
            db.initialize_database()
            
            # Check that database file was created
            self.assertTrue(self.db_path.exists())
            
            # Check that database connection exists
            self.assertIsNotNone(db.connection)
            if db.connection:  # Type guard for linter
                # Basic smoke test - database is functional
                # DuckDB uses different system tables than SQLite
                self.assertTrue(hasattr(db.connection, 'execute'))
    
    def test_entity_operations(self):
        """Test entity CRUD operations."""
        with DatabaseManager(str(self.db_path)) as db:
            db.initialize_database()
            
            # Create test entity
            entity = Entity(
                name="Test Person",
                entity_type="person",
                wiki_path="wiki/People/Test_Person.md"
            )
            
            # Test adding entity
            success = db.add_entity(entity)
            self.assertTrue(success)
            
            # Test retrieving entity
            retrieved = db.get_entity("Test Person")
            self.assertIsNotNone(retrieved)
            if retrieved:  # Type guard for linter
                self.assertEqual(retrieved.name, "Test Person")
                self.assertEqual(retrieved.entity_type, "person")
            
            # Test listing entities
            all_entities = db.list_entities()
            self.assertEqual(len(all_entities), 1)
            self.assertEqual(all_entities[0].name, "Test Person")
    
    def test_processed_block_operations(self):
        """Test processed block tracking."""
        with DatabaseManager(str(self.db_path)) as db:
            db.initialize_database()
            
            # Create test block
            block = CanonicalBlock(
                block_id="test-block-123",
                source_ref="test.md",
                content="Test content",
                children=[]
            )
            
            # Test adding processed block
            success = db.add_processed_block(block)
            self.assertTrue(success)
            
            # Test checking if block needs processing (should return False)
            needs_processing = db.block_needs_processing(block)
            self.assertFalse(needs_processing)
            
            # Test with modified content
            modified_block = CanonicalBlock(
                block_id="test-block-123",
                source_ref="test.md", 
                content="Modified content",  # Different content
                children=[]
            )
            
            needs_processing = db.block_needs_processing(modified_block)
            self.assertTrue(needs_processing)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_safe_filename_generation(self):
        """Test safe filename generation from entity names."""
        # This tests the logic in get_entity_wiki_path
        from main import get_entity_wiki_path
        from kultivator.config import config
        
        # Test normal name
        entity = Entity(name="John Doe", entity_type="person", wiki_path=None)
        path = get_entity_wiki_path(entity)
        expected = f"{config.wiki_directory}/People/John_Doe.md"
        self.assertEqual(path, expected)
        
        # Test name with special characters
        entity = Entity(name="John/Doe\\Test", entity_type="person", wiki_path=None)
        path = get_entity_wiki_path(entity)
        self.assertIn("John_Doe_Test", path)
        self.assertNotIn("/", path.split("/")[-1])  # No slashes in filename
        self.assertNotIn("\\", path.split("/")[-1])  # No backslashes in filename
    
    def test_entity_type_mapping(self):
        """Test entity type to directory mapping."""
        from main import get_entity_wiki_path
        from kultivator.config import config
        
        # Test known types
        person = Entity(name="Test", entity_type="person", wiki_path=None)
        project = Entity(name="Test", entity_type="project", wiki_path=None)
        unknown = Entity(name="Test", entity_type="unknown", wiki_path=None)
        
        person_path = get_entity_wiki_path(person)
        project_path = get_entity_wiki_path(project)
        unknown_path = get_entity_wiki_path(unknown)
        
        self.assertIn("/People/", person_path)
        self.assertIn("/Projects/", project_path)
        self.assertIn("/Other/", unknown_path)  # Default for unknown types


class TestLogseqRealData(unittest.TestCase):
    def test_real_logseq_hierarchy(self):
        """Test that real LogSeq data import skips empty pages and preserves top-level hierarchy."""
        # Path to real LogSeq export
        test_dir = Path(__file__).parent
        logseq_path = test_dir / "test_logseq_data"

        if not logseq_path.exists():
            self.skipTest(f"Test data directory not found: {logseq_path}")

        importer = LogseqEDNImporter(str(logseq_path))
        blocks = importer.get_all_blocks()
        # 1. Ensure only the two journal pages with content are present
        journal_titles = set()
        for block in blocks:
            # Print for manual inspection
            print(f"[TEST] Top-level block: {block.block_id} | {block.content[:60]} | children: {len(block.children)}")
            # Check for journal pages by looking for a date in the source_ref or content
            if "20250712" in block.source_ref or "20250712" in block.content:
                journal_titles.add("20250712")
            if "20250713" in block.source_ref or "20250713" in block.content:
                journal_titles.add("20250713")
        self.assertEqual(len(blocks), 2, f"Expected 2 top-level journal pages, got {len(blocks)}")
        self.assertEqual(journal_titles, {"20250712", "20250713"}, f"Expected journal pages 20250712 and 20250713, got {journal_titles}")
        # 2. Ensure no child block appears as a top-level block
        child_ids = set()
        def collect_child_ids(b):
            for c in b.children:
                child_ids.add(c.block_id)
                collect_child_ids(c)
        for block in blocks:
            collect_child_ids(block)
        all_ids = set(b.block_id for b in blocks)
        self.assertTrue(child_ids.isdisjoint(all_ids), "Some child blocks appear as top-level blocks!")
        # 4. Print a summary for manual inspection
        print(f"\n[TEST] Top-level blocks loaded: {len(blocks)}")
        for block in blocks:
            print(f"  - {block.block_id}: {block.content[:60]} (children: {len(block.children)})")


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2) 