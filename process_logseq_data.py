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
    edn_file = Path("test_logseq_data/real_logseq_export.edn")
    
    if not edn_file.exists():
        print("❌ LogSeq EDN file not found!")
        return [], {}
    
    with open(edn_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract UUID to page title mappings
    uuid_mappings = {}
    uuid_pattern = r':page[^}]*:block/uuid\s+#uuid\s+"([^"]+)"[^}]*:block/title\s+"([^"]+)"'
    for match in re.finditer(uuid_pattern, content):
        uuid, title = match.groups()
        uuid_mappings[uuid] = title
    
    # Extract meaningful content blocks from both block titles and page titles
    block_titles = re.findall(r':block/title\s+"([^"]+)"', content)
    page_titles = re.findall(r':page[^}]*:block/title\s+"([^"]+)"', content)
    
    blocks = []
    block_id = 1
    
    # Process page titles as entities first (these are our main entities)
    for title in page_titles:
        # Skip system pages
        if (title.startswith('$$$') or 
            title in ['Contents', 'Library', 'Quick add'] or
            title.startswith('202507')):  # Skip journal dates
            continue
            
        blocks.append(CanonicalBlock(
            block_id=f"page-{block_id}",
            source_ref=f"{edn_file.name}#page-{title}",
            content=title,
            children=[]
        ))
        block_id += 1
    
    # Process block titles, but skip those that are already page entities
    for title in block_titles:
        # Skip system/metadata blocks and plain UUID references
        if (title.startswith('$$$') or 
            title in ['All', 'Contents', 'Library', 'Quick add', ''] or
            re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', title)):
            continue
        
        # Skip if this is already a page entity to avoid duplicates
        if title in page_titles:
            continue
            
        blocks.append(CanonicalBlock(
            block_id=f"block-{block_id}",
            source_ref=f"{edn_file.name}#block-{block_id}",
            content=title,
            children=[]
        ))
        block_id += 1
    
    return blocks, uuid_mappings


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
        entity_type = classify_entity(entity_name)
        entities.append(Entity(name=entity_name, entity_type=entity_type, wiki_path=None))
    
    # Check if this is a page entity (from page-* block IDs)
    if (block.block_id.startswith("page-") and len(block.content.strip()) > 0):
        # This is a page title - create an entity from it
        entity_type = classify_entity(block.content)
        entities.append(Entity(name=block.content, entity_type=entity_type, wiki_path=None))
    
    # Extract implicit entities from Norwegian text content
    if 'oslo' in content and not any(e.name.lower() == 'oslo' for e in entities):
        entities.append(Entity(name="Oslo", entity_type="place", wiki_path=None))
    if 'isshp' in content and not any('isshp' in e.name.lower() for e in entities):
        entities.append(Entity(name="ISSHP Conference", entity_type="event", wiki_path=None))
    
    # Generate summary
    summary = f"LogSeq content: {len(entities)} entities"
    if "møte" in content:
        summary += " (meeting notes)"
    elif "kjøpt" in content or "kjøpte" in content:
        summary += " (purchase)"
    elif "konferanse" in content:
        summary += " (conference)"
    elif "bursdagen" in content:
        summary += " (birthday)"
    elif block.block_id.startswith("page-"):
        summary += " (page entity)"
    
    return TriageResult(entities=entities, summary=summary)


def classify_entity(name):
    """Classify entity type based on name."""
    name_lower = name.lower()
    
    # Person names
    if any(word in name_lower for word in ['kari nordmann', 'ola nordmann']):
        return "person"
    elif 'nordmann' in name_lower:
        return "person"
        
    # Places
    elif any(word in name_lower for word in ['oslo', 'børgefjell']):
        return "place"
        
    # Projects
    elif any(word in name_lower for word in ['prosjekt', 'isshp']):
        return "project"
        
    # Food
    elif any(word in name_lower for word in ['kake', 'jordbær']):
        return "food"
        
    # Stores
    elif any(word in name_lower for word in ['coop']):
        return "store"
        
    # Events
    elif any(word in name_lower for word in ['konferanse', 'conference']):
        return "event"
        
    return "other"


def get_wiki_path(entity):
    """Generate wiki file path for entity."""
    type_mapping = {
        'person': 'People',
        'project': 'Projects', 
        'place': 'Places',
        'food': 'Food',
        'store': 'Stores',
        'event': 'Events'
    }
    
    wiki_subdir = type_mapping.get(entity.entity_type.lower(), 'Other')
    safe_name = entity.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-åäöæøå')
    
    return f"wiki/{wiki_subdir}/{safe_name}.md"


def create_wiki_file(entity, wiki_path, context_info=None):
    """Create wiki file for entity with contextual information."""
    file_path = Path(wiki_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""# {entity.name}

*Type: {entity.entity_type.title()}*

*Generated from Norwegian LogSeq data by Kultivator*

---

## Summary

"""

    if context_info and context_info.get('mentions'):
        content += f"Entity mentioned in **{len(context_info['mentions'])}** LogSeq blocks.\n\n"
        
        # Add summary of activities/context
        activities = []
        for mention in context_info['mentions']:
            if 'møte' in mention.lower():
                activities.append("🤝 Meeting participant")
            elif 'bursdagen' in mention.lower():
                activities.append("🎂 Birthday celebration")
            elif 'prosjekt' in mention.lower():
                activities.append("📋 Project work")
            elif 'konferanse' in mention.lower():
                activities.append("🎤 Conference")
            elif 'kjøpt' in mention.lower():
                activities.append("🛒 Shopping/purchase")
                
        if activities:
            content += f"**Activities:** {', '.join(set(activities))}\n\n"
    else:
        content += "*Information about {entity.name} will be populated here.*\n\n"

    content += """## Details

"""

    if context_info and context_info.get('mentions'):
        content += "### Mentions from LogSeq Notes\n\n"
        for i, mention in enumerate(context_info['mentions'], 1):
            content += f"**{i}.** {mention}\n\n"
            
        if context_info.get('related_content'):
            content += "### Related Context\n\n"
            for context in context_info['related_content']:
                content += f"- {context}\n"
            content += "\n"

    content += """## Related Notes

"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logging.info(f"Created: {wiki_path}")


def collect_entity_context(blocks, entities, uuid_mappings):
    """Collect contextual information about entities from all blocks."""
    entity_contexts = {}
    
    # Initialize context for all entities
    for entity in entities:
        entity_contexts[entity.name] = {
            'mentions': [],
            'related_content': []
        }
    
    # Create reverse UUID mapping for quick lookup
    uuid_to_entity = {}
    for uuid, page_title in uuid_mappings.items():
        for entity in entities:
            if entity.name == page_title:
                uuid_to_entity[uuid] = entity.name
                break
    
    for block in blocks:
        content = block.content
        
        # Check which entities are mentioned in this block
        for entity in entities:
            entity_mentioned = False
            
            # Check for direct mentions
            if entity.name.lower() in content.lower():
                entity_mentioned = True
            
            # Check for UUID references that map to this entity
            for uuid, entity_name in uuid_to_entity.items():
                if f"[[{uuid}]]" in content and entity_name == entity.name:
                    entity_mentioned = True
                    break
                    
            if entity_mentioned:
                # Clean up the content for display
                clean_content = content
                
                # Replace UUID links with readable names
                for uuid, page_title in uuid_mappings.items():
                    clean_content = clean_content.replace(f"[[{uuid}]]", page_title)
                
                # Skip "Page: " entries to avoid duplication
                if not clean_content.startswith('Page: '):
                    entity_contexts[entity.name]['mentions'].append(clean_content)
    
    # Add related context based on Norwegian keywords (data-driven)
    for block in blocks:
        content = block.content.lower()
        
        # Find relevant contextual patterns for any entity
        for entity in entities:
            entity_name_lower = entity.name.lower()
            
            # Skip if this block doesn't mention the entity
            if entity_name_lower not in content and not any(f"[[{uuid}]]" in block.content for uuid, name in uuid_mappings.items() if name == entity.name):
                continue
                
            # Add context based on Norwegian keywords
            if 'introduksjon og metode' in content:
                entity_contexts[entity.name]['related_content'].append("Working on introduction and methodology")
            elif 'e-post' in content and '@' in block.content:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', block.content)
                if email_match:
                    entity_contexts[entity.name]['related_content'].append(f"Email: {email_match.group()}")
            elif '30 år' in content:
                entity_contexts[entity.name]['related_content'].append("Turned 30 years old")
            elif 'ullsokker' in content:
                entity_contexts[entity.name]['related_content'].append("Received wool socks as birthday gift")
            elif 'konferanse' in content and 'oslo' in content:
                entity_contexts[entity.name]['related_content'].append("Conference in Oslo")
            elif 'forside' in content:
                entity_contexts[entity.name]['related_content'].append("Working on cover/front page design")
            elif 'oransje' in content:
                entity_contexts[entity.name]['related_content'].append("Prefers orange color")
            elif 'frø' in content:
                entity_contexts[entity.name]['related_content'].append("Seeds obtained")
            elif 'plante' in content:
                entity_contexts[entity.name]['related_content'].append("Planning to plant")
    
    return entity_contexts


def main():
    """Process Norwegian LogSeq data with Kultivator."""
    setup_logging()
    
    print("🇳🇴 KULTIVATOR - PROCESSING NORWEGIAN LOGSEQ DATA")
    print("="*60)
    
    # Extract content from LogSeq
    blocks, uuid_mappings = extract_logseq_content()
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
                
                # Add to database (or check if it already exists)
                db.add_entity(entity)
                
                # Add to our list whether it's new or already existed
                all_entities.append(entity)
                entity_count += 1
        
        # Collect contextual information for all entities
        print("\n🔍 Collecting contextual information...")
        entity_contexts = collect_entity_context(blocks, all_entities, uuid_mappings)
        
        # Create wiki files with context
        print("📝 Creating enriched wiki files...")
        for entity in all_entities:
            context_info = entity_contexts.get(entity.name)
            create_wiki_file(entity, entity.wiki_path, context_info)
        
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