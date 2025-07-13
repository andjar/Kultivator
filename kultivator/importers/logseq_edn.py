"""
Logseq EDN importer for Kultivator.

This module provides an importer for Logseq's EDN database format,
converting the hierarchical block structure into CanonicalBlock objects.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime
import collections.abc

try:
    import edn_format
    EDN_AVAILABLE = True
except ImportError:
    edn_format = None
    EDN_AVAILABLE = False

# --- THE FIX: REMOVE THE PLACEHOLDER CLASSES ---
# The local, plain-python CanonicalBlock and BaseImporter classes are removed.

# --- THE FIX: IMPORT THE CORRECT MODELS FROM THE PROJECT ---
from ..models import CanonicalBlock
from .base import BaseImporter


class LogseqEDNImporter(BaseImporter):
    """
    Importer for Logseq EDN database files.
    """

    def __init__(self, logseq_db_path: str):
        self.logseq_db_path = Path(logseq_db_path)
        # Place state file next to the db directory, not inside it
        self.last_state_file = self.logseq_db_path.parent / "logseq_last_state.json"
        self.uuid_mappings: Dict[str, str] = {}

        if not EDN_AVAILABLE:
            raise ImportError("The 'edn-format' package is required. Please install it with: pip install edn-format")

        logging.info(f"Initialized Logseq EDN importer for: {self.logseq_db_path}")

    def get_all_blocks(self) -> List[CanonicalBlock]:
        logging.debug("--- Starting get_all_blocks ---")
        
        edn_file = self._find_main_edn_file()
        if not edn_file:
            logging.error("No 'db.edn' file found. Cannot proceed.")
            return []

        try:
            with open(edn_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if not EDN_AVAILABLE or edn_format is None:
                raise ImportError("The 'edn-format' package is required.")

            parsed_data = edn_format.loads(content)
            
            data_to_parse = None
            if isinstance(parsed_data, tuple) and len(parsed_data) > 0:
                data_to_parse = parsed_data[0]
            elif isinstance(parsed_data, collections.abc.Mapping):
                data_to_parse = parsed_data
            else:
                logging.error(f"Parsed EDN data is not a recognized format. Expected a map or tuple, but got {type(parsed_data)}.")
                return []

            all_page_blocks = self._parse_edn_data(data_to_parse, edn_file.name)
        
        except Exception as e:
            logging.error(f"An exception occurred during file reading or parsing in get_all_blocks: {e}", exc_info=True)
            return []

        logging.info(f"Importer finished. Found {len(all_page_blocks)} pages with content.")
        return all_page_blocks

    def _parse_edn_data(self, edn_data: Any, source_filename: str) -> List[CanonicalBlock]:
        pages_and_blocks_data = self._get_logseq_value(edn_data, 'pages-and-blocks')
        
        is_valid_list = isinstance(pages_and_blocks_data, collections.abc.Sequence) and not isinstance(pages_and_blocks_data, str)

        if not pages_and_blocks_data or not is_valid_list:
            logging.error("CRITICAL: Failed to get a valid list from ':pages-and-blocks' key.")
            return []
        
        logging.debug(f"Successfully retrieved ':pages-and-blocks'. It is a list-like object with {len(pages_and_blocks_data)} items.")

        self._extract_uuid_mappings(pages_and_blocks_data)
        logging.debug(f"Extracted {len(self.uuid_mappings)} page UUID mappings.")

        all_pages = []
        for item in pages_and_blocks_data:
            page_info = self._get_logseq_value(item, 'page')
            blocks_data = self._get_logseq_value(item, 'blocks')

            if not page_info: continue
            
            properties = self._get_logseq_value(page_info, 'build/properties', {})
            if self._get_logseq_value(properties, 'logseq.property/built-in?'): continue
            
            page_title = None
            journal_date_int = self._get_logseq_value(page_info, 'build/journal')
            if journal_date_int:
                try:
                    page_title = datetime.strptime(str(journal_date_int), '%Y%m%d').strftime('%Y-%m-%d')
                except ValueError:
                    page_title = f"Journal {journal_date_int}"
            else:
                page_title = self._get_logseq_value(page_info, 'block/title')

            if not page_title: continue

            child_blocks = []
            if isinstance(blocks_data, collections.abc.Sequence) and not isinstance(blocks_data, str):
                for block_item in blocks_data:
                    canonical_block = self._build_canonical_tree(block_item, page_title, source_filename)
                    if canonical_block:
                        child_blocks.append(canonical_block)
            
            if child_blocks:
                page_uuid_obj = self._get_logseq_value(page_info, 'block/uuid')
                page_id = str(page_uuid_obj) if page_uuid_obj else f"page_{hash(page_title)}"
                
                # Instantiating the Pydantic model
                all_pages.append(CanonicalBlock(
                    block_id=page_id,
                    source_ref=f"{source_filename}#page={page_title}",
                    content=str(page_title),
                    children=child_blocks
                ))
        
        return all_pages

    @staticmethod
    def _get_logseq_value(data: Dict, key: str, default: Any = None) -> Any:
        if not isinstance(data, collections.abc.Mapping):
            return default
        key_as_keyword = edn_format.Keyword(key)
        return data.get(key_as_keyword, default)

    def _find_main_edn_file(self) -> Optional[Path]:
        db_file = self.logseq_db_path / "db.edn"
        if db_file.is_file():
            logging.debug(f"Found main database file at: {db_file}")
            return db_file
        
        logging.error(f"Could not find db.edn inside the specified directory: {self.logseq_db_path}")
        return None

    def _extract_uuid_mappings(self, pages_and_blocks_data: List[Dict]):
        self.uuid_mappings = {}
        for item in pages_and_blocks_data:
            page_info = self._get_logseq_value(item, 'page')
            if page_info:
                uuid_obj = self._get_logseq_value(page_info, 'block/uuid')
                title = self._get_logseq_value(page_info, 'block/title')
                if uuid_obj and title:
                    self.uuid_mappings[str(uuid_obj)] = str(title)

    def _build_canonical_tree(self, logseq_block: Dict, page_title: str, source_filename: str) -> Optional[CanonicalBlock]:
        content = self._get_logseq_value(logseq_block, 'block/content', '')
        if not content:
            content = self._get_logseq_value(logseq_block, 'block/title', '')

        children_data = self._get_logseq_value(logseq_block, 'build/children', [])
        is_valid_children_list = isinstance(children_data, collections.abc.Sequence) and not isinstance(children_data, str)

        if (content is None or not str(content).strip()) and not (children_data and is_valid_children_list):
            return None
        
        resolved_content = self._resolve_uuid_references(str(content))
        block_uuid_obj = self._get_logseq_value(logseq_block, 'block/uuid')
        block_id = str(block_uuid_obj) if block_uuid_obj else f"block_{hashlib.sha1(str(logseq_block).encode()).hexdigest()[:12]}"
        
        children = []
        if children_data and is_valid_children_list:
            for child_item in children_data:
                if isinstance(child_item, dict):
                    child_block = self._build_canonical_tree(child_item, page_title, source_filename)
                    if child_block:
                        children.append(child_block)

        # Instantiating the Pydantic model
        return CanonicalBlock(block_id=block_id, source_ref=f"{source_filename}#{page_title}#{block_id}", content=resolved_content, children=children)
        
    def _resolve_uuid_references(self, content: str) -> str:
        uuid_pattern = r'\[\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]\]'
        def replace_match(match):
            uuid = match.group(1)
            page_title = self.uuid_mappings.get(uuid, f"Unknown Page ({uuid[:8]})")
            return f"[[{page_title}]]"
        return re.sub(uuid_pattern, replace_match, content)

    def get_changed_blocks(self) -> List[CanonicalBlock]:
        logging.info("Detecting changed blocks...")
        current_blocks = self.get_all_blocks()
        current_state = self._calculate_block_state(current_blocks)
        last_state = self._load_last_state()

        if not last_state:
            logging.info("No previous state found. Treating all blocks as changed.")
            self._save_current_state(current_state)
            return current_blocks

        changed_blocks = []
        current_block_ids = {block.block_id for block in current_blocks}

        for block in current_blocks:
            block_hash = self._calculate_block_hash(block)
            if block.block_id not in last_state or last_state[block.block_id] != block_hash:
                logging.info(f"Detected change in block: {block.block_id} ('{block.content[:30]}...')")
                changed_blocks.append(block)

        deleted_block_ids = set(last_state.keys()) - current_block_ids
        if deleted_block_ids:
            logging.info(f"Detected {len(deleted_block_ids)} deleted pages/blocks.")

        self._save_current_state(current_state)
        logging.info(f"Found {len(changed_blocks)} changed pages/blocks.")
        return changed_blocks

    def _calculate_block_state(self, blocks: List[CanonicalBlock]) -> Dict[str, str]:
        return {block.block_id: self._calculate_block_hash(block) for block in blocks}

    def _calculate_block_hash(self, block: CanonicalBlock) -> str:
        # Now this will work because 'block' is a Pydantic model
        block_dict = block.model_dump()
        block_json = json.dumps(block_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_json.encode('utf-8')).hexdigest()

    def _load_last_state(self) -> Optional[Dict[str, str]]:
        if not self.last_state_file.exists():
            return None
        try:
            with open(self.last_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load last state file: {e}")
            return None

    def _save_current_state(self, state: Dict[str, str]):
        try:
            with open(self.last_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save current state: {e}")