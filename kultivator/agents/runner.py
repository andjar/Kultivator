"""
AI Agent runner for Kultivator.

This module handles communication with Ollama and implements the various AI agents
used for processing and synthesis.
"""

import httpx
import json
import time
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone

from ..models import CanonicalBlock, TriageResult, Entity
from ..database import DatabaseManager
from ..config import config
from .registry import agent_registry, AgentConfig


class AgentRunner:
    """
    Manages communication with Ollama and runs AI agents.
    """
    
    def __init__(self, ollama_host: Optional[str] = None, model: Optional[str] = None, 
                 database_manager: Optional[DatabaseManager] = None):
        """
        Initialize the agent runner.
        
        Args:
            ollama_host: The Ollama server URL (defaults to config value)
            model: The model name to use for inference (defaults to config value)
            database_manager: Optional database manager for agent tools
        """
        self.ollama_host = ollama_host or config.ollama_host
        self.model = model or config.model_name
        self.client = httpx.Client(timeout=config.ollama_timeout)
        self.db = database_manager
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()
        
    async def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """
        Make a request to Ollama.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for agent persona
            
        Returns:
            The model's response text
            
        Raises:
            Exception: If the Ollama request fails
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            response = self.client.post(
                f"{self.ollama_host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Ollama: {e}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Ollama request failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error calling Ollama: {e}")
            
    def _call_ollama_sync(
        self, 
        prompt: str, 
        system_prompt: str = "",
        agent_name: str = "unknown",
        input_data: str = "",
        block_id: Optional[str] = None,
        entity_name: Optional[str] = None
    ) -> str:
        """
        Synchronous wrapper for Ollama calls with AI logging.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for agent persona
            agent_name: Name of the agent making the call
            input_data: Original input data for logging
            block_id: Related block ID (optional)
            entity_name: Related entity name (optional)
            
        Returns:
            The model's response text
        """
        start_time = time.time()
        success = False
        error_message = None
        raw_response = ""
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            response = self.client.post(
                f"{self.ollama_host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            raw_response = result.get("response", "")
            success = True
            
            return raw_response
            
        except httpx.RequestError as e:
            error_message = f"Failed to connect to Ollama: {e}"
            raise Exception(error_message)
        except httpx.HTTPStatusError as e:
            error_message = f"Ollama request failed: {e}"
            raise Exception(error_message)
        except Exception as e:
            error_message = f"Unexpected error calling Ollama: {e}"
            raise Exception(error_message)
        finally:
            # Log the AI call to database for reproducibility
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if self.db:
                try:
                    self.db.log_ai_agent_call(
                        agent_name=agent_name,
                        input_data=input_data,
                        system_prompt=system_prompt,
                        user_prompt=prompt,
                        model_name=self.model,
                        raw_response=raw_response,
                        success=success,
                        error_message=error_message,
                        execution_time_ms=execution_time_ms,
                        block_id=block_id,
                        entity_name=entity_name
                    )
                except Exception as log_error:
                    logging.warning(f"Failed to log AI agent call: {log_error}")
    
    def run_triage_agent(self, block: CanonicalBlock) -> TriageResult:
        """
        Run the Triage Agent to identify entities and summarize content.
        
        Args:
            block: The canonical block to process
            
        Returns:
            TriageResult containing discovered entities and summary
        """
        # Get agent configuration from registry
        agent_config = agent_registry.get_agent("triage")
        if not agent_config:
            raise ValueError("Triage agent not found in registry")
            
        system_prompt = agent_config.system_prompt

        # Format the block content for processing
        content_text = self._format_block_for_prompt(block)
        
        # Prepare timestamp information
        current_timestamp = int(time.time())
        current_time_str = datetime.fromtimestamp(current_timestamp, tz=timezone.utc).isoformat()
        created_at_str = datetime.fromtimestamp(block.created_at, tz=timezone.utc).isoformat() if block.created_at else "N/A"
        updated_at_str = datetime.fromtimestamp(block.updated_at, tz=timezone.utc).isoformat() if block.updated_at else "N/A"

        prompt = f"""Please analyze this content block and extract entities.

Current Time: {current_time_str}
Source: {block.source_ref}
Content: {content_text}
Created At: {created_at_str}
Updated At: {updated_at_str}

Remember to output only valid JSON."""

        try:
            # Format input data for logging
            input_data = json.dumps({
                "block_id": block.block_id,
                "source_ref": block.source_ref,
                "content": content_text,
                "created_at": block.created_at,
                "updated_at": block.updated_at,
                "current_time": current_timestamp,
            })
            
            response = self._call_ollama_sync(
                prompt=prompt,
                system_prompt=system_prompt,
                agent_name="triage",
                input_data=input_data,
                block_id=block.block_id
            )
            
            # Try to parse the JSON response
            response = response.strip()
            
            # Remove any markdown code block formatting if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
                
            response = response.strip()
            
            result_dict = json.loads(response)
            
            # Log parsed response for better reproducibility
            if self.db and self.db.connection:
                try:
                    # Find the most recent call for this block to update with parsed response
                    recent_calls = self.db.get_ai_agent_calls(
                        agent_name="triage",
                        block_id=block.block_id,
                        limit=1
                    )
                    if recent_calls:
                        call_id = recent_calls[0]["call_id"]
                        # Update with parsed response
                        self.db.connection.execute("""
                            UPDATE ai_agent_calls 
                            SET parsed_response = ? 
                            WHERE call_id = ?
                        """, [json.dumps(result_dict), call_id])
                except Exception as log_error:
                    logging.warning(f"Failed to log parsed triage response: {log_error}")
            
            # Convert to our data models
            entities = []
            for entity_data in result_dict.get("entities", []):
                entity = Entity(
                    name=entity_data["name"],
                    entity_type=entity_data["type"],
                    wiki_path=None  # Will be set when creating wiki files
                )
                entities.append(entity)
                
            return TriageResult(
                entities=entities,
                summary=result_dict.get("summary", "")
            )
            
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse Triage Agent JSON response: {e}")
            logging.warning(f"Raw response: {response}")
            # Return empty result on parse failure
            return TriageResult(entities=[], summary="Failed to process content")
            
        except Exception as e:
            logging.error(f"Triage Agent failed: {e}")
            return TriageResult(entities=[], summary="Error processing content")
    
    def run_synthesizer_agent(self, entity: Entity, summary: str, block: CanonicalBlock, existing_content: Optional[str] = None) -> str:
        """
        Run the Synthesizer Agent to generate or update wiki content for an entity.
        
        Args:
            entity: The entity to generate content for
            summary: Summary of new information about the entity
            existing_content: Optional existing content to merge with new information
            
        Returns:
            Generated or updated Markdown content for the entity's wiki page
        """
        # Gather additional context using database tools
        context_info = self._gather_entity_context(entity)
        
        # Prepare timestamp information
        current_timestamp = int(time.time())
        
        # Format timestamps into human-readable dates
        created_at_str = datetime.fromtimestamp(block.created_at, tz=timezone.utc).isoformat() if block.created_at else "N/A"
        updated_at_str = datetime.fromtimestamp(block.updated_at, tz=timezone.utc).isoformat() if block.updated_at else "N/A"
        content_text = self._format_block_for_prompt(block)

        # Select appropriate agent based on mode
        if existing_content:
            # Merge mode: Update existing content with new information
            agent_config = agent_registry.get_agent("synthesizer_merge")
            if not agent_config:
                raise ValueError("Synthesizer merge agent not found in registry")
                
            system_prompt = agent_config.system_prompt
            prompt = f"""Update this existing wiki page with new information:

Entity Name: {entity.name}
Entity Type: {entity.entity_type}
Current Time: {current_timestamp}

KNOWLEDGE BASE CONTEXT:
{context_info}

EXISTING CONTENT:
{existing_content}

NEW INFORMATION:
{summary}

SOURCE BLOCK CONTEXT:
Created At: {created_at_str}
Updated At: {updated_at_str}
Source: {block.source_ref}
Raw Content: {content_text}

Generate the complete updated Markdown page, preserving existing content while seamlessly integrating the new information. Use the knowledge base context to create relevant cross-references where appropriate."""

        else:
            # Creation mode: Generate new content from scratch
            agent_config = agent_registry.get_agent("synthesizer_create")
            if not agent_config:
                raise ValueError("Synthesizer create agent not found in registry")
                
            system_prompt = agent_config.system_prompt
            prompt = f"""Create a wiki page for this entity:

Entity Name: {entity.name}
Entity Type: {entity.entity_type}

KNOWLEDGE BASE CONTEXT:
{context_info}

NEW INFORMATION:
{summary}

SOURCE BLOCK CONTEXT:
Source: {block.source_ref}
Content: {content_text}
Created At: {created_at_str}
Updated At: {updated_at_str}
Current Time: {current_timestamp}

Generate a complete Markdown page with proper structure and formatting. Use the knowledge base context to create relevant cross-references where appropriate."""

        try:
            # Format input data for logging
            input_data = json.dumps({
                "entity_name": entity.name,
                "entity_type": entity.entity_type,
                "summary": summary,
                "has_existing_content": existing_content is not None
            })
            
            response = self._call_ollama_sync(
                prompt=prompt,
                system_prompt=system_prompt,
                agent_name="synthesizer_merge" if existing_content else "synthesizer_create",
                input_data=input_data,
                entity_name=entity.name
            )
            
            # Clean up the response
            response = response.strip()
            
            # Remove any markdown code block formatting if present
            if response.startswith("```markdown"):
                response = response[11:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
                
            return response.strip()
            
        except Exception as e:
            logging.error(f"Synthesizer Agent failed for {entity.name}: {e}")
            # Return a basic fallback content
            if existing_content:
                # If we have existing content, preserve it and add a note about the update
                return f"""{existing_content}

---

## Update Note

*New information could not be processed due to an error: {str(e)}*

**New Information:** {summary}

*This update was attempted on {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}*
"""
            else:
                # Return basic new content
                return f"""# {entity.name}

*Type: {entity.entity_type.title()}*

## Summary

{summary}

## Details

*Additional information about {entity.name} will be added as it becomes available.*

## Related Notes

*This page was generated automatically by Kultivator.*
"""
    
    def _format_block_for_prompt(self, block: CanonicalBlock, indent: int = 0) -> str:
        """
        Format a canonical block and its children for AI processing.
        
        Args:
            block: The block to format
            indent: Current indentation level
            
        Returns:
            Formatted text representation
        """
        prefix = "  " * indent
        lines = [f"{prefix}- {block.content}"]
        
        for child in block.children:
            lines.append(self._format_block_for_prompt(child, indent + 1))
            
        return "\n".join(lines) 

    def list_entities(self, entity_type: Optional[str] = None) -> List[str]:
        """
        Tool: List entities from the database, optionally filtered by type.
        
        Args:
            entity_type: Optional entity type to filter by
            
        Returns:
            List of entity names
        """
        if not self.db or not self.db.connection:
            logging.warning("Database not available for list_entities tool")
            return []
            
        try:
            if entity_type:
                result = self.db.connection.execute(
                    "SELECT entity_name FROM entities WHERE entity_type = ? ORDER BY entity_name",
                    [entity_type]
                ).fetchall()
            else:
                result = self.db.connection.execute(
                    "SELECT entity_name FROM entities ORDER BY entity_name"
                ).fetchall()
                
            return [row[0] for row in result]
            
        except Exception as e:
            logging.error(f"Error in list_entities tool: {e}")
            return []
    
    def get_entity_context(self, entity_name: str, limit: Optional[int] = None) -> List[str]:
        """
        Tool: Get context about an entity from blocks that mention it.
        
        Args:
            entity_name: Name of the entity to get context for
            limit: Maximum number of context blocks to return (defaults to config value)
            
        Returns:
            List of block contents that mention the entity
        """
        if not self.db or not self.db.connection:
            logging.warning("Database not available for get_entity_context tool")
            return []
            
        # Use config value if limit not specified
        if limit is None:
            limit = config.context_limit
            
        try:
            # Get block IDs that mention this entity
            mention_results = self.db.connection.execute("""
                SELECT DISTINCT em.block_id, pb.processed_at
                FROM entity_mentions em
                JOIN processed_blocks pb ON em.block_id = pb.block_id
                WHERE em.entity_name = ?
                ORDER BY pb.processed_at DESC
                LIMIT ?
            """, [entity_name, limit]).fetchall()
            
            if not mention_results:
                return []
            
            # For now, return the block IDs as context
            # In a full implementation, we'd need access to the original block content
            # This is a simplified version that returns block references
            context = []
            for row in mention_results:
                block_id = row[0]
                processed_at = row[1]
                context.append(f"Referenced in block {block_id} (processed: {processed_at})")
                
            return context
            
        except Exception as e:
            logging.error(f"Error in get_entity_context tool: {e}")
            return []

    def _gather_entity_context(self, entity: Entity) -> str:
        """
        Gather relevant context about an entity using database tools.
        
        Args:
            entity: The entity to gather context for
            
        Returns:
            Formatted string with context information
        """
        if not self.db:
            return "Database context not available."
            
        context_parts = []
        
        # Get entities of the same type for context
        similar_entities = self.list_entities(entity.entity_type)
        if similar_entities:
            # Limit to 5 for brevity
            similar_count = len(similar_entities)
            similar_sample = similar_entities[:5]
            context_parts.append(f"Related {entity.entity_type} entities ({similar_count} total): {', '.join(similar_sample)}")
        
        # Get mention context for this entity
        entity_context = self.get_entity_context(entity.name)
        if entity_context:
            context_parts.append(f"Previous mentions: {', '.join(entity_context)}")
        
        # Get total entity count for general context
        all_entities = self.list_entities()
        if all_entities:
            context_parts.append(f"Total entities in knowledge base: {len(all_entities)}")
            
        return "\n".join(context_parts) if context_parts else "No additional context available."

    def _get_available_tools_description(self) -> str:
        """
        Get a description of available tools for AI agents.
        
        Returns:
            String describing available tools
        """
        if not self.db:
            return "No database tools available."
            
        return """Available tools you can request:
- list_entities(type): Get all entities of a specific type (person, project, place, etc.)
- get_entity_context(name): Get context about how an entity is mentioned in the knowledge base

To use a tool, mention it in your response like: "I need to check related entities: [TOOL: list_entities(person)]"
""" 