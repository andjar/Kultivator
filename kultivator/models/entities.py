"""
Entity models for Kultivator.

This module defines data structures for entities discovered and tracked by the system.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """
    Represents a discovered entity (person, project, place, etc.).
    """
    
    name: str = Field(
        ..., 
        description="The canonical name of the entity"
    )
    
    entity_type: str = Field(
        ..., 
        description="The classified type (e.g., 'person', 'project', 'place')"
    )
    
    wiki_path: Optional[str] = Field(
        None,
        description="Relative path to the entity's wiki page"
    )


class TriageResult(BaseModel):
    """
    The output from the Triage Agent when processing a block.
    """
    
    entities: List[Entity] = Field(
        default_factory=list,
        description="List of entities discovered in the block"
    )
    
    summary: str = Field(
        ...,
        description="A concise summary of the new information in the block"
    )


class ProcessedBlock(BaseModel):
    """
    Represents a block that has been processed by the system.
    """
    
    block_id: str = Field(
        ...,
        description="The unique ID from the Canonical Block"
    )
    
    content_hash: str = Field(
        ...,
        description="SHA-256 hash of the block's canonical JSON"
    )
    
    processed_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of the last successful processing"
    )


class EntityMention(BaseModel):
    """
    Represents a mention of an entity in a specific block.
    """
    
    mention_id: Optional[int] = Field(
        None,
        description="Primary key (auto-increment in database)"
    )
    
    block_id: str = Field(
        ...,
        description="Foreign key referencing processed_blocks.block_id"
    )
    
    entity_name: str = Field(
        ...,
        description="Foreign key referencing entities.entity_name"
    ) 