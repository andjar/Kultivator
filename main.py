#!/usr/bin/env python3
"""
Kultivator - Automated Knowledge Synthesis Engine

Main entry point for the Kultivator system. This orchestrator coordinates
the entire pipeline from data import through AI processing to wiki generation.
"""

import logging
import sys
from pathlib import Path
from typing import Dict

from kultivator.models import Entity
from kultivator.importers import MockImporter
from kultivator.agents import AgentRunner
from kultivator.database import DatabaseManager


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('kultivator.log')
        ]
    )


def get_entity_wiki_path(entity: Entity) -> str:
    """
    Determine the wiki file path for an entity based on its type.
    
    Args:
        entity: The entity to get the path for
        
    Returns:
        Relative path to the entity's wiki file
    """
    # Map entity types to wiki subdirectories
    type_mapping = {
        'person': 'People',
        'project': 'Projects', 
        'place': 'Places',
        'company': 'Companies',
        'book': 'Books'
    }
    
    # Default to 'Other' for unknown types
    wiki_subdir = type_mapping.get(entity.entity_type.lower(), 'Other')
    
    # Create a safe filename from the entity name
    safe_name = entity.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    # Remove any characters that might be problematic in filenames
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-')
    
    return f"wiki/{wiki_subdir}/{safe_name}.md"


def create_placeholder_wiki_file(entity: Entity, wiki_path: str):
    """
    Create an empty placeholder wiki file for an entity.
    
    Args:
        entity: The entity to create a file for
        wiki_path: Path where the file should be created
    """
    file_path = Path(wiki_path)
    
    # Create the directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create placeholder content
    placeholder_content = f"""# {entity.name}

*Type: {entity.entity_type.title()}*

*This page is a placeholder. Content will be generated automatically.*

---

## Summary

## Details

## Related Notes

"""

    # Write the placeholder file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(placeholder_content)
        
    logging.info(f"Created placeholder wiki file: {wiki_path}")


def create_wiki_file_with_content(entity: Entity, wiki_path: str, content: str):
    """
    Create a wiki file with generated content for an entity.
    
    Args:
        entity: The entity to create a file for
        wiki_path: Path where the file should be created
        content: Generated content for the file
    """
    file_path = Path(wiki_path)
    
    # Create the directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the generated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logging.info(f"Created wiki file with generated content: {wiki_path}")


def run_epoch1_pipeline():
    """
    Execute the EPOCH 1 pipeline: mock data -> triage -> database + placeholders.
    
    This is the core testable outcome for EPOCH 1.
    """
    logging.info("Starting Kultivator EPOCH 1 pipeline...")
    
    # Initialize components
    logging.info("Initializing components...")
    importer = MockImporter()
    
    # Initialize database
    with DatabaseManager() as db:
        db.initialize_database()
        logging.info("Database initialized")
        
        # Get all blocks from mock importer
        blocks = importer.get_all_blocks()
        logging.info(f"Retrieved {len(blocks)} blocks from mock importer")
        
        # Initialize agent runner
        with AgentRunner() as agent_runner:
            entity_count = 0
            
            # Process each block
            for i, block in enumerate(blocks, 1):
                logging.info(f"Processing block {i}/{len(blocks)}: {block.source_ref}")
                
                try:
                    # Run triage agent to extract entities
                    triage_result = agent_runner.run_triage_agent(block)
                    
                    logging.info(f"Found {len(triage_result.entities)} entities")
                    logging.info(f"Summary: {triage_result.summary}")
                    
                    # Process each discovered entity
                    for entity in triage_result.entities:
                        logging.info(f"Processing entity: {entity.name} ({entity.entity_type})")
                        
                        # Check if entity already exists in database
                        existing_entity = db.get_entity(entity.name)
                        
                        if existing_entity:
                            logging.info(f"Entity {entity.name} already exists in database")
                            continue
                            
                        # Determine wiki path
                        wiki_path = get_entity_wiki_path(entity)
                        entity.wiki_path = wiki_path
                        
                        # Add entity to database
                        success = db.add_entity(entity)
                        if success:
                            logging.info(f"Added entity {entity.name} to database")
                            entity_count += 1
                            
                            # Create placeholder wiki file
                            create_placeholder_wiki_file(entity, wiki_path)
                        else:
                            logging.warning(f"Failed to add entity {entity.name} to database")
                            
                except Exception as e:
                    logging.error(f"Error processing block {block.block_id}: {e}")
                    continue
                    
            logging.info(f"Pipeline completed. Processed {entity_count} new entities.")
            
            # Summary of results
            all_entities = db.list_entities()
            entity_types = {}
            for entity in all_entities:
                entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1
                
            logging.info("Summary of entities by type:")
            for entity_type, count in entity_types.items():
                logging.info(f"  {entity_type}: {count}")


def run_epoch2_pipeline():
    """
    Execute the EPOCH 2 pipeline: mock data -> triage -> synthesizer -> wiki content.
    
    This is the core testable outcome for EPOCH 2.
    """
    logging.info("Starting Kultivator EPOCH 2 pipeline...")
    
    # Initialize components
    logging.info("Initializing components...")
    importer = MockImporter()
    
    # Initialize database
    with DatabaseManager() as db:
        db.initialize_database()
        logging.info("Database initialized")
        
        # Get all blocks from mock importer
        blocks = importer.get_all_blocks()
        logging.info(f"Retrieved {len(blocks)} blocks from mock importer")
        
        # Initialize agent runner
        with AgentRunner() as agent_runner:
            entity_count = 0
            
            # Process each block
            for i, block in enumerate(blocks, 1):
                logging.info(f"Processing block {i}/{len(blocks)}: {block.source_ref}")
                
                try:
                    # Run triage agent to extract entities
                    triage_result = agent_runner.run_triage_agent(block)
                    
                    logging.info(f"Found {len(triage_result.entities)} entities")
                    logging.info(f"Summary: {triage_result.summary}")
                    
                    # Process each discovered entity
                    for entity in triage_result.entities:
                        logging.info(f"Processing entity: {entity.name} ({entity.entity_type})")
                        
                        # Check if entity already exists in database
                        existing_entity = db.get_entity(entity.name)
                        
                        if existing_entity:
                            logging.info(f"Entity {entity.name} already exists in database")
                            continue
                            
                        # Determine wiki path
                        wiki_path = get_entity_wiki_path(entity)
                        entity.wiki_path = wiki_path
                        
                        # Add entity to database
                        success = db.add_entity(entity)
                        if success:
                            logging.info(f"Added entity {entity.name} to database")
                            entity_count += 1
                            
                            # EPOCH 2: Generate content using Synthesizer Agent
                            logging.info(f"Generating content for {entity.name}...")
                            try:
                                wiki_content = agent_runner.run_synthesizer_agent(entity, triage_result.summary)
                                create_wiki_file_with_content(entity, wiki_path, wiki_content)
                                logging.info(f"Generated content for {entity.name}")
                            except Exception as e:
                                logging.error(f"Failed to generate content for {entity.name}: {e}")
                                # Fall back to placeholder
                                create_placeholder_wiki_file(entity, wiki_path)
                                
                        else:
                            logging.warning(f"Failed to add entity {entity.name} to database")
                            
                except Exception as e:
                    logging.error(f"Error processing block {block.block_id}: {e}")
                    continue
                    
            logging.info(f"Pipeline completed. Processed {entity_count} new entities.")
            
            # Summary of results
            all_entities = db.list_entities()
            entity_types = {}
            for entity in all_entities:
                entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1
                
            logging.info("Summary of entities by type:")
            for entity_type, count in entity_types.items():
                logging.info(f"  {entity_type}: {count}")


def main():
    """Main entry point."""
    setup_logging()
    
    logging.info("Kultivator - Automated Knowledge Synthesis Engine")
    logging.info("EPOCH 2: The Synthesizer & Content Generation")
    
    try:
        run_epoch2_pipeline()
        
        print("\n" + "="*60)
        print("EPOCH 2 PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nResults:")
        print("- Mock data processed through Triage Agent")
        print("- Entities discovered and stored in kultivator.db")
        print("- AI-generated content written to wiki files")
        print("\nCheck the following:")
        print("- kultivator.db for entity records")
        print("- wiki/ directories for generated .md files with content")
        print("- kultivator.log for detailed processing logs")
        
    except KeyboardInterrupt:
        logging.info("Pipeline interrupted by user")
        print("\nPipeline interrupted.")
        
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        print(f"\nPipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 