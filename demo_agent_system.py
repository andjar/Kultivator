#!/usr/bin/env python3
"""
Example script demonstrating the improved AI agent system in Kultivator.

This script shows how to use the new configuration-based agents,
template system, and specialized agents.
"""

import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate the new AI agent system."""
    
    try:
        # Import the new agent system
        from kultivator.agents import agent_manager, AgentManager
        from kultivator.agents.runner import AgentRunner
        from kultivator.models import Entity, CanonicalBlock
        from kultivator.config import config
        
        print("🌱 Kultivator AI Agent System Demo")
        print("=" * 50)
        
        # 1. Show available agents
        print("\n1. Available Agents:")
        agents = agent_manager.list_agents()
        for agent_name in agents:
            agent_def = agent_manager.get_agent_definition(agent_name)
            if agent_def:
                print(f"   - {agent_name}: {agent_def.description}")
        
        # 2. Show agent validation
        print("\n2. Agent Validation:")
        for agent_name in agents:
            validation = agent_manager.validate_agent_definition(agent_name)
            status = "✅ Valid" if validation['valid'] else "❌ Invalid"
            print(f"   - {agent_name}: {status}")
            if validation['warnings']:
                for warning in validation['warnings']:
                    print(f"     ⚠️  {warning}")
            if validation['errors']:
                for error in validation['errors']:
                    print(f"     ❌ {error}")
        
        # 3. Show template rendering
        print("\n3. Template Rendering Demo:")
        
        # Example template variables
        template_vars = {
            'content': 'Meeting with John about the new project roadmap',
            'entity_name': 'Project Alpha',
            'entity_type': 'project',
            'source_ref': 'daily-notes/2024-01-15.md',
            'created_at': '2024-01-15T10:30:00Z',
            'updated_at': '2024-01-15T10:30:00Z',
            'current_time': '2024-01-15T10:30:00Z',
            'context_info': 'Related projects: Project Beta, Project Gamma'
        }
        
        # Try rendering different agent templates
        for agent_name in ['triage', 'task_manager', 'travel_planner']:
            if agent_name in agents:
                try:
                    rendered = agent_manager.render_user_prompt(agent_name, **template_vars)
                    print(f"\n   {agent_name} template:")
                    print(f"   {'-' * 40}")
                    print(f"   {rendered[:200]}...")
                except Exception as e:
                    print(f"   {agent_name}: Error - {e}")
        
        # 4. Show specialized agent capabilities
        print("\n4. Specialized Agent Features:")
        
        specialized_agents = ['task_manager', 'travel_planner']
        for agent_name in specialized_agents:
            if agent_name in agents:
                agent_def = agent_manager.get_agent_definition(agent_name)
                if agent_def:
                    print(f"\n   {agent_name.replace('_', ' ').title()}:")
                    print(f"   - Tools: {', '.join(agent_def.available_tools)}")
                    print(f"   - Database required: {agent_def.requires_database}")
                    print(f"   - Timeout: {agent_def.timeout}s")
                    
                    # Extract key capabilities from system prompt
                    system_prompt = agent_def.system_prompt
                    if "capabilities:" in system_prompt.lower():
                        capabilities_section = system_prompt.split("capabilities:")[1].split("\n\n")[0]
                        print(f"   - Key capabilities: {capabilities_section.strip()[:100]}...")
        
        # 5. Show configuration customization
        print("\n5. Configuration Customization:")
        print("   The new system allows you to:")
        print("   - Modify agent prompts in config.yaml without code changes")
        print("   - Add new specialized agents through configuration")
        print("   - Customize prompt templates for different use cases")
        print("   - Validate agent definitions for correctness")
        
        # 6. Configuration example
        print("\n6. Configuration Example:")
        print("   To add a new agent, add to config.yaml:")
        example_config = """
   agents:
     definitions:
       my_custom_agent:
         description: "Custom agent for specific domain"
         system_prompt: "You are a specialized assistant for..."
         user_prompt_template: "Process this {content} for {entity_name}"
         available_tools: ["list_entities"]
         requires_database: true
         timeout: 30.0
"""
        print(example_config)
        
        print("\n✅ Demo completed successfully!")
        print("\nNext steps:")
        print("- Modify config.yaml to customize agent behavior")
        print("- Add new specialized agents for your domain")
        print("- Use agent_manager.validate_agent_definition() to check changes")
        print("- Call agent_runner.run_specialized_agent() to use custom agents")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the Kultivator directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Demo failed")


if __name__ == "__main__":
    main()