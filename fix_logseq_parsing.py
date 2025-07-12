#!/usr/bin/env python3
"""
Fix LogSeq EDN parsing to handle the real Norwegian content.
"""

import edn_format
from pathlib import Path
from kultivator.models import CanonicalBlock

def parse_logseq_edn_properly():
    """Parse the LogSeq EDN file and extract the real Norwegian content."""
    edn_file = Path("test_logseq_data/49b58be1-e0ce-4ef6-bec4-3187660b5e61.edn")
    
    print("🔧 FIXING LOGSEQ EDN PARSING")
    print("=" * 50)
    
    # Parse the EDN file
    with open(edn_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        edn_data = edn_format.loads(content)
        print("✅ EDN parsing successful")
        
        # Navigate the structure
        if ':pages-and-blocks' in edn_data:
            pages_and_blocks = edn_data[':pages-and-blocks']
            print(f"✅ Found {len(pages_and_blocks)} pages")
            
            blocks = []
            block_count = 0
            
            for page_data in pages_and_blocks:
                if ':page' in page_data and ':blocks' in page_data:
                    page_info = page_data[':page']
                    page_blocks = page_data[':blocks']
                    
                    # Get page title
                    page_title = page_info.get(':block/title', page_info.get('block/title', 'unknown'))
                    
                    print(f"\n📄 Page: {page_title}")
                    print(f"   Blocks: {len(page_blocks)}")
                    
                    # Process each block in this page
                    for block_item in page_blocks:
                        if isinstance(block_item, dict) or hasattr(block_item, 'get'):
                            # Extract block title/content
                            block_title = (
                                block_item.get(':block/title', '') or
                                block_item.get('block/title', '') or
                                block_item.get(':block/content', '') or
                                block_item.get('block/content', '')
                            )
                            
                            if block_title and isinstance(block_title, str) and block_title.strip():
                                block_count += 1
                                block_id = f"real-block-{block_count}"
                                source_ref = f"{edn_file.name}#{page_title}#{block_id}"
                                
                                print(f"   📝 Block {block_count}: {block_title[:60]}...")
                                
                                # Create canonical block
                                canonical_block = CanonicalBlock(
                                    block_id=block_id,
                                    source_ref=source_ref,
                                    content=block_title,
                                    children=[]  # Simplified for now
                                )
                                blocks.append(canonical_block)
                                
                                # Check for entities in Norwegian content
                                import re
                                entities = re.findall(r'\[\[([^\]]+)\]\]', block_title)
                                if entities:
                                    print(f"      🎯 Entities: {entities}")
            
            print(f"\n✅ Extracted {len(blocks)} real blocks with Norwegian content")
            return blocks
            
        else:
            print("❌ No :pages-and-blocks structure found")
            return []
            
    except Exception as e:
        print(f"❌ EDN parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_entity_extraction():
    """Test entity extraction from the real blocks."""
    blocks = parse_logseq_edn_properly()
    
    if not blocks:
        print("❌ No blocks to process")
        return
    
    print(f"\n🎯 TESTING ENTITY EXTRACTION FROM {len(blocks)} REAL BLOCKS")
    print("=" * 60)
    
    all_entities = []
    
    for i, block in enumerate(blocks, 1):
        import re
        entities = re.findall(r'\[\[([^\]]+)\]\]', block.content)
        
        if entities:
            print(f"\nBlock {i}: {block.content[:50]}...")
            print(f"  🎯 Entities found: {entities}")
            all_entities.extend(entities)
        elif any(word in block.content.lower() for word in ['tur', 'kjøpte', 'møte', 'kake', 'canon', 'mariell']):
            print(f"\nBlock {i}: {block.content[:50]}...")
            print(f"  🇳🇴 Norwegian content (no entities)")
    
    # Show unique entities
    unique_entities = list(dict.fromkeys(all_entities))
    print(f"\n✅ TOTAL UNIQUE ENTITIES FOUND: {len(unique_entities)}")
    for i, entity in enumerate(unique_entities, 1):
        print(f"  {i}. {entity}")

if __name__ == "__main__":
    test_entity_extraction() 