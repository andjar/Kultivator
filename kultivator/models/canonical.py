"""
Canonical data models for Kultivator.

This module defines the standardized internal data structures that all importers
must convert their source data into.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CanonicalBlock(BaseModel):
    """
    The universal data structure for representing hierarchical content blocks.
    
    All data from various sources (Logseq, Obsidian, etc.) is converted into
    this standardized format for processing by the AI agents.
    """
    
    block_id: str = Field(
        ..., 
        description="A unique and persistent identifier for the top-level block from the source"
    )
    
    source_ref: str = Field(
        ..., 
        description="A human-readable reference to the source (e.g., file path, page name)"
    )
    
    content: str = Field(
        ..., 
        description="The text content of the top-level block/bullet"
    )

    created_at: Optional[int] = Field(
        default=None,
        description="The timestamp (seconds since epoch) when the block was created."
    )

    updated_at: Optional[int] = Field(
        default=None,
        description="The timestamp (seconds since epoch) when the block was last updated."
    )
    
    children: List['CanonicalBlock'] = Field(
        default_factory=list,
        description="A nested list of objects with the same structure, representing child blocks"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            # Custom encoders if needed
        }
        
        
# Enable forward references for self-referencing model
CanonicalBlock.model_rebuild() 