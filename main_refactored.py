#!/usr/bin/env python3

import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM


# ============= Data Models =============
class Article(BaseModel):
    """Article data model with extraction schema."""
    base_url: str = Field(..., description="The base URL of the website")
    title: str = Field(..., description="Article title")
    author: Optional[str] = Field(None, description="Article author if visible")
    date: Optional[str] = Field(None, description="Publication date if available")  # Changed to str to handle various date formats
    content: str = Field(default="", description="Full article content (not stored in sheets)")
    used: int = Field(default=0, ge=0, le=1, description="Whether article was used for social posts")
    link: Optional[str] = Field(None, description="Direct link to the article")
    
    @property
    def id(self) -> str:
        """Generate unique ID for duplicate checking."""
        # Normalize title to handle special characters
        import unicodedata
        import re
        
        # Normalize unicode characters (— to -, etc.)
        normalized_title = unicodedata.normalize('NFKD', self.title)
        # Replace various dashes with standard dash
        normalized_title = re.sub(r'[—–―−]', '-', normalized_title)
        # Remove extra spaces and lowercase for consistency
        normalized_title = re.sub(r'\s+', ' ', normalized_title).strip().lower()
        
        return f"{self.base_url}|{normalized_title}"
    
    @classmethod
    def get_extraction_schema(cls) -> Dict[str, Any]:
        """Get Firecrawl extraction schema from the model."""
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Article title"},
                "author": {"type": "string", "description": "Author name if available"},
                "date": {"type": "string", "description": "Publication date"},
                "link": {"type": "string", "description": "Direct link to the article"}
            },
            "required": ["title", "link"]
        }
    
    def to_sheet_row(self) -> Dict[str, str]:
        """Convert to Google Sheets row format (no content in sheets)."""
        return {
            "id": self.id,
            "base_url": self.base_url,
            "title": self.title,
            "author": self.author or "",
            "date": self.date if self.date else "",  # Already a string now
            "used": str(self.used),
            "link": self.link or ""
        }


class BatchArticles(BaseModel):
    """Batch of articles for processing."""
    articles: List[Article]
    
    def to_sheet_rows(self) -> List[Dict[str, str]]:
        """Convert all articles to sheet rows."""
        return [article.to_sheet_row() for article in self.articles]


class SocialPosts(BaseModel):
    """Social media posts with validation."""
    linkedin_post: str = Field(..., min_length=50, max_length=3000)
    twitter_post: str = Field(..., min_length=10, max_length=280)
    instagram_post: str = Field(..., min_length=20, max_length=2200)

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get schema for social posts generation."""
        return {
            "linkedin_post": "string",
            "twitter_post": "string",
            "instagram_post": "string"
        }


# ============= Configuration =============
# Default values - will be overridden by parameters
DEFAULT_CRITERIA = "education and AI"
DEFAULT_SPREADSHEET_ID = "1PMId37fQEBHPSdmZKcI36b1h0Jumy7ZsstF4u6v_QnA"
DEFAULT_URLS = ["https://latent.space"]


# ============= Helper Functions =============
def parse_json_response(response: str) -> Any:
    """Extract and parse JSON from LLM response, handling markdown blocks."""
    import re
    
    json_str = response.strip()
    
    # Remove markdown code blocks if present
    if "```" in json_str:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if match:
            json_str = match.group(1).strip()
    
    # Try to find JSON object in the response
    # Look for patterns like {"title": ..., "link": ...}
    json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', json_str, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
    elif not json_str.startswith(('[', '{')):
        # Extract JSON object/array from text
        match = re.search(r'[\[\{].*[\]\}]', json_str, re.DOTALL)
        if match:
            json_str = match.group(0)
    
    # Clean up any escape sequences that might cause issues
    json_str = json_str.replace('\\n', '\n').replace('\\t', '\t')
    
    return json.loads(json_str)


# ============= Agent Workflows =============
class WebScraperWorkflow:
    """Manages the complete web scraping workflow with 3 optimized agents."""
    
    def __init__(self, logger, urls: List[str] = None, criteria: str = None, 
                 spreadsheet_id: str = None, progress_callback=None):
        self.logger = logger
        self.urls = urls or DEFAULT_URLS
        self.criteria = criteria or DEFAULT_CRITERIA
        self.spreadsheet_id = spreadsheet_id or DEFAULT_SPREADSHEET_ID
        self.progress_callback = progress_callback
        self.scraped_articles: List[Article] = []
        self.new_articles: List[Article] = []
        self.selected_article: Optional[Article] = None
        self.social_posts: Optional[SocialPosts] = None
    
    async def run(self) -> Dict[str, Any]:
        """Execute the complete workflow and return results."""
        self.logger.info("Starting web scraper workflow", 
                        data={"urls": self.urls, "criteria": self.criteria})
        
        if self.progress_callback:
            await self.progress_callback(0.1, "Starting web scraper workflow...")
    
        # Step 1: Scrape articles from URLs
        await self._scrape_articles()
        
        if self.progress_callback:
            await self.progress_callback(0.3, f"Scraped {len(self.scraped_articles)} articles")
        
        if not self.scraped_articles:
            self.logger.warning("No articles scraped, exiting workflow")
            return {"status": "failed", "reason": "no_articles_scraped"}
        
        # Step 2: Check duplicates and add new articles to spreadsheet
        await self._manage_spreadsheet()
        
        if self.progress_callback:
            await self.progress_callback(0.6, f"Found {len(self.new_articles)} new articles")
        
        if not self.new_articles:
            self.logger.info("No new articles found, all are duplicates")
            return {"status": "completed", "new_articles": 0}
        
        # Step 3: Select best article and generate content
        await self._process_content()
        
        if self.progress_callback:
            await self.progress_callback(1.0, "Workflow completed")
        
        return {
            "status": "completed",
            "scraped": len(self.scraped_articles),
            "new_articles": len(self.new_articles),
            "selected": self.selected_article.title if self.selected_article else None,
            "social_posts": self.social_posts.model_dump() if self.social_posts else None
        }
    
    async def _scrape_articles(self):
        """Agent 1: Web scraper using Firecrawl for article extraction."""
        if self.progress_callback:
            await self.progress_callback(0.1, "🔍 Initializing web scraper agent...")
        
        scraper = Agent(
            name="web_scraper",
            instruction="""You are a web scraping specialist using Firecrawl tools.
            Your task: Extract article information from provided URLs.
            
            Instructions:
            1. Use firecrawl_extract with the provided JSON schema
            2. Focus on the most recent/prominent article on each page
            3. Omit data that is not available with ""
            4. Return clean JSON data without any explanatory text
            
            Important: Only extract from the main page, do not follow links.""",
            server_names=["firecrawl"]
        )
        
        async with scraper:
            self.logger.info("Web Scraper Agent: Starting article extraction")
            if self.progress_callback:
                await self.progress_callback(0.15, "🤖 Web scraper agent initialized")
            
            llm = await scraper.attach_llm(AnthropicAugmentedLLM)
            
            # Get the extraction schema from the Article model
            extraction_schema = Article.get_extraction_schema()
            
            # Process each URL
            for i, url in enumerate(self.urls):
                try:
                    if self.progress_callback:
                        await self.progress_callback(
                            0.15 + (0.15 * i / len(self.urls)),
                            f"🌐 Scraping URL {i+1}/{len(self.urls)}: {url}"
                        )
                    
                    result = await llm.generate_str(
                        f"""Extract article information from {url}
                        
                        Steps:
                        1. Use the firecrawl_extract tool with URL: {url}
                        2. Use this extraction schema:
                        {json.dumps(extraction_schema, indent=2)}
                        3. Return the extracted data as JSON
                        
                        The response should be valid JSON with title, link, author (if available), and date (if available).
                        """
                    )
                    
                    # Log raw response for debugging
                    self.logger.info(f"Raw response length: {len(result)} chars")
                    if len(result) < 1000:
                        self.logger.info(f"Raw response: {result}")
                    
                    # Try to extract JSON from the response
                    try:
                        # Check if result contains extraction data
                        if "title" in result or "link" in result:
                            article_data = parse_json_response(result)
                            # Ensure date is a string or None
                            if 'date' in article_data and article_data['date']:
                                # Convert datetime objects to string if needed
                                if hasattr(article_data['date'], 'isoformat'):
                                    article_data['date'] = article_data['date'].isoformat()
                                else:
                                    article_data['date'] = str(article_data['date'])
                        else:
                            # If no article data, create minimal entry
                            self.logger.warning(f"No article data found in response for {url}")
                            article_data = {
                                "title": "Unable to extract article",
                                "link": url,
                                "author": None,
                                "date": None
                            }
                    except json.JSONDecodeError as je:
                        self.logger.error(f"JSON parse error: {je}")
                        self.logger.error(f"Response preview: {result[:200]}...")
                        # Create a minimal article entry
                        article_data = {
                            "title": f"Failed extraction from {url}",
                            "link": url,
                            "author": None,
                            "date": None
                        }
                    except Exception as e:
                        self.logger.error(f"Unexpected error: {e}")
                        # Create a minimal article entry
                        article_data = {
                            "title": f"Error extracting from {url}",
                            "link": url,
                            "author": None,
                            "date": None
                        }
                    
                    article_data['base_url'] = url  # Ensure base_url is set
                    
                    try:
                        article = Article(**article_data)
                        self.scraped_articles.append(article)
                    except Exception as e:
                        self.logger.error(f"Failed to create Article object: {e}")
                        self.logger.error(f"Article data was: {article_data}")
                        # Create minimal valid article
                        minimal_article = Article(
                            base_url=url,
                            title=article_data.get('title', 'Unknown'),
                            link=article_data.get('link', url)
                        )
                        self.scraped_articles.append(minimal_article)
                    
                    self.logger.info(f"Scraped: {article.title[:60]}...")
                    if self.progress_callback:
                        await self.progress_callback(
                            0.15 + (0.15 * (i+1) / len(self.urls)),
                            f"✅ Found article: {article.title[:60]}..."
                        )
                    
                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}", error=str(e))
                    if self.progress_callback:
                        await self.progress_callback(
                            0.15 + (0.15 * (i+1) / len(self.urls)),
                            f"⚠️ Failed to scrape {url}: {str(e)[:50]}"
                        )
            
            self.logger.info(f"Completed scraping: {len(self.scraped_articles)} articles")
    
    async def _manage_spreadsheet(self):
        """Agent 2: Spreadsheet manager for duplicate checking and data storage."""
        if self.progress_callback:
            await self.progress_callback(0.35, "📄 Initializing spreadsheet manager...")
        
        sheets_manager = Agent(
            name="spreadsheet_manager",
            instruction=f"""You are a Google Sheets data manager using Zapier tools.
            Your spreadsheet ID: {self.spreadsheet_id}
            
            Key responsibilities:
            1. Check for duplicate articles using the 'id' column
            2. Add new articles to the spreadsheet
            3. Update article status when needed
            
            Available batch operations for efficiency:
            - zapier_google_sheets_create_multiple_spreadsheet_rows (add multiple rows)
            - zapier_google_sheets_lookup_spreadsheet_rows_advanced (find up to 500 rows)
            - zapier_google_sheets_get_many_spreadsheet_rows_advanced (get up to 1500 rows)
            
            Always prefer batch operations over single operations when possible.""",
            server_names=["zapier"]
        )
        
        async with sheets_manager:
            self.logger.info("Spreadsheet Manager: Checking for duplicates")
            if self.progress_callback:
                await self.progress_callback(0.4, "🤖 Spreadsheet manager initialized")
            
            llm = await sheets_manager.attach_llm(AnthropicAugmentedLLM)
            
            # Check for duplicates
            if self.progress_callback:
                await self.progress_callback(0.45, "🔍 Checking for duplicate articles...")
            await self._check_duplicates(llm)
            
            # Add new articles to spreadsheet
            if self.new_articles:
                if self.progress_callback:
                    await self.progress_callback(0.55, f"📝 Adding {len(self.new_articles)} new articles to spreadsheet...")
                await self._add_articles_to_sheet(llm)
            else:
                if self.progress_callback:
                    await self.progress_callback(0.55, "ℹ️ No new articles to add (all duplicates)")
    
    async def _check_duplicates(self, llm):
        """Check which articles already exist in the spreadsheet."""
        article_ids = [article.id for article in self.scraped_articles]
        
        if len(article_ids) == 1:
            # Single article - use simple lookup
            result = await llm.generate_str(
                f"""Check if this article exists in the spreadsheet:
                
                Use: zapier_google_sheets_lookup_spreadsheet_row
                Spreadsheet ID: {self.spreadsheet_id}
                Column to search: 'id'
                Value to find: '{article_ids[0]}'
                
                Return only: 'EXISTS' if found, 'NOT_FOUND' if not found"""
            )
            
            if "NOT_FOUND" in result.upper():
                self.new_articles = self.scraped_articles
                self.logger.info("Article is new")
            else:
                self.logger.info("Article already exists")
        else:
            # Multiple articles - use batch lookup
            self.logger.info(f"Checking {len(article_ids)} articles for duplicates")
            
            result = await llm.generate_str(
                f"""Get all existing article IDs from the spreadsheet:
                
                Use: zapier_google_sheets_get_many_spreadsheet_rows_advanced
                Spreadsheet ID: {self.spreadsheet_id}
                Rows to fetch: First 500 rows
                
                Return ONLY a JSON array of the 'id' column values.
                Example: ["url1|title1", "url2|title2"]"""
            )
            
            try:
                existing_ids = parse_json_response(result)
                if isinstance(existing_ids, list):
                    # Filter out duplicates
                    self.new_articles = [
                        article for article in self.scraped_articles 
                        if article.id not in existing_ids
                    ]
                    self.logger.info(f"Found {len(self.new_articles)} new articles")
                else:
                    # Fallback - treat all as new
                    self.new_articles = self.scraped_articles
                    self.logger.warning("Could not parse existing IDs, treating all as new")
            except Exception as e:
                self.logger.warning(f"Duplicate check failed: {e}, treating all as new")
                self.new_articles = self.scraped_articles
    
    async def _add_articles_to_sheet(self, llm):
        """Add new articles to the spreadsheet."""
        batch = BatchArticles(articles=self.new_articles)
        rows_data = batch.to_sheet_rows()
        
        if len(rows_data) > 1:
            # Use batch creation for multiple rows
            self.logger.info(f"Adding {len(rows_data)} articles in batch")
            
            result = await llm.generate_str(
                f"""Add multiple articles to the spreadsheet:
                
                Use: zapier_google_sheets_create_multiple_spreadsheet_rows
                Spreadsheet ID: {self.spreadsheet_id}
                
                Rows to add:
                {json.dumps(rows_data, indent=2)}
                
                Confirm completion with 'ADDED'"""
            )
            
            if "ADDED" in result.upper() or "success" in result.lower():
                self.logger.info("Batch addition successful")
        else:
            # Single row addition
            self.logger.info("Adding single article")
            
            await llm.generate_str(
                f"""Add this article to the spreadsheet:
                
                Use: zapier_google_sheets_create_spreadsheet_row
                Spreadsheet ID: {self.spreadsheet_id}
                
                Row data: {json.dumps(rows_data[0], indent=2)}"""
            )
            
            self.logger.info("Article added successfully")
    
    async def _process_content(self):
        """Agent 3: Content processor for article selection and social media generation."""
        if self.progress_callback:
            await self.progress_callback(0.65, "📝 Initializing content processor...")
        
        processor = Agent(
            name="content_processor",
            instruction=f"""You are a content strategist and social media expert.
            Your focus area: {self.criteria}
            
            Tasks:
            1. Analyze articles for relevance, impact, and educational value
            2. Select the most valuable article for the audience
            3. Generate engaging social media content
            
            Selection criteria:
            - Direct relevance to {self.criteria}
            - Potential impact on the field
            - Novelty and innovation
            - Practical applications
            - Educational value
            
            Social media guidelines:
            - LinkedIn: Professional, insightful, 150-200 words
            - Twitter: Concise, engaging, under 280 characters
            - Instagram: Visual-focused, storytelling, 100-150 words
            - Include key takeaways and encourage discussion""",
            server_names=[]  # Pure LLM operations
        )
        
        async with processor:
            self.logger.info("Content Processor: Analyzing articles")
            if self.progress_callback:
                await self.progress_callback(0.7, "🤖 Content processor initialized")
            
            llm = await processor.attach_llm(AnthropicAugmentedLLM)
            
            # Select best article
            if self.progress_callback:
                await self.progress_callback(0.75, f"🎯 Selecting best article from {len(self.new_articles)} candidates...")
            await self._select_best_article(llm)
            
            if self.selected_article:
                # Fetch full content for selected article only
                if self.progress_callback:
                    await self.progress_callback(0.8, f"📥 Fetching full content for: {self.selected_article.title[:50]}...")
                await self._fetch_full_content()
                
                # Generate social posts
                if self.progress_callback:
                    await self.progress_callback(0.9, "✍️ Generating social media posts...")
                await self._generate_social_posts(llm)
                
                # Mark article as used in spreadsheet
                if self.progress_callback:
                    await self.progress_callback(0.95, "📋 Updating spreadsheet status...")
                await self._mark_article_used()
    
    async def _select_best_article(self, llm):
        """Select the most relevant article based on criteria."""
        articles_summary = "\n".join([
            f"{i+1}. {article.title}"
            f"{f' by {article.author}' if article.author else ''}"
            f"{f' ({article.date})' if article.date else ''}"
            for i, article in enumerate(self.new_articles)
        ])
        
        result = await llm.generate_str(
            f"""Analyze these articles about {self.criteria} and select the BEST one:
            
            {articles_summary}
            
            Consider:
            - Relevance to {self.criteria}
            - Timeliness and freshness
            
            Return ONLY the number (1-{len(self.new_articles)}) of your selection."""
        )
        
        try:
            idx = int(result.strip()) - 1
            if 0 <= idx < len(self.new_articles):
                self.selected_article = self.new_articles[idx]
                self.selected_article.used = 1
                self.logger.info(f"Selected: {self.selected_article.title}")
            else:
                raise ValueError("Index out of range")
        except (ValueError, IndexError):
            # Fallback to first article
            self.selected_article = self.new_articles[0]
            self.selected_article.used = 1
            self.logger.info(f"Selected (fallback): {self.selected_article.title}")
    
    async def _fetch_full_content(self):
        """Fetch full article content for the selected article only."""
        if not self.selected_article or not self.selected_article.link:
            return
        
        scraper = Agent(
            name="content_fetcher",
            instruction="""You are a content extraction specialist.
            Use firecrawl_scrape to get the full article text.
            Extract only the main article body, removing navigation, ads, and other clutter.""",
            server_names=["firecrawl"]
        )
        
        async with scraper:
            self.logger.info("Fetching full content for selected article")
            llm = await scraper.attach_llm(AnthropicAugmentedLLM)
            
            result = await llm.generate_str(
                f"""Extract the full article content:
                
                Use: firecrawl_scrape
                URL: {self.selected_article.link}
                
                Extract the main article text only.
                Remove navigation, advertisements, and non-content elements.
                Return the clean article text."""
            )
            
            # Store content (not sent to spreadsheet)
            self.selected_article.content = result[:5000]  # Limit for processing
            self.logger.info(f"Extracted {len(result)} characters of content")
    
    async def _generate_social_posts(self, llm):
        """Generate LinkedIn and Twitter posts for the selected article."""
        self.logger.info("Generating social media posts")
        
        # Use content if available, otherwise use title
        content_preview = self.selected_article.content[:1500] if self.selected_article.content else ""

        json_schema = SocialPosts.get_schema()
        
        posts_json = await llm.generate_str(
            f"""Create engaging social media posts for this {self.criteria} article:
            
            Title: {self.selected_article.title}
            Author: {self.selected_article.author or 'Unknown'}
            Link: {self.selected_article.link}
            
            {f'Key content: {content_preview}' if content_preview else ''}
            
            Requirements:
            1. LinkedIn post (150-200 words):
               - Professional tone
               - Include 2-3 key insights
               - End with a thought-provoking question
               - Add relevant hashtags
            
            2. Twitter post (under 280 characters):
               - Punchy and engaging
               - Include the main insight
               - Use 1-2 emojis strategically
               - Add 2-3 hashtags
            
            3. Instagram post (100-150 words):
               - Visual and storytelling focus
               - Start with a hook
               - Include call-to-action
               - Add 5-10 relevant hashtags
               - Use line breaks for readability
            
            Return as JSON using this schema:
            {json.dumps(json_schema, indent=2)}
            """
        )
        
        try:
            posts_data = parse_json_response(posts_json)
            self.social_posts = SocialPosts(**posts_data)
            
            self.logger.info("Generated social posts successfully")
            
            # Display posts
            print("\n" + "="*60)
            print("📝 LINKEDIN POST:")
            print("="*60)
            print(self.social_posts.linkedin_post)
            print("\n" + "="*60)
            print("🐦 TWITTER POST:")
            print("="*60)
            print(self.social_posts.twitter_post)
            print("\n" + "="*60)
            print("📸 INSTAGRAM POST:")
            print("="*60)
            print(self.social_posts.instagram_post)
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"Failed to generate social posts: {e}")
    
    async def _mark_article_used(self):
        """Update spreadsheet to mark the selected article as used."""
        if not self.selected_article:
            return
        
        sheets_updater = Agent(
            name="sheets_updater",
            instruction=f"""Update article status in Google Sheets.
            Spreadsheet ID: {self.spreadsheet_id}
            Find rows by 'id' column and update the 'used' field.""",
            server_names=["zapier"]
        )
        
        async with sheets_updater:
            llm = await sheets_updater.attach_llm(AnthropicAugmentedLLM)
            
            await llm.generate_str(
                f"""Mark article as used in spreadsheet:
                
                1. First use: zapier_google_sheets_lookup_spreadsheet_row
                   - Spreadsheet ID: {self.spreadsheet_id}
                   - Find row where id = '{self.selected_article.id}'
                
                2. Then use: zapier_google_sheets_update_spreadsheet_row
                   - Update the found row
                   - Set used = '1'
                
                Confirm with 'UPDATED' when complete."""
            )
            
            self.logger.info("Marked article as used in spreadsheet")


# ============= Main Entry Point =============
app = MCPApp(name="web_scraper")


async def web_scraper(urls: List[str] = None, criteria: str = None, 
                     spreadsheet_id: str = None, progress_callback=None):
    """Main entry point for the web scraper."""
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        urls = urls or DEFAULT_URLS
        criteria = criteria or DEFAULT_CRITERIA
        spreadsheet_id = spreadsheet_id or DEFAULT_SPREADSHEET_ID
        
        logger.info("="*60)
        logger.info("Web Scraper Started", data={
            "urls": urls,
            "criteria": criteria,
            "spreadsheet": spreadsheet_id
        })
        logger.info("="*60)
        
        workflow = WebScraperWorkflow(
            logger=logger,
            urls=urls,
            criteria=criteria,
            spreadsheet_id=spreadsheet_id,
            progress_callback=progress_callback
        )
        results = await workflow.run()
        
        # Log summary
        logger.info("="*60)
        logger.info("Workflow Complete", data=results)
        logger.info("="*60)
        
        return results


if __name__ == "__main__":
    start = time.time()
    results = asyncio.run(web_scraper())
    end = time.time()
    
    print(f"\n⏱️ Execution time: {end - start:.2f}s")
    print(f"📊 Results: {json.dumps(results, indent=2)}")
