#!/usr/bin/env python3
"""
Kultivator AI Inspector - Tool for inspecting and reproducing AI agent calls.

This tool provides reproducibility features for the Kultivator system by allowing
users to inspect, query, and reproduce AI agent interactions logged in the database.
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Optional, List
from kultivator.database import DatabaseManager
from kultivator.agents import AgentRunner
from kultivator.config import config


def setup_logging():
    """Configure logging for the inspector."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def list_ai_calls(
    agent_name: Optional[str] = None,
    success_only: bool = False,
    limit: int = 10
):
    """List recent AI agent calls."""
    print(f"\n{'='*60}")
    print("KULTIVATOR AI AGENT CALL LOG")
    print(f"{'='*60}")
    
    with DatabaseManager() as db:
        db.initialize_database()
        
        calls = db.get_ai_agent_calls(
            agent_name=agent_name,
            success_only=success_only,
            limit=limit
        )
        
        if not calls:
            print("No AI agent calls found.")
            return
        
        print(f"\nFound {len(calls)} calls:")
        print(f"{'ID':<6} {'Agent':<15} {'Success':<8} {'Time (ms)':<10} {'Called At':<20}")
        print("-" * 70)
        
        for call in calls:
            success_symbol = "✅" if call["success"] else "❌"
            execution_time = call["execution_time_ms"] or 0
            called_at = call["called_at"][:19] if call["called_at"] else "Unknown"
            
            print(f"{call['call_id']:<6} {call['agent_name']:<15} {success_symbol:<8} {execution_time:<10} {called_at:<20}")


def show_call_details(call_id: int):
    """Show detailed information about a specific AI call."""
    print(f"\n{'='*60}")
    print(f"AI AGENT CALL DETAILS - ID: {call_id}")
    print(f"{'='*60}")
    
    with DatabaseManager() as db:
        db.initialize_database()
        
        call = db.reproduce_ai_agent_call(call_id)
        
        if not call:
            print(f"❌ Call ID {call_id} not found.")
            return
        
        # Basic info
        print(f"\n📋 BASIC INFORMATION")
        print(f"   Agent Name: {call['agent_name']}")
        print(f"   Model: {call['model_name']}")
        print(f"   Success: {'✅ Yes' if call['success'] else '❌ No'}")
        print(f"   Execution Time: {call['execution_time_ms']}ms")
        print(f"   Called At: {call['called_at']}")
        
        if call['error_message']:
            print(f"   Error: {call['error_message']}")
        
        # Context
        print(f"\n🔗 CONTEXT")
        if call['block_id']:
            print(f"   Block ID: {call['block_id']}")
        if call['entity_name']:
            print(f"   Entity Name: {call['entity_name']}")
        
        # Input data
        print(f"\n📥 INPUT DATA")
        try:
            input_data = json.loads(call['input_data'])
            print(json.dumps(input_data, indent=2))
        except:
            print(call['input_data'])
        
        # System prompt
        if call['system_prompt']:
            print(f"\n🤖 SYSTEM PROMPT")
            print(call['system_prompt'])
        
        # User prompt
        print(f"\n👤 USER PROMPT")
        print(call['user_prompt'])
        
        # Raw response
        print(f"\n📤 RAW RESPONSE")
        print(call['raw_response'])
        
        # Parsed response
        if call['parsed_response']:
            print(f"\n🔄 PARSED RESPONSE")
            try:
                parsed = json.loads(call['parsed_response'])
                print(json.dumps(parsed, indent=2))
            except:
                print(call['parsed_response'])


def reproduce_call(call_id: int, dry_run: bool = True):
    """Reproduce a specific AI agent call."""
    print(f"\n{'='*60}")
    print(f"REPRODUCING AI AGENT CALL - ID: {call_id}")
    print(f"{'='*60}")
    
    with DatabaseManager() as db:
        db.initialize_database()
        
        call = db.reproduce_ai_agent_call(call_id)
        
        if not call:
            print(f"❌ Call ID {call_id} not found.")
            return
        
        print(f"🔄 Reproducing call to {call['agent_name']} agent...")
        print(f"   Original call made at: {call['called_at']}")
        print(f"   Model: {call['model_name']}")
        
        if dry_run:
            print(f"\n🧪 DRY RUN MODE - No actual AI call will be made")
            print(f"\nWould call Ollama with:")
            print(f"   Model: {call['model_name']}")
            print(f"   System Prompt: {call['system_prompt'][:100]}..." if call['system_prompt'] else "   No system prompt")
            print(f"   User Prompt: {call['user_prompt'][:100]}...")
            return
        
        # Actual reproduction
        print(f"\n🚀 Making actual AI call...")
        try:
            with AgentRunner(database_manager=db) as agent_runner:
                # Override model if different
                if agent_runner.model != call['model_name']:
                    print(f"⚠️  Model mismatch: Using {agent_runner.model} instead of {call['model_name']}")
                
                start_time = datetime.now()
                response = agent_runner._call_ollama_sync(
                    prompt=call['user_prompt'],
                    system_prompt=call['system_prompt'] or "",
                    agent_name=f"reproduction_{call['agent_name']}",
                    input_data=call['input_data']
                )
                end_time = datetime.now()
                
                execution_time = int((end_time - start_time).total_seconds() * 1000)
                
                print(f"\n✅ Reproduction completed in {execution_time}ms")
                print(f"\n📤 NEW RESPONSE:")
                print(response)
                
                print(f"\n🔍 COMPARISON:")
                print(f"Original length: {len(call['raw_response'])} chars")
                print(f"New length: {len(response)} chars")
                
                if response.strip() == call['raw_response'].strip():
                    print("✅ Responses are identical!")
                else:
                    print("⚠️  Responses differ (expected for non-deterministic models)")
                
        except Exception as e:
            print(f"❌ Reproduction failed: {e}")


def analyze_agent_performance():
    """Analyze performance statistics of AI agents."""
    print(f"\n{'='*60}")
    print("AI AGENT PERFORMANCE ANALYSIS")
    print(f"{'='*60}")
    
    with DatabaseManager() as db:
        db.initialize_database()
        
        # Get all calls
        all_calls = db.get_ai_agent_calls()
        
        if not all_calls:
            print("No AI agent calls found.")
            return
        
        # Analyze by agent
        agent_stats = {}
        for call in all_calls:
            agent_name = call['agent_name']
            if agent_name not in agent_stats:
                agent_stats[agent_name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_time_ms': 0,
                    'avg_time_ms': 0
                }
            
            stats = agent_stats[agent_name]
            stats['total_calls'] += 1
            
            if call['success']:
                stats['successful_calls'] += 1
            else:
                stats['failed_calls'] += 1
            
            if call['execution_time_ms']:
                stats['total_time_ms'] += call['execution_time_ms']
        
        # Calculate averages
        for agent_name, stats in agent_stats.items():
            if stats['total_calls'] > 0:
                stats['avg_time_ms'] = stats['total_time_ms'] / stats['total_calls']
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls'] * 100
        
        # Display results
        print(f"\n📊 AGENT STATISTICS:")
        print(f"{'Agent':<20} {'Calls':<8} {'Success Rate':<12} {'Avg Time (ms)':<15}")
        print("-" * 60)
        
        for agent_name, stats in agent_stats.items():
            print(f"{agent_name:<20} {stats['total_calls']:<8} {stats['success_rate']:.1f}%{'':<7} {stats['avg_time_ms']:.1f}")
        
        print(f"\n📈 OVERALL STATISTICS:")
        total_calls = len(all_calls)
        successful_calls = sum(1 for call in all_calls if call['success'])
        overall_success_rate = successful_calls / total_calls * 100 if total_calls > 0 else 0
        
        print(f"   Total Calls: {total_calls}")
        print(f"   Successful Calls: {successful_calls}")
        print(f"   Failed Calls: {total_calls - successful_calls}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")


def main():
    """Main CLI entry point."""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="Kultivator AI Inspector - Tool for inspecting and reproducing AI agent calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                           # List recent AI calls
  %(prog)s list --agent triage           # List calls from triage agent only
  %(prog)s list --success-only --limit 5 # List 5 most recent successful calls
  %(prog)s show 42                       # Show details of call ID 42
  %(prog)s reproduce 42                  # Reproduce call ID 42 (dry run)
  %(prog)s reproduce 42 --execute        # Actually reproduce call ID 42
  %(prog)s analyze                       # Show performance analysis
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List AI agent calls')
    list_parser.add_argument('--agent', help='Filter by agent name')
    list_parser.add_argument('--success-only', action='store_true', help='Show only successful calls')
    list_parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10)')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show detailed information about a specific call')
    show_parser.add_argument('call_id', type=int, help='Call ID to show')
    
    # Reproduce command
    reproduce_parser = subparsers.add_parser('reproduce', help='Reproduce a specific AI agent call')
    reproduce_parser.add_argument('call_id', type=int, help='Call ID to reproduce')
    reproduce_parser.add_argument('--execute', action='store_true', help='Actually execute the call (default is dry run)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze AI agent performance')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            list_ai_calls(
                agent_name=args.agent,
                success_only=args.success_only,
                limit=args.limit
            )
        elif args.command == 'show':
            show_call_details(args.call_id)
        elif args.command == 'reproduce':
            reproduce_call(args.call_id, dry_run=not args.execute)
        elif args.command == 'analyze':
            analyze_agent_performance()
        
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.exception("Unexpected error")


if __name__ == "__main__":
    main() 