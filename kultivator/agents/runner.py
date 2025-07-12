"""
AI Agent runner for Kultivator.

This module handles communication with Ollama and implements the various AI agents
used for processing and synthesis.
"""

import httpx
import json
from typing import Dict, Any, Optional
import logging

from ..models import CanonicalBlock, TriageResult, Entity


class AgentRunner:
    """
    Manages communication with Ollama and runs AI agents.
    """
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "llama3.2"):
        """
        Initialize the agent runner.
        
        Args:
            ollama_host: The Ollama server URL
            model: The model name to use for inference
        """
        self.ollama_host = ollama_host
        self.model = model
        self.client = httpx.Client(timeout=30.0)
        
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
            
    def _call_ollama_sync(self, prompt: str, system_prompt: str = "") -> str:
        """
        Synchronous wrapper for Ollama calls.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for agent persona
            
        Returns:
            The model's response text
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
    
    def run_triage_agent(self, block: CanonicalBlock) -> TriageResult:
        """
        Run the Triage Agent to identify entities and summarize content.
        
        Args:
            block: The canonical block to process
            
        Returns:
            TriageResult containing discovered entities and summary
        """
        system_prompt = """You are an information clerk. Read this data block and identify all key entities (people, projects, etc.) and summarize the core fact. Output only valid JSON.

Your task:
1. Identify entities mentioned in the content (look for [[Entity Name]] patterns and other clear references)
2. Classify each entity type as one of: person, project, place, company, book, other
3. Provide a concise summary of the key information

Output format (JSON only, no explanations):
{
  "entities": [
    {"name": "Entity Name", "type": "person|project|place|company|book|other"}
  ],
  "summary": "Brief summary of the core information"
}"""

        # Format the block content for processing
        content_text = self._format_block_for_prompt(block)
        
        prompt = f"""Please analyze this content block and extract entities:

Source: {block.source_ref}
Content: {content_text}

Remember to output only valid JSON."""

        try:
            response = self._call_ollama_sync(prompt, system_prompt)
            
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
    
    def run_synthesizer_agent(self, entity: Entity, summary: str, existing_content: Optional[str] = None) -> str:
        """
        Run the Synthesizer Agent to generate or update wiki content for an entity.
        
        Args:
            entity: The entity to generate content for
            summary: Summary of new information about the entity
            existing_content: Optional existing content to merge with new information
            
        Returns:
            Generated or updated Markdown content for the entity's wiki page
        """
        if existing_content:
            # Merge mode: Update existing content with new information
            system_prompt = """You are a meticulous archivist. Your task is to update an existing wiki page with new information while preserving the existing structure and content.

Guidelines for content merging:
1. Preserve the existing title and overall structure
2. Add new information to appropriate sections
3. If new information contradicts existing content, note both versions
4. Add specific details (dates, names, numbers) to a "Details" section
5. Maintain consistent Markdown formatting
6. Keep a neutral, encyclopedic tone
7. Add an "Updates" section if significant new information is added

Do not duplicate existing information. Focus on integrating new details seamlessly.
Do not include any metadata or front matter - just the updated Markdown content."""

            prompt = f"""Update this existing wiki page with new information:

Entity Name: {entity.name}
Entity Type: {entity.entity_type}

EXISTING CONTENT:
{existing_content}

NEW INFORMATION:
{summary}

Generate the complete updated Markdown page, preserving existing content while seamlessly integrating the new information."""

        else:
            # Creation mode: Generate new content from scratch
            system_prompt = """You are a meticulous archivist. Your task is to create a comprehensive wiki page for an entity based on the provided information. 

Write a complete, well-structured Markdown page that includes:
1. A clear title using the entity name
2. Basic information about the entity type
3. A summary section with key details
4. A details section for additional information
5. Proper Markdown formatting

Keep the content informative but concise. Use proper Markdown headers, lists, and formatting. 
Write in a neutral, encyclopedic tone suitable for a personal knowledge base.

Do not include any metadata or front matter - just the Markdown content."""

            prompt = f"""Create a wiki page for this entity:

Entity Name: {entity.name}
Entity Type: {entity.entity_type}
Information: {summary}

Generate a complete Markdown page with proper structure and formatting."""

        try:
            response = self._call_ollama_sync(prompt, system_prompt)
            
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