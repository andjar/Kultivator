# Welcome to Kultivator

**An Automated Knowledge Synthesis Engine**

Kultivator is an intelligent system that connects to hierarchical note-taking applications, processes your notes using local AI, and cultivates them into a structured, cross-referenced wiki. Think of it as your personal knowledge gardener that helps your ideas grow and interconnect.

---

## 🚦 Simple Usage Example

Kultivator supports two types of Logseq databases:
- **Modern Logseq (EDN):** Uses a `db.edn` file (recent Logseq versions)
- **Classic Logseq (Legacy EDN):** Uses a `logseq.edn` file (older Logseq versions)

Kultivator will automatically detect which importer to use based on the files present in your Logseq export directory.

### 1. Bootstrap your knowledge base (first time)

```bash
python main.py --importer logseq --bootstrap --logseq-path /path/to/your/logseq/export
```
- This will process all your Logseq notes (whether classic or modern), create a `wiki/` directory, and initialize versioning.

### 2. Incremental update (daily use)

```bash
python main.py --importer logseq --logseq-path /path/to/your/logseq/export
```
- This will process only new or changed notes and update your wiki accordingly.

> **Tip:**
> - For **modern Logseq**, ensure your export contains a `db.edn` file.
> - For **classic Logseq**, ensure your export contains a `logseq.edn` file.
> - Kultivator will choose the correct importer automatically—no extra configuration needed!

---
