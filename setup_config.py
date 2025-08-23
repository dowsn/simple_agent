#!/usr/bin/env python3
"""
Setup configuration files from environment variables.
This script creates the necessary YAML config files from environment variables,
allowing for secure deployment without committing sensitive data.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

def setup_config():
    """Generate config files from environment variables or .env file."""
    
    # Load environment variables from .env if it exists
    load_dotenv()
    
    # Check if config files already exist
    config_file = Path("mcp_agent.config.yaml")
    secrets_file = Path("mcp_agent.secrets.yaml")
    
    # Create mcp_agent.secrets.yaml if needed
    if not secrets_file.exists():
        secrets_data = {}
        
        # Required API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            secrets_data["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
        if os.getenv("FIRECRAWL_API_KEY"):
            secrets_data["FIRECRAWL_API_KEY"] = os.getenv("FIRECRAWL_API_KEY")
        if os.getenv("ZAPIER_NLA_API_KEY"):
            secrets_data["ZAPIER_NLA_API_KEY"] = os.getenv("ZAPIER_NLA_API_KEY")
        
        # Optional API keys
        if os.getenv("OPENAI_API_KEY"):
            secrets_data["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        
        if secrets_data:
            with open(secrets_file, 'w') as f:
                yaml.dump(secrets_data, f, default_flow_style=False)
            print(f"✅ Created {secrets_file}")
        else:
            print("⚠️  No API keys found in environment variables")
    
    # Create mcp_agent.config.yaml if needed
    if not config_file.exists():
        config_data = {
            "mcp": {
                "servers": {
                    "firecrawl": {
                        "command": "uvx",
                        "args": ["mcp-server-firecrawl"]
                    },
                    "zapier": {
                        "command": "uvx",
                        "args": ["mcp-server-zapier-nla"]
                    }
                }
            }
        }
        
        # Add Zapier connection URL if provided
        zapier_oauth_url = os.getenv("ZAPIER_OAUTH_URL")
        zapier_server_url = os.getenv("ZAPIER_SERVER_URL")
        
        if zapier_oauth_url:
            config_data["mcp"]["servers"]["zapier"]["env"] = {
                "ZAPIER_OAUTH_URL": zapier_oauth_url
            }
            print("📌 Using Zapier OAuth URL for connection")
        elif zapier_server_url:
            config_data["mcp"]["servers"]["zapier"]["env"] = {
                "ZAPIER_SERVER_URL": zapier_server_url
            }
            print("📌 Using Zapier server-specific URL for connection")
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        print(f"✅ Created {config_file}")
    
    # Verify required keys are present
    required_keys = ["ANTHROPIC_API_KEY", "FIRECRAWL_API_KEY", "ZAPIER_NLA_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print("\n⚠️  Missing required environment variables:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\nPlease set these in your .env file or environment")
        return False
    
    print("\n✅ Configuration is ready!")
    return True

if __name__ == "__main__":
    import sys
    
    if setup_config():
        sys.exit(0)
    else:
        sys.exit(1)