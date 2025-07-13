"""
Logseq EDN importer for Kultivator.

This module provides an importer for Logseq's EDN database format,
converting the hierarchical block structure into CanonicalBlock objects.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import hashlib
from datetime import datetime

try:
    import edn_format  # type: ignore
    EDN_AVAILABLE = True
except ImportError:
    edn_format = None  # type: ignore
    EDN_AVAILABLE = False

# from ..models import CanonicalBlock
# from .base import BaseImporter

class CanonicalBlock:
    def __init__(self, block_id: str, source_ref: str, content: str, children: List['CanonicalBlock']):
        self.block_id = block_id
        self.source_ref = source_ref
        self.content = content
        self.children = children

    def __repr__(self):
        child_count = len(self.children)
        return f"CanonicalBlock(id='{self.block_id}', content='{self.content[:50]}...', children={child_count})"

class BaseImporter:
    def get_all_blocks(self) -> List[CanonicalBlock]:
        raise NotImplementedError
    def get_changed_blocks(self) -> List[CanonicalBlock]:
        raise NotImplementedError

class LogseqEDNImporter(BaseImporter):
    """
    Importer for Logseq EDN database files.

    Parses Logseq's EDN format and converts pages and their hierarchical
    blocks into CanonicalBlock objects.
    """

    def __init__(self, logseq_db_path: str):
        """
        Initialize the Logseq EDN importer.

        Args:
            logseq_db_path: Path to the Logseq database directory.
        """
        self.logseq_db_path = Path(logseq_db_path)
        self.last_state_file = self.logseq_db_path / "logseq_last_state.json"
        self.uuid_mappings: Dict[str, str] = {}

        if not EDN_AVAILABLE:
            raise ImportError("The 'edn-format' package is required. Please install it with: pip install edn-format")

        if not self.logseq_db_path.is_dir():
            logging.warning(f"Logseq database directory not found: {logseq_db_path}")

        logging.info(f"Initialized Logseq EDN importer for: {self.logseq_db_path}")

    def get_all_blocks(self) -> List[CanonicalBlock]:
        """
        Retrieve all pages and their content blocks from the Logseq database.

        Each non-empty page is returned as a top-level CanonicalBlock, with its
        content blocks nested as children.

        Returns:
            A list of CanonicalBlock objects, each representing a page.
        """
        logging.info("Loading all blocks from Logseq database...")

        # Find the main EDN database file. We expect one primary `db.edn`.
        edn_file = self._find_main_edn_file()
        if not edn_file:
            logging.warning("No main 'db.edn' file found. Creating sample data.")
            return self._create_sample_logseq_blocks()

        try:
            logging.info(f"Parsing data file: {edn_file}")
            with open(edn_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # The edn_format library can handle EDN's tagged elements like #uuid
            if not EDN_AVAILABLE or edn_format is None:
                raise ImportError("The 'edn-format' package is required. Please install it with: pip install edn-format")
            parsed_data = edn_format.loads(content)
            
            all_page_blocks = self._parse_edn_data(parsed_data, edn_file.name)
        
        except Exception as e:
            logging.error(f"Failed to parse or process data file {edn_file}: {e}", exc_info=True)
            return self._create_sample_logseq_blocks()

        if not all_page_blocks:
            logging.warning("No content blocks found in data files. Returning empty list.")
            return []

        logging.info(f"Successfully loaded {len(all_page_blocks)} pages with content.")
        return all_page_blocks

    def _parse_edn_data(self, edn_data: Any, source_filename: str) -> List[CanonicalBlock]:
        """
        Parses the structured EDN data into a list of CanonicalBlocks.

        This is the core data-driven parsing logic. It performs two passes:
        1. Extracts all UUID-to-title mappings from pages.
        2. Builds the hierarchical block structure, resolving UUIDs along the way.
        """
        pages_and_blocks_data = self._get_logseq_value(edn_data, 'pages-and-blocks')
        if not pages_and_blocks_data or not isinstance(pages_and_blocks_data, list):
            logging.warning("EDN data does not contain a valid ':pages-and-blocks' list.")
            return []

        # Pass 1: Extract all UUID-to-title mappings for link resolution.
        self._extract_uuid_mappings(pages_and_blocks_data)
        logging.info(f"Extracted {len(self.uuid_mappings)} page UUID mappings.")

        # Pass 2: Build CanonicalBlock trees for each page.
        all_pages = []
        for item in pages_and_blocks_data:
            page_info = self._get_logseq_value(item, 'page')
            blocks_data = self._get_logseq_value(item, 'blocks')

            if not page_info:
                continue
            
            # Skip built-in/hidden pages that are usually not user content.
            properties = self._get_logseq_value(page_info, 'build/properties', {})
            if self._get_logseq_value(properties, 'logseq.property/built-in?'):
                continue
            
            # Determine page title (handles normal pages and journal pages)
            page_title = self._get_logseq_value(page_info, 'block/title')
            journal_date_int = self._get_logseq_value(page_info, 'build/journal')
            if journal_date_int:
                try:
                    # Format YYYYMMDD into a standard date format.
                    page_title = datetime.strptime(str(journal_date_int), '%Y%m%d').strftime('%Y-%m-%d')
                except ValueError:
                    page_title = f"Journal {journal_date_int}"

            if not page_title:
                continue

            # Recursively build the tree for all top-level blocks on the page.
            child_blocks = []
            if isinstance(blocks_data, list):
                for block_item in blocks_data:
                    canonical_block = self._build_canonical_tree(block_item, page_title, source_filename)
                    if canonical_block:
                        child_blocks.append(canonical_block)
            
            # Only include the page if it has non-empty top-level blocks.
            if child_blocks:
                page_uuid = self._get_logseq_value(page_info, 'block/uuid')
                page_id = str(page_uuid) if page_uuid else f"page_{hash(page_title)}"

                all_pages.append(CanonicalBlock(
                    block_id=page_id,
                    source_ref=f"{source_filename}#page={page_title}",
                    content=str(page_title),
                    children=child_blocks
                ))
        
        return all_pages

    def _extract_uuid_mappings(self, pages_and_blocks_data: List[Dict]):
        """Populate self.uuid_mappings from all page definitions."""
        self.uuid_mappings = {}
        for item in pages_and_blocks_data:
            page_info = self._get_logseq_value(item, 'page')
            if page_info:
                uuid = self._get_logseq_value(page_info, 'block/uuid')
                title = self._get_logseq_value(page_info, 'block/title')
                if uuid and title:
                    self.uuid_mappings[str(uuid)] = str(title)

    def _build_canonical_tree(self, logseq_block: Dict, page_title: str, source_filename: str) -> Optional[CanonicalBlock]:
        """
        Recursively convert a Logseq block dictionary and its children
        into a CanonicalBlock tree.
        """
        # Extract content, preferring ':block/content' for blocks.
        content = self._get_logseq_value(logseq_block, 'block/content', '')
        if not content: # Fallback to title for some block types
            content = self._get_logseq_value(logseq_block, 'block/title', '')

        # An empty string is valid content (e.g., a divider), but skip if None or just whitespace
        if content is None or not str(content).strip():
            # If there's no content, only proceed if there are children to preserve structure
             children_data = self._get_logseq_value(logseq_block, 'build/children', [])
             if not children_data:
                 return None
        
        # Resolve any [[uuid]] references in the content string.
        resolved_content = self._resolve_uuid_references(str(content))

        # Get block UUID for a stable ID. Fallback to hashing the raw block.
        block_uuid = self._get_logseq_value(logseq_block, 'block/uuid')
        block_id = str(block_uuid) if block_uuid else f"block_{hashlib.sha1(str(logseq_block).encode()).hexdigest()[:12]}"

        # Recursively process children
        children = []
        children_data = self._get_logseq_value(logseq_block, 'build/children', [])
        if isinstance(children_data, list):
            for child_item in children_data:
                if isinstance(child_item, dict):
                    child_block = self._build_canonical_tree(child_item, page_title, source_filename)
                    if child_block:
                        children.append(child_block)
        
        # If the block itself was empty but had children, don't create a node for it,
        # but "promote" its children. This avoids empty parent blocks.
        # However, for simplicity and structure preservation, we'll keep the empty parent.
        # This can be adjusted if needed.

        return CanonicalBlock(
            block_id=block_id,
            source_ref=f"{source_filename}#{page_title}#{block_id}",
            content=resolved_content,
            children=children
        )
        
    def _resolve_uuid_references(self, content: str) -> str:
        """Replace [[uuid]] references in content with [[Page Title]]."""
        # Regex to find UUIDs inside double brackets
        uuid_pattern = r'\\[\\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\]\\]'
        
        def replace_match(match):
            uuid = match.group(1)
            # Replace with the mapped title, or keep original if not found
            page_title = self.uuid_mappings.get(uuid, uuid)
            return f"[[{page_title}]]"

        return re.sub(uuid_pattern, replace_match, content)

    @staticmethod
    def _get_logseq_value(data: Dict, key: str, default: Any = None) -> Any:
        """
        Gets a value from a dictionary that may use keywords (e.g., ':key')
        or strings as keys.
        """
        if not isinstance(data, dict):
            return default
        # Only use edn_format.Keyword if available
        if EDN_AVAILABLE and edn_format is not None:
            key_as_keyword = edn_format.Keyword(key)
            return data.get(key_as_keyword, data.get(f":{key}", data.get(key, default)))
        else:
            return data.get(f":{key}", data.get(key, default))

    def _find_main_edn_file(self) -> Optional[Path]:
        """Find the main EDN database file."""
        # The primary database file is the most reliable source.
        possible_locations = [
            self.logseq_db_path / "logseq" / "db.edn",
            self.logseq_db_path / "db.edn"
        ]
        for location in possible_locations:
            if location.is_file():
                logging.info(f"Found main database file at: {location}")
                return location
        
        # Fallback to looking in the backup directory if the main one is missing.
        bak_location = self.logseq_db_path / "logseq" / "bak" / "db.edn"
        if bak_location.is_file():
            logging.warning(f"Using backup database file at: {bak_location}")
            return bak_location
            
        return None

    def get_changed_blocks(self) -> List[CanonicalBlock]:
        """Retrieve only blocks that have changed since the last run."""
        logging.info("Detecting changed blocks...")
        current_blocks = self.get_all_blocks()
        current_state = self._calculate_block_state(current_blocks)
        last_state = self._load_last_state()

        if not last_state:
            logging.info("No previous state found. Treating all blocks as changed.")
            self._save_current_state(current_state)
            return current_blocks

        changed_blocks = []
        current_block_ids = set()

        for block in current_blocks:
            current_block_ids.add(block.block_id)
            block_hash = self._calculate_block_hash(block)
            if block.block_id not in last_state or last_state[block.block_id] != block_hash:
                logging.info(f"Detected change in block: {block.block_id} ('{block.content[:30]}...')")
                changed_blocks.append(block)

        deleted_block_ids = set(last_state.keys()) - current_block_ids
        if deleted_block_ids:
            logging.info(f"Detected {len(deleted_block_ids)} deleted pages/blocks.")
            # Here you could emit events for deleted blocks if needed.

        self._save_current_state(current_state)
        logging.info(f"Found {len(changed_blocks)} changed pages/blocks.")
        return changed_blocks

    def _calculate_block_state(self, blocks: List[CanonicalBlock]) -> Dict[str, str]:
        """Calculate a state dictionary mapping block_id to its hash."""
        return {block.block_id: self._calculate_block_hash(block) for block in blocks}

    def _calculate_block_hash(self, block: CanonicalBlock) -> str:
        """Calculate a stable hash for a CanonicalBlock and its children."""
        block_repr = {
            'id': block.block_id,
            'content': block.content,
            'children': [self._calculate_block_hash(child) for child in sorted(block.children, key=lambda b: b.block_id)]
        }
        # Using a sorted, compact JSON representation for a stable hash
        block_json = json.dumps(block_repr, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_json.encode('utf-8')).hexdigest()

    def _load_last_state(self) -> Optional[Dict[str, str]]:
        """Load the last recorded state from the state file."""
        if not self.last_state_file.exists():
            return None
        try:
            with open(self.last_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load last state file: {e}")
            return None

    def _save_current_state(self, state: Dict[str, str]):
        """Save the current state for future comparison."""
        try:
            with open(self.last_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save current state: {e}")

    def _create_sample_logseq_blocks(self) -> List[CanonicalBlock]:
        """Creates sample blocks for testing when no real data is found."""
        logging.info("Creating sample Logseq blocks for testing...")
        return [
            CanonicalBlock(
                block_id="page_journal_2024-05-22",
                source_ref="sample.edn#page=2024-05-22",
                content="2024-05-22",
                children=[
                    CanonicalBlock(
                        block_id="block_journal_1",
                        source_ref="sample.edn#2024-05-22#block_journal_1",
                        content="Had a productive meeting with [[Sarah Wilson]] about the [[Data Migration Project]].",
                        children=[
                            CanonicalBlock(
                                block_id="block_journal_1_1",
                                source_ref="sample.edn#2024-05-22#block_journal_1_1",
                                content="Need to follow up on the database schema changes.",
                                children=[]
                            )
                        ]
                    )
                ]
            )
        ] 