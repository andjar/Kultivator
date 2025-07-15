# Configuration

Kultivator is configured using the `config.yaml` file.

## AI Settings
- `ai.ollama_host`: Ollama server URL
- `ai.model`: Model name (gemma3, llama3.2, etc.)
- `ai.timeout`: Request timeout in seconds

## Database Settings
- `database.filename`: DuckDB database file
- `database.timeout`: Database operation timeout

## Wiki Settings
- `wiki.file_extension`: File extension for wiki pages
- `wiki.entity_directories`: Mapping of entity types to directories

## Git Settings
- `git.auto_commit`: Enable automatic commits
- `git.commit_messages`: Templates for commit messages
