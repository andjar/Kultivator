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

# Import the correct models from the project structure
from ..models import CanonicalBlock
from .base import BaseImporter


class LogseqClassicEDNImporter(BaseImporter):
    """
    Importer for classic Logseq EDN database files.
    """

    def __init__(self, logseq_db_path: str, output_file_path: Optional[str] = None):
        self.logseq_db_path = Path(logseq_db_path)
        self.last_state_file = self.logseq_db_path.parent / "logseq_classic_last_state.json"
        self.output_file_path = Path(output_file_path) if output_file_path else None

        if not EDN_AVAILABLE:
            raise ImportError("The 'edn-format' package is required. Please install it with: pip install edn-format")

        logging.info(f"Initialized Logseq Classic EDN importer for: {self.logseq_db_path}")

    def get_all_blocks(self) -> List[CanonicalBlock]:
        edn_file = self._find_main_edn_file()
        if not edn_file:
            logging.error("No 'logseq.edn' file found. Cannot proceed.")
            return []

        try:
            with open(edn_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if not EDN_AVAILABLE or edn_format is None:
                raise ImportError("The 'edn-format' package is required.")

            parsed_data = edn_format.loads(content)

            data_to_parse = None
            if isinstance(parsed_data, collections.abc.Mapping):
                data_to_parse = parsed_data
            else:
                logging.error(f"Parsed EDN data is not a recognized format. Expected a map, but got {type(parsed_data)}.")
                return []

            all_page_blocks = self._parse_edn_data(data_to_parse, edn_file.name)

        except Exception as e:
            logging.error(f"An exception occurred during file reading or parsing in get_all_blocks: {e}", exc_info=True)
            return []

        self._save_output_to_json(all_page_blocks)
        logging.info(f"Importer finished. Found {len(all_page_blocks)} top-level blocks.")
        return all_page_blocks

    def _parse_edn_data(self, edn_data: Any, source_filename: str) -> List[CanonicalBlock]:
        blocks_data = self._get_logseq_value(edn_data, 'blocks')

        is_valid_list = isinstance(blocks_data, collections.abc.Sequence) and not isinstance(blocks_data, str)

        if not blocks_data or not is_valid_list:
            logging.error("CRITICAL: Failed to get a valid list from ':blocks' key.")
            return []

        all_blocks = []
        for page_block in blocks_data:
            if not isinstance(page_block, collections.abc.Mapping):
                continue

            page_name = self._get_logseq_value(page_block, 'block/page-name')
            if not page_name:
                continue

            children_data = self._get_logseq_value(page_block, 'block/children', [])
            if isinstance(children_data, collections.abc.Sequence) and not isinstance(children_data, str):
                for block_item in children_data:
                    canonical_block = self._build_canonical_tree(block_item, page_name, source_filename)
                    if canonical_block:
                        all_blocks.append(canonical_block)

        return all_blocks

    @staticmethod
    def _get_logseq_value(data: Any, key: str, default: Any = None) -> Any:
        if not isinstance(data, collections.abc.Mapping):
            return default
        if edn_format is None:
            return default
        key_as_keyword = edn_format.Keyword(key)
        return data.get(key_as_keyword, default)

    def _find_main_edn_file(self) -> Optional[Path]:
        db_file = self.logseq_db_path / "logseq.edn"
        if db_file.is_file():
            return db_file
        logging.error(f"Could not find logseq.edn inside the specified directory: {self.logseq_db_path}")
        return None

    def _build_canonical_tree(self, logseq_block: collections.abc.Mapping, page_title: str, source_filename: str) -> Optional[CanonicalBlock]:
        content = self._get_logseq_value(logseq_block, 'block/content', '')
        if not content:
            content = self._get_logseq_value(logseq_block, 'block/title', '')

        children_data = self._get_logseq_value(logseq_block, 'block/children', [])
        is_valid_children_list = isinstance(children_data, collections.abc.Sequence) and not isinstance(children_data, str)

        if (content is None or not str(content).strip()) and not (children_data and is_valid_children_list):
            return None

        resolved_content = str(content)

        block_uuid_obj = self._get_logseq_value(logseq_block, 'block/id')
        if block_uuid_obj:
            block_id = str(block_uuid_obj)
        else:
            unique_str = f"{page_title}-{resolved_content}-{len(children_data)}"
            block_id = f"block_{hashlib.sha1(unique_str.encode()).hexdigest()[:12]}"

        children = []
        if children_data and is_valid_children_list:
            for child_item in children_data:
                if isinstance(child_item, collections.abc.Mapping):
                    child_block = self._build_canonical_tree(child_item, page_title, source_filename)
                    if child_block:
                        children.append(child_block)

        created_at = self._get_logseq_value(logseq_block, 'block/created-at')
        updated_at = self._get_logseq_value(logseq_block, 'block/updated-at')

        return CanonicalBlock(
            block_id=block_id,
            source_ref=f"{source_filename}#{page_title}#{block_id}",
            content=resolved_content,
            children=children,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _save_output_to_json(self, blocks: List[CanonicalBlock]):
        if not self.output_file_path:
            return
        try:
            serializable_blocks = [block.model_dump() for block in blocks]
            with open(self.output_file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_blocks, f, indent=2, ensure_ascii=False)
            logging.info(f"Successfully saved importer output to: {self.output_file_path}")
        except (IOError, TypeError) as e:
            logging.error(f"Failed to save importer output to JSON: {e}")


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
                changed_blocks.append(block)

        self._save_current_state(current_state)
        logging.info(f"Found {len(changed_blocks)} changed pages/blocks.")
        return changed_blocks

    def _calculate_block_state(self, blocks: List[CanonicalBlock]) -> Dict[str, str]:
        return {block.block_id: self._calculate_block_hash(block) for block in blocks}

    def _calculate_block_hash(self, block: CanonicalBlock) -> str:
        """
        Calculates a stable hash for a CanonicalBlock.
        """
        # Dump to dict, then to a sorted, compact JSON string for a canonical representation.
        block_dict = block.model_dump()
        block_json = json.dumps(block_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_json.encode('utf-8')).hexdigest()

    def _load_last_state(self) -> Optional[Dict[str, str]]:
        if not self.last_state_file.exists():
            return None
        try:
            with open(self.last_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_current_state(self, state: Dict[str, str]):
        try:
            with open(self.last_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save current state: {e}")