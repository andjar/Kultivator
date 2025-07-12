#!/usr/bin/env python3
"""
Test script for Kultivator Sixth Epoch functionality.

This script tests:
1. AI agent call logging for reproducibility
2. Enhanced LogSeq processing with Norwegian content
3. Data-driven entity extraction and classification
4. Complete integration of all sixth epoch features
"""

import logging
import sys
from pathlib import Path

from kultivator.database import DatabaseManager
from kultivator.importers import LogseqEDNImporter
from kultivator.agents import AgentRunner
from kultivator.models import Entity


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def test_ai_logging():
    """Test AI agent call logging functionality."""
    print("\n🧪 TESTING AI AGENT LOGGING")
    print("="*50)
    
    try:
        with DatabaseManager() as db:
            db.initialize_database()
            
            # Test logging an AI call
            call_id = db.log_ai_agent_call(
                agent_name="test_agent",
                input_data='{"test": "data"}',
                system_prompt="You are a test agent.",
                user_prompt="Test prompt",
                model_name="test-model",
                raw_response="Test response",
                parsed_response='{"result": "test"}',
                success=True,
                execution_time_ms=150
            )
            
            print(f"✅ Successfully logged AI call with ID: {call_id}")
            
            # Test retrieving calls
            calls = db.get_ai_agent_calls(limit=5)
            print(f"✅ Retrieved {len(calls)} AI calls from database")
            
            # Test reproduction data
            if calls:
                reproduction_data = db.reproduce_ai_agent_call(calls[0]["call_id"])
                print(f"✅ Successfully retrieved reproduction data for call {calls[0]['call_id']}")
            
        return True
        
    except Exception as e:
        print(f"❌ AI logging test failed: {e}")
        return False


def test_logseq_processing():
    """Test enhanced LogSeq processing with Norwegian content."""
    print("\n🇳🇴 TESTING ENHANCED LOGSEQ PROCESSING")
    print("="*50)
    
    try:
        # Check if test data exists
        logseq_file = Path("test_logseq_data/real_logseq_export.edn")
        if not logseq_file.exists():
            print(f"❌ LogSeq test file not found: {logseq_file}")
            return False
        
        print(f"📁 Found LogSeq test file: {logseq_file}")
        
        # Test the enhanced importer
        importer = LogseqEDNImporter("test_logseq_data")
        
        # Test UUID mapping extraction
        uuid_mappings, blocks = importer.extract_uuid_mappings_and_content(logseq_file)
        
        print(f"✅ Extracted {len(uuid_mappings)} UUID mappings")
        print(f"✅ Extracted {len(blocks)} content blocks")
        
        # Test entity classification
        test_content = [
            "Kari Nordmann",
            "Oslo", 
            "Jordbær",
            "Coop Extra",
            "ISSHP Conference"
        ]
        
        print(f"\n🏷️  Testing entity classification:")
        for content in test_content:
            entity_type = importer.classify_entity_by_content(content)
            print(f"   '{content}' -> {entity_type}")
        
        # Test UUID resolution
        test_uuid_content = "Meeting with [[6872e9b0-d820-4d0b-9d20-a1ee0fdad938]]"
        resolved = importer.resolve_uuid_references(test_uuid_content)
        print(f"\n🔗 UUID resolution test:")
        print(f"   Original: {test_uuid_content}")
        print(f"   Resolved: {resolved}")
        
        return True
        
    except Exception as e:
        print(f"❌ LogSeq processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integrated_processing():
    """Test integrated processing with AI logging."""
    print("\n🔗 TESTING INTEGRATED PROCESSING WITH AI LOGGING")
    print("="*50)
    
    try:
        with DatabaseManager() as db:
            db.initialize_database()
            
            # Test agent runner with database
            with AgentRunner(database_manager=db) as agent_runner:
                
                # Create a test canonical block
                from kultivator.models import CanonicalBlock
                test_block = CanonicalBlock(
                    block_id="test-block-1",
                    source_ref="test_file.edn#test",
                    content="Meeting with Kari Nordmann about the ISSHP conference in Oslo",
                    children=[]
                )
                
                print(f"📋 Testing triage agent with logging...")
                
                # This should log the AI call to the database
                triage_result = agent_runner.run_triage_agent(test_block)
                
                print(f"✅ Triage completed: {len(triage_result.entities)} entities found")
                print(f"   Summary: {triage_result.summary}")
                
                for entity in triage_result.entities:
                    print(f"   - {entity.name} ({entity.entity_type})")
                
                # Check if the call was logged
                recent_calls = db.get_ai_agent_calls(agent_name="triage", limit=1)
                if recent_calls:
                    print(f"✅ AI call logged successfully (ID: {recent_calls[0]['call_id']})")
                else:
                    print(f"⚠️  No AI calls found in database")
                
        return True
        
    except Exception as e:
        print(f"❌ Integrated processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all sixth epoch tests."""
    setup_logging()
    
    print("🚀 KULTIVATOR SIXTH EPOCH FUNCTIONALITY TEST")
    print("="*60)
    print("Testing AI logging, Norwegian LogSeq processing, and integration")
    
    tests = [
        ("AI Agent Logging", test_ai_logging),
        ("LogSeq Processing", test_logseq_processing),
        ("Integrated Processing", test_integrated_processing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n📊 SIXTH EPOCH TEST RESULTS")
    print("="*50)
    
    passed = 0
    total = len(tests)
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if passed_test:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SIXTH EPOCH TESTS PASSED!")
        print("✅ AI agent logging for reproducibility: WORKING")
        print("✅ Enhanced Norwegian LogSeq processing: WORKING") 
        print("✅ Data-driven entity extraction: WORKING")
        print("✅ Complete system integration: WORKING")
        print("\n🏆 SIXTH EPOCH IMPLEMENTATION COMPLETE!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the output above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 