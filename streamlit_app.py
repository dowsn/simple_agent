"""
Simple Streamlit Configuration for MCP Web Scraper
"""

import streamlit as st
import yaml
import os
import asyncio
import sys
import json

# Add current directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main

st.set_page_config(page_title="MCP Web Scraper", page_icon="🕷️", layout="wide")

st.title("🕷️ MCP Web Scraper Configuration")

# Tabs
tab1, tab2, tab3 = st.tabs(["🔑 API Keys", "⚙️ Settings", "▶️ Run"])

with tab1:
    st.header("API Keys")
    
    # Load existing secrets if available
    secrets = {}
    if os.path.exists("mcp_agent.secrets.yaml"):
        with open("mcp_agent.secrets.yaml", 'r') as f:
            secrets = yaml.safe_load(f) or {}
    
    anthropic_key = st.text_input("Anthropic API Key", value=secrets.get("ANTHROPIC_API_KEY", ""), type="password")
    firecrawl_key = st.text_input("Firecrawl API Key", value=secrets.get("FIRECRAWL_API_KEY", ""), type="password")
    zapier_key = st.text_input("Zapier NLA API Key", value=secrets.get("ZAPIER_NLA_API_KEY", ""), type="password")
    
    if st.button("Save API Keys"):
        secrets = {
            "ANTHROPIC_API_KEY": anthropic_key,
            "OPENAI_API_KEY": secrets.get("OPENAI_API_KEY", ""),  # Keep existing if present
            "FIRECRAWL_API_KEY": firecrawl_key,
            "ZAPIER_NLA_API_KEY": zapier_key
        }
        with open("mcp_agent.secrets.yaml", 'w') as f:
            yaml.dump(secrets, f)
        st.success("✅ API keys saved!")

with tab2:
    st.header("Scraper Settings")
    
    # URLs to scrape
    urls_input = st.text_area("URLs to Scrape (one per line)", value="\n".join(main.urls))
    
    # Spreadsheet settings
    spreadsheet_id = st.text_input("Google Sheets ID", value=main.spreadsheet_id)
    spreadsheet_name = st.text_input("Spreadsheet Name", value=main.spreadsheet_name)
    
    # Article criteria
    criteria = st.text_input("Article Selection Criteria", value=main.CRITERIA)
    
    if st.button("Update Settings"):
        # Update the variables in main module
        main.urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
        main.spreadsheet_id = spreadsheet_id
        main.spreadsheet_name = spreadsheet_name
        main.CRITERIA = criteria
        st.success("✅ Settings updated!")
        st.session_state.settings_updated = True

with tab3:
    st.header("Run Web Scraper")
    
    # Check if API keys exist
    config_exists = os.path.exists("mcp_agent.config.yaml")
    secrets_exists = os.path.exists("mcp_agent.secrets.yaml")
    
    if not secrets_exists:
        st.error("❌ Please configure API keys first")
    else:
        # Load and check if keys are set
        with open("mcp_agent.secrets.yaml", 'r') as f:
            secrets = yaml.safe_load(f) or {}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if secrets.get("ANTHROPIC_API_KEY"):
                st.success("✅ Anthropic Key")
            else:
                st.error("❌ Anthropic Key")
        with col2:
            if secrets.get("FIRECRAWL_API_KEY"):
                st.success("✅ Firecrawl Key")
            else:
                st.error("❌ Firecrawl Key")
        with col3:
            if secrets.get("ZAPIER_NLA_API_KEY"):
                st.success("✅ Zapier Key")
            else:
                st.error("❌ Zapier Key")
    
    # Ensure MCP config exists
    if not config_exists:
        st.warning("Creating default MCP configuration...")
        config = {
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
        with open("mcp_agent.config.yaml", 'w') as f:
            yaml.dump(config, f)
        st.success("✅ MCP configuration created")
    
    st.markdown("---")
    
    # Display current settings
    st.subheader("Current Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**URLs:** {len(main.urls)} URL(s)")
        st.info(f"**Criteria:** {main.CRITERIA}")
    with col2:
        st.info(f"**Spreadsheet ID:** {main.spreadsheet_id}")
    
    if st.button("🚀 Run Web Scraper", type="primary"):
        with st.spinner("Running web scraper..."):
            try:
                # Create a placeholder for output
                output_placeholder = st.empty()
                
                # Run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Capture output by redirecting stdout
                import io
                from contextlib import redirect_stdout
                
                f = io.StringIO()
                with redirect_stdout(f):
                    result = loop.run_until_complete(main.web_scraper())
                
                output = f.getvalue()
                
                # Display output
                output_placeholder.success("✅ Web scraper completed!")
                st.text_area("Output", value=output, height=400)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)