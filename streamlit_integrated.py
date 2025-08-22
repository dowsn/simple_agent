"""
Streamlit Web Application for AI-Powered Web Scraper
Integrates with mcp-agent workflow for article scraping and social media generation
"""

import streamlit as st
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from dotenv import load_dotenv

# Import local modules
from database import Database, init_default_admin
from main_refactored import web_scraper, WebScraperWorkflow
from streamlit_logger import StreamlitLogger, AsyncProgressCallback

# Load environment variables
load_dotenv()

# Initialize database
db = Database(os.getenv("DB_PATH", "./app_data.db"))

# Page configuration
st.set_page_config(
    page_title="AI Web Scraper & Social Media Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
    }
    .social-post-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# ============= Authentication =============

def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'workflow_results' not in st.session_state:
        st.session_state.workflow_results = None
    if 'social_posts' not in st.session_state:
        st.session_state.social_posts = None
    if 'streamlit_logger' not in st.session_state:
        st.session_state.streamlit_logger = StreamlitLogger()

def login_page():
    """Display login page."""
    st.markdown('<h1 class="main-header">🤖 AI Web Scraper Login</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.session_token = db.create_session(user['id'])
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        # Default credentials hint
        st.info("Default: admin / Use password from .env file")

def logout():
    """Logout user."""
    if 'session_token' in st.session_state:
        db.delete_session(st.session_state.session_token)
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.clear()
    st.rerun()

# ============= API Configuration =============

def save_api_keys():
    """Save API keys to configuration files."""
    try:
        # Save to secrets file
        secrets = {
            'ANTHROPIC_API_KEY': st.session_state.anthropic_key,
            'FIRECRAWL_API_KEY': st.session_state.firecrawl_key,
            'ZAPIER_NLA_API_KEY': st.session_state.zapier_key,
        }
        
        # Save to mcp_agent.secrets.yaml
        with open('mcp_agent.secrets.yaml', 'w') as f:
            yaml.dump(secrets, f)
        
        # Also save to database for user-specific configs
        if st.session_state.user:
            db.save_api_config(st.session_state.user['id'], 'api_keys', secrets)
        
        return True
    except Exception as e:
        st.error(f"Error saving API keys: {str(e)}")
        return False

def load_api_keys():
    """Load API keys from configuration."""
    keys = {}
    
    # Try to load from database first
    if st.session_state.user:
        db_config = db.get_api_config(st.session_state.user['id'], 'api_keys')
        if db_config:
            return db_config
    
    # Fallback to secrets file
    try:
        if Path('mcp_agent.secrets.yaml').exists():
            with open('mcp_agent.secrets.yaml', 'r') as f:
                keys = yaml.safe_load(f) or {}
    except:
        pass
    
    # Fallback to environment variables
    keys.setdefault('ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY', ''))
    keys.setdefault('FIRECRAWL_API_KEY', os.getenv('FIRECRAWL_API_KEY', ''))
    keys.setdefault('ZAPIER_NLA_API_KEY', os.getenv('ZAPIER_NLA_API_KEY', ''))
    
    return keys

# ============= Workflow Execution =============

def run_workflow(urls: List[str], criteria: str, spreadsheet_id: str, logger: StreamlitLogger = None, progress_bar = None):
    """Run the web scraper workflow."""
    try:
        # Create workflow run in database
        workflow_config = {
            'urls': urls,
            'criteria': criteria,
            'spreadsheet_id': spreadsheet_id
        }
        
        run_id = db.create_workflow_run(st.session_state.user['id'], workflow_config)
        
        # Create progress callback with logger
        callback = AsyncProgressCallback(progress_bar, logger)
        
        # Run the async workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            web_scraper(
                urls=urls,
                criteria=criteria,
                spreadsheet_id=spreadsheet_id,
                progress_callback=callback
            )
        )
        
        # Update database with results
        if results.get('social_posts'):
            db.update_workflow_run(
                run_id, 
                'completed',
                results,
                results['social_posts']
            )
        else:
            db.update_workflow_run(run_id, 'completed', results)
        
        return results
        
    except Exception as e:
        st.error(f"Workflow error: {str(e)}")
        if 'run_id' in locals():
            db.update_workflow_run(run_id, 'failed', {'error': str(e)})
        return None

# ============= Social Media Publishing =============

async def publish_to_social(platform: str, content: str):
    """Publish content to social media platform via Zapier MCP."""
    try:
        from mcp_agent.app import MCPApp
        from mcp_agent.agents.agent import Agent
        from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
        
        # Create publishing agent
        app = MCPApp(name="social_publisher")
        async with app.run() as agent_app:
            publisher = Agent(
                name="social_publisher",
                instruction=f"""You are a social media publisher using Zapier tools.
                Your task: Publish the provided content to {platform}.
                
                Instructions:
                1. Find the appropriate Zapier action for posting to {platform}
                2. Use the action to publish the content
                3. Confirm the post was created successfully
                
                Important: Only publish to {platform}, nothing else.""",
                server_names=["zapier"]
            )
            
            async with publisher:
                llm = await publisher.attach_llm(AnthropicAugmentedLLM)
                
                # Publish to the platform
                result = await llm.generate_str(
                    f"""Publish this content to {platform}:
                    
                    Content:
                    {content}
                    
                    Use the appropriate Zapier action to create a post on {platform}.
                    Confirm when the post is successfully created.
                    """
                )
                
                if "success" in result.lower() or "created" in result.lower() or "published" in result.lower():
                    st.success(f"✅ Published to {platform}!")
                    
                    # Log the publication
                    if st.session_state.user and 'current_run_id' in st.session_state:
                        db.add_log(
                            st.session_state.current_run_id,
                            'info',
                            f'Published to {platform}',
                            {'platform': platform, 'content': content[:100]}
                        )
                    return True
                else:
                    st.warning(f"Could not confirm publication to {platform}")
                    return False
                    
    except Exception as e:
        st.error(f"Publishing error: {str(e)}")
        return False

def run_publish_task(platform: str, content: str):
    """Wrapper to run async publish task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(publish_to_social(platform, content))

# ============= Main Application =============

def main_app():
    """Main application interface."""
    # Sidebar
    with st.sidebar:
        st.title("🤖 AI Web Scraper")
        st.write(f"Welcome, **{st.session_state.user['username']}**!")
        
        if st.button("Logout", use_container_width=True):
            logout()
        
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "⚙️ Settings", "🔑 API Keys", "📊 History", "🚀 Run Scraper"]
        )
    
    # Main content based on selected page
    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "⚙️ Settings":
        settings_page()
    elif page == "🔑 API Keys":
        api_keys_page()
    elif page == "📊 History":
        history_page()
    elif page == "🚀 Run Scraper":
        scraper_page()

def dashboard_page():
    """Dashboard page showing recent activity."""
    st.title("Dashboard")
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    
    # Get recent runs
    recent_runs = db.get_workflow_runs(st.session_state.user['id'], limit=5)
    
    with col1:
        st.metric("Total Runs", len(recent_runs))
    with col2:
        completed = sum(1 for r in recent_runs if r['status'] == 'completed')
        st.metric("Successful", completed)
    with col3:
        if recent_runs and recent_runs[0]['social_posts']:
            st.metric("Last Posts", "3")
        else:
            st.metric("Last Posts", "0")
    with col4:
        st.metric("Active", "✅" if st.session_state.get('workflow_results') else "❌")
    
    # Recent activity
    st.subheader("Recent Activity")
    if recent_runs:
        for run in recent_runs[:3]:
            with st.expander(f"Run at {run['started_at']}", expanded=False):
                st.write(f"**Status:** {run['status']}")
                if run['config']:
                    st.write(f"**URLs:** {', '.join(run['config'].get('urls', []))}")
                    st.write(f"**Criteria:** {run['config'].get('criteria', 'N/A')}")
                if run['results']:
                    st.write(f"**Articles Scraped:** {run['results'].get('scraped', 0)}")
                    st.write(f"**New Articles:** {run['results'].get('new_articles', 0)}")
    else:
        st.info("No recent activity. Run your first scraper!")

def settings_page():
    """Settings configuration page."""
    st.title("Settings")
    
    # Load current settings
    api_keys = load_api_keys()
    
    with st.form("settings_form"):
        st.subheader("Default Configuration")
        
        criteria = st.text_input(
            "Default Criteria",
            value=os.getenv("DEFAULT_CRITERIA", "education and AI"),
            help="Default topic criteria for article selection"
        )
        
        spreadsheet_id = st.text_input(
            "Google Spreadsheet ID",
            value=os.getenv("DEFAULT_SPREADSHEET_ID", ""),
            help="Default Google Sheets ID for storing articles"
        )
        
        urls = st.text_area(
            "Default URLs (one per line)",
            value=os.getenv("DEFAULT_URLS", "https://latent.space"),
            help="Default websites to scrape"
        )
        
        if st.form_submit_button("Save Settings", use_container_width=True):
            # Save to database
            settings = {
                'criteria': criteria,
                'spreadsheet_id': spreadsheet_id,
                'urls': urls.split('\n')
            }
            db.save_api_config(st.session_state.user['id'], 'settings', settings)
            
            # Also save to JSON file for persistence
            try:
                with open('user_settings.json', 'w') as f:
                    json.dump({
                        'urls': settings['urls'],
                        'criteria': settings['criteria'],
                        'spreadsheet_id': settings['spreadsheet_id'],
                        'last_updated': datetime.now().isoformat(),
                        'comment': 'User settings backup - survives database deletion'
                    }, f, indent=2)
            except Exception as e:
                st.warning(f"Could not save backup: {e}")
            
            st.success("Settings saved successfully!")

def api_keys_page():
    """API keys configuration page."""
    st.title("API Keys Configuration")
    
    # Load current keys
    api_keys = load_api_keys()
    
    with st.form("api_keys_form"):
        st.subheader("API Keys")
        
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=api_keys.get('ANTHROPIC_API_KEY', ''),
            type="password",
            key="anthropic_key"
        )
        
        firecrawl_key = st.text_input(
            "Firecrawl API Key",
            value=api_keys.get('FIRECRAWL_API_KEY', ''),
            type="password",
            key="firecrawl_key"
        )
        
        zapier_key = st.text_input(
            "Zapier NLA API Key",
            value=api_keys.get('ZAPIER_NLA_API_KEY', ''),
            type="password",
            key="zapier_key"
        )
        
        if st.form_submit_button("Save API Keys", use_container_width=True):
            if save_api_keys():
                st.success("API keys saved successfully!")
            else:
                st.error("Failed to save API keys")
    
    # Test connections
    st.subheader("Test Connections")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Test Anthropic"):
            # Add test logic here
            st.info("Testing Anthropic connection...")
    
    with col2:
        if st.button("Test Firecrawl"):
            # Add test logic here
            st.info("Testing Firecrawl connection...")
    
    with col3:
        if st.button("Test Zapier"):
            # Add test logic here
            st.info("Testing Zapier connection...")

def history_page():
    """Workflow history page."""
    st.title("Workflow History")
    
    # Get workflow runs
    runs = db.get_workflow_runs(st.session_state.user['id'], limit=20)
    
    if runs:
        for run in runs:
            with st.expander(f"🕐 {run['started_at']} - Status: {run['status']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Configuration:**")
                    if run['config']:
                        st.json(run['config'])
                
                with col2:
                    st.write("**Results:**")
                    if run['results']:
                        st.json(run['results'])
                
                if run['social_posts']:
                    st.write("**Generated Posts:**")
                    posts = run['social_posts']
                    
                    # LinkedIn
                    if 'linkedin_post' in posts:
                        st.text_area("LinkedIn", posts['linkedin_post'], height=100, disabled=True)
                    
                    # Twitter
                    if 'twitter_post' in posts:
                        st.text_area("Twitter", posts['twitter_post'], height=50, disabled=True)
                    
                    # Instagram
                    if 'instagram_post' in posts:
                        st.text_area("Instagram", posts['instagram_post'], height=100, disabled=True)
    else:
        st.info("No workflow history yet. Run your first scraper!")

def scraper_page():
    """Main scraper execution page."""
    st.title("Run Web Scraper")
    
    # Load settings from database, JSON file, or environment (in that order)
    user_settings = db.get_api_config(st.session_state.user['id'], 'settings') or {}
    
    # If no database settings, try loading from JSON file
    if not user_settings:
        try:
            if Path('user_settings.json').exists():
                with open('user_settings.json', 'r') as f:
                    file_settings = json.load(f)
                    user_settings = {
                        'urls': file_settings.get('urls', []),
                        'criteria': file_settings.get('criteria', ''),
                        'spreadsheet_id': file_settings.get('spreadsheet_id', '')
                    }
        except Exception:
            pass
    
    # Fall back to environment variables
    urls = user_settings.get('urls', [os.getenv('DEFAULT_URLS', 'https://latent.space')])
    if isinstance(urls, str):
        urls = [urls]
    criteria = user_settings.get('criteria', os.getenv('DEFAULT_CRITERIA', 'education and AI'))
    spreadsheet_id = user_settings.get('spreadsheet_id', os.getenv('DEFAULT_SPREADSHEET_ID', ''))
    
    # Quick summary of configuration
    with st.expander("⚙️ Current Configuration", expanded=False):
        st.write(f"**URLs:** {', '.join(urls)}")
        st.write(f"**Criteria:** {criteria}")
        st.write(f"**Spreadsheet ID:** {spreadsheet_id[:20]}..." if spreadsheet_id else "Not set")
        st.caption("💡 Change settings in the Settings page")
    
    # Run button and status
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        run_button = st.button(
            "🚀 Run Web Scraper",
            use_container_width=True,
            type="primary",
            disabled=not (urls and criteria)
        )
    
    with col2:
        if st.button("🔄 Clear Logs", use_container_width=True):
            if 'streamlit_logger' in st.session_state:
                st.session_state.streamlit_logger.clear()
            st.session_state.workflow_results = None
            st.session_state.social_posts = None
            st.rerun()
    
    with col3:
        has_logs = 'streamlit_logger' in st.session_state and st.session_state.streamlit_logger.logs
        if st.button("⬇️ Export Logs", use_container_width=True, disabled=not has_logs):
            if has_logs:
                log_text = st.session_state.streamlit_logger.get_logs()
                st.download_button(
                    label="Download",
                    data=log_text,
                    file_name=f"scraper_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
    
    # Progress bar placeholder
    progress_placeholder = st.empty()
    
    # Terminal-style log display
    st.markdown("### 🖥️ Terminal Output")
    
    # Create a single placeholder for logs
    log_container = st.empty()
    
    # Initialize logger if not exists
    if 'streamlit_logger' not in st.session_state:
        st.session_state.streamlit_logger = StreamlitLogger()
    
    # Set the container for the logger
    st.session_state.streamlit_logger.container = log_container
    
    # Display current logs using code block (terminal-like)
    log_text = st.session_state.streamlit_logger.get_logs() if st.session_state.streamlit_logger.logs else "[Ready] Waiting for workflow execution..."
    log_container.code(log_text, language="log")
    
    # Run workflow when button is clicked
    if run_button:
        if not urls or not criteria:
            st.error("❌ Configuration missing. Please set URLs and criteria in Settings.")
        else:
            # Clear previous logs and initialize
            logger = st.session_state.streamlit_logger
            logger.clear()
            logger.add_log("=== WORKFLOW STARTED ===", "INFO")
            logger.add_log(f"URLs: {', '.join(urls)}", "INFO")
            logger.add_log(f"Criteria: {criteria}", "INFO")
            logger.add_log(f"Spreadsheet: {spreadsheet_id[:20]}..." if spreadsheet_id else "Not set", "INFO")
            logger.add_log("="*50, "INFO")
            
            # Run workflow
            with st.spinner("🔄 Workflow running... Check terminal output below"):
                try:
                    results = run_workflow(
                        urls if isinstance(urls, list) else urls.strip().split('\n'),
                        criteria,
                        spreadsheet_id,
                        logger=logger,
                        progress_bar=progress_placeholder
                    )
                    
                    if results:
                        st.session_state.workflow_results = results
                        if results.get('social_posts'):
                            st.session_state.social_posts = results['social_posts']
                        
                        logger.add_log("="*50, "INFO")
                        logger.add_log("=== WORKFLOW COMPLETED ===", "SUCCESS")
                        logger.add_log(f"Status: {results.get('status', 'unknown')}", "SUCCESS")
                        logger.add_log(f"Articles scraped: {results.get('scraped', 0)}", "INFO")
                        logger.add_log(f"New articles: {results.get('new_articles', 0)}", "INFO")
                        
                        st.success("✅ Workflow completed successfully!")
                        st.balloons()
                    else:
                        logger.add_log("WORKFLOW FAILED", "ERROR")
                        st.error("❌ Workflow failed. Check terminal output for details.")
                        
                except Exception as e:
                    logger.add_log(f"ERROR: {str(e)}", "ERROR")
                    st.error(f"❌ Workflow error: {str(e)}")
    
    # Results section
    if st.session_state.workflow_results:
        st.divider()
        st.subheader("Results")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        results = st.session_state.workflow_results
        
        with col1:
            st.metric("Articles Scraped", results.get('scraped', 0))
        with col2:
            st.metric("New Articles", results.get('new_articles', 0))
        with col3:
            st.metric("Selected Article", "✅" if results.get('selected') else "❌")
        
        if results.get('selected'):
            st.info(f"📰 Selected: {results['selected']}")
    
    # Social media posts section
    if st.session_state.social_posts:
        st.divider()
        st.subheader("Generated Social Media Posts")
        
        posts = st.session_state.social_posts
        
        # LinkedIn Post
        st.markdown("### LinkedIn")
        linkedin_content = st.text_area(
            "Edit LinkedIn Post",
            value=posts.get('linkedin_post', ''),
            height=150,
            key="linkedin_edit"
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📤 Publish to LinkedIn", key="pub_linkedin"):
                with st.spinner("Publishing to LinkedIn..."):
                    run_publish_task("LinkedIn", linkedin_content)
        
        # Twitter Post
        st.markdown("### Twitter")
        twitter_content = st.text_area(
            "Edit Twitter Post",
            value=posts.get('twitter_post', ''),
            height=80,
            max_chars=280,
            key="twitter_edit"
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📤 Publish to Twitter", key="pub_twitter"):
                with st.spinner("Publishing to Twitter..."):
                    run_publish_task("Twitter", twitter_content)
        with col2:
            st.caption(f"Characters: {len(twitter_content)}/280")
        
        # Instagram Post
        st.markdown("### Instagram")
        instagram_content = st.text_area(
            "Edit Instagram Post",
            value=posts.get('instagram_post', ''),
            height=120,
            key="instagram_edit"
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📤 Publish to Instagram", key="pub_instagram"):
                with st.spinner("Publishing to Instagram..."):
                    run_publish_task("Instagram", instagram_content)

# ============= Main Entry Point =============

def main():
    """Main application entry point."""
    init_session_state()
    
    # Check if user is authenticated
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    # Initialize default admin if needed
    admin_username = os.getenv("STREAMLIT_AUTH_USERNAME", "admin")
    admin_password = os.getenv("STREAMLIT_AUTH_PASSWORD", "admin123")
    init_default_admin(db, admin_username, admin_password)
    
    # Run the app
    main()