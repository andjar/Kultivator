"""
Base importer interface for Kultivator.

This module defines the abstract interface that all data importers must implement.
"""

from abc import ABC, abstractmethod
from typing import List

from ..models import CanonicalBlock


class BaseImporter(ABC):
    """
    Abstract base class for all data importers.
    
    Each importer converts data from a specific source format (Logseq EDN, 
    Obsidian Markdown, etc.) into the standardized CanonicalBlock format.
    """
    
    @abstractmethod
    def get_all_blocks(self) -> List[CanonicalBlock]:
        """
        Retrieve all blocks from the data source.
        
        Returns:
            List of CanonicalBlock objects representing all content
        """
        pass
        
    @abstractmethod  
    def get_changed_blocks(self) -> List[CanonicalBlock]:
        """
        Retrieve only blocks that have changed since the last run.
        
        This method will be implemented in EPOCH 4 for incremental updates.
        
        Returns:
            List of CanonicalBlock objects that have been added or modified
        """
        pass 