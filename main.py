import asyncio
import os
import time
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from mcp_agent.app import MCPApp
from mcp_agent.config import (
    Settings,
    LoggerSettings,
    MCPSettings,
    MCPServerSettings,
    OpenAISettings,
    AnthropicSettings,
)
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.llm_selector import ModelPreferences
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.tracing.token_counter import TokenSummary


# Article data model
class Article(BaseModel):
    base_url: str
    title: str
    author: Optional[str] = None
    date: Optional[datetime] = None
    summary: str = ""
    used: int = Field(default=0, ge=0, le=1)
    link: Optional[str] = None
    
    def to_dict(self):
        return {
            "base_url": self.base_url,
            "title": self.title,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "summary": self.summary,
            "used": self.used,
            "link": self.link
        }
    
    @classmethod
    def get_schema_json(cls) -> str:
        """Returns the JSON schema of the Article model as a string"""
        return json.dumps(cls.model_json_schema(), indent=2)
    
    @classmethod
    def get_example_json(cls) -> str:
        """Returns an example JSON representation"""
        example = cls(
            base_url="https://example.com",
            title="Example Article Title",
            author="John Doe",
            date=datetime.now(),
            summary="",
            used=0,
            link="https://example.com/article"
        )
        return json.dumps(example.to_dict(), indent=2)


def extract_json_from_response(response: str) -> str:
    """Extract JSON from various response formats including markdown code blocks."""
    import re
    
    json_str = response.strip()
    
    # Remove markdown code blocks if present
    if "```json" in json_str or "```" in json_str:
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if json_match:
            json_str = json_match.group(1).strip()
    
    # If there's still non-JSON text, try to extract JSON object
    if not json_str.startswith('{'):
        # Look for JSON object in the text
        json_match = re.search(r'\{[^{}]*"base_url"[^{}]*\}', json_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
    
    return json_str


app = MCPApp(name="mcp_basic_agent")  

# Configuration
CRITERIA = "education and AI"
LINKEDIN_EXAMPLE = """🚀 Exciting developments in AI Education!

Recent insights from the tech community highlight three transformative trends:

1️⃣ [Article 1 Title] - [Key insight about how this impacts education]

2️⃣ [Article 2 Title] - [Brief explanation of the innovation]

3️⃣ [Article 3 Title] - [Why this matters for educators]

These advances show how AI is reshaping learning experiences and making education more accessible and personalized.

What are your thoughts on AI's role in education? 

#AIEducation #EdTech #Innovation #FutureOfLearning"""

TWITTER_EXAMPLE = """🧵 AI is transforming education in 3 key ways:

1/ [Article 1 Title]: [One-line insight]

2/ [Article 2 Title]: [One-line insight]  

3/ [Article 3 Title]: [One-line insight]

The future of learning is here! 🎓✨

#AI #EdTech #Education"""

urls = ["https://latent.space"]
spreadsheet_name = "articles"
spreadsheet_id = "1PMId37fQEBHPSdmZKcI36b1h0Jumy7ZsstF4u6v_QnA"


async def web_scraper():
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context

        logger.info("Current config:", data=context.config.model_dump())
        
        # Step 1: RSS/Web Scraper Agent
        scraped_articles = []
        
        rss_agent = Agent(
                name="rss",
                instruction=f"""You are an agent with Firecrawl access for efficient web scraping.
                
                Use firecrawl_extract to get the most recent article from the website.
                IMPORTANT: Only extract from the main page URL provided - DO NOT follow article links.
                
                Use this exact schema for firecrawl_extract:
                {{
                  "type": "object",
                  "properties": {{
                    "base_url": {{ "type": "string", "description": "The base URL of the website" }},
                    "title": {{ "type": "string", "description": "Article title" }},
                    "author": {{ "type": "string", "description": "Article author if visible" }},
                    "date": {{ "type": "string", "description": "Publication date if available" }},
                    "summary": {{ "type": "string", "description": "Brief summary or excerpt" }},
                    "link": {{ "type": "string", "description": "Direct link to the article" }}
                  }},
                  "required": ["title", "link"]
                }}
                
                Set the prompt parameter to: "Extract the most recent article's information from this page. Only use information visible on this page, do not follow links."
                
                CRITICAL: Return ONLY the extracted JSON matching this format:
                {Article.get_example_json()}
                
                Leave fields empty ("") if not found. NO explanatory text.""",
                server_names=["firecrawl"],
                )

        async with rss_agent:
            logger.info("RSS Agent: Starting article extraction...")
            llm = await rss_agent.attach_llm(AnthropicAugmentedLLM)
            
            for url in urls:
                max_retries = 0
                article_data = None
                
                for attempt in range(max_retries + 1):
                    try:
                        result = await llm.generate_str(
                            message=f"""Use firecrawl_extract on {url} to get the most recent article.
                            Use the schema and prompt as specified in your instructions.
                            Return ONLY the extracted JSON data.""",
                        )
                        
                        json_str = extract_json_from_response(result)
                        article_data = json.loads(json_str)
                        article = Article(**article_data)
                        break
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                        if attempt == max_retries:
                            logger.error(f"Failed to parse article from {url} after {max_retries + 1} attempts")
                            continue
                
                if article_data:
                    logger.info(f"Scraped: '{article.title}'")
                    scraped_articles.append(article)

            logger.info(f"RSS Agent completed. Scraped {len(scraped_articles)} articles.")

        # Step 2: Check for duplicates in spreadsheet
        new_articles = []
        
        duplicate_checker = Agent(
                name="duplicate_checker",
                instruction=f"""You are an agent with access to Google Sheets via Zapier. 
                Check if articles already exist in the spreadsheet.
                
                Spreadsheet ID: {spreadsheet_id}
                
                Use zapier_google_sheets_lookup_spreadsheet_row to check if article exists.
                Construct unique identifier by combining base_url and title.""",
                server_names=["zapier"]
                )
        
        async with duplicate_checker:
            logger.info("Duplicate Checker: Checking for existing articles...")
            llm = await duplicate_checker.attach_llm(AnthropicAugmentedLLM)
            
            for article in scraped_articles:
                unique_id = f"{article.base_url}|{article.title}"
                
                lookup_result = await llm.generate_str(
                    message=f"""Use zapier_google_sheets_lookup_spreadsheet_row to check if this article exists:
                    
                    Spreadsheet ID: {spreadsheet_id}
                    Lookup column: 'unique_id' 
                    Lookup value: '{unique_id}'
                    
                    If the lookup finds a match, return "EXISTS".
                    If no match is found or there's an error, return "NOT_FOUND".
                    Return ONLY one of these two words."""
                )
                
                if "NOT_FOUND" in lookup_result.upper():
                    new_articles.append(article)
                    logger.info(f"New article: '{article.title}'")
                else:
                    logger.info(f"Duplicate found: '{article.title}'")
            
            logger.info(f"Found {len(new_articles)} new articles out of {len(scraped_articles)} total")

        # Step 3: Select top 3 articles from NEW articles only
        selected_articles = []
        
        if new_articles:
            selector_agent = Agent(
                name="selector",
                instruction=f"""You are an expert content curator.
                
                Review the provided article titles and select the best one     
                that is most relevant to: {CRITERIA}
                
                Consider:
                - Direct relevance to the criteria
                - Recency and timeliness
                - Impact and innovation potential
                - Quality of insights
                
                Return ONLY an article title.

                Example:
                Title1
                """,
                server_names=[]
            )
            
            async with selector_agent:
                logger.info("Selector Agent: Selecting top articles...")
                llm = await selector_agent.attach_llm(AnthropicAugmentedLLM)
                
                articles_text = "\n\n".join([
                    f"Title: {article.title}\nDate: {article.date}"
                    for i, article in enumerate(new_articles)
                ])
                
                result = await llm.generate_str(
                    message=f"""From these NEW article titles, select the most relevant to "{CRITERIA}":

{articles_text}

Return ONLY one article title."""
                )
                
                try:
                    for article in new_articles:
                        if article.title == resutl:
                            article.used = 1
                            selected_articles.append(article)
                            logger.info(f"Selected: '{article.title}'")
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse selector response: {e}")
                    # Fallback: select first 3
                    selected_articles = new_articles[:3]
                    for article in selected_articles:
                        article.used = 1

        # Step 4: Extract full content for selected articles
        if selected_articles:
            content_extractor = Agent(
                name="content_extractor",
                instruction=f"""You are an agent with Firecrawl access for extracting article content.
                
                Use firecrawl_scrape to get the full text content of articles.
                Extract the main article body text, removing navigation, ads, and other non-content elements.
                
                Return the extracted content as clean text.""",
                server_names=["firecrawl"]
            )
            
            async with content_extractor:
                logger.info("Content Extractor: Fetching full article content for selected articles...")
                llm = await content_extractor.attach_llm(AnthropicAugmentedLLM)
                
                for article in selected_articles:
                    if article.link:
                        logger.info(f"Extracting content for: '{article.title}'")
                        
                        try:
                            result = await llm.generate_str(
                                message=f"""Use firecrawl_scrape to extract the full article content from this URL:
                                {article.link}
                                
                                Extract the main article text content.
                                Return ONLY the article text, no metadata or explanations."""
                            )
                            
                            # Replace the summary with the full extracted content
                            article.summary = result[:5000]  # Limit to 5000 chars to avoid token issues
                            logger.info(f"Extracted {len(result)} characters of content for '{article.title}'")
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract content for '{article.title}': {e}")
                            # Keep original summary if extraction fails

        # Step 5: Add all new articles to spreadsheet with proper used flags
        if new_articles:
            spreadsheet_writer = Agent(
                name="spreadsheet_writer",
                instruction=f"""You are an agent with access to Google Sheets via Zapier.
                Add new articles to the spreadsheet.
                
                Spreadsheet ID: {spreadsheet_id}
                
                Use zapier_google_sheets_create_spreadsheet_row to add articles.""",
                server_names=["zapier"]
            )
            
            async with spreadsheet_writer:
                logger.info("Spreadsheet Writer: Adding new articles...")
                llm = await spreadsheet_writer.attach_llm(AnthropicAugmentedLLM)
                
                for article in new_articles:
                    unique_id = f"{article.base_url}|{article.title}"
                    
                    await llm.generate_str(
                        message=f"""Use zapier_google_sheets_create_spreadsheet_row to add this article:
                        
                        Spreadsheet ID: {spreadsheet_id}
                        
                        Row data:
                        - unique_id: {unique_id}
                        - base_url: {article.base_url}
                        - title: {article.title}
                        - author: {article.author or ''}
                        - date: {article.date.isoformat() if article.date else ''}
                        - summary: {article.summary}
                        - used: {article.used}
                        - link: {article.link or ''}
                        
                        Add this as a new row to the spreadsheet."""
                    )
                    
                    status = "SELECTED" if article.used == 1 else "stored"
                    logger.info(f"Added ({status}): '{article.title}'")

        # Step 6: Generate social media posts from selected articles with full content
        if selected_articles:
            summarizer_agent = Agent(
                name="summarizer",
                instruction=f"""You are an expert social media content creator.
                
                Create engaging posts for LinkedIn and Twitter based on the provided articles. Mention source link in the post.
                
                LINKEDIN POST:
                - Professional tone, 150-300 words
                - Start with a hook
                - Include key insights from the articles
                - Use strategic emojis
                - End with a thought-provoking question
                - Add relevant hashtags
                
                TWITTER POST:
                - Concise and punchy, under 280 characters
                - Can be a thread if needed (mark with 1/, 2/, etc.)
                - Include the most impactful insight
                - Use 1-2 emojis
                - Add 2-3 trending hashtags
                
                Make each post unique and tailored to the specific articles.
                
                Return in this JSON format:
                {{
                    "linkedin_post": "Your LinkedIn post",
                    "twitter_post": "Your Twitter post"
                }}""",
                server_names=[]
            )
            
            async with summarizer_agent:
                logger.info("Summarizer Agent: Creating social media posts...")
                llm = await summarizer_agent.attach_llm(AnthropicAugmentedLLM)
                
                articles_text = "\n\n".join([
                    f"Article {i+1}:\nTitle: {article.title}\nContent: {article.summary[:1500]}\nURL: {article.link or article.base_url}"
                    for i, article in enumerate(selected_articles)
                ])
                
                result = await llm.generate_str(
                    message=f"""Create LinkedIn and Twitter posts based on these selected articles about {CRITERIA}.
                    
The content provided is the full article text - analyze it to extract the most important insights and trends.

{articles_text}

Focus on:
- Key innovations and breakthroughs mentioned
- Practical applications and impact
- Future implications
- Connecting themes across the articles

Return the posts in the specified JSON format."""
                )
                
                try:
                    json_str = extract_json_from_response(result)
                    posts = json.loads(json_str)
                    
                    twitter_post = posts.get("twitter_post", "")
                    print("\n" + "="*50)
                    print("LINKEDIN POST:")
                    print("="*50)
                    print(linkedin_post)
                    
                    print("\n" + "="*50)
                    print("TWITTER POST:")
                    print("="*50)
                    print(twitter_post)

                    return posts
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse posts: {e}")
        
        else:
            logger.info("No new articles to summarize.")
            
        return selected_articles

                    
async def example_usage():
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context

        logger.info("Current config:", data=context.config.model_dump())

        # Add the current directory to the filesystem server's args
        context.config.mcp.servers["filesystem"].args.extend([os.getcwd()])

        finder_agent = Agent(
            name="finder",
            instruction="""You are an agent with access to the filesystem, 
            as well as the ability to fetch URLs. Your job is to identify 
            the closest match to a user's request, make the appropriate tool calls, 
            and return the URI and CONTENTS of the closest match.""",
            server_names=["fetch", "filesystem"],
        )

        async with finder_agent:
            logger.info("finder: Connected to server, calling list_tools...")
            result = await finder_agent.list_tools()
            logger.info("Tools available:", data=result.model_dump())

            llm = await finder_agent.attach_llm(OpenAIAugmentedLLM)
            result = await llm.generate_str(
                message="Print the contents of mcp_agent.config.yaml verbatim",
            )
            logger.info(f"mcp_agent.config.yaml contents: {result}")

            # Let's switch the same agent to a different LLM
            llm = await finder_agent.attach_llm(AnthropicAugmentedLLM)

            result = await llm.generate_str(
                message="Print the first 2 paragraphs of https://modelcontextprotocol.io/introduction",
            )
            logger.info(f"First 2 paragraphs of Model Context Protocol docs: {result}")

            # Multi-turn conversations
            result = await llm.generate_str(
                message="Summarize those paragraphs in a 128 character tweet",
                # You can configure advanced options by setting the request_params object
                request_params=RequestParams(
                    # See https://modelcontextprotocol.io/docs/concepts/sampling#model-preferences for more details
                    modelPreferences=ModelPreferences(
                        costPriority=0.1, speedPriority=0.2, intelligencePriority=0.7
                    ),
                    # You can also set the model directly using the 'model' field
                    # Generally request_params type aligns with the Sampling API type in MCP
                ),
            )
            logger.info(f"Paragraph as a tweet: {result}")

        # Display final comprehensive token usage summary (use app convenience)
        await display_token_summary(agent_app, finder_agent)


async def display_token_summary(app_ctx: MCPApp, agent: Agent | None = None):
    """Display comprehensive token usage summary using app/agent convenience APIs."""
    summary: TokenSummary = await app_ctx.get_token_summary()

    print("\n" + "=" * 50)
    print("TOKEN USAGE SUMMARY")
    print("=" * 50)
    print(f"  Total tokens: {summary.usage.total_tokens:,}")
    print(f"  Input tokens: {summary.usage.input_tokens:,}")
    print(f"  Output tokens: {summary.usage.output_tokens:,}")
    print(f"  Total cost: ${summary.cost:.4f}")

    # Breakdown by model
    if summary.model_usage:
        print("\nBreakdown by Model:")
        for model_key, data in summary.model_usage.items():
            print(f"\n  {model_key}:")
            print(
                f"    Tokens: {data.usage.total_tokens:,} (input: {data.usage.input_tokens:,}, output: {data.usage.output_tokens:,})"
            )
            print(f"    Cost: ${data.cost:.4f}")

    # Optional: show a specific agent's aggregated usage
    if agent is not None:
        agent_usage = await agent.get_token_usage()
        if agent_usage:
            print("\nAgent Usage:")
            print(f"  Agent: {agent.name}")
            print(f"  Total tokens: {agent_usage.total_tokens:,}")
            print(f"  Input tokens: {agent_usage.input_tokens:,}")
            print(f"  Output tokens: {agent_usage.output_tokens:,}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(web_scraper())
    end = time.time()
    t = end - start

    print(f"Total run time: {t:.2f}s")
