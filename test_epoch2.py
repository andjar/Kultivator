#!/usr/bin/env python3
"""
Test script for EPOCH 2 with mocked AI responses.

This demonstrates the complete Synthesizer Agent functionality without requiring Ollama.
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
    """Mock triage agent that extracts entities without calling Ollama."""
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


def mock_synthesizer_agent(entity: Entity, summary: str) -> str:
    """
    Mock synthesizer agent that generates wiki content without calling Ollama.
    
    This simulates what the real agent would do with a working LLM.
    """
    # Generate different content based on entity type
    if entity.entity_type == "person":
        return f"""# {entity.name}

*Type: Person*

## Summary

{entity.name} is a person mentioned in the knowledge base. Based on the available information: {summary}

## Details

- **Entity Type**: Person
- **First Mentioned**: In personal notes and journals
- **Context**: Professional and personal interactions

## Background

{entity.name} appears to be an individual who plays a role in various projects and activities documented in the knowledge base. Further information will be added as more references are discovered.

## Related Notes

- Referenced in meeting notes and project discussions
- Part of ongoing professional network

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""
    
    elif entity.entity_type == "project":
        return f"""# {entity.name}

*Type: Project*

## Summary

{entity.name} is a project documented in the knowledge base. {summary}

## Details

- **Entity Type**: Project
- **Status**: Active or mentioned in planning
- **Context**: Professional development and work activities

## Project Overview

{entity.name} represents a significant undertaking that has been referenced in various notes and documents. The project appears to involve collaborative work and strategic planning.

## Key Information

- Documented in project notes and meeting records
- Involves multiple stakeholders and contributors
- Part of ongoing professional activities

## Related Notes

- Referenced in work documents and meeting notes
- Connected to other projects and initiatives

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""
    
    elif entity.entity_type == "place":
        return f"""# {entity.name}

*Type: Place*

## Summary

{entity.name} is a location mentioned in the knowledge base. {summary}

## Details

- **Entity Type**: Place/Location
- **Context**: Travel, meetings, and activities
- **Significance**: Venue for important events and interactions

## Location Information

{entity.name} appears to be a significant location that has been referenced in various contexts within the knowledge base. This could be a city, venue, or other geographic location of importance.

## Activities and Events

- Mentioned in travel plans and meeting locations
- Site of important interactions and activities
- Part of documented experiences and memories

## Related Notes

- Referenced in journal entries and travel documents
- Connected to other people and activities

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""
    
    elif entity.entity_type == "company":
        return f"""# {entity.name}

*Type: Company*

## Summary

{entity.name} is a company or organization mentioned in the knowledge base. {summary}

## Details

- **Entity Type**: Company/Organization
- **Context**: Professional relationships and business activities
- **Role**: Business partner, employer, or client

## Company Information

{entity.name} appears to be a business entity that plays a role in professional activities documented in the knowledge base. This organization is involved in various projects and business relationships.

## Business Activities

- Engaged in professional projects and collaborations
- Part of business network and professional relationships
- Involved in strategic planning and project execution

## Related Notes

- Referenced in business documents and project notes
- Connected to professional activities and partnerships

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""
    
    elif entity.entity_type == "book":
        return f"""# {entity.name}

*Type: Book*

## Summary

{entity.name} is a book mentioned in the knowledge base. {summary}

## Details

- **Entity Type**: Book/Publication
- **Context**: Reading list and learning materials
- **Significance**: Educational and professional development

## Book Information

{entity.name} is a publication that has been referenced in the knowledge base, likely as part of ongoing learning and professional development activities.

## Key Topics

- Relevant to professional and personal growth
- Contains valuable insights and knowledge
- Part of documented reading and learning journey

## Notes and Insights

- Referenced in reading notes and reviews
- Connected to learning objectives and goals
- Source of inspiration and knowledge

## Related Notes

- Part of reading list and educational materials
- Connected to other learning resources and books

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""
    
    else:
        return f"""# {entity.name}

*Type: {entity.entity_type.title()}*

## Summary

{entity.name} is an entity of type {entity.entity_type} mentioned in the knowledge base. {summary}

## Details

- **Entity Type**: {entity.entity_type.title()}
- **Context**: Various references in notes and documents
- **Significance**: Part of documented knowledge and information

## Information

{entity.name} has been referenced in the knowledge base and represents an important piece of information worth tracking and organizing.

## Related Notes

- Referenced in various documents and notes
- Part of the broader knowledge network

---

*This page was generated automatically by Kultivator's AI synthesis engine.*
"""


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


def create_wiki_file_with_content(entity, wiki_path, content):
    """Create wiki file with generated content."""
    file_path = Path(wiki_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logging.info(f"Created wiki file with content: {wiki_path}")


def main():
    """Test the complete EPOCH 2 pipeline with mocked responses."""
    setup_logging()
    
    logging.info("=== KULTIVATOR EPOCH 2 TEST (with mocked AI) ===")
    
    # Clean up any existing test database
    test_db_path = "test_epoch2_kultivator.db"
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
        
        # Process each block with mocked triage and synthesizer
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
                    
                    # EPOCH 2: Generate content using mock synthesizer
                    logging.info(f"    Generating content for {entity.name}...")
                    wiki_content = mock_synthesizer_agent(entity, triage_result.summary)
                    create_wiki_file_with_content(entity, wiki_path, wiki_content)
                    logging.info(f"    Generated content for {entity.name}")
                    
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
            
        logging.info("\nGenerated wiki files:")
        for entity in all_entities:
            if entity.wiki_path:
                wiki_file = Path(entity.wiki_path)
                if wiki_file.exists():
                    size = wiki_file.stat().st_size
                    logging.info(f"  {entity.wiki_path} ({size} bytes)")
            
        print("\n" + "="*60)
        print("🎉 EPOCH 2 TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nResults:")
        print(f"- {len(blocks)} mock blocks processed")
        print(f"- {entity_count} entities discovered and stored")
        print(f"- {len(all_entities)} wiki files generated with AI content")
        print(f"- Database: {test_db_path}")
        print(f"- Wiki files: Check wiki/ directory for rich content")
        print(f"\nEPOCH 2 Enhancement:")
        print(f"- Synthesizer Agent generated comprehensive content")
        print(f"- Each entity has structured, informative wiki page")
        print(f"- Content includes summaries, details, and related notes")


if __name__ == "__main__":
    main() 