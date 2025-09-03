#!/usr/bin/env python3
"""
Simple Streamlit Web Application for AI-Powered Web Scraper
Uses main.py workflow with console logging
"""

import streamlit as st
import os
import json
import time
import sys
import io
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import redirect_stdout, redirect_stderr

# Import the workflow from webscraper.py
from webscraper import WebScraperWorkflow, Article, SocialPosts
# Import the email management system from mail_agent.py
from mail_agent import EmailManagementSystem

# Page configuration
st.set_page_config(
    page_title="Web Scraper",
    page_icon="🌐",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .console-output {
        background-color: #1e1e1e;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

class ConsoleCapture:
    """Capture console output for display."""
    def __init__(self):
        self.output = io.StringIO()
        
    def get_output(self):
        return self.output.getvalue()
        
    def clear(self):
        self.output = io.StringIO()

def load_todays_files():
    """Load today's files if they exist."""
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = Path(f"outputs/{today}")
    
    if output_dir.exists():
        # Load social posts from individual files
        posts = {}
        
        # Load LinkedIn post
        linkedin_file = output_dir / "linkedin.txt"
        if linkedin_file.exists():
            with open(linkedin_file, 'r', encoding='utf-8') as f:
                posts['linkedin_post'] = f.read()
        
        # Load Twitter post
        twitter_file = output_dir / "twitter.txt"
        if twitter_file.exists():
            with open(twitter_file, 'r', encoding='utf-8') as f:
                posts['twitter_post'] = f.read()
        
        # Load Instagram post
        instagram_file = output_dir / "instagram.txt"
        if instagram_file.exists():
            with open(instagram_file, 'r', encoding='utf-8') as f:
                posts['instagram_post'] = f.read()
        
        # Load image prompt
        prompt_file = output_dir / "image_prompt.txt"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                st.session_state.image_prompt = f.read()
        
        # Load image
        image_files = list(output_dir.glob("generated_image_*.png"))
        if image_files:
            latest_image = max(image_files, key=lambda x: x.stat().st_mtime)
            st.session_state.image_path = str(latest_image)
        
        # Update session state if we have posts
        if posts:
            st.session_state.social_posts = posts

def init_session_state():
    """Initialize session state variables."""
    if 'workflow_results' not in st.session_state:
        st.session_state.workflow_results = None
    if 'social_posts' not in st.session_state:
        st.session_state.social_posts = None
    if 'image_path' not in st.session_state:
        st.session_state.image_path = None
    if 'image_prompt' not in st.session_state:
        st.session_state.image_prompt = ""
    if 'console_logs' not in st.session_state:
        st.session_state.console_logs = ""
    
    # Always load today's files if they exist
    load_todays_files()

def load_file(filename: str) -> str:
    """Load content from any text file."""
    try:
        with open(filename, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def save_config_file(filename: str, content: str):
    """Save content to a config file."""
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        st.error(f"Error saving {filename}: {e}")
        return False

def load_articles():
    """Load and display articles.txt content."""
    try:
        with open('webscraper_inputs/articles.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "# No articles.txt found"

def save_individual_posts(posts_data: dict, output_dir: Path):
    """Save individual platform posts as separate txt files."""
    try:
        # Save LinkedIn post
        with open(output_dir / "linkedin.txt", 'w', encoding='utf-8') as f:
            f.write(posts_data.get('linkedin_post', ''))
            
        # Save Twitter post
        with open(output_dir / "twitter.txt", 'w', encoding='utf-8') as f:
            f.write(posts_data.get('twitter_post', ''))
            
        # Save Instagram post
        with open(output_dir / "instagram.txt", 'w', encoding='utf-8') as f:
            f.write(posts_data.get('instagram_post', ''))
            
        # Save image prompt
        with open(output_dir / "image_prompt.txt", 'w', encoding='utf-8') as f:
            f.write(posts_data.get('image_prompt', ''))
            
        return True
    except Exception as e:
        st.error(f"Error saving posts: {e}")
        return False

def configuration_section():
    """Configuration section."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Sources")
        sources_content = st.text_area(
            "URLs (one per line)",
            value=load_file('webscraper_inputs/sources.txt'),
            height=150,
            help="Enter URLs to scrape, one per line",
            key="sources_config"
        )
    
    with col2:
        st.subheader("Selection Criteria")
        criteria_content = st.text_area(
            "Article selection criteria",
            value=load_file('webscraper_inputs/selection_criteria.txt'),
            height=150,
            help="Describe what type of articles to select",
            key="criteria_config"
        )
    
    with col3:
        st.subheader("Image Style")
        image_style_content = st.text_area(
            "Image generation style",
            value=load_file('webscraper_inputs/image_style.txt'),
            height=150,
            help="Describe the style for generated images",
            key="image_style_config"
        )
    
    # Save Configuration Button
    if st.button("💾 Save Configuration", type="primary"):
        success = True
        success &= save_config_file('webscraper_inputs/sources.txt', sources_content)
        success &= save_config_file('webscraper_inputs/selection_criteria.txt', criteria_content)
        success &= save_config_file('webscraper_inputs/image_style.txt', image_style_content)
        
        if success:
            st.success("✅ Configuration saved successfully!")
        else:
            st.error("❌ Failed to save some configuration files")
    
    st.divider()
    
    # Articles Preview in Configuration
    st.subheader("📚 Articles")
    articles_content = load_articles()
    
    # Show count first
    article_count = len([line for line in articles_content.split('\n') if line.strip() and not line.startswith('#')])
    st.write(f"**{article_count} articles already processed**")
    
    # Collapsible expander for full list
    with st.expander("👁️ View processed articles", expanded=False):
        st.text_area(
            "Previously processed articles:",
            value=articles_content,
            height=200,
            disabled=True,
            help="Articles that have already been processed (read-only)"
        )

def run_section():
    """Run workflow section."""
    col1, col2 = st.columns([1, 4])
    
    with col1:
        run_button = st.button(
            "🚀 Run Scraper",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.workflow_results = None
            st.session_state.social_posts = None
            st.session_state.image_path = None
            st.session_state.console_logs = ""
            st.rerun()
    
    # Console Output
    st.subheader("🖥️ Console Output")
    console_placeholder = st.empty()
    
    # Run workflow when button is clicked
    if run_button:
        with st.spinner("🔄 Running workflow..."):
            # Clear previous results
            st.session_state.workflow_results = None
            st.session_state.social_posts = None
            st.session_state.image_path = None
            st.session_state.console_logs = "🚀 Starting workflow...\n"
            
            # Update console display
            console_placeholder.markdown(f'<div class="console-output">{st.session_state.console_logs}</div>', unsafe_allow_html=True)
            
            try:
                # Capture console output
                console_capture = ConsoleCapture()
                
                # Redirect stdout/stderr to capture
                with redirect_stdout(console_capture.output), redirect_stderr(console_capture.output):
                    # Run workflow
                    workflow = WebScraperWorkflow()
                    results = workflow.run()
                
                # Get captured output
                captured_output = console_capture.get_output()
                st.session_state.console_logs += captured_output
                
                st.session_state.workflow_results = results
                
                # Load today's files after workflow
                load_todays_files()
                        
                st.session_state.console_logs += "\n✅ Workflow completed successfully!"
                st.success("✅ Workflow completed!")
                st.rerun()
                    
            except Exception as e:
                st.session_state.console_logs += f"\n❌ Error: {str(e)}"
                st.error(f"❌ Workflow error: {e}")
    
    # Display console logs
    if st.session_state.console_logs:
        console_placeholder.markdown(f'<div class="console-output">{st.session_state.console_logs}</div>', unsafe_allow_html=True)
    else:
        console_placeholder.markdown('<div class="console-output">[Ready] Waiting for workflow execution...</div>', unsafe_allow_html=True)
    
    # Results Section
    if st.session_state.workflow_results:
        st.divider()
        results = st.session_state.workflow_results
        
        # Show basic metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", results.get('status', 'unknown'))
        with col2:
            st.metric("Articles Scraped", results.get('scraped_articles', 0))
        with col3:
            st.metric("New Articles", results.get('new_articles', 0))
        
        # Show selected article info
        if results.get('selected_article'):
            selected = results['selected_article']
            st.info(f"📰 Selected: **{selected['title']}** by {selected.get('author', 'Unknown')}")

def preview_section():
    """Preview section - shows generated social content."""
    # Always load today's content at the start
    load_todays_files()
    
    # Always show the interface, even if no content yet
    # Image Section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖼️ Generated Image")
        if st.session_state.image_path and Path(st.session_state.image_path).exists():
            st.image(st.session_state.image_path, use_column_width=True)
        else:
            st.info("No image generated yet")
    
    with col2:
        st.subheader("🎨 Image Prompt")
        edited_prompt = st.text_area(
            "Edit image prompt:",
            value=st.session_state.image_prompt,
            height=150,
            key="image_prompt_edit"
        )
        
        if st.button("🔄 Regenerate Image"):
            if edited_prompt:
                with st.spinner("Generating new image..."):
                    try:
                        # Get current output folder
                        today = datetime.now().strftime('%Y-%m-%d')
                        output_dir = Path(f"outputs/{today}")
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Create workflow instance to use image generation
                        workflow = WebScraperWorkflow()
                        new_image_path = workflow.generate_image(edited_prompt, output_dir)
                        
                        if new_image_path:
                            st.session_state.image_path = new_image_path
                            st.session_state.image_prompt = edited_prompt
                            st.success("✅ Image regenerated!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate image")
                    except Exception as e:
                        st.error(f"❌ Error generating image: {e}")
    
    st.divider()
    
    # Social Media Posts Section
    st.subheader("📱 Social Media Posts")
    
    # Load current posts or show empty
    posts = st.session_state.social_posts or {}
    
    # LinkedIn Post
    st.markdown("#### LinkedIn")
    linkedin_post = st.text_area(
        "LinkedIn Post",
        value=posts.get('linkedin_post', ''),
        height=200,
        key="linkedin_edit"
    )
    
    # Twitter Post
    st.markdown("#### Twitter")
    twitter_post = st.text_area(
        "Twitter Post",
        value=posts.get('twitter_post', ''),
        height=120,
        max_chars=280,
        key="twitter_edit"
    )
    st.caption(f"Characters: {len(twitter_post)}/280")
    
    # Instagram Post
    st.markdown("#### Instagram")
    instagram_post = st.text_area(
        "Instagram Post",
        value=posts.get('instagram_post', ''),
        height=180,
        key="instagram_edit"
    )
    
    # Save All Posts Button
    st.divider()
    
    if st.button("💾 Save All Posts", type="primary", use_container_width=True):
        try:
            # Create today's output directory
            today = datetime.now().strftime('%Y-%m-%d')
            output_dir = Path(f"outputs/{today}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare posts data with edited content
            posts_data = {
                'linkedin_post': linkedin_post,
                'twitter_post': twitter_post,
                'instagram_post': instagram_post,
                'image_prompt': edited_prompt
            }
            
            # Save individual posts
            if save_individual_posts(posts_data, output_dir):
                st.success(f"✅ All posts saved to {output_dir}/")
                
                # Show saved files
                st.info("📁 Saved files:\n" + 
                       f"• linkedin.txt\n" + 
                       f"• twitter.txt\n" + 
                       f"• instagram.txt\n" + 
                       f"• image_prompt.txt")
                
                # Reload the files to update session state
                load_todays_files()
            else:
                st.error("❌ Failed to save some posts")
                
        except Exception as e:
            st.error(f"❌ Error saving posts: {e}")
    
    if not st.session_state.social_posts:
        st.info("🔄 Run the workflow first to generate content, or content will load if files exist for today")


def mail_settings_section():
    """Mail settings section."""
    st.subheader("📧 Mail Agent Configuration")
    
    # Task Description
    st.markdown("#### Task Description")
    task_content = st.text_area(
        "Default workflow task for creating drafts",
        value=load_file('contexts/cron_draft_task.txt'),
        height=300,
        help="The default task description for the mail agent workflow",
        key="task_description_config"
    )
    
    # Context Files - Schools
    st.markdown("#### School Contexts")
    col1, col2 = st.columns(2)
    
    with col1:
        school_info_content = st.text_area(
            "School Info",
            value=load_file('contexts/schools/info.txt'),
            height=150,
            key="school_info_config"
        )
        
        school_new_content = st.text_area(
            "School - New Status",
            value=load_file('contexts/schools/status/new.txt'),
            height=100,
            key="school_new_config"
        )
        
        school_meeting_content = st.text_area(
            "School - Meeting Status",
            value=load_file('contexts/schools/status/meeting.txt'),
            height=100,
            key="school_meeting_config"
        )
    
    with col2:
        school_interested_content = st.text_area(
            "School - Interested Status",
            value=load_file('contexts/schools/status/interested.txt'),
            height=100,
            key="school_interested_config"
        )
        
        school_enrolled_content = st.text_area(
            "School - Enrolled Status",
            value=load_file('contexts/schools/status/enrolled.txt'),
            height=100,
            key="school_enrolled_config"
        )
    
    # Context Files - Companies
    st.markdown("#### Company Contexts")
    col1, col2 = st.columns(2)
    
    with col1:
        company_info_content = st.text_area(
            "Company Info",
            value=load_file('contexts/companies/info.txt'),
            height=150,
            key="company_info_config"
        )
        
        company_lead_content = st.text_area(
            "Company - Lead Status",
            value=load_file('contexts/companies/status/lead.txt'),
            height=100,
            key="company_lead_config"
        )
        
        company_active_content = st.text_area(
            "Company - Active Status",
            value=load_file('contexts/companies/status/active.txt'),
            height=100,
            key="company_active_config"
        )
    
    with col2:
        company_closed_content = st.text_area(
            "Company - Closed Status",
            value=load_file('contexts/companies/status/closed.txt'),
            height=100,
            key="company_closed_config"
        )
    
    # General Context Files
    st.markdown("#### General Contexts")
    col1, col2 = st.columns(2)
    
    with col1:
        general_content = st.text_area(
            "General Context",
            value=load_file('contexts/general_context.txt'),
            height=150,
            key="general_context_config"
        )
    
    with col2:
        enhancer_content = st.text_area(
            "Enhancer Context (Signature & Style)",
            value=load_file('contexts/enhancer_context.txt'),
            height=150,
            key="enhancer_context_config"
        )
    
    # Save Configuration Button
    if st.button("💾 Save Mail Configuration", type="primary"):
        success = True
        success &= save_config_file('contexts/cron_draft_task.txt', task_content)
        success &= save_config_file('contexts/schools/info.txt', school_info_content)
        success &= save_config_file('contexts/schools/status/new.txt', school_new_content)
        success &= save_config_file('contexts/schools/status/meeting.txt', school_meeting_content)
        success &= save_config_file('contexts/schools/status/interested.txt', school_interested_content)
        success &= save_config_file('contexts/schools/status/enrolled.txt', school_enrolled_content)
        success &= save_config_file('contexts/companies/info.txt', company_info_content)
        success &= save_config_file('contexts/companies/status/lead.txt', company_lead_content)
        success &= save_config_file('contexts/companies/status/active.txt', company_active_content)
        success &= save_config_file('contexts/companies/status/closed.txt', company_closed_content)
        success &= save_config_file('contexts/general_context.txt', general_content)
        success &= save_config_file('contexts/enhancer_context.txt', enhancer_content)
        
        if success:
            st.success("✅ Mail configuration saved successfully!")
        else:
            st.error("❌ Failed to save some configuration files")


def mail_run_section():
    """Mail workflow run section."""
    st.subheader("📧 Email Draft Generation")
    
    # Task Selection
    task_type = st.radio(
        "Select task type:",
        ["Create Drafts (Default Workflow)", "Custom Instruction"],
        index=0
    )
    
    custom_instruction = ""
    if task_type == "Custom Instruction":
        custom_instruction = st.text_area(
            "Custom instruction for the orchestrator:",
            height=200,
            placeholder="Enter your custom instruction here..."
        )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        run_button = st.button(
            "🚀 Run Mail Agent",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.mail_results = None
            st.session_state.mail_console_logs = ""
            st.rerun()
    
    # Console Output
    st.subheader("🖥️ Console Output")
    console_placeholder = st.empty()
    
    # Initialize mail session state
    if 'mail_results' not in st.session_state:
        st.session_state.mail_results = None
    if 'mail_console_logs' not in st.session_state:
        st.session_state.mail_console_logs = ""
    
    # Run workflow when button is clicked
    if run_button:
        with st.spinner("🔄 Running mail workflow..."):
            # Clear previous results
            st.session_state.mail_results = None
            st.session_state.mail_console_logs = "🚀 Starting mail workflow...\\n"
            
            # Update console display
            console_placeholder.markdown(f'<div class="console-output">{st.session_state.mail_console_logs}</div>', unsafe_allow_html=True)
            
            try:
                # Capture console output
                console_capture = ConsoleCapture()
                
                # Redirect stdout/stderr to capture
                with redirect_stdout(console_capture.output), redirect_stderr(console_capture.output):
                    # Create mail system
                    mail_system = EmailManagementSystem()
                    
                    if task_type == "Custom Instruction" and custom_instruction:
                        # Use custom instruction
                        results = asyncio.run(mail_system.process_new_emails(custom_task=custom_instruction))
                    else:
                        # Run default workflow (loads from cron_draft_task.txt)
                        results = asyncio.run(mail_system.process_new_emails())
                
                # Get captured output
                captured_output = console_capture.get_output()
                st.session_state.mail_console_logs += captured_output
                
                st.session_state.mail_results = results
                        
                st.session_state.mail_console_logs += "\\n✅ Mail workflow completed successfully!"
                st.success("✅ Mail workflow completed!")
                st.rerun()
                    
            except Exception as e:
                st.session_state.mail_console_logs += f"\\n❌ Error: {str(e)}"
                st.error(f"❌ Mail workflow error: {e}")
    
    # Display console logs
    if st.session_state.mail_console_logs:
        console_placeholder.markdown(f'<div class="console-output">{st.session_state.mail_console_logs}</div>', unsafe_allow_html=True)
    else:
        console_placeholder.markdown('<div class="console-output">[Ready] Waiting for mail workflow execution...</div>', unsafe_allow_html=True)
    
    # Results Section
    if st.session_state.mail_results:
        st.divider()
        st.subheader("📊 Workflow Results")
        
        if isinstance(st.session_state.mail_results, str):
            st.text_area("Results", value=st.session_state.mail_results, height=200)
        else:
            st.json(st.session_state.mail_results)


def main():
    """Main Streamlit application."""
    init_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        # Top-level application selection
        app_choice = st.radio(
            "Application",
            ["Web Scraper", "Mailing"],
            index=0,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Sub-navigation based on app choice
        if app_choice == "Web Scraper":
            st.subheader("Web Scraping")
            selected_section = st.radio(
                "Web Scraping Options",
                ["Configuration", "Run", "Preview"],
                index=0,
                label_visibility="collapsed"
            )
            
            # Show current date folder info
            today = datetime.now().strftime('%Y-%m-%d')
            st.write(f"📅 Working folder: {today}")
            
            if st.session_state.social_posts:
                st.write("✅ Content available")
            else:
                st.write("⏳ No content yet")
        
        else:  # Mailing
            st.subheader("Mailing")
            mailing_section = st.radio(
                "Mailing Options",
                ["Settings", "Run"],
                index=0,
                key="mailing_nav",
                label_visibility="collapsed"
            )
    
    # Main content based on app choice and sub-selection
    if app_choice == "Web Scraper":
        if selected_section == "Configuration":
            configuration_section()
        elif selected_section == "Run":
            run_section()
        elif selected_section == "Preview":
            preview_section()
    
    else:  # Mailing
        if mailing_section == "Settings":
            mail_settings_section()
        elif mailing_section == "Run":
            mail_run_section()

if __name__ == "__main__":
    main()