# Configuration Setup Guide

## Overview
This project uses configuration files that contain sensitive API keys and connection URLs. These files are gitignored for security. Here's how to set them up for local development and production.

## Quick Setup

### Option 1: Using Environment Variables (Recommended for Production)

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your actual API keys and Zapier connection URL

3. Run the setup script to generate config files:
```bash
uv run python setup_config.py
```

### Option 2: Manual Setup (For Local Development)

1. Copy the example files:
```bash
cp mcp_agent.config.yaml.example mcp_agent.config.yaml
cp mcp_agent.secrets.yaml.example mcp_agent.secrets.yaml
```

2. Edit both files and add your actual values

## Zapier MCP Connection

You have two options for connecting to Zapier MCP:

### OAuth URL (Recommended for Production)
- More secure, supports token refresh
- URL format: `https://mcp.zapier.com/api/mcp/a/YOUR_ACCOUNT_ID/mcp?serverId=YOUR_SERVER_ID`
- Set as `ZAPIER_OAUTH_URL` in your `.env` file

### Server-Specific URL (Simpler Setup)
- Treat this URL like a password - it provides full access
- URL format: `https://mcp.zapier.com/api/mcp/s/YOUR_SECRET/mcp`
- Set as `ZAPIER_SERVER_URL` in your `.env` file
- ⚠️ Warning: Anyone with this URL can access your Zapier tools

## Required Environment Variables

```bash
# API Keys (Required)
ANTHROPIC_API_KEY=sk-ant-api03-...
FIRECRAWL_API_KEY=fc-...
ZAPIER_NLA_API_KEY=...

# Zapier Connection (Choose One)
ZAPIER_OAUTH_URL=https://mcp.zapier.com/api/mcp/a/.../mcp?serverId=...
# OR
ZAPIER_SERVER_URL=https://mcp.zapier.com/api/mcp/s/.../mcp

# Optional
OPENAI_API_KEY=sk-...
```

## Production Deployment

For production environments:

1. Set all environment variables in your deployment platform (Heroku, AWS, etc.)
2. Run `setup_config.py` during deployment to generate config files
3. Never commit the actual `.env`, `mcp_agent.config.yaml`, or `mcp_agent.secrets.yaml` files

## Docker Deployment

If using Docker, pass environment variables:

```bash
docker run -e ANTHROPIC_API_KEY=... -e FIRECRAWL_API_KEY=... your-image
```

Or use a `.env` file with Docker Compose:

```yaml
version: '3.8'
services:
  app:
    env_file: .env
    # ... rest of config
```

## Security Best Practices

1. **Never commit sensitive files** - They're in `.gitignore` for a reason
2. **Rotate keys regularly** - Especially if accidentally exposed
3. **Use OAuth for production** - It's more secure than server-specific URLs
4. **Limit permissions** - Only grant necessary Zapier actions
5. **Monitor usage** - Check your API usage regularly

## Troubleshooting

### Config files not found
Run: `uv run python setup_config.py`

### Missing API keys error
Check your `.env` file has all required keys

### Zapier connection fails
- Verify your Zapier URL is correct
- Check if the server exists in your Zapier account
- Try regenerating the server URL in Zapier

## Getting Your Zapier URLs

1. Go to [Zapier MCP Dashboard](https://actions.zapier.com/mcp/servers)
2. Create or select your server
3. Choose either:
   - OAuth URL (recommended)
   - Server-specific URL (simpler)
4. Copy the URL to your `.env` file