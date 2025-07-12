"""
Database manager for Kultivator.

This module handles all database operations using DuckDB for state tracking.
"""

import duckdb
import hashlib
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models import Entity, ProcessedBlock, EntityMention, CanonicalBlock


class DatabaseManager:
    """
    Manages the DuckDB database for tracking processed content and entities.
    """
    
    def __init__(self, db_path: str = "kultivator.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Establish connection to the database."""
        self.connection = duckdb.connect(self.db_path)
        
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        
    def initialize_database(self):
        """
        Create all necessary tables if they don't exist.
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        # Create entities table for EPOCH 1
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_name VARCHAR PRIMARY KEY,
                entity_type VARCHAR NOT NULL,
                wiki_path VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tables for later epochs (will be used in EPOCH 3)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS processed_blocks (
                block_id VARCHAR PRIMARY KEY,
                content_hash VARCHAR NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS entity_mentions (
                mention_id INTEGER PRIMARY KEY,
                block_id VARCHAR NOT NULL,
                entity_name VARCHAR NOT NULL,
                FOREIGN KEY (block_id) REFERENCES processed_blocks(block_id),
                FOREIGN KEY (entity_name) REFERENCES entities(entity_name)
            )
        """)
        
    def add_entity(self, entity: Entity) -> bool:
        """
        Add a new entity to the database.
        
        Args:
            entity: The entity to add
            
        Returns:
            True if entity was added, False if it already existed
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        try:
            self.connection.execute("""
                INSERT INTO entities (entity_name, entity_type, wiki_path, created_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, [
                entity.name,
                entity.entity_type, 
                entity.wiki_path,
                datetime.now(),
                datetime.now()
            ])
            return True
        except duckdb.IntegrityError:
            # Entity already exists
            return False
            
    def get_entity(self, entity_name: str) -> Optional[Entity]:
        """
        Retrieve an entity by name.
        
        Args:
            entity_name: The name of the entity to retrieve
            
        Returns:
            The entity if found, None otherwise
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        result = self.connection.execute("""
            SELECT entity_name, entity_type, wiki_path
            FROM entities 
            WHERE entity_name = ?
        """, [entity_name]).fetchone()
        
        if result:
            return Entity(
                name=result[0],
                entity_type=result[1],
                wiki_path=result[2]
            )
        return None
        
    def list_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        """
        List all entities, optionally filtered by type.
        
        Args:
            entity_type: Optional filter by entity type
            
        Returns:
            List of entities
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        if entity_type:
            results = self.connection.execute("""
                SELECT entity_name, entity_type, wiki_path
                FROM entities 
                WHERE entity_type = ?
                ORDER BY entity_name
            """, [entity_type]).fetchall()
        else:
            results = self.connection.execute("""
                SELECT entity_name, entity_type, wiki_path
                FROM entities 
                ORDER BY entity_name
            """).fetchall()
            
        return [
            Entity(name=row[0], entity_type=row[1], wiki_path=row[2])
            for row in results
        ]
        
    def calculate_content_hash(self, block: CanonicalBlock) -> str:
        """
        Calculate SHA-256 hash of a block's canonical JSON representation.
        
        Args:
            block: The canonical block to hash
            
        Returns:
            The SHA-256 hash as a hex string
        """
        # Convert to dict, then to JSON with sorted keys for consistent hashing
        block_dict = block.model_dump()
        json_str = json.dumps(block_dict, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        
    def add_processed_block(self, block: CanonicalBlock) -> bool:
        """
        Record that a block has been processed.
        
        Args:
            block: The processed block
            
        Returns:
            True if block was recorded, False if it already existed
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        content_hash = self.calculate_content_hash(block)
        
        try:
            self.connection.execute("""
                INSERT INTO processed_blocks (block_id, content_hash, processed_at)
                VALUES (?, ?, ?)
            """, [block.block_id, content_hash, datetime.now()])
            return True
        except duckdb.IntegrityError:
            # Block already processed
            return False
            
    def block_needs_processing(self, block: CanonicalBlock) -> bool:
        """
        Check if a block needs processing (new or changed).
        
        Args:
            block: The block to check
            
        Returns:
            True if the block needs processing
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        current_hash = self.calculate_content_hash(block)
        
        result = self.connection.execute("""
            SELECT content_hash FROM processed_blocks WHERE block_id = ?
        """, [block.block_id]).fetchone()
        
        if not result:
            # Block has never been processed
            return True
            
        # Check if content has changed
        return result[0] != current_hash 