# Kultivator Importer Specification

This document provides a detailed specification for creating new importers for the Kultivator system. Its purpose is to ensure that all importers adhere to a common standard, producing data that the core Kultivator engine can process reliably.

## 1. The Role of an Importer

An importer acts as a bridge between a specific note-taking application (like Logseq, Obsidian, or a simple directory of Markdown files) and the Kultivator system. Its primary responsibility is to read data from the source, transform it into a standardized format, and pass it to the Kultivator pipeline.

The core design principle is **separation of concerns**: the importer knows everything about the *source format* but nothing about the *AI processing* that comes later. The rest of the system knows everything about AI processing but nothing about the source format.

## 2. The CanonicalBlock Data Structure

The single most important contract an importer must fulfill is to convert source data into a list of `CanonicalBlock` objects. This is the universal data structure used by the entire Kultivator system.

The `CanonicalBlock` is defined in `kultivator/models/canonical.py` using Pydantic.

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class CanonicalBlock(BaseModel):
    """
    The universal data structure for representing hierarchical content blocks.
    """
    block_id: str = Field(
        ...,
        description="A unique and persistent identifier for the top-level block from the source"
    )

    source_ref: str = Field(
        ...,
        description="A human-readable reference to the source (e.g., file path, page name)"
    )

    content: str = Field(
        ...,
        description="The text content of the top-level block/bullet"
    )

    created_at: Optional[int] = Field(
        default=None,
        description="The timestamp (seconds since epoch) when the block was created."
    )

    updated_at: Optional[int] = Field(
        default=None,
        description="The timestamp (seconds since epoch) when the block was last updated."
    )

    children: List['CanonicalBlock'] = Field(
        default_factory=list,
        description="A nested list of objects with the same structure, representing child blocks"
    )
```

### Field Explanations

-   `block_id` **(str, required)**: A unique and **persistent** identifier for the block.
    -   **Persistence is key.** If the user runs the importer today and again tomorrow, the same block in the source data must have the same `block_id`.
    -   If the source format provides its own UUIDs (like Logseq), use them.
    -   If not, you must generate a stable ID. A good strategy is to hash a combination of the file path and the block's content or position.

-   `source_ref` **(str, required)**: A human-readable string that helps a user trace the block back to its origin.
    -   Examples: `"pages/My_Project.md"`, `"journals/2024-05-25.md#block-123"`, `"logseq-page:Project_Phoenix"`.

-   `content` **(str, required)**: The actual text content of the block.
    -   This should be the "raw" text as a user would see it.
    -   If the source format uses special link syntax (e.g., `[[Page Title]]`), it should be preserved in the content.

-   `created_at` **(int, optional)**: A Unix timestamp (seconds since epoch) indicating when the block was created.
    -   If the source provides this information, it should be included. Otherwise, it can be `null`.

-   `updated_at` **(int, optional)**: A Unix timestamp (seconds since epoch) indicating when the block was last updated.
    -   This is crucial for incremental processing. If the source provides it, it must be included.

-   `children` **(List\[CanonicalBlock], optional)**: A list of nested `CanonicalBlock` objects.
    -   This represents the hierarchical nature of outliners. If a block has sub-bullets, they become `children` of the parent block.

### JSON Example

Here is an example of what a list of two `CanonicalBlock` objects would look like in JSON format. This is the data that your importer's `get_all_blocks()` method should produce.

```json
[
  {
    "block_id": "664e1c2a-9f6b-4a3b-8b0a-1a2b3c4d5e6f",
    "source_ref": "journals/2024_05_22.md",
    "content": "Met with [[Jane Doe]] about [[Project Phoenix]].",
    "created_at": 1653234567,
    "updated_at": 1653234578,
    "children": [
      {
        "block_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "source_ref": "journals/2024_05_22.md",
        "content": "Her birthday is on June 15th.",
        "created_at": 1653234580,
        "updated_at": 1653234580,
        "children": []
      }
    ]
  },
  {
    "block_id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
    "source_ref": "pages/reading_list.md",
    "content": "Finished reading [[The Pragmatic Programmer]].",
    "created_at": 1653123456,
    "updated_at": 1653123456,
    "children": []
  }
]
```

## 3. The BaseImporter Interface

All importers must inherit from the `BaseImporter` abstract base class defined in `kultivator/importers/base.py`.

```python
from abc import ABC, abstractmethod
from typing import List
from ..models import CanonicalBlock

class BaseImporter(ABC):
    @abstractmethod
    def get_all_blocks(self) -> List[CanonicalBlock]:
        pass

    @abstractmethod
    def get_changed_blocks(self) -> List[CanonicalBlock]:
        pass
```

### Methods to Implement

-   `__init__(self, ...)`: The constructor should accept any necessary configuration, such as the path to the data source.

-   `get_all_blocks(self) -> List[CanonicalBlock]`:
    -   This method is called during a "bootstrap" run.
    -   It must scan the *entire* data source and return a list of `CanonicalBlock` objects for *all* content.

-   `get_changed_blocks(self) -> List[CanonicalBlock]`:
    -   This method is called during an incremental run.
    -   It should only return blocks that are new or have been modified since the last run.
    -   **Implementation Strategy:** A common way to achieve this is to store a "state" file. After `get_all_blocks` runs, you can save a manifest of file hashes. On the next run, `get_changed_blocks` can compare the current file hashes against the saved manifest to detect changes. The `logseq_edn.py` importer provides a good example of this.

## 4. Implementation Guidelines

Here are some best practices and solutions to common challenges you may encounter while building an importer.

### Handling Hierarchical Data

Most outliners produce nested or hierarchical data. Your parser needs to recursively build the `CanonicalBlock` structure. A typical approach is a function that takes a source block, converts it to a `CanonicalBlock`, and then calls itself for all of the source block's children, appending the results to the `children` list.

### Generating Persistent `block_id`s

-   **Priority 1: Use Source UUIDs.** If the source format provides a unique and persistent ID for each block (like Logseq's `:block/uuid`), always prefer it. This is the most reliable method.
-   **Priority 2: Generate a Hash.** If no UUID is available, you must generate your own. Create a string that is unique to the block and hash it (e.g., using SHA-256). This string could be a combination of:
    -   The file path or page title.
    -   The block's content.
    -   The block's position in the file (e.g., line number, or index in a list).
    -   **Caution:** Be mindful that if a user edits the content, the `block_id` will change. This is sometimes unavoidable, but it means the system will treat the edited block as a new block.

### Managing State for Incremental Updates

The `get_changed_blocks()` method is crucial for efficiency. It prevents the system from reprocessing the entire knowledge base every time it runs.

-   **State File:** The recommended approach is to use a state file (e.g., a JSON file) stored in a known location (like next to the source database or in a cache directory).
-   **Content Hashing:** After a successful run, generate a hash for the content of each file (or each block, if you can do so efficiently). Store a map of `{file_path: content_hash}` in your state file.
-   **Comparison:** On the next run, `get_changed_blocks()` will:
    1.  Load the old state map from the JSON file.
    2.  For each file in the source, calculate its current content hash.
    3.  If a file is new, or if its hash has changed compared to the old state, it needs to be parsed.
    4.  Return the `CanonicalBlock`s from only the changed files.

The `logseq_edn.py` importer is a good reference for this pattern.

### Resolving Internal Links

Many note-taking apps have a syntax for linking between pages (e.g., `[[Page Title]]` or `((block-uuid))` ).

-   Your importer should **preserve these links** in the `content` string.
-   If the links use an ID that is not human-readable (like a UUID), the importer should resolve it to a human-readable title if possible. The `logseq_edn.py` importer does this by first scanning all pages to build a `uuid -> title` map, and then using that map to substitute references.

## 5. Implementation Example: MockImporter

The `MockImporter` is the simplest possible implementation and serves as a great starting point.

```python
# In kultivator/importers/my_new_importer.py

import uuid
from typing import List
from ..models import CanonicalBlock
from .base import BaseImporter

class MyNewImporter(BaseImporter):
    """
    A new importer for my custom note format.
    """

    def __init__(self, source_path: str):
        """
        Initialize the importer with the path to the notes.
        """
        self.source_path = source_path
        # Add any other setup needed, like loading state

    def get_all_blocks(self) -> List[CanonicalBlock]:
        """
        Return all blocks from the source. For this example, we use hardcoded data.
        In a real implementation, you would parse files from self.source_path.
        """
        # --- Your parsing logic goes here ---

        # Example hardcoded data:
        example_blocks = [
            CanonicalBlock(
                block_id=str(uuid.uuid4()),
                source_ref="file1.txt",
                content="This is the first block.",
                children=[
                    CanonicalBlock(
                        block_id=str(uuid.uuid4()),
                        source_ref="file1.txt",
                        content="This is a child of the first block.",
                        children=[]
                    )
                ]
            ),
            CanonicalBlock(
                block_id=str(uuid.uuid4()),
                source_ref="file2.txt",
                content="This is the second block from a different file.",
                children=[]
            )
        ]
        return example_blocks

    def get_changed_blocks(self) -> List[CanonicalBlock]:
        """
        For now, we can fall back to returning all blocks.
        A real implementation would compare current state vs. a saved state.
        """
        # A simple, though inefficient, strategy for V1
        return self.get_all_blocks()

```

## 6. Registration

To make your importer available to the Kultivator CLI, you will need to add it to the importer registry in `kultivator/config.py` or a similar configuration entry point. (This step will be further standardized in future versions).

By following this specification, you can build an importer that seamlessly integrates with the Kultivator ecosystem, allowing users to bring their knowledge from any source into the system.
