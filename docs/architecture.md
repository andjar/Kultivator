# Architecture

## Core Components

#### **Importers** (`kultivator/importers/`)
- **MockImporter**: For testing and examples
- **LogseqEDNImporter**: Parses Logseq EDN/JSON exports
- *Extensible*: Add new importers for other note-taking apps

#### **AI Agents** (`kultivator/agents/`)
- **Triage Agent**: Extracts entities and creates summaries
- **Synthesizer Agent**: Generates and updates wiki content
- **Agent Registry**: Centralized configuration system

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

Kultivator uses a sophisticated AI agent system:

1. **Triage Agent**:
   - Reads note blocks
   - Identifies entities (people, projects, etc.)
   - Creates summaries

2. **Synthesizer Agent**:
   - Has access to database tools
   - Can query related entities for context
   - Generates rich, cross-referenced content

3. **Database Tools**:
   - `list_entities(type)`: Get entities by type
   - `get_entity_context(name)`: Get mention history
