---

# **Project Specification & Implementation Plan: Kultivator**

## 1. Overview & Goal

**Kultivator** is an automated knowledge synthesis engine. It is designed to connect with hierarchical note-taking applications (outliners), process notes, and cultivate them into a structured, cross-referenced wiki.

The system is architected with a pluggable **Importer Module** system, allowing it to support various source formats (e.g., Logseq EDN, Obsidian Markdown, OPML). The core logic remains agnostic to the data source, operating on a standardized internal data format.

Kultivator uses AI agents powered by a local LLM (Ollama) to understand, extract, and synthesize information, populating and updating wiki pages for key entities. A local database (DuckDB) acts as the system's "memory," tracking processed content, discovered entities, and their relationships to ensure efficiency and idempotency.

## 2. Core Philosophy

*   **Data Sovereignty:** All user data (notes, wiki, database) remains local on the user's machine.
*   **Open Formats:** The primary output (the Wiki) is composed of plain text Markdown files, ensuring they are future-proof, portable, and accessible.
*   **Modularity:** The system is decoupled from any single note-taking application via a well-defined importer interface, allowing for future expansion.
*   **Idempotency:** Re-running the script on the same unchanged data will produce no new changes.
*   **Auditability:** All changes to the wiki are versioned in a Git repository, providing a complete and revertible history of the AI's actions.

## 3. Technology Stack

*   **Scripting Language:** **Python 3.10+** (for its rich AI and data handling ecosystem).
*   **LLM Engine:** **Ollama** (for local, private, and cost-effective AI processing).
*   **Knowledge Store (Wiki):** **Folder of Markdown Files** (for simplicity and portability), versioned with **Git**.
*   **State Database:** **DuckDB** (for a fast, file-based, serverless SQL database).

## 4. Data Architecture

### 4.1. Canonical Block Structure (Internal Standard)

All data, regardless of its source, is converted by an Importer Module into this standard internal structure. This is the universal language the rest of the system speaks.

| Field      | Type   | Description                                                                    |
| :--------- | :----- | :----------------------------------------------------------------------------- |
| `block_id`   | `str`  | A unique and persistent identifier for the top-level block from the source.    |
| `source_ref` | `str`  | A human-readable reference to the source (e.g., file path, page name).         |
| `content`    | `str`  | The text content of the top-level block/bullet.                                |
| `children`   | `list` | A nested list of objects with the same structure, representing child blocks.   |

**Example Canonical Block (JSON):**
```json
{
  "block_id": "664e1c2a-9f6b-4a3b-8b0a-1a2b3c4d5e6f",
  "source_ref": "journals/2024_05_22.md",
  "content": "Met with [[Jane Doe]] about [[Project Phoenix]].",
  "children": [
    {
      "block_id": "664e1c3b-...",
      "source_ref": "journals/2024_05_22.md",
      "content": "Her birthday is on June 15th.",
      "children": []
    }
  ]
}
```

### 4.2. Wiki Data Structure

A hierarchical folder structure based on entity type, located in the `/wiki` directory.
```
wiki/
├── People/
│   └── Jane_Doe.md
├── Projects/
│   └── Project_Phoenix.md
└── Places/
    └── New_York_City.md
```

### 4.3. DuckDB Database Schema

A single `kultivator.db` file will contain the following tables:

| Table: `processed_blocks` | | |
| :--- | :--- | :--- |
| **Column** | **Type** | **Description** |
| `block_id` | `VARCHAR` | PRIMARY KEY. The unique ID from the Canonical Block. |
| `content_hash` | `VARCHAR` | SHA-256 hash of the block's canonical JSON. Used to detect changes. |
| `processed_at`| `TIMESTAMP` | Timestamp of the last successful processing. |

| Table: `entities` | | |
| :--- | :--- | :--- |
| **Column** | **Type** | **Description** |
| `entity_name` | `VARCHAR` | PRIMARY KEY. The canonical name of the entity (e.g., "Jane Doe"). |
| `entity_type` | `VARCHAR` | Classified type (e.g., "person", "project"). |
| `wiki_path` | `VARCHAR` | Relative path to the entity's wiki page. |
| `created_at`| `TIMESTAMP` | When the entity was first discovered. |
| `last_updated_at`| `TIMESTAMP` | When the entity's wiki page was last modified. |

| Table: `entity_mentions` | | |
| :--- | :--- | :--- |
| **Column** | **Type** | **Description** |
| `mention_id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT. |
| `block_id` | `VARCHAR` | Foreign key referencing `processed_blocks.block_id`. |
| `entity_name` | `VARCHAR` | Foreign key referencing `entities.entity_name`. |

---
## 5. Implementation Plan by Testable Epochs

### **EPOCH 1: The Core Pipeline & Entity Discovery**
**Goal:** Create a non-stateful, end-to-end pipeline that can read mock data, use an AI agent to identify entities, and create corresponding placeholder files in a wiki structure. This proves the foundational architecture.

**Key Tasks:**
1.  **Project Scaffolding:** Set up the Python project and directory structure (`kultivator/`, `wiki/`, `tests/`).
2.  **Core Data Models:** Define the `CanonicalBlock` structure using Pydantic.
3.  **Database Setup:** Create a `DatabaseManager` class to initialize `kultivator.db` and create the `entities` table.
4.  **Mock Importer:** Create a `MockImporter` with a `get_all_blocks()` method that returns a hardcoded list of `CanonicalBlock` objects for testing.
5.  **Triage Agent:** Create an `AgentRunner` class to call Ollama. Implement the **Triage Agent** to take a `CanonicalBlock` and output JSON with a list of discovered entities (`[{ "name": "...", "type": "..." }]`).
6.  **Basic Orchestrator:** Write a `main.py` that uses the mock importer, passes blocks to the Triage Agent, and for each discovered entity, adds it to the DB and creates an empty placeholder file in the correct `/wiki` subdirectory.

**Testable Outcome:**
> Running `python main.py` processes the hardcoded blocks, populates the `entities` table in `kultivator.db`, and creates a folder structure in `/wiki` with empty `.md` files corresponding to the discovered entities.

---
### **EPOCH 2: The Synthesizer & Content Generation**
**Goal:** Enhance the pipeline to generate and write meaningful content into the wiki files using a second AI agent. The system will now produce a basic but readable wiki.

**Key Tasks:**
1.  **Synthesizer Agent:** Implement the **Synthesizer Agent** within the `AgentRunner`. Its prompt will take a summary of new information (from the Triage Agent) and generate a complete Markdown page from scratch.
2.  **Orchestrator Enhancement:** Modify the main loop to extract the `summary` from the Triage Agent's output. For each entity, call the Synthesizer Agent with this summary and write its Markdown response into the entity's `.md` file, overwriting the placeholder.

**Testable Outcome:**
> Running `python main.py` now produces a wiki where the `.md` files are populated with AI-generated introductory content based on the mock data.

---
### **EPOCH 3: Real Data, Statefulness & Versioning (Bootstrap)**
**Goal:** Replace the mock importer with a real one for Logseq. Implement the stateful database logic and Git versioning to perform a complete, idempotent "bootstrap" run on real data.

**Key Tasks:**
1.  **Real Importer (Logseq):** Implement a `LogseqEDNImporter`. Its `get_all_blocks()` method will parse the entire Logseq EDN database and convert every top-level block into the `CanonicalBlock` format.
2.  **Database Statefulness:** Expand the `DatabaseManager` to create the `processed_blocks` and `entity_mentions` tables. Implement logic to calculate a SHA-256 `content_hash` for any `CanonicalBlock`.
3.  **Orchestrator (Bootstrap Mode):** Implement logic to record work. After processing a block, save its `block_id` and `content_hash` to `processed_blocks` and create links in `entity_mentions`.
4.  **Versioning:** Integrate `gitpython`. Create a `VersionManager` to initialize a Git repo, stage files, and commit.
5.  **CLI:** Use `argparse` to add commands: `python main.py --importer logseq --bootstrap`. This mode will wipe the wiki and DB (with confirmation), process all blocks, and create a single initial Git commit.

**Testable Outcome:**
> Running `python main.py --importer logseq --bootstrap` on a copy of a real Logseq graph generates a complete wiki with versioned content. Running the same command again does nothing, proving idempotency.

---
### **EPOCH 4: The "Living" System (Incremental Updates)**
**Goal:** Enable the system to run in an incremental mode, detecting only new or changed notes and intelligently updating the existing wiki.

**Key Tasks:**
1.  **Importer Change Detection:** Implement the `get_changed_blocks()` method in `LogseqEDNImporter`. (Strategy: save a copy of the EDN file after each run and compare it on the next run to find changed/new blocks).
2.  **Orchestrator (Incremental Mode):** Implement the default run mode (no `--bootstrap`). This mode calls `get_changed_blocks()` and compares each block's `content_hash` with the one stored in `processed_blocks` to decide if processing is needed.
3.  **Synthesizer Agent Enhancement:** The Synthesizer Agent's prompt must be updated. It will now be given **existing page content** *and* the **new information**, and instructed to *merge* the new info into the existing content.
4.  **Versioning (Incremental):** In this mode, the `VersionManager` will be called after each block is processed, creating small, atomic commits with descriptive messages (e.g., `AI: Update Jane_Doe.md from block [block_id]`).

**Testable Outcome:**
> After a bootstrap, a new note is added in Logseq. Running `python main.py --importer logseq` results in only the relevant wiki page being modified, its content correctly updated, and a single new commit appearing in the Git log.

---
### **EPOCH 5: Advanced Context & Extensibility**
**Goal:** Make the agents "smarter" by providing them with more context, and refactor the codebase to be more configurable and easier to extend.

**Key Tasks:**
1.  **Agent Tools:** Implement `list_entities(entity_type)` and `get_entity_context(entity_name)` to query the DuckDB database. Integrate these into the `AgentRunner` (e.g., using LangChain's tool-use features).
2.  **Agent Architecture:** Formalize the agent system using a registry (e.g., a dictionary) that maps agent names to their prompts and tools. This simplifies adding new agents.
3.  **Synthesizer Prompt Enhancement:** Update the Synthesizer prompt to encourage it to use the new tools for richer context before writing its output.
4.  **Configuration:** Move hardcoded values (paths, prompts, model names) into a `config.yaml` file.
5.  **Documentation & Testing:** Write a comprehensive `README.md` and add unit tests for non-AI components (e.g., importer parsing, hashing).

**Testable Outcome:**
> The quality of generated wiki pages improves. The project is configurable via a `.yaml` file. A developer can add a new agent or importer by following a clear, documented pattern.

## 6. AI Agent Design

### 6.1. Agent Personas & Prompts
*   **Triage Agent:**
    *   **Persona:** "You are an information clerk. Read this data block and identify all key entities (people, projects, etc.) and summarize the core fact. Output only valid JSON."
    *   **Input:** A `CanonicalBlock`.
    *   **Output:** `{"entities": [{"name": "...", "type": "..."}], "summary": "A concise summary of the new information."}`

*   **Synthesizer Agent:**
    *   **Persona:** "You are a meticulous archivist. Given an existing wiki page and new information, seamlessly integrate the new info. Preserve the existing structure. Add specific attributes (birthdays, emails) to a structured 'Details' section. Output the complete, updated Markdown file."
    *   **Input:** Existing page content (string), new information summary (string), and access to tools.
    *   **Output:** The full text of the updated Markdown page.

### 6.2. Agent Tools (Functions callable by the AI)
*   `list_entities(entity_type: str) -> List[str]`: Executes `SELECT entity_name FROM entities WHERE entity_type = ?` in DuckDB.
*   `get_entity_context(entity_name: str, limit: int = 5) -> List[str]`: Queries `entity_mentions` for `block_id`s associated with the entity, then retrieves the original block content to provide broader context.

## 7. Future Considerations (Out of Scope for Initial Version)

*   **New Importer Modules:** Develop importers for Obsidian, Roam Research, TiddlyWiki, or OPML.
*   **Relationship Extraction:** Enhance the Triage Agent to extract explicit relationships (e.g., `(Jane Doe, works at, ACME Corp)`) for storage and graph visualization.
*   **Conflict Resolution:** Implement a mechanism to flag contradictory information for manual user review.
*   **Semantic Search:** Use embeddings to enable powerful semantic search across notes and the wiki.