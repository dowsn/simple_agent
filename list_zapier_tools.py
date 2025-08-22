#!/usr/bin/env python3
"""
Script to list all available Zapier MCP tools.
This helps understand what batch operations are available for optimization.
"""

import asyncio
import json
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM


async def list_zapier_tools():
    """List all available Zapier MCP tools and their descriptions."""
    
    app = MCPApp(name="zapier_tools_lister")
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        # Create agent with Zapier access
        zapier_agent = Agent(
            name="zapier_lister",
            instruction="List available tools",
            server_names=["zapier"]
        )
        
        async with zapier_agent:
            # List all available tools
            tools_result = await zapier_agent.list_tools()
            
            print("\n" + "="*80)
            print("ZAPIER MCP TOOLS AVAILABLE")
            print("="*80 + "\n")
            
            tools_dict = {}
            
            for tool in tools_result.tools:
                # Handle inputSchema as dict or object
                input_schema = None
                if tool.inputSchema:
                    if hasattr(tool.inputSchema, 'model_dump'):
                        input_schema = tool.inputSchema.model_dump()
                    else:
                        input_schema = tool.inputSchema
                
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": input_schema
                }
                tools_dict[tool.name] = tool_info
                
                print(f"📌 Tool: {tool.name}")
                print(f"   Description: {tool.description}")
                if input_schema:
                    print(f"   Input Schema: {json.dumps(input_schema, indent=6)}")
                print("-" * 40)
            
            # Check for batch operations
            print("\n" + "="*80)
            print("BATCH OPERATION ANALYSIS")
            print("="*80 + "\n")
            
            batch_tools = [name for name in tools_dict.keys() if 'batch' in name.lower() or 'bulk' in name.lower()]
            lookup_tools = [name for name in tools_dict.keys() if 'lookup' in name.lower()]
            create_tools = [name for name in tools_dict.keys() if 'create' in name.lower()]
            sheets_tools = [name for name in tools_dict.keys() if 'sheets' in name.lower() or 'spreadsheet' in name.lower()]
            
            print(f"🔄 Batch/Bulk Tools Found: {len(batch_tools)}")
            for tool in batch_tools:
                print(f"   - {tool}")
            
            print(f"\n🔍 Lookup Tools Found: {len(lookup_tools)}")
            for tool in lookup_tools:
                print(f"   - {tool}")
                
            print(f"\n➕ Create Tools Found: {len(create_tools)}")
            for tool in create_tools:
                print(f"   - {tool}")
                
            print(f"\n📊 Google Sheets Tools Found: {len(sheets_tools)}")
            for tool in sheets_tools:
                print(f"   - {tool}")
            
            # Save to JSON file for reference
            with open("zapier_tools.json", "w") as f:
                json.dump(tools_dict, f, indent=2, default=str)
            
            print(f"\n✅ Tools list saved to zapier_tools.json")
            
            # Return tools for documentation
            return tools_dict


async def test_batch_capabilities():
    """Test if Zapier supports batch operations for Google Sheets."""
    
    app = MCPApp(name="zapier_batch_tester")
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        zapier_agent = Agent(
            name="batch_tester",
            instruction="Test batch operations",
            server_names=["zapier"]
        )
        
        async with zapier_agent:
            llm = await zapier_agent.attach_llm(AnthropicAugmentedLLM)
            
            # Test if we can lookup multiple rows at once
            test_result = await llm.generate_str(
                """Can you check if there's a way to:
                1. Lookup multiple rows in a Google Sheets spreadsheet at once
                2. Create multiple rows in a single operation
                3. Any batch or bulk operations available
                
                Just list the tool names that could help with this."""
            )
            
            print("\n" + "="*80)
            print("BATCH CAPABILITY TEST RESULTS")
            print("="*80 + "\n")
            print(test_result)
            
            return test_result


if __name__ == "__main__":
    print("🚀 Starting Zapier MCP Tools Discovery...")
    
    # List all tools
    tools = asyncio.run(list_zapier_tools())
    
    # Test batch capabilities
    print("\n🧪 Testing batch capabilities...")
    batch_test = asyncio.run(test_batch_capabilities())
    
    print("\n✨ Discovery complete!")