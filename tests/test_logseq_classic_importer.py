import pytest
from pathlib import Path
import os
from kultivator.importers.logseq_classic_edn import LogseqClassicEDNImporter
from kultivator.models.canonical import CanonicalBlock

@pytest.fixture
def classic_logseq_repo(tmp_path):
    logseq_dir = tmp_path / "logseq"
    logseq_dir.mkdir()
    edn_content = """
{:version 1,
 :blocks
 ({:block/id #uuid "67cccfe0-de30-4301-8787-4de0bc67c0e2",
   :block/page-name "Feb 25th, 2022",
   :block/properties nil,
   :block/children
   ({:block/id #uuid "67cccfe0-c971-411b-a140-fbf49bca1198",
     :block/properties nil,
     :block/format :markdown,
     :block/children [],
     :block/content "Test content"})})}
"""
    (logseq_dir / "logseq.edn").write_text(edn_content)
    return logseq_dir

def test_logseq_classic_importer(classic_logseq_repo):
    importer = LogseqClassicEDNImporter(logseq_db_path=str(classic_logseq_repo))
    blocks = importer.get_all_blocks()
    assert len(blocks) == 1
    block = blocks[0]
    assert block.content == "Test content"
    assert block.block_id == "67cccfe0-c971-411b-a140-fbf49bca1198"
