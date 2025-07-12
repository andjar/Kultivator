"""
Logseq EDN importer for Kultivator.

This module provides an importer for Logseq's EDN database format,
converting the hierarchical block structure into CanonicalBlock objects.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import shutil
from datetime import datetime

try:
    import edn_format  # type: ignore
    EDN_AVAILABLE = True
except ImportError:
    edn_format = None  # type: ignore
    EDN_AVAILABLE = False

from ..models import CanonicalBlock
from .base import BaseImporter


class LogseqEDNImporter(BaseImporter):
    """
    Importer for Logseq EDN database files.
    
    Parses Logseq's EDN format and converts blocks into CanonicalBlock objects.
    """
    
    def __init__(self, logseq_db_path: str):
        """
        Initialize the Logseq EDN importer.
        
        Args:
            logseq_db_path: Path to the Logseq database directory
        """
        self.logseq_db_path = Path(logseq_db_path)
        self.db_file_path = self.logseq_db_path / "logseq" / "bak" / "db.edn"
        self.last_state_file = Path("logseq_last_state.json")
        
        if not EDN_AVAILABLE:
            raise ImportError("edn-format package is required for Logseq import. Install with: pip install edn-format")
            
        if not self.logseq_db_path.exists():
            logging.warning(f"Logseq database directory not found: {logseq_db_path}. Will use sample data.")
            
        logging.info(f"Initialized Logseq EDN importer for: {self.logseq_db_path}")
    
    def get_all_blocks(self) -> List[CanonicalBlock]:
        """
        Retrieve all blocks from the Logseq database.
        
        Returns:
            List of CanonicalBlock objects representing all content
        """
        logging.info("Loading all blocks from Logseq database...")
        
        # Try to find the EDN database file
        edn_files = self._find_edn_files()
        
        if not edn_files:
            logging.warning("No EDN/JSON database files found. Creating sample data.")
            return self._create_sample_logseq_blocks()
        
        all_blocks = []
        
        for edn_file in edn_files:
            try:
                logging.info(f"Parsing data file: {edn_file}")
                blocks = self._parse_edn_file(edn_file)
                all_blocks.extend(blocks)
            except Exception as e:
                logging.error(f"Failed to parse data file {edn_file}: {e}")
                continue
        
        if not all_blocks:
            logging.warning("No blocks found in data files. Creating sample data.")
            return self._create_sample_logseq_blocks()
        
        logging.info(f"Successfully loaded {len(all_blocks)} blocks from real data")
        return all_blocks
    
    def get_changed_blocks(self) -> List[CanonicalBlock]:
        """
        Retrieve only blocks that have changed since the last run.
        
        Returns:
            List of CanonicalBlock objects that have been added or modified
        """
        logging.info("Detecting changed blocks...")
        
        # Get current blocks and calculate their state
        current_blocks = self.get_all_blocks()
        current_state = self._calculate_block_state(current_blocks)
        last_state = self._load_last_state()
        
        if not last_state:
            logging.info("No previous state found. Treating all blocks as changed.")
            self._save_current_state(current_state)
            return current_blocks
        
        # Compare states to find changes
        changed_blocks = []
        
        # Find new or modified blocks
        for block in current_blocks:
            block_hash = self._calculate_block_hash(block)
            
            if block.block_id not in last_state or last_state[block.block_id] != block_hash:
                logging.info(f"Detected change in block: {block.block_id}")
                changed_blocks.append(block)
        
        # Also check for blocks that exist in last_state but not in current_state
        # (these are deleted blocks - we might want to handle them separately)
        current_block_ids = {block.block_id for block in current_blocks}
        deleted_block_ids = set(last_state.keys()) - current_block_ids
        
        if deleted_block_ids:
            logging.info(f"Detected {len(deleted_block_ids)} deleted blocks: {list(deleted_block_ids)[:5]}...")
        
        self._save_current_state(current_state)
        
        logging.info(f"Found {len(changed_blocks)} changed blocks")
        return changed_blocks
    
    def _find_edn_files(self) -> List[Path]:
        """Find EDN database files in the Logseq directory."""
        edn_files = []
        
        # Common locations for Logseq database files
        possible_locations = [
            self.logseq_db_path / "logseq" / "bak" / "db.edn",
            self.logseq_db_path / "logseq" / "db.edn",
            self.logseq_db_path / "db.edn"
        ]
        
        for location in possible_locations:
            if location.exists():
                edn_files.append(location)
        
        # Also search for any .edn files in the directory
        for edn_file in self.logseq_db_path.rglob("*.edn"):
            if edn_file not in edn_files:
                edn_files.append(edn_file)
        
        # For testing: also look for JSON files
        for json_file in self.logseq_db_path.rglob("*.json"):
            if json_file not in edn_files:
                edn_files.append(json_file)
        
        return edn_files
    
    def _parse_edn_file(self, edn_file: Path) -> List[CanonicalBlock]:
        """
        Parse a single EDN file and convert to CanonicalBlock objects.
        
        Args:
            edn_file: Path to the EDN file to parse
            
        Returns:
            List of CanonicalBlock objects
        """
        blocks = []
        
        try:
            with open(edn_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the content (EDN or JSON)
            try:
                if edn_file.suffix.lower() == '.json':
                    # Parse as JSON directly
                    edn_data = json.loads(content)
                    logging.info(f"Parsed {edn_file} as JSON")
                elif EDN_AVAILABLE and edn_format:
                    edn_data = edn_format.loads(content)  # type: ignore
                    logging.info(f"Parsed {edn_file} as EDN")
                else:
                    raise ImportError("EDN format not available")
            except Exception as e:
                logging.warning(f"Failed to parse {edn_file.suffix} format in {edn_file}: {e}")
                logging.info("Attempting to parse as JSON-like format...")
                # Fallback: try to parse as JSON if EDN parsing fails
                try:
                    edn_data = json.loads(content)
                except Exception:
                    logging.error(f"Failed to parse {edn_file} as EDN or JSON")
                    return blocks
            
            # Convert EDN data to CanonicalBlock objects
            if isinstance(edn_data, list):
                for item in edn_data:
                    if isinstance(item, dict):
                        block = self._convert_edn_item_to_block(item, edn_file)
                        if block:
                            blocks.append(block)
            elif isinstance(edn_data, dict):
                block = self._convert_edn_item_to_block(edn_data, edn_file)
                if block:
                    blocks.append(block)
                    
        except Exception as e:
            logging.error(f"Error parsing EDN file {edn_file}: {e}")
            
        return blocks
    
    def _convert_edn_item_to_block(self, item: Dict[str, Any], source_file: Path) -> Optional[CanonicalBlock]:
        """
        Convert an EDN item (dict) to a CanonicalBlock.
        
        Args:
            item: The EDN item to convert
            source_file: Source file for reference
            
        Returns:
            CanonicalBlock object or None if conversion fails
        """
        try:
            # Extract block ID (common Logseq fields)
            block_id = str(item.get('block/uuid', item.get('id', item.get('uuid', f"block_{hash(str(item))}"))))
            
            # Extract content (various possible fields)
            content = item.get('block/content', item.get('content', item.get('text', str(item))))
            
            # Clean up content
            if not isinstance(content, str):
                content = str(content)
            
            # Create source reference
            source_ref = f"{source_file.name}#{block_id}"
            
            # Handle children (nested blocks)
            children = []
            children_data = item.get('block/children', item.get('children', []))
            
            if children_data:
                for child_item in children_data:
                    if isinstance(child_item, dict):
                        child_block = self._convert_edn_item_to_block(child_item, source_file)
                        if child_block:
                            children.append(child_block)
            
            return CanonicalBlock(
                block_id=block_id,
                source_ref=source_ref,
                content=content,
                children=children
            )
            
        except Exception as e:
            logging.warning(f"Failed to convert EDN item to block: {e}")
            return None
    
    def _create_sample_logseq_blocks(self) -> List[CanonicalBlock]:
        """
        Create sample blocks that represent what would come from a Logseq database.
        
        This is used when no real Logseq data is available for testing.
        """
        logging.info("Creating sample Logseq blocks for testing...")
        
        blocks = []
        
        # Sample journal entries
        blocks.append(CanonicalBlock(
            block_id="logseq-journal-1",
            source_ref="journals/2024_05_22.edn",
            content="Had a productive meeting with [[Sarah Wilson]] about the [[Data Migration Project]].",
            children=[
                CanonicalBlock(
                    block_id="logseq-journal-1-1",
                    source_ref="journals/2024_05_22.edn",
                    content="Need to follow up on the database schema changes.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id="logseq-journal-1-2",
                    source_ref="journals/2024_05_22.edn",
                    content="Timeline: Complete by end of month.",
                    children=[]
                )
            ]
        ))
        
        # Sample page content
        blocks.append(CanonicalBlock(
            block_id="logseq-page-1",
            source_ref="pages/company_notes.edn",
            content="[[TechCorp Industries]] has approved the [[Cloud Infrastructure Project]].",
            children=[
                CanonicalBlock(
                    block_id="logseq-page-1-1",
                    source_ref="pages/company_notes.edn",
                    content="Budget: $75,000 allocated for Q2.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id="logseq-page-1-2",
                    source_ref="pages/company_notes.edn",
                    content="Team: [[Mike Chen]], [[Lisa Rodriguez]], [[Alex Kim]].",
                    children=[]
                )
            ]
        ))
        
        # Sample research notes
        blocks.append(CanonicalBlock(
            block_id="logseq-research-1",
            source_ref="pages/research.edn",
            content="Reading [[Clean Architecture]] by [[Robert Martin]].",
            children=[
                CanonicalBlock(
                    block_id="logseq-research-1-1",
                    source_ref="pages/research.edn",
                    content="Chapter 3: Key insight about dependency inversion.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id="logseq-research-1-2",
                    source_ref="pages/research.edn",
                    content="Apply these principles to our current architecture.",
                    children=[]
                )
            ]
        ))
        
        # Sample location-based note
        blocks.append(CanonicalBlock(
            block_id="logseq-location-1",
            source_ref="journals/2024_05_24.edn",
            content="Conference at [[Seattle Convention Center]] next week.",
            children=[
                CanonicalBlock(
                    block_id="logseq-location-1-1",
                    source_ref="journals/2024_05_24.edn",
                    content="Sessions on [[Machine Learning]] and [[DevOps]].",
                    children=[]
                )
            ]
        ))
        
        # Sample project planning
        blocks.append(CanonicalBlock(
            block_id="logseq-planning-1",
            source_ref="pages/project_planning.edn",
            content="Q3 goals for [[Mobile App Development]] initiative.",
            children=[
                CanonicalBlock(
                    block_id="logseq-planning-1-1",
                    source_ref="pages/project_planning.edn",
                    content="Phase 1: User research and requirements gathering.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id="logseq-planning-1-2",
                    source_ref="pages/project_planning.edn",
                    content="Phase 2: Design and prototyping.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id="logseq-planning-1-3",
                    source_ref="pages/project_planning.edn",
                    content="Phase 3: Development and testing.",
                    children=[]
                )
            ]
        ))
        
        logging.info(f"Created {len(blocks)} sample Logseq blocks")
        return blocks
    
    def _calculate_current_state(self) -> Dict[str, str]:
        """Calculate current state of the database for change detection (legacy method)."""
        state = {}
        
        edn_files = self._find_edn_files()
        
        for edn_file in edn_files:
            try:
                with open(edn_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    state[str(edn_file)] = file_hash
            except Exception as e:
                logging.warning(f"Failed to hash file {edn_file}: {e}")
                
        return state
    
    def _calculate_block_state(self, blocks: List[CanonicalBlock]) -> Dict[str, str]:
        """
        Calculate state of individual blocks for change detection.
        
        Args:
            blocks: List of CanonicalBlock objects
            
        Returns:
            Dictionary mapping block_id to block_hash
        """
        state = {}
        
        for block in blocks:
            block_hash = self._calculate_block_hash(block)
            state[block.block_id] = block_hash
            
        return state
    
    def _calculate_block_hash(self, block: CanonicalBlock) -> str:
        """
        Calculate a hash for a CanonicalBlock to detect changes.
        
        Args:
            block: CanonicalBlock to hash
            
        Returns:
            SHA-256 hash of the block's content and structure
        """
        # Create a canonical representation of the block
        block_data = {
            'block_id': block.block_id,
            'source_ref': block.source_ref,
            'content': block.content,
            'children': self._serialize_children(block.children)
        }
        
        # Convert to JSON and hash
        block_json = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_json.encode('utf-8')).hexdigest()
    
    def _serialize_children(self, children: List[CanonicalBlock]) -> List[Dict[str, Any]]:
        """
        Serialize children blocks for hashing.
        
        Args:
            children: List of child CanonicalBlock objects
            
        Returns:
            List of serialized child blocks
        """
        serialized = []
        
        for child in children:
            child_data = {
                'block_id': child.block_id,
                'source_ref': child.source_ref,
                'content': child.content,
                'children': self._serialize_children(child.children)
            }
            serialized.append(child_data)
            
        return serialized
    
    def _load_last_state(self) -> Optional[Dict[str, str]]:
        """Load the last recorded state."""
        try:
            if self.last_state_file.exists():
                with open(self.last_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load last state: {e}")
        return None
    
    def _save_current_state(self, state: Dict[str, str]):
        """Save the current state for future comparison."""
        try:
            with open(self.last_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logging.warning(f"Failed to save current state: {e}") 