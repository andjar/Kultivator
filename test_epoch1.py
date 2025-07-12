#!/usr/bin/env python3
"""
Test script for EPOCH 1 with mocked AI responses.

This demonstrates the complete functionality without requiring Ollama to be running.
"""

import logging
import sys
from pathlib import Path

from kultivator.models import Entity, TriageResult
from kultivator.importers import MockImporter
from kultivator.database import DatabaseManager


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def mock_triage_agent(block):
    """
    Mock triage agent that extracts entities without calling Ollama.
    
    This simulates what the real agent would do with a working LLM.
    """
    content = block.content.lower()
    entities = []
    
    # Extract entities from [[Entity Name]] patterns
    import re
    entity_matches = re.findall(r'\[\[([^\]]+)\]\]', block.content)
    
    for entity_name in entity_matches:
        # Simple heuristic classification
        entity_type = "other"
        
        # People (names with spaces, common person indicators)
        if any(word in entity_name.lower() for word in ['doe', 'smith', 'johnson', 'hunt']):
            entity_type = "person"
        # Places (geographic indicators)
        elif any(word in entity_name.lower() for word in ['city', 'park', 'downtown', 'starbucks']):
            entity_type = "place"
        # Projects (project indicators)
        elif any(word in entity_name.lower() for word in ['project', 'integration']):
            entity_type = "project"
        # Companies (business indicators)
        elif any(word in entity_name.lower() for word in ['corporation', 'acme']):
            entity_type = "company"
        # Books (title patterns)
        elif any(word in entity_name.lower() for word in ['programmer', 'pragmatic']):
            entity_type = "book"
            
        entities.append(Entity(
            name=entity_name,
            entity_type=entity_type,
            wiki_path=None
        ))
    
    # Generate a summary
    summary = f"Content from {block.source_ref} containing {len(entities)} entities"
    
    return TriageResult(entities=entities, summary=summary)


def get_entity_wiki_path(entity):
    """Get wiki path for an entity."""
    type_mapping = {
        'person': 'People',
        'project': 'Projects', 
        'place': 'Places',
        'company': 'Companies',
        'book': 'Books'
    }
    
    wiki_subdir = type_mapping.get(entity.entity_type.lower(), 'Other')
    safe_name = entity.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-')
    
    return f"wiki/{wiki_subdir}/{safe_name}.md"


def create_placeholder_wiki_file(entity, wiki_path):
    """Create placeholder wiki file."""
    file_path = Path(wiki_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    placeholder_content = f"""# {entity.name}

*Type: {entity.entity_type.title()}*

*This page was generated automatically by Kultivator.*

---

## Summary

*Information about {entity.name} will be populated here.*

## Details

## Related Notes

"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(placeholder_content)
        
    logging.info(f"Created wiki file: {wiki_path}")


def main():
    """Test the complete EPOCH 1 pipeline with mocked responses."""
    setup_logging()
    
    logging.info("=== KULTIVATOR EPOCH 1 TEST (with mocked AI) ===")
    
    # Clean up any existing test database
    test_db_path = "test_kultivator.db"
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()
        
    # Initialize components
    importer = MockImporter()
    
    with DatabaseManager(test_db_path) as db:
        db.initialize_database()
        logging.info("Test database initialized")
        
        blocks = importer.get_all_blocks()
        logging.info(f"Retrieved {len(blocks)} test blocks")
        
        entity_count = 0
        
        # Process each block with mocked triage
        for i, block in enumerate(blocks, 1):
            logging.info(f"\nProcessing block {i}/{len(blocks)}: {block.source_ref}")
            logging.info(f"Content: {block.content}")
            
            # Mock triage agent
            triage_result = mock_triage_agent(block)
            
            logging.info(f"Found {len(triage_result.entities)} entities")
            logging.info(f"Summary: {triage_result.summary}")
            
            # Process discovered entities
            for entity in triage_result.entities:
                logging.info(f"  Entity: {entity.name} ({entity.entity_type})")
                
                # Check if already exists
                existing = db.get_entity(entity.name)
                if existing:
                    logging.info(f"    Already exists in database")
                    continue
                    
                # Set wiki path
                wiki_path = get_entity_wiki_path(entity)
                entity.wiki_path = wiki_path
                
                # Add to database
                success = db.add_entity(entity)
                if success:
                    entity_count += 1
                    logging.info(f"    Added to database: {wiki_path}")
                    
                    # Create wiki file
                    create_placeholder_wiki_file(entity, wiki_path)
                    
        logging.info(f"\n=== RESULTS ===")
        logging.info(f"Processed {entity_count} new entities")
        
        # Show summary
        all_entities = db.list_entities()
        entity_types = {}
        for entity in all_entities:
            entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1
            
        logging.info("Entities by type:")
        for entity_type, count in entity_types.items():
            logging.info(f"  {entity_type}: {count}")
            
        logging.info("\nCreated files:")
        for entity in all_entities:
            logging.info(f"  {entity.wiki_path}")
            
        print("\n" + "="*60)
        print("🎉 EPOCH 1 TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nResults:")
        print(f"- {len(blocks)} mock blocks processed")
        print(f"- {entity_count} entities discovered and stored")
        print(f"- {len(all_entities)} total entities in database")
        print(f"- Wiki files created in /wiki subdirectories")
        print(f"\nDatabase: {test_db_path}")
        print("Wiki files: Check wiki/ directory")


if __name__ == "__main__":
    main() 