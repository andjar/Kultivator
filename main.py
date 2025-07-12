#!/usr/bin/env python3
"""
Kultivator - Automated Knowledge Synthesis Engine

Main entry point for the Kultivator system. This orchestrator coordinates
the entire pipeline from data import through AI processing to wiki generation.
"""

import logging
import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict

from kultivator.models import Entity
from kultivator.importers import MockImporter, LogseqEDNImporter
from kultivator.agents import AgentRunner
from kultivator.database import DatabaseManager
from kultivator.versioning import VersionManager


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


def confirm_bootstrap_wipe() -> bool:
    """
    Ask user to confirm wiping existing data for bootstrap mode.
    
    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "="*60)
    print("⚠️  BOOTSTRAP MODE WARNING")
    print("="*60)
    print("\nBootstrap mode will:")
    print("- DELETE all existing wiki files")
    print("- DELETE the existing database")
    print("- Process all data from scratch")
    print("- Create a new Git repository")
    print("\nThis operation cannot be undone!")
    
    while True:
        response = input("\nDo you want to continue? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def run_bootstrap_pipeline(importer_type: str, logseq_path: str | None = None):
    """
    Execute the bootstrap pipeline: full processing with versioning.
    
    Args:
        importer_type: Type of importer to use ('mock' or 'logseq')
        logseq_path: Path to Logseq database (required for logseq importer)
    """
    logging.info("Starting Kultivator EPOCH 3 bootstrap pipeline...")
    
    # Confirm operation
    if not confirm_bootstrap_wipe():
        logging.info("Bootstrap cancelled by user")
        print("Bootstrap cancelled.")
        return
    
    # Clean up existing data
    logging.info("Cleaning up existing data...")
    wiki_path = Path("wiki")
    db_path = Path("kultivator.db")
    
    if wiki_path.exists():
        shutil.rmtree(wiki_path)
        logging.info("Removed existing wiki directory")
    
    if db_path.exists():
        db_path.unlink()
        logging.info("Removed existing database")
    
    # Initialize components
    logging.info("Initializing components...")
    
    # Select importer
    if importer_type == "logseq":
        if not logseq_path:
            raise ValueError("Logseq path is required for logseq importer")
        try:
            importer = LogseqEDNImporter(logseq_path)
        except Exception as e:
            logging.error(f"Failed to initialize Logseq importer: {e}")
            logging.info("Falling back to mock importer with sample Logseq data")
            importer = MockImporter()
    else:
        importer = MockImporter()
    
    # Initialize version manager
    version_manager = VersionManager("wiki")
    version_manager.initialize_repository()
    
    # Initialize database
    with DatabaseManager() as db:
        db.initialize_database()
        logging.info("Database initialized")
        
        # Get all blocks
        blocks = importer.get_all_blocks()
        logging.info(f"Retrieved {len(blocks)} blocks")
        
        # Initialize agent runner
        with AgentRunner() as agent_runner:
            entity_count = 0
            processed_blocks = 0
            
            # Process each block
            for i, block in enumerate(blocks, 1):
                logging.info(f"Processing block {i}/{len(blocks)}: {block.source_ref}")
                
                try:
                    # Check if block needs processing
                    if not db.block_needs_processing(block):
                        logging.info(f"Block {block.block_id} already processed, skipping")
                        continue
                    
                    # Run triage agent to extract entities
                    triage_result = agent_runner.run_triage_agent(block)
                    
                    logging.info(f"Found {len(triage_result.entities)} entities")
                    logging.info(f"Summary: {triage_result.summary}")
                    
                    # Process each discovered entity
                    for entity in triage_result.entities:
                        logging.info(f"Processing entity: {entity.name} ({entity.entity_type})")
                        
                        # Check if entity already exists
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
                            
                            # Generate content using Synthesizer Agent
                            logging.info(f"Generating content for {entity.name}...")
                            try:
                                wiki_content = agent_runner.run_synthesizer_agent(entity, triage_result.summary)
                                create_wiki_file_with_content(entity, wiki_path, wiki_content)
                                logging.info(f"Generated content for {entity.name}")
                                
                                # Create entity mention record
                                if db.connection:
                                    db.connection.execute("""
                                        INSERT INTO entity_mentions (block_id, entity_name)
                                        VALUES (?, ?)
                                    """, [block.block_id, entity.name])
                                
                            except Exception as e:
                                logging.error(f"Failed to generate content for {entity.name}: {e}")
                                # Fall back to placeholder
                                create_placeholder_wiki_file(entity, wiki_path)
                                
                        else:
                            logging.warning(f"Failed to add entity {entity.name} to database")
                    
                    # Record that this block has been processed
                    db.add_processed_block(block)
                    processed_blocks += 1
                    
                except Exception as e:
                    logging.error(f"Error processing block {block.block_id}: {e}")
                    continue
                    
            logging.info(f"Bootstrap completed. Processed {processed_blocks} blocks and {entity_count} entities.")
            
            # Create bootstrap commit
            logging.info("Creating bootstrap commit...")
            success = version_manager.create_bootstrap_commit(entity_count, processed_blocks)
            if success:
                logging.info("Bootstrap commit created successfully")
            else:
                logging.error("Failed to create bootstrap commit")
            
            # Summary of results
            all_entities = db.list_entities()
            entity_types = {}
            for entity in all_entities:
                entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1
                
            logging.info("Summary of entities by type:")
            for entity_type, count in entity_types.items():
                logging.info(f"  {entity_type}: {count}")
            
            # Repository status
            repo_status = version_manager.get_repository_status()
            logging.info(f"Repository status: {repo_status}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Kultivator - Automated Knowledge Synthesis Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                  # Run with mock data (EPOCH 2 mode)
  python main.py --importer logseq --bootstrap   # Bootstrap with sample Logseq data
  python main.py --importer logseq --bootstrap --logseq-path /path/to/logseq  # Bootstrap with real Logseq data
        """
    )
    
    parser.add_argument(
        "--importer",
        choices=["mock", "logseq"],
        default="mock",
        help="Data importer to use (default: mock)"
    )
    
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Run in bootstrap mode (wipe existing data and process everything)"
    )
    
    parser.add_argument(
        "--logseq-path",
        type=str,
        help="Path to Logseq database directory (required for logseq importer)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Kultivator 0.1.0"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    setup_logging()
    
    logging.info("Kultivator - Automated Knowledge Synthesis Engine")
    
    if args.bootstrap:
        logging.info("EPOCH 3: Bootstrap Mode - Real Data, Statefulness & Versioning")
        
        try:
            run_bootstrap_pipeline(args.importer, args.logseq_path)
            
            print("\n" + "="*60)
            print("🎉 EPOCH 3 BOOTSTRAP COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nResults:")
            print("- All data processed from scratch")
            print("- Entities discovered and stored in kultivator.db")
            print("- AI-generated content written to wiki files")
            print("- Complete Git repository created with initial commit")
            print("\nCheck the following:")
            print("- kultivator.db for entity records")
            print("- wiki/ directories for generated .md files with content")
            print("- .git/ directory for version history")
            print("- kultivator.log for detailed processing logs")
            
        except KeyboardInterrupt:
            logging.info("Bootstrap interrupted by user")
            print("\nBootstrap interrupted.")
            
        except Exception as e:
            logging.error(f"Bootstrap failed: {e}")
            print(f"\nBootstrap failed: {e}")
            sys.exit(1)
    else:
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
            print("\nTip: Use --bootstrap flag for full processing with Git versioning")
            
        except KeyboardInterrupt:
            logging.info("Pipeline interrupted by user")
            print("\nPipeline interrupted.")
            
        except Exception as e:
            logging.error(f"Pipeline failed: {e}")
            print(f"\nPipeline failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main() 