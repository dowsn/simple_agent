#!/usr/bin/env python3
"""
Script to automatically update Zapier tools documentation.
Run this periodically to keep the tools list current.
"""

import asyncio
import json
from datetime import datetime
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent


async def get_zapier_tools():
    """Fetch current Zapier MCP tools."""
    
    app = MCPApp(name="zapier_tools_updater")
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        zapier_agent = Agent(
            name="zapier_lister",
            instruction="List available tools",
            server_names=["zapier"]
        )
        
        async with zapier_agent:
            tools_result = await zapier_agent.list_tools()
            
            tools_dict = {}
            for tool in tools_result.tools:
                # Handle inputSchema as dict or object
                input_schema = None
                if tool.inputSchema:
                    if hasattr(tool.inputSchema, 'model_dump'):
                        input_schema = tool.inputSchema.model_dump()
                    else:
                        input_schema = tool.inputSchema
                
                tools_dict[tool.name] = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": input_schema
                }
            
            return tools_dict


def categorize_tools(tools_dict):
    """Categorize tools by functionality."""
    categories = {
        "Google Sheets": [],
        "Gmail": [],
        "LinkedIn": [],
        "Firecrawl": [],
        "Other": []
    }
    
    batch_operations = []
    
    for name, info in tools_dict.items():
        # Categorize
        if "google_sheets" in name:
            categories["Google Sheets"].append(info)
            # Check for batch operations
            if any(keyword in name.lower() for keyword in ['multiple', 'rows', 'many']):
                batch_operations.append(name)
        elif "gmail" in name:
            categories["Gmail"].append(info)
        elif "linkedin" in name:
            categories["LinkedIn"].append(info)
        elif "firecrawl" in name:
            categories["Firecrawl"].append(info)
        else:
            categories["Other"].append(info)
    
    return categories, batch_operations


def generate_markdown_docs(tools_dict, categories, batch_operations):
    """Generate markdown documentation."""
    
    timestamp = datetime.now().isoformat()
    
    md_content = f"""# Zapier MCP Tools Reference
*Auto-generated on {timestamp}*

## Summary
- Total tools available: {len(tools_dict)}
- Google Sheets tools: {len(categories['Google Sheets'])}
- Gmail tools: {len(categories['Gmail'])}
- LinkedIn tools: {len(categories['LinkedIn'])}
- Firecrawl tools: {len(categories['Firecrawl'])}
- Batch operations: {len(batch_operations)}

## Google Sheets Tools

### Batch Operations (Optimized for Multiple Items)
"""
    
    # List batch operations
    for name in batch_operations:
        tool = tools_dict[name]
        md_content += f"- **`{name}`** - {tool['description']}\n"
    
    md_content += "\n### Single Operations\n"
    
    # List single operations
    for tool in categories["Google Sheets"]:
        if tool['name'] not in batch_operations:
            md_content += f"- `{tool['name']}` - {tool['description']}\n"
    
    # Add other categories
    md_content += "\n## Gmail Tools\n"
    for tool in categories["Gmail"][:5]:  # Show first 5
        md_content += f"- `{tool['name']}` - {tool['description']}\n"
    
    if len(categories["Gmail"]) > 5:
        md_content += f"*...and {len(categories['Gmail']) - 5} more*\n"
    
    md_content += "\n## LinkedIn Tools\n"
    for tool in categories["LinkedIn"]:
        md_content += f"- `{tool['name']}` - {tool['description']}\n"
    
    md_content += "\n## Firecrawl Tools\n"
    for tool in categories["Firecrawl"]:
        md_content += f"- `{tool['name']}` - {tool['description']}\n"
    
    # Add optimization recommendations
    md_content += """
## Optimization Recommendations

### For Web Scraper Workflow
1. **Batch Duplicate Checking**: Use `zapier_google_sheets_lookup_spreadsheet_rows_advanced` to check up to 500 rows at once
2. **Batch Creation**: Use `zapier_google_sheets_create_multiple_spreadsheet_rows` to add all new articles in one operation
3. **Batch Updates**: Use `zapier_google_sheets_update_spreadsheet_row_s` for multiple row updates
4. **Bulk Retrieval**: Use `zapier_google_sheets_get_many_spreadsheet_rows_advanced` to fetch up to 1,500 rows

### Token Saving Tips
- Combine multiple single operations into batch operations wherever possible
- Use `lookup_spreadsheet_rows_advanced` with smart filters instead of multiple single lookups
- Cache spreadsheet data locally when doing multiple operations on the same data
"""
    
    return md_content


async def main():
    """Main function to update documentation."""
    
    print("🔄 Fetching current Zapier tools...")
    tools_dict = await get_zapier_tools()
    
    print(f"📊 Found {len(tools_dict)} tools")
    
    # Categorize tools
    categories, batch_operations = categorize_tools(tools_dict)
    
    # Save JSON for programmatic access
    with open("zapier_tools_current.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tools": tools_dict,
            "categories": {k: [t["name"] for t in v] for k, v in categories.items()},
            "batch_operations": batch_operations
        }, f, indent=2, default=str)
    
    print("✅ Saved to zapier_tools_current.json")
    
    # Generate and save markdown documentation
    md_content = generate_markdown_docs(tools_dict, categories, batch_operations)
    
    with open("ZAPIER_TOOLS.md", "w") as f:
        f.write(md_content)
    
    print("✅ Saved to ZAPIER_TOOLS.md")
    
    print(f"""
📋 Summary:
- Google Sheets tools: {len(categories['Google Sheets'])} (including {len(batch_operations)} batch operations)
- Gmail tools: {len(categories['Gmail'])}
- LinkedIn tools: {len(categories['LinkedIn'])}
- Firecrawl tools: {len(categories['Firecrawl'])}

💡 Update CLAUDE.md to reference ZAPIER_TOOLS.md for current tool list
""")


if __name__ == "__main__":
    asyncio.run(main())