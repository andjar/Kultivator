"""
Mock importer for testing Kultivator.

This module provides a mock data source with hardcoded blocks for testing
the core pipeline during development.
"""

from typing import List
import uuid

from ..models import CanonicalBlock
from .base import BaseImporter


class MockImporter(BaseImporter):
    """
    Mock importer that returns hardcoded test data.
    
    Used for testing the core pipeline without requiring real data sources.
    """
    
    def __init__(self):
        """Initialize the mock importer with test data."""
        self._test_blocks = self._create_test_blocks()
        
    def get_all_blocks(self) -> List[CanonicalBlock]:
        """
        Return all hardcoded test blocks.
        
        Returns:
            List of test CanonicalBlock objects
        """
        return self._test_blocks
        
    def get_changed_blocks(self) -> List[CanonicalBlock]:
        """
        Return empty list for mock implementation.
        
        In EPOCH 4, this will return changed blocks.
        
        Returns:
            Empty list for now
        """
        return []
        
    def _create_test_blocks(self) -> List[CanonicalBlock]:
        """
        Create hardcoded test blocks with various entity types.
        
        Returns:
            List of test blocks covering different scenarios
        """
        blocks = []
        
        # Block 1: Meeting with person and project
        blocks.append(CanonicalBlock(
            block_id=str(uuid.uuid4()),
            source_ref="journals/2024_05_22.md",
            content="Met with [[Jane Doe]] about [[Project Phoenix]].",
            children=[
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="journals/2024_05_22.md", 
                    content="Her birthday is on June 15th.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="journals/2024_05_22.md",
                    content="Project deadline is next month.",
                    children=[]
                )
            ]
        ))
        
        # Block 2: Travel planning with places
        blocks.append(CanonicalBlock(
            block_id=str(uuid.uuid4()),
            source_ref="journals/2024_05_23.md",
            content="Planning trip to [[New York City]] with [[John Smith]].",
            children=[
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="journals/2024_05_23.md",
                    content="Flight booked for July 10th.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="journals/2024_05_23.md",
                    content="Hotel near [[Central Park]].",
                    children=[]
                )
            ]
        ))
        
        # Block 3: Work project with company
        blocks.append(CanonicalBlock(
            block_id=str(uuid.uuid4()),
            source_ref="pages/work_notes.md",
            content="[[ACME Corporation]] approved the [[AI Integration Project]].",
            children=[
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="pages/work_notes.md",
                    content="Budget allocated: $50,000",
                    children=[]
                ),
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="pages/work_notes.md",
                    content="Team lead: [[Sarah Johnson]]",
                    children=[]
                )
            ]
        ))
        
        # Block 4: Book and author
        blocks.append(CanonicalBlock(
            block_id=str(uuid.uuid4()),
            source_ref="pages/reading_list.md",
            content="Finished reading [[The Pragmatic Programmer]] by [[Andy Hunt]].",
            children=[
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="pages/reading_list.md",
                    content="Key takeaway: Always use version control.",
                    children=[]
                ),
                CanonicalBlock(
                    block_id=str(uuid.uuid4()),
                    source_ref="pages/reading_list.md",
                    content="Rating: 5/5 stars",
                    children=[]
                )
            ]
        ))
        
        # Block 5: Simple note with location
        blocks.append(CanonicalBlock(
            block_id=str(uuid.uuid4()),
            source_ref="journals/2024_05_24.md",
            content="Coffee meeting at [[Starbucks Downtown]] at 3 PM.",
            children=[]
        ))
        
        return blocks 