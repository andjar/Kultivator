#!/usr/bin/env python3
"""
Example: Adding a Custom Research Agent

This example demonstrates how to add a custom research agent to Kultivator
by modifying the configuration file and using the new agent system.
"""

import yaml
import tempfile
import os
from pathlib import Path

def create_custom_config():
    """Create a configuration file with a custom research agent."""
    
    config = {
        'ai': {
            'ollama_host': 'http://localhost:11434',
            'model': 'gemma3',
            'timeout': 30.0
        },
        'agents': {
            'max_retries': 3,
            'enable_tools': True,
            'context_limit': 5,
            'definitions': {
                'research_agent': {
                    'description': 'Organizes and manages research information and references',
                    'system_prompt': '''You are a research management assistant. Your role is to organize research information, manage references, and help structure academic or professional research projects.

Your capabilities:
1. Extract research topics, questions, and hypotheses from content
2. Organize research materials and references
3. Create structured research overviews and literature reviews
4. Track research progress and findings
5. Identify knowledge gaps and research opportunities
6. Suggest research methodologies and approaches

Always provide well-structured research information in Markdown format.
Use proper academic formatting and citation styles where appropriate.
Include research questions, methodologies, findings, and conclusions.''',
                    'user_prompt_template': '''Analyze this research-related content:

Content: {content}
Source: {source_ref}
Entity Name: {entity_name}
Entity Type: {entity_type}

KNOWLEDGE BASE CONTEXT:
{context_info}

Create a comprehensive research page that includes:
- Research questions and objectives
- Methodology and approach
- Key findings and insights
- References and citations
- Future research directions
- Related research areas

Format everything as a structured academic-style document in Markdown.''',
                    'available_tools': ['list_entities', 'get_entity_context'],
                    'requires_database': True,
                    'timeout': 45.0
                },
                'meeting_organizer': {
                    'description': 'Organizes and manages meeting information and action items',
                    'system_prompt': '''You are a meeting management assistant. Your role is to organize meeting information, track action items, and help manage meeting-related tasks.

Your capabilities:
1. Extract meeting details, attendees, and agenda items
2. Identify action items and assignments
3. Track meeting decisions and outcomes
4. Create structured meeting summaries
5. Identify follow-up tasks and deadlines
6. Organize meeting series and recurring meetings

Always provide clear, actionable meeting information in Markdown format.
Use proper formatting for meeting minutes, action items, and follow-ups.''',
                    'user_prompt_template': '''Organize this meeting-related content:

Content: {content}
Source: {source_ref}
Entity Name: {entity_name}
Entity Type: {entity_type}

KNOWLEDGE BASE CONTEXT:
{context_info}

Create a comprehensive meeting page that includes:
- Meeting details (date, time, attendees)
- Agenda and discussion topics
- Key decisions and outcomes
- Action items with assignments and deadlines
- Follow-up meetings and next steps
- Related meetings and context

Format everything as professional meeting minutes in Markdown.''',
                    'available_tools': ['list_entities', 'get_entity_context'],
                    'requires_database': True,
                    'timeout': 30.0
                }
            }
        },
        'wiki': {
            'file_extension': '.md',
            'entity_directories': {
                'person': 'People',
                'project': 'Projects',
                'place': 'Places',
                'company': 'Companies',
                'book': 'Books',
                'research': 'Research',
                'meeting': 'Meetings',
                'other': 'Other'
            }
        }
    }
    
    return config

def demonstrate_custom_agent():
    """Demonstrate the custom research agent functionality."""
    
    print("🔬 Custom Research Agent Demo")
    print("=" * 50)
    
    # Create temporary config file
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / "custom_config.yaml"
    
    try:
        # Write custom configuration
        config = create_custom_config()
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Created custom configuration at {config_path}")
        
        # Import and initialize with custom config
        from kultivator.config import ConfigManager
        from kultivator.agents.manager import AgentManager
        
        # Create config manager with custom config
        config_manager = ConfigManager(str(config_path))
        
        # Create agent manager with custom config
        agent_manager = AgentManager(config_manager=config_manager)
        
        # Show available agents
        print("\n📋 Available Agents:")
        agents = agent_manager.list_agents()
        for agent_name in agents:
            agent_def = agent_manager.get_agent_definition(agent_name)
            if agent_def:
                print(f"   - {agent_name}: {agent_def.description}")
        
        # Focus on custom agents
        custom_agents = ['research_agent', 'meeting_organizer']
        
        print("\n🎯 Custom Agent Details:")
        for agent_name in custom_agents:
            if agent_name in agents:
                agent_def = agent_manager.get_agent_definition(agent_name)
                print(f"\n   {agent_name.replace('_', ' ').title()}:")
                print(f"   - Description: {agent_def.description}")
                print(f"   - Tools: {', '.join(agent_def.available_tools)}")
                print(f"   - Database required: {agent_def.requires_database}")
                print(f"   - Timeout: {agent_def.timeout}s")
        
        # Validate custom agents
        print("\n✅ Agent Validation:")
        for agent_name in custom_agents:
            if agent_name in agents:
                validation = agent_manager.validate_agent_definition(agent_name)
                status = "✅ Valid" if validation['valid'] else "❌ Invalid"
                print(f"   - {agent_name}: {status}")
                if validation['warnings']:
                    for warning in validation['warnings']:
                        print(f"     ⚠️  {warning}")
                if validation['errors']:
                    for error in validation['errors']:
                        print(f"     ❌ {error}")
        
        # Demonstrate template rendering
        print("\n📝 Template Rendering Demo:")
        
        # Example research content
        research_vars = {
            'content': '''Literature review on machine learning applications in healthcare.
            Key papers: Smith et al. (2024) on neural networks for diagnosis,
            Jones & Brown (2023) on ethical considerations in AI healthcare.
            Research question: How can ML improve diagnostic accuracy while maintaining patient privacy?''',
            'entity_name': 'ML Healthcare Research',
            'entity_type': 'research',
            'source_ref': 'research/ml-healthcare-2024.md',
            'created_at': '2024-01-15T10:30:00Z',
            'updated_at': '2024-01-15T10:30:00Z',
            'current_time': '2024-01-15T10:30:00Z',
            'context_info': 'Related research: AI Ethics Project, Healthcare Data Analysis'
        }
        
        # Example meeting content
        meeting_vars = {
            'content': '''Weekly team meeting - Project Alpha status update.
            Attendees: Alice (PM), Bob (Dev), Carol (Design)
            Action items: Bob to fix login bug by Friday, Carol to update mockups.
            Next meeting: Thursday 2PM to review progress.''',
            'entity_name': 'Project Alpha Weekly',
            'entity_type': 'meeting',
            'source_ref': 'meetings/2024-01-15-alpha-weekly.md',
            'created_at': '2024-01-15T10:30:00Z',
            'updated_at': '2024-01-15T10:30:00Z',
            'current_time': '2024-01-15T10:30:00Z',
            'context_info': 'Related meetings: Project Alpha Kickoff, Design Review'
        }
        
        # Test research agent template
        if 'research_agent' in agents:
            try:
                research_prompt = agent_manager.render_user_prompt('research_agent', **research_vars)
                print(f"\n   Research Agent Template:")
                print(f"   {'-' * 40}")
                print(f"   {research_prompt[:300]}...")
            except Exception as e:
                print(f"   Research Agent: Error - {e}")
        
        # Test meeting organizer template
        if 'meeting_organizer' in agents:
            try:
                meeting_prompt = agent_manager.render_user_prompt('meeting_organizer', **meeting_vars)
                print(f"\n   Meeting Organizer Template:")
                print(f"   {'-' * 40}")
                print(f"   {meeting_prompt[:300]}...")
            except Exception as e:
                print(f"   Meeting Organizer: Error - {e}")
        
        # Show configuration snippet
        print("\n⚙️  Configuration Snippet:")
        print("   Add this to your config.yaml to use these custom agents:")
        print()
        print('''   agents:
     definitions:
       research_agent:
         description: "Organizes and manages research information and references"
         system_prompt: "You are a research management assistant..."
         user_prompt_template: "Analyze this research-related content: {content}"
         available_tools: ["list_entities", "get_entity_context"]
         requires_database: true
         timeout: 45.0''')
        
        print("\n📚 Usage Example:")
        print('''   # Use the custom agent in your code
   from kultivator.agents.runner import AgentRunner
   from kultivator.models import Entity, CanonicalBlock
   
   runner = AgentRunner(database_manager=db)
   content = runner.run_specialized_agent(
       "research_agent",
       entity,
       "Research summary",
       block
   )''')
        
        print("\n✅ Custom agent demo completed!")
        print("\n📋 Next steps:")
        print("   1. Copy the configuration to your config.yaml")
        print("   2. Modify the prompts for your specific needs")
        print("   3. Add more custom agents as needed")
        print("   4. Use agent_manager.validate_agent_definition() to test changes")
        print("   5. Call runner.run_specialized_agent() to use your custom agents")
        
    finally:
        # Clean up
        if config_path.exists():
            config_path.unlink()
        os.rmdir(temp_dir)

if __name__ == "__main__":
    demonstrate_custom_agent()