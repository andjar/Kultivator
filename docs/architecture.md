# Architecture

## Core Components

#### **Importers** (`kultivator/importers/`)
- **MockImporter**: For testing and examples
- **LogseqEDNImporter**: Parses Logseq EDN/JSON exports
- *Extensible*: Add new importers for other note-taking apps

#### **AI Agents** (`kultivator/agents/`)
- **AgentManager**: Manages agents defined in `config.yaml`.
- **Configuration-based Agents**: Agents are defined in `config.yaml`, allowing for easy customization.
- **Template System**: User prompts are generated from templates with dynamic variables.
- **Specialized Agents**: Pre-configured agents for tasks, travel, and more.

#### **Database** (`kultivator/database/`)
- **DuckDB-based**: Fast, serverless SQL database
- **Entity tracking**: Stores discovered entities and relationships
- **Change detection**: SHA-256 hashing for efficient updates

#### **Versioning** (`kultivator/versioning/`)
- **Git integration**: Automatic commits and version tracking
- **Atomic updates**: Each entity change is a separate commit

## Data Flow

```
Notes → Importer → CanonicalBlock → Triage Agent → Entities
                                                       ↓
Wiki ← Synthesizer Agent ← Database ← Entity Processing
```

## Agent Architecture

Kultivator's agent architecture is designed for flexibility and ease of customization. All agents are defined in `config.yaml` and managed by the `AgentManager`.

- **Agent Definitions**: Each agent is defined with a system prompt, a user prompt template, available tools, and other settings.
- **Template System**: User prompts are dynamically rendered using a template system that injects context-specific variables.
- **Specialized Agents**: The system comes with pre-configured agents for common tasks like `task_manager` and `travel_planner`.
- **Custom Agents**: New agents can be added by simply defining them in the `config.yaml` file.

For a detailed explanation of the agent system, see the [Agent System Documentation](agent_system.md).
