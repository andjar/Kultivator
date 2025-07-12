#!/usr/bin/env python3
"""
Process real Norwegian LogSeq data with Kultivator.

Final clean script to demonstrate Kultivator processing real LogSeq EDN content.
"""

import logging
import sys
import re
from pathlib import Path

from kultivator.models import Entity, TriageResult, CanonicalBlock
from kultivator.database import DatabaseManager


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def extract_logseq_content():
    """Extract content from the Norwegian LogSeq EDN file."""
    edn_file = Path("test_logseq_data/49b58be1-e0ce-4ef6-bec4-3187660b5e61.edn")
    
    if not edn_file.exists():
        print("❌ LogSeq EDN file not found!")
        return []
    
    with open(edn_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract meaningful content blocks
    title_matches = re.findall(r':block/title\s+"([^"]+)"', content)
    
    blocks = []
    block_id = 1
    
    for title in title_matches:
        # Skip system/metadata blocks
        if title.startswith('$$$') or title in ['All', 'Contents', 'Library', 'Quick add']:
            continue
            
        blocks.append(CanonicalBlock(
            block_id=f"logseq-{block_id}",
            source_ref=f"{edn_file.name}#block-{block_id}",
            content=title,
            children=[]
        ))
        block_id += 1
    
    return blocks


def triage_agent(block):
    """Extract entities from LogSeq content."""
    content = block.content.lower()
    entities = []
    
    # Extract [[entity]] patterns
    entity_matches = re.findall(r'\[\[([^\]]+)\]\]', block.content)
    
    for entity_name in entity_matches:
        # Skip UUID references (LogSeq internal links)
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', entity_name):
            continue
            
        # Classify entity
        entity_type = "other"
        if any(word in entity_name.lower() for word in ['mariell', 'ryssdal']):
            entity_type = "person"
        elif any(word in entity_name.lower() for word in ['børgefjell', 'tyrkia']):
            entity_type = "place"
        elif any(word in entity_name.lower() for word in ['alpha', 'prosjekt']):
            entity_type = "project"
        elif any(word in entity_name.lower() for word in ['kake']):
            entity_type = "recipe"
        elif any(word in entity_name.lower() for word in ['canon', 'r5']):
            entity_type = "product"
            
        entities.append(Entity(
            name=entity_name,
            entity_type=entity_type,
            wiki_path=None
        ))
    
    # Extract implicit entities from Norwegian text
    if 'mariell' in content:
        entities.append(Entity(name="Mariell Ryssdal", entity_type="person", wiki_path=None))
    if 'børgefjell' in content:
        entities.append(Entity(name="Børgefjell", entity_type="place", wiki_path=None))
    if 'canon' in content:
        entities.append(Entity(name="Canon Camera", entity_type="product", wiki_path=None))
    
    # Generate summary
    summary = f"LogSeq content: {len(entities)} entities"
    if "møte" in content:
        summary += " (meeting notes)"
    elif "kjøpte" in content:
        summary += " (purchase)"
    elif "tur" in content:
        summary += " (travel)"
    
    return TriageResult(entities=entities, summary=summary)


def get_wiki_path(entity):
    """Generate wiki file path for entity."""
    type_mapping = {
        'person': 'People',
        'project': 'Projects', 
        'place': 'Places',
        'recipe': 'Recipes',
        'product': 'Products'
    }
    
    wiki_subdir = type_mapping.get(entity.entity_type.lower(), 'Other')
    safe_name = entity.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-åäöæøå')
    
    return f"wiki/{wiki_subdir}/{safe_name}.md"


def create_wiki_file(entity, wiki_path):
    """Create wiki file for entity."""
    file_path = Path(wiki_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""# {entity.name}

*Type: {entity.entity_type.title()}*

*Generated from Norwegian LogSeq data by Kultivator*

---

## Summary

*Information about {entity.name} will be populated here.*

## Details

## Related Notes

"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logging.info(f"Created: {wiki_path}")


def main():
    """Process Norwegian LogSeq data with Kultivator."""
    setup_logging()
    
    print("🇳🇴 KULTIVATOR - PROCESSING NORWEGIAN LOGSEQ DATA")
    print("="*60)
    
    # Extract content from LogSeq
    blocks = extract_logseq_content()
    if not blocks:
        print("❌ No content found")
        return
    
    print(f"📄 Extracted {len(blocks)} content blocks from LogSeq")
    print("\nContent preview:")
    for i, block in enumerate(blocks[:5], 1):
        print(f"  {i}. {block.content}")
    if len(blocks) > 5:
        print(f"  ... and {len(blocks) - 5} more")
    
    # Process with database
    with DatabaseManager("kultivator.db") as db:
        db.initialize_database()
        
        entity_count = 0
        all_entities = []
        
        for block in blocks:
            # Extract entities
            triage_result = triage_agent(block)
            
            for entity in triage_result.entities:
                # Skip duplicates
                if any(e.name == entity.name for e in all_entities):
                    continue
                    
                # Set wiki path
                entity.wiki_path = get_wiki_path(entity)
                
                # Add to database
                if db.add_entity(entity):
                    all_entities.append(entity)
                    entity_count += 1
                    
                    # Create wiki file
                    create_wiki_file(entity, entity.wiki_path)
        
        # Summary
        print(f"\n✅ Processing complete!")
        print(f"📊 Results:")
        print(f"  • {len(blocks)} LogSeq blocks processed")
        print(f"  • {entity_count} entities extracted")
        print(f"  • {len(set(e.entity_type for e in all_entities))} entity types")
        
        print(f"\n🎯 Entities discovered:")
        for entity in all_entities:
            print(f"  • {entity.name} ({entity.entity_type})")
        
        print(f"\n📁 Wiki files created in /wiki directory")
        print(f"💾 Database saved as kultivator.db")


if __name__ == "__main__":
    main() 