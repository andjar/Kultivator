# Enhanced AI Agent System

The Kultivator AI agent system has been significantly improved to provide better flexibility, easier customization, and support for specialized agents. This document describes the new features and how to use them.

## Overview

The enhanced system introduces:

1. **Configuration-based agents**: Define agents in `config.yaml` instead of code
2. **Template system**: Dynamic user prompt generation with variables
3. **Specialized agents**: Pre-configured agents for specific domains (tasks, travel, etc.)
4. **Agent validation**: Validate agent definitions for correctness
5. **Backward compatibility**: Existing code continues to work

## Key Components

### AgentManager
Central manager for configuration-based agents with template support.

### AgentDefinition
Data structure representing a complete agent configuration loaded from YAML.

### Template System
Dynamic prompt generation using Python's `str.format()` method with `{variable}` syntax.

## Configuration

### Basic Agent Structure

```yaml
agents:
  definitions:
    my_agent:
      description: "Brief description of the agent"
      system_prompt: |
        Multi-line system prompt that defines the agent's role,
        capabilities, and behavior guidelines.
      user_prompt_template: |
        Template for user prompts with {variables} that will be
        replaced with actual values at runtime.
      available_tools: ["list_entities", "get_entity_context"]
      requires_database: true
      timeout: 30.0
```

### Template Variables

Common template variables available:

- `{content}`: Raw content from the block
- `{entity_name}`: Name of the entity being processed
- `{entity_type}`: Type of entity (person, project, etc.)
- `{source_ref}`: Reference to the source block
- `{created_at}`: Creation timestamp
- `{updated_at}`: Last updated timestamp
- `{current_time}`: Current processing time
- `{context_info}`: Knowledge base context
- `{existing_content}`: Existing content for merge operations
- `{summary}`: Summary of new information

## Pre-configured Specialized Agents

### Task Manager (`task_manager`)
Specialized for organizing and tracking tasks and project information.

**Capabilities:**
- Extract tasks, deadlines, and priorities
- Identify project dependencies and relationships
- Create structured task lists and project overviews
- Track task status and progress
- Suggest task categorization and prioritization

**Use cases:**
- Project management notes
- Task tracking and organization
- Deadline management
- Progress tracking

### Travel Planner (`travel_planner`)
Specialized for travel information organization and itinerary planning.

**Capabilities:**
- Extract travel dates, destinations, and activities
- Create structured itineraries and travel plans
- Identify travel-related entities (places, accommodations, activities)
- Organize travel information by trip or destination
- Track travel expenses and bookings

**Use cases:**
- Travel planning and itineraries
- Trip organization
- Travel expense tracking
- Destination information management

## Usage Examples

### Basic Agent Usage

```python
from kultivator.agents import agent_manager, AgentRunner

# List available agents
agents = agent_manager.list_agents()
print("Available agents:", agents)

# Get agent definition
agent_def = agent_manager.get_agent_definition("task_manager")
print("Description:", agent_def.description)

# Validate agent
validation = agent_manager.validate_agent_definition("task_manager")
if validation['valid']:
    print("Agent is valid")
else:
    print("Errors:", validation['errors'])
```

### Template Rendering

```python
# Render a user prompt
template_vars = {
    'content': 'Meeting with John about project deadlines',
    'entity_name': 'Project Alpha',
    'entity_type': 'project',
    'source_ref': 'notes/2024-01-15.md'
}

prompt = agent_manager.render_user_prompt("task_manager", **template_vars)
print("Rendered prompt:", prompt)
```

### Using Specialized Agents

```python
from kultivator.agents.runner import AgentRunner
from kultivator.models import Entity, CanonicalBlock

# Create test data
entity = Entity(name="European Trip", entity_type="travel")
block = CanonicalBlock(
    block_id="travel-1",
    content="Flight to Paris on March 15, hotel booking at Hotel Louvre",
    source_ref="travel/europe-2024.md",
    created_at=1234567890,
    updated_at=1234567890
)

# Run specialized agent
runner = AgentRunner(database_manager=db)
content = runner.run_specialized_agent(
    "travel_planner",
    entity,
    "New travel information",
    block
)
print("Generated content:", content)
```

## Adding Custom Agents

### 1. Define in Configuration

Add to `config.yaml`:

```yaml
agents:
  definitions:
    finance_manager:
      description: "Manages financial information and expense tracking"
      system_prompt: |
        You are a financial management assistant. Your role is to organize
        financial information, track expenses, and provide financial insights.
        
        Your capabilities:
        1. Extract financial data from notes
        2. Categorize expenses and income
        3. Create financial summaries and reports
        4. Track budgets and financial goals
        5. Identify financial trends and patterns
        
        Always provide clear, accurate financial information in Markdown format.
      user_prompt_template: |
        Analyze this financial content:
        
        Content: {content}
        Source: {source_ref}
        Entity Name: {entity_name}
        Entity Type: {entity_type}
        
        KNOWLEDGE BASE CONTEXT:
        {context_info}
        
        Create a structured financial page with:
        - Income and expense categorization
        - Budget tracking
        - Financial goals and progress
        - Spending patterns and insights
      available_tools: ["list_entities", "get_entity_context"]
      requires_database: true
      timeout: 30.0
```

### 2. Use the Custom Agent

```python
# The agent is automatically available after config reload
agent_manager.reload_definitions()

# Validate the new agent
validation = agent_manager.validate_agent_definition("finance_manager")
if validation['valid']:
    print("Custom agent is ready to use!")

# Use the agent
runner = AgentRunner(database_manager=db)
content = runner.run_specialized_agent(
    "finance_manager",
    entity,
    "Monthly expenses summary",
    block
)
```

## Agent Validation

The system includes comprehensive validation:

```python
# Validate an agent definition
validation = agent_manager.validate_agent_definition("my_agent")

print("Valid:", validation['valid'])
print("Errors:", validation['errors'])
print("Warnings:", validation['warnings'])
```

### Validation Checks

- **Required fields**: Description, system_prompt, user_prompt_template
- **Empty prompts**: System prompt and template cannot be empty
- **Template variables**: Checks for recommended variables
- **Tool availability**: Warns about unknown tools
- **Timeout values**: Must be positive
- **Agent existence**: Verifies agent exists in configuration

## Migration Guide

### From Hard-coded Agents

Old approach:
```python
# Hard-coded in registry.py
agent_registry.register_agent(AgentConfig(
    name="my_agent",
    description="My agent",
    system_prompt="You are my agent...",
    # ... other config
))
```

New approach:
```yaml
# In config.yaml
agents:
  definitions:
    my_agent:
      description: "My agent"
      system_prompt: "You are my agent..."
      user_prompt_template: "Process: {content}"
      # ... other config
```

### Updating Existing Code

The new system is backward compatible. Existing code will continue to work, but you can gradually migrate to the new system:

1. Move agent definitions from code to `config.yaml`
2. Use `agent_manager` instead of `agent_registry` for new features
3. Leverage template system for dynamic prompts
4. Use specialized agents where appropriate

## Best Practices

### 1. Agent Design

- **Clear purpose**: Each agent should have a specific, well-defined purpose
- **Comprehensive prompts**: Include detailed instructions and examples
- **Proper tools**: Only include tools the agent actually needs
- **Reasonable timeouts**: Set appropriate timeouts for agent complexity

### 2. Template Design

- **Descriptive variables**: Use clear, descriptive variable names
- **Consistent format**: Maintain consistent template structure
- **Required vs optional**: Clearly distinguish required from optional variables
- **Fallback handling**: Consider what happens with missing variables

### 3. Configuration Management

- **Version control**: Keep config.yaml in version control
- **Validation**: Always validate agents after configuration changes
- **Documentation**: Document custom agents and their intended use
- **Testing**: Test custom agents thoroughly before deployment

## Troubleshooting

### Common Issues

1. **Template rendering errors**: Check variable names and availability
2. **Agent not found**: Verify agent name in configuration
3. **Validation failures**: Check required fields and syntax
4. **Import errors**: Ensure proper imports and module structure

### Debug Mode

Enable debug logging to see detailed agent execution:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run your agent code
```

### Validation Tool

Use the validation tool to check agent definitions:

```python
from kultivator.agents import agent_manager

# Validate all agents
for agent_name in agent_manager.list_agents():
    validation = agent_manager.validate_agent_definition(agent_name)
    if not validation['valid']:
        print(f"Agent {agent_name} has issues:")
        for error in validation['errors']:
            print(f"  Error: {error}")
        for warning in validation['warnings']:
            print(f"  Warning: {warning}")
```

## Future Enhancements

The new system provides a foundation for future enhancements:

1. **Multi-language support**: Different prompts for different languages
2. **Agent plugins**: Pluggable agent systems
3. **Advanced templates**: More sophisticated templating features
4. **Agent chaining**: Chain multiple agents together
5. **Performance optimization**: Caching and optimization features

## Conclusion

The enhanced AI agent system provides a more flexible, maintainable, and extensible approach to AI agent management in Kultivator. By moving configuration out of code and into YAML files, users can easily customize and extend the system without modifying the codebase.

The specialized agents (task management, travel planning) demonstrate the power of this approach, while the template system enables dynamic prompt generation for various use cases.

This system maintains backward compatibility while providing a clear path forward for future enhancements and customizations.