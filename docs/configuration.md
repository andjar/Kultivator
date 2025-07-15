# Configuration

Kultivator is configured using the `config.yaml` file.

## AI Settings
- `ai.ollama_host`: Ollama server URL
- `ai.model`: Model name (gemma3, llama3.2, etc.)
- `ai.timeout`: Request timeout in seconds

## Modifying AI Agent Prompts
The prompts that guide Kultivator's AI agents are not set in `config.yaml`, but are defined directly in the codebase. To change the behavior, tone, or instructions of an agent, you need to edit the agent's `system_prompt` in the file [`kultivator/agents/registry.py`].

**How to modify an agent's prompt:**
1. Open `kultivator/agents/registry.py` in your code editor.
2. Locate the `AgentConfig` for the agent you wish to modify (e.g., `triage`, `synthesizer_create`, or `synthesizer_merge`).
3. Edit the `system_prompt` string to adjust the agent's instructions, style, or output format.
4. Save your changes and restart Kultivator for the new prompt to take effect.

> **Tip:** Each agent's prompt is a multi-line string in the `system_prompt` field. Be careful to preserve the required output format and any JSON/Markdown structure expected by the system.

## Database Settings
- `database.filename`: DuckDB database file
- `database.timeout`: Database operation timeout

## Wiki Settings
- `wiki.file_extension`: File extension for wiki pages
- `wiki.entity_directories`: Mapping of entity types to directories

## Git Settings
- `git.auto_commit`: Enable automatic commits
- `git.commit_messages`: Templates for commit messages
