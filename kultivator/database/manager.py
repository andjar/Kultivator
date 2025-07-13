"""
Database manager for Kultivator.

This module handles all database operations using DuckDB for state tracking.
"""

import duckdb
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
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
        
        # Drop entity_mentions table if it exists with old schema and recreate
        try:
            # Check if table exists and has the old schema (with mention_id column)
            result = self.connection.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'entity_mentions' AND column_name = 'mention_id'
            """).fetchall()
            
            if result:
                # Table exists with old schema, drop it
                logging.info("Dropping entity_mentions table with old schema")
                self.connection.execute("DROP TABLE IF EXISTS entity_mentions")
        except:
            # If information_schema doesn't work, try to drop anyway
            pass
        
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS entity_mentions (
                block_id VARCHAR NOT NULL,
                entity_name VARCHAR NOT NULL,
                PRIMARY KEY (block_id, entity_name),
                FOREIGN KEY (block_id) REFERENCES processed_blocks(block_id),
                FOREIGN KEY (entity_name) REFERENCES entities(entity_name)
            )
        """)
        
        # Create sequence for auto-incrementing call_id in ai_agent_calls
        self.connection.execute("CREATE SEQUENCE IF NOT EXISTS call_id_seq;")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS ai_agent_calls (
                call_id BIGINT PRIMARY KEY DEFAULT nextval('call_id_seq'),
                agent_name VARCHAR NOT NULL,
                input_data TEXT NOT NULL,
                system_prompt TEXT,
                user_prompt TEXT NOT NULL,
                model_name VARCHAR NOT NULL,
                raw_response TEXT NOT NULL,
                parsed_response TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                execution_time_ms INTEGER,
                block_id VARCHAR,
                entity_name VARCHAR,
                called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    
    def add_entity_mention(self, block_id: str, entity_name: str) -> bool:
        """
        Add an entity mention record.
        
        Args:
            block_id: The ID of the block containing the mention
            entity_name: The name of the entity mentioned
            
        Returns:
            True if mention was added, False if it already existed
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        try:
            # Insert new mention (will fail if duplicate due to primary key constraint)
            self.connection.execute("""
                INSERT INTO entity_mentions (block_id, entity_name)
                VALUES (?, ?)
            """, [block_id, entity_name])
            return True
            
        except duckdb.IntegrityError:
            # Mention already exists (duplicate primary key)
            return False
        except Exception as e:
            logging.error(f"Failed to add entity mention: {e}")
            return False
    
    def log_ai_agent_call(
        self, 
        agent_name: str,
        input_data: str,
        system_prompt: Optional[str],
        user_prompt: str,
        model_name: str,
        raw_response: str,
        parsed_response: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        block_id: Optional[str] = None,
        entity_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Log an AI agent call to the database for reproducibility.
        (Defensive: Only log valid block_id/entity_name, else set to None and warn)
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")

        # Defensive check for block_id
        valid_block_id = None
        if block_id is not None:
            result = self.connection.execute(
                "SELECT 1 FROM processed_blocks WHERE block_id = ? LIMIT 1",
                [block_id]
            ).fetchone()
            if result:
                valid_block_id = block_id
            else:
                logging.warning(f"log_ai_agent_call: block_id '{block_id}' does not exist in processed_blocks; setting to None.")

        # Defensive check for entity_name
        valid_entity_name = None
        if entity_name is not None:
            result = self.connection.execute(
                "SELECT 1 FROM entities WHERE entity_name = ? LIMIT 1",
                [entity_name]
            ).fetchone()
            if result:
                valid_entity_name = entity_name
            else:
                logging.warning(f"log_ai_agent_call: entity_name '{entity_name}' does not exist in entities; setting to None.")

        result = self.connection.execute("""
            INSERT INTO ai_agent_calls (
                agent_name, input_data, system_prompt, user_prompt, model_name,
                raw_response, parsed_response, success, error_message, 
                execution_time_ms, block_id, entity_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING call_id
        """, [
            agent_name, input_data, system_prompt, user_prompt, model_name,
            raw_response, parsed_response, success, error_message,
            execution_time_ms, valid_block_id, valid_entity_name
        ]).fetchone()
        return result[0] if result else None
    
    def get_ai_agent_calls(
        self, 
        agent_name: Optional[str] = None,
        block_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        success_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve AI agent calls from the database.
        
        Args:
            agent_name: Filter by agent name (optional)
            block_id: Filter by block ID (optional)
            entity_name: Filter by entity name (optional)
            success_only: Only return successful calls
            limit: Limit number of results
            
        Returns:
            List of AI agent call records
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        query = """
            SELECT call_id, agent_name, input_data, system_prompt, user_prompt,
                   model_name, raw_response, parsed_response, success, error_message,
                   execution_time_ms, block_id, entity_name, called_at
            FROM ai_agent_calls
            WHERE 1=1
        """
        params = []
        
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
            
        if block_id:
            query += " AND block_id = ?"
            params.append(block_id)
            
        if entity_name:
            query += " AND entity_name = ?"
            params.append(entity_name)
            
        if success_only:
            query += " AND success = true"
            
        query += " ORDER BY called_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        results = self.connection.execute(query, params).fetchall()
        
        return [
            {
                "call_id": row[0],
                "agent_name": row[1],
                "input_data": row[2],
                "system_prompt": row[3],
                "user_prompt": row[4],
                "model_name": row[5],
                "raw_response": row[6],
                "parsed_response": row[7],
                "success": row[8],
                "error_message": row[9],
                "execution_time_ms": row[10],
                "block_id": row[11],
                "entity_name": row[12],
                "called_at": row[13]
            }
            for row in results
        ]
    
    def reproduce_ai_agent_call(self, call_id: int) -> Optional[Dict]:
        """
        Get all details needed to reproduce a specific AI agent call.
        
        Args:
            call_id: The ID of the call to reproduce
            
        Returns:
            Dictionary with all call details or None if not found
        """
        if not self.connection:
            raise RuntimeError("Database connection not established")
            
        result = self.connection.execute("""
            SELECT call_id, agent_name, input_data, system_prompt, user_prompt,
                   model_name, raw_response, parsed_response, success, error_message,
                   execution_time_ms, block_id, entity_name, called_at
            FROM ai_agent_calls
            WHERE call_id = ?
        """, [call_id]).fetchone()
        
        if result:
            return {
                "call_id": result[0],
                "agent_name": result[1],
                "input_data": result[2],
                "system_prompt": result[3],
                "user_prompt": result[4],
                "model_name": result[5],
                "raw_response": result[6],
                "parsed_response": result[7],
                "success": result[8],
                "error_message": result[9],
                "execution_time_ms": result[10],
                "block_id": result[11],
                "entity_name": result[12],
                "called_at": result[13]
            }
        return None 