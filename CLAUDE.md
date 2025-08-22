# MCP Agent - Web Scraper with Streamlit Interface

## Overview
This project is a web scraper built with mcp-agent - a Python framework for AI agents with Model Context Protocol (MCP) support. It scrapes articles from websites, filters duplicates using Google Sheets, and can generate social media posts.

## Features
- **Web Scraping**: Uses Firecrawl MCP server to extract articles from websites
- **Duplicate Detection**: Uses Zapier MCP server to check Google Sheets for existing articles  
- **Streamlit UI**: Simple interface for configuring API keys and running the scraper
- **Social Media Integration**: Can generate LinkedIn and Twitter posts from articles

## Installation & Setup

### Prerequisites
- Python 3.9+
- uv package manager: `pip install uv`
- Node.js (for some MCP servers)

### Install Dependencies
```bash
# Sync project dependencies
uv sync

# Install additional requirements
uv pip install -r requirements.txt

# Install Streamlit if not included
uv pip install streamlit
```

### Configure API Keys

#### Option 1: Using Streamlit Interface (Recommended)
```bash
# Run the Streamlit configuration interface
uv run streamlit run streamlit_app.py

# Then in the web interface:
# 1. Go to "API Keys" tab
# 2. Enter your keys:
#    - Anthropic API Key (required)
#    - Firecrawl API Key (required)
#    - Zapier NLA API Key (required)
# 3. Click "Save API Keys"
```

#### Option 2: Manual Configuration
```bash
# Copy the example secrets file
cp mcp_agent.secrets.yaml.example mcp_agent.secrets.yaml

# Edit the file and add your API keys:
# - ANTHROPIC_API_KEY (required for Claude)
# - FIRECRAWL_API_KEY (required for web scraping)
# - ZAPIER_NLA_API_KEY (required for Google Sheets)
# - OPENAI_API_KEY (optional)
```

## Running the Web Scraper

### Using Streamlit Interface (Recommended)
```bash
# Start the Streamlit app
uv run streamlit run streamlit_app.py

# In the web interface:
# 1. Configure API keys in the "API Keys" tab
# 2. Set URLs and spreadsheet ID in "Settings" tab
# 3. Click "Run Web Scraper" in the "Run" tab
```

### Command Line Execution
```bash
# Run directly from command line
uv run main.py
```

### Running Tests
```bash
# If tests exist, run them with:
uv run pytest tests/
```

### Linting & Type Checking
```bash
# Run linting (if configured)
uv run ruff check .

# Run type checking (if configured)
uv run mypy .
```

## Configuration

### Default Settings (in main.py)
- **URLs**: List of websites to scrape (default: ["https://latent.space"])
- **Spreadsheet ID**: Google Sheets ID for tracking articles  
- **Criteria**: Article selection criteria (default: "education and AI")

### Project Structure

#### Key Files
- `main.py` - Main web scraper logic with two agents
- `streamlit_app.py` - Web interface for configuration and execution
- `mcp_agent.config.yaml` - MCP server configurations
- `mcp_agent.secrets.yaml` - API keys and secrets (do not commit!)
- `requirements.txt` - Python dependencies

#### MCP Servers Configuration
The `mcp_agent.config.yaml` defines available MCP servers:
```yaml
mcp:
  servers:
    firecrawl:
      command: "uvx"
      args: ["mcp-server-firecrawl"]
    zapier:
      command: "uvx"
      args: ["mcp-server-zapier-nla"]
```

## Claude Code Integration

**IMPORTANT**: When working with mcp-agent in Claude Code, always use the Context7 MCP server to fetch the latest documentation:

```
1. First resolve library ID: mcp__context7__resolve-library-id with "mcp-agent"
2. Then fetch docs: mcp__context7__get-library-docs with the resolved ID
3. Use topics like "streamlit", "agents", "workflows" for specific areas
```

This ensures you always have access to the most up-to-date mcp-agent documentation and examples.

## Zapier MCP Tools Reference

### 📋 Current Tools Documentation
**See [ZAPIER_TOOLS.md](./ZAPIER_TOOLS.md) for the current list of available Zapier tools.**

To update the tools list:
```bash
# Run this script to fetch current tools and update documentation
uv run update_zapier_tools_docs.py
```

This generates:
- `ZAPIER_TOOLS.md` - Human-readable documentation with categorized tools
- `zapier_tools_current.json` - Machine-readable JSON with full tool details

### Optimization Strategy for Web Scraper

#### Token Reduction Techniques
1. **Consolidate to 3 agents** (from 6):
   - `web_scraper`: Handles all Firecrawl operations
   - `spreadsheet_manager`: Handles all Zapier/Google Sheets operations
   - `content_processor`: Selection and social media generation

2. **Batch Operations** (check ZAPIER_TOOLS.md for current batch tools):
   - Use batch creation for multiple rows
   - Use advanced lookup for checking multiple duplicates
   - Avoid one-by-one operations wherever possible

3. **Instruction Optimization**:
   - Keep agent instructions under 100 characters
   - Move detailed schemas to code, not instructions
   - Use structured outputs (Pydantic) instead of JSON parsing

4. **Smart Content Extraction**:
   - Only fetch full content for the ONE selected article
   - Not for all new articles (saves ~70% content tokens)

5. **Parallel Processing**:
   - Use `asyncio.gather()` for concurrent URL scraping
   - Process multiple operations in parallel where possible

## Quick Reference

### Run with Streamlit
```bash
uv run streamlit run streamlit_app.py
```

### Run directly
```bash
uv run main.py
```

### Required API Keys
- `ANTHROPIC_API_KEY` - For Claude
- `FIRECRAWL_API_KEY` - For web scraping  
- `ZAPIER_NLA_API_KEY` - For Google Sheets

### MCP Servers Used
- `firecrawl` - Web scraping
- `zapier` - Google Sheets integration