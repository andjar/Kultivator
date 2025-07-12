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