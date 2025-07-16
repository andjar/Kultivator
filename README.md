# 🌱 Kultivator

**An Automated Knowledge Synthesis Engine**

Kultivator is an intelligent system that connects to hierarchical note-taking applications, processes your notes using local AI, and cultivates them into a structured, cross-referenced wiki. Think of it as your personal knowledge gardener that helps your ideas grow and interconnect.

## ✨ Features

### 🧠 **Intelligent Processing**
- **AI-Powered Entity Extraction**: Automatically identifies people, projects, places, companies, and other key entities from your notes
- **Content Synthesis**: Generates comprehensive wiki pages with intelligent cross-references
- **Incremental Updates**: Only processes changed content, making it efficient for daily use

### 🔧 **Flexible Architecture**
- **Pluggable Importers**: Currently supports Logseq EDN/JSON format, designed for easy extension to Obsidian, Roam, etc.
- **Local AI**: Uses Ollama for complete data sovereignty - no cloud dependencies
- **Git Versioning**: Every change is tracked and reversible with full commit history

### 📚 **Knowledge Management**
- **Structured Wiki**: Organizes entities by type (People, Projects, Places, etc.)
- **Cross-References**: Automatically creates links between related entities
- **Context-Aware**: Uses knowledge base context to generate richer content
- **Idempotent**: Safe to run multiple times without duplicating work

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Ollama** with a compatible model (e.g., gemma3, llama3.2)
3. **Git** (for versioning)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Kultivator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Ollama** (if not already running):
   ```bash
   ollama serve
   ```

4. **Pull a compatible model:**
   ```bash
   ollama pull gemma3
   # or
   ollama pull llama3.2
   ```

### Basic Usage

1. **Bootstrap your knowledge base** (first time):
   ```bash
   python main.py --importer logseq --bootstrap
   ```
   
   This will:
   - Process all your Logseq notes
   - Create a wiki/ directory with organized content
   - Initialize a Git repository for tracking changes

2. **Update incrementally** (daily use):
   ```bash
   python main.py --importer logseq
   ```
   
   This will:
   - Detect only new/changed notes
   - Update relevant wiki pages
   - Create atomic commits for each change

### Configuration

Customize Kultivator by editing `config.yaml`:

```yaml
# AI Configuration
ai:
  ollama_host: "http://localhost:11434"
  model: "gemma3"
  timeout: 30.0

# Paths
paths:
  wiki_dir: "wiki"
  state_file: "logseq_last_state.json"
  log_file: "kultivator.log"

# Wiki Organization
wiki:
  entity_directories:
    person: "People"
    project: "Projects"
    place: "Places"
    # ... customize as needed
```

## 📖 Detailed Usage

### Working with Logseq

1. **Export your Logseq database**:
   - Go to Settings → Export → Export graph as EDN
   - Place the exported file where Kultivator can access it

2. **Run bootstrap**:
   ```bash
   python main.py --importer logseq --bootstrap /path/to/logseq/export.edn
   ```

3. **Daily incremental updates**:
   ```bash
   python main.py --importer logseq /path/to/logseq/export.edn
   ```

### Understanding the Output

After processing, you'll have:

```
wiki/
├── People/
│   ├── Jane_Doe.md
│   └── John_Smith.md
├── Projects/
│   ├── Project_Alpha.md
│   └── Research_Initiative.md
├── Places/
│   └── New_York_City.md
└── Companies/
    └── ACME_Corp.md
```

Each wiki page contains:
- **Title and basic information**
- **Summary** of key details
- **Details section** with specific information
- **Cross-references** to related entities
- **Source tracking** for auditability

### Git Integration

Kultivator automatically creates meaningful Git commits:

```bash
git log --oneline
f2a1b3c AI: Update Jane_Doe.md from block abc123
e4d5f6g AI: Create Project_Alpha.md from block def456
a7b8c9d AI: Bootstrap knowledge base with 45 entities from 123 blocks
```

## 🏗️ Architecture

### Core Components

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

### Data Flow

```
Notes → Importer → CanonicalBlock → Triage Agent → Entities
                                                       ↓
Wiki ← Synthesizer Agent ← Database ← Entity Processing
```

### Agent Architecture

Kultivator uses a sophisticated, configuration-driven AI agent system. Agents are defined in `config.yaml` and managed by the `AgentManager`.

- **Configuration-based agents**: Define agents in `config.yaml` instead of code
- **Template system**: Dynamic user prompt generation with variables
- **Specialized agents**: Pre-configured agents for specific domains (tasks, travel, etc.)
- **Agent validation**: Validate agent definitions for correctness

For more details, see the [Agent System Documentation](docs/agent_system.md).

## ⚙️ Configuration Reference

### AI Settings
- `ai.ollama_host`: Ollama server URL
- `ai.model`: Model name (gemma3, llama3.2, etc.)
- `ai.timeout`: Request timeout in seconds

### Agent Settings (`agents`)
- `agents.definitions`: Contains all agent configurations.
  - `description`: Brief description of the agent
  - `system_prompt`: The system prompt for the agent
  - `user_prompt_template`: Template for user prompts with `{variables}`
  - `available_tools`: List of tools the agent can use
  - `requires_database`: Whether the agent needs database access
  - `timeout`: Agent-specific timeout

### Database Settings
- `database.filename`: DuckDB database file
- `database.timeout`: Database operation timeout

### Wiki Settings
- `wiki.file_extension`: File extension for wiki pages
- `wiki.entity_directories`: Mapping of entity types to directories

### Git Settings
- `git.auto_commit`: Enable automatic commits
- `git.commit_messages`: Templates for commit messages

## 🧪 Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/ -v
```

### Manual Testing

Test the system step by step:

```bash
# 1. Test configuration
python -c "from kultivator.config import config; print(f'Config loaded: {config.ai.model}')"

# 2. Test agent manager
python -c "from kultivator.agents import agent_manager; print('Agents:', agent_manager.list_agents())"

# 3. Test database
python -c "from kultivator.database import DatabaseManager; db = DatabaseManager(); db.initialize_database(); print('Database OK')"
```

## 🔧 Troubleshooting

### Common Issues

**"Ollama request failed"**
- Ensure Ollama is running: `ollama serve`
- Check if model is available: `ollama list`
- Verify model name in config.yaml matches installed model

**"No Git repository found"**
- Run bootstrap mode first: `python main.py --importer logseq --bootstrap`
- Bootstrap creates the initial Git repository

**"Database connection error"**
- Check file permissions in current directory
- Ensure DuckDB can create kultivator.db file

**"No changes detected"**
- This is normal if no notes have changed
- Check logseq_last_state.json is present after first run

### Debug Mode

Enable verbose logging:

```yaml
# In config.yaml
logging:
  level: "DEBUG"
```

Or check log file:
```bash
tail -f kultivator.log
```

## 🛠️ Development

### Adding New Importers

1. **Create new importer class**:
   ```python
   from kultivator.importers.base import BaseImporter
   
   class MyAppImporter(BaseImporter):
       def get_all_blocks(self) -> List[CanonicalBlock]:
           # Implementation here
           pass
           
       def get_changed_blocks(self) -> List[CanonicalBlock]:
           # Implementation here  
           pass
   ```

2. **Register in main.py**:
   ```python
   elif importer_type == "myapp":
       importer = MyAppImporter(path)
   ```

### Adding New Agents

1. **Define agent in `config.yaml`**:
   ```yaml
   agents:
     definitions:
       my_custom_agent:
         description: "Custom agent for special processing"
         system_prompt: "You are a specialist in..."
         user_prompt_template: "Process this: {content}"
         available_tools: ["list_entities"]
         requires_database: true
         timeout: 30.0
   ```

2. **Use the new agent**:
   ```python
   from kultivator.agents import agent_manager

   # The agent is automatically available
   agent_def = agent_manager.get_agent_definition("my_custom_agent")

   # Use it in the runner
   runner.run_specialized_agent("my_custom_agent", ...)
   ```

### Database Schema

```sql
-- Entities discovered from notes
CREATE TABLE entities (
    entity_name VARCHAR PRIMARY KEY,
    entity_type VARCHAR NOT NULL,
    wiki_path VARCHAR,
    created_at TIMESTAMP,
    last_updated_at TIMESTAMP
);

-- Processed blocks (for change detection)
CREATE TABLE processed_blocks (
    block_id VARCHAR PRIMARY KEY,
    content_hash VARCHAR NOT NULL,
    processed_at TIMESTAMP
);

-- Entity mentions in blocks
CREATE TABLE entity_mentions (
    block_id VARCHAR NOT NULL,
    entity_name VARCHAR NOT NULL,
    PRIMARY KEY (block_id, entity_name)
);
```

## 🗺️ Roadmap

### Planned Features
- **Multi-language support**: Extend beyond English
- **Obsidian importer**: Direct integration with Obsidian vaults
- **Relationship extraction**: Explicit entity relationships
- **Search interface**: Web-based search and browse
- **Export formats**: PDF, HTML, static site generation

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[License information here]

## 🙏 Acknowledgments

- **Ollama**: For making local AI accessible
- **DuckDB**: For providing an excellent embedded database
- **Logseq**: For creating an open, extensible note-taking platform

---

**Happy Knowledge Cultivation! 🌱**

*Transform your scattered notes into a living, breathing knowledge garden.* 