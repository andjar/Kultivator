# Configuration

Kultivator is configured using the `config.yaml` file.

## AI Settings
- `ai.ollama_host`: Ollama server URL
- `ai.model`: Model name (gemma3, llama3.2, etc.)
- `ai.timeout`: Request timeout in seconds

## Agent Settings (`agents`)

The `agents` section in `config.yaml` is used to define and configure all AI agents.

- `agents.definitions`: This is a dictionary containing the definitions of all available agents. Each agent is defined by its name (e.g., `task_manager`).

### Agent Definition

Each agent definition has the following properties:

- `description`: A brief description of what the agent does.
- `system_prompt`: A detailed prompt that defines the agent's role, capabilities, and behavior.
- `user_prompt_template`: A template for the user prompt, which can include variables like `{content}`, `{entity_name}`, etc.
- `available_tools`: A list of tools that the agent can use, such as `list_entities` or `get_entity_context`.
- `requires_database`: A boolean indicating whether the agent needs access to the database.
- `timeout`: The timeout for the agent in seconds.

### Example Agent Definition

```yaml
agents:
  definitions:
    my_agent:
      description: "A custom agent."
      system_prompt: "You are a custom agent."
      user_prompt_template: "Process this: {content}"
      available_tools: []
      requires_database: false
      timeout: 30.0
```

For more details on the agent system, see the [Agent System Documentation](agent_system.md).

## Database Settings
- `database.filename`: DuckDB database file
- `database.timeout`: Database operation timeout

## Wiki Settings
- `wiki.file_extension`: File extension for wiki pages
- `wiki.entity_directories`: Mapping of entity types to directories

## Git Settings
- `git.auto_commit`: Enable automatic commits
- `git.commit_messages`: Templates for commit messages
