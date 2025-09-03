#!/usr/bin/env python3
"""
Simple Web Scraper using Direct API Calls
==========================================

A clean implementation using:
- Firecrawl API for web scraping
- Anthropic API for content generation  
- Pure Python for workflow orchestration
- File-based I/O for configuration and outputs

No agents or complex frameworks - just direct API calls.
"""

import json
import os
import requests
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Third-party imports
from anthropic import Anthropic
from firecrawl import FirecrawlApp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Article:
    """Simple article data structure."""
    title: str
    link: str
    author: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


@dataclass 
class SocialPosts:
    """Social media posts data structure."""
    linkedin_post: str
    twitter_post: str
    instagram_post: str


class WebScraperWorkflow:
    """Simple web scraper workflow using direct API calls."""
    
    def __init__(self):
        # Load API keys from environment
        self.firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.stability_api_key = os.getenv('STABILITY_API_KEY')
        
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is required")
        if not self.stability_api_key:
            raise ValueError("STABILITY_API_KEY environment variable is required")

        # Initialize Anthropic client
        self.anthropic = Anthropic(api_key=self.anthropic_api_key)
        
        # Initialize Firecrawl client
        self.firecrawl = FirecrawlApp(api_key=self.firecrawl_api_key)
        
        # Load configuration
        self.urls = self._load_urls()
        self.selection_criteria = self._load_selection_criteria()
        self.image_style = self._load_image_style()
        self.image_prompt = None  # Will be set by generate_image_prompt
        self.processed_articles = self._load_processed_articles()
        
        print(f"🚀 Initialized Web Scraper")
        print(f"📋 URLs to process: {len(self.urls)}")
        print(f"🎯 Criteria: {self.selection_criteria}")
        print(f"📚 Previously processed: {len(self.processed_articles)}")
    
    def _load_urls(self) -> List[str]:
        """Load URLs from sources.txt file."""
        try:
            with open('webscraper_inputs/sources.txt', 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return urls
        except FileNotFoundError:
            print("⚠️  sources.txt not found, using default URL")
            return ["https://www.uipath.com/blog/ai"]
    
    def _load_selection_criteria(self) -> str:
        """Load selection criteria from criteria.txt file."""
        try:
            with open('webscraper_inputs/selection_criteria.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            print("⚠️  criteria.txt not found, using default criteria")
            return "education and AI"

    def _load_image_style(self) -> str:
        """Load image style for image prompt"""
        try:
            with open('webscraper_inputs/image_style.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            print("⚠️ image_style.txt not found, using default style")
            return "nice picture"

    def _load_processed_articles(self) -> set:
        """Load previously processed article URLs from articles.txt."""
        try:
            with open('webscraper_inputs/articles.txt', 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return set(lines)
        except FileNotFoundError:
            # Create empty file
            with open('webscraper_inputs/articles.txt', 'w') as f:
                f.write("# This file tracks processed article URLs to prevent duplicates\n")
                f.write("# Each line contains one article URL\n")
                f.write("# New articles will be automatically appended by the system")
            return set()
    
    def _save_processed_article(self, url: str):
        """Add a new processed article URL to articles.txt."""
        with open('webscraper_inputs/articles.txt', 'a') as f:
            f.write(f"{url}\n")
        self.processed_articles.add(url)
    
    def scrape_article_from_url(self, url: str) -> Optional[Article]:
        """Scrape the most recent article from a URL using Firecrawl API."""
        print(f"🌐 Extracting most recent article from: {url}")
        
        # Define JSON schema for extraction
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Article title"},
                "author": {"type": "string", "description": "Author name if available"},
                "date": {"type": "string", "description": "Publication date in YYYY-MM-DD format if available"},
                "link": {"type": "string", "description": "Direct link to the article"},
                "description": {"type": "string", "description": "Description of what is article about if available"}
            },
            "required": ["title", "link"]
        }
        
        try:
            # Use Firecrawl scrape_url method
            result = self.firecrawl.scrape_url(
                url,
                params={
                    'formats': ['extract'],
                    'extract': {
                        'prompt': 'Extract the most recent article information including title, author, publication date, and direct link to the article',
                        'schema': schema
                    }
                }
            )
            
            # Extract the JSON data from the result
            if result and 'extract' in result:
                article_data = result['extract']
                
                return Article(
                    title=article_data.get('title', 'Unknown Title'),
                    link=article_data.get('link', url),
                    author=article_data.get('author'),
                    date=article_data.get('date'),
                    description=article_data.get('description')
                )
            else:
                print(f"⚠️  No article found for {url}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to extract article from {url}: {e}")
            return None
    
    def get_full_article_content(self, article: Article) -> Article :
        """Get full article content using Firecrawl scrape."""
        print(f"📖 Fetching full content for: {article.title}")
        
        try:
            # Use Firecrawl scrape_url method
            result = self.firecrawl.scrape_url(
                article.link,
                params={'formats': ['markdown']}
            )
            
            content = result.get('markdown', '') if result else ''
            
            # Limit content length for processing
            description = content[:5000] if content else article.description
            
            article.description = description
            return article  

            
        except Exception as e:
            print(f"⚠️  Failed to fetch full content: {e}")
            return article   
    
    def select_best_article(self, articles: List[Article]) -> Optional[Article]:
        """Select the best article based on criteria using Anthropic."""
        if not articles:
            return None
        
        if len(articles) == 1:
            return articles[0]
        
        print(f"🤔 Selecting best article from {len(articles)} candidates...")
        
        # Prepare article summaries
        articles_text = "\n\n".join([
    "\n".join(filter(None, [
        f"Article {i+1}:",
        f"Title: {article.title}",
        f"Author: {article.author}" if article.author else None,
        f"Date: {article.date}" if article.date else None,
        f"Description: {article.description}" if article.description else None
    ]))
    for i, article in enumerate(articles)
        ])

        try:
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""🎯 ARTICLE SELECTION TASK

You are an expert content curator selecting the BEST article for social media engagement.

📊 ARTICLES TO EVALUATE:
{articles_text}

🔍 SELECTION CRITERIA (in order of importance):
1. **Relevance to "{self.selection_criteria}"** - How directly does it address this topic?
2. **Social Media Potential** - Will this generate engagement, shares, and discussions?
3. **Timeliness** - Is this current, trending, or newsworthy?
4. **Content Quality** - Is it well-written, authoritative, and informative?
5. **Uniqueness** - Does it offer fresh insights or unique perspectives?
6. **Actionability** - Does it provide practical value readers can apply?

💡 EVALUATION FRAMEWORK:
- Score each article 1-10 on relevance to "{self.selection_criteria}"
- Consider which article would perform best on LinkedIn, Twitter, and Instagram
- Prioritize articles that spark conversation and professional discussion
- Look for content that offers concrete insights, not just generic information

📝 RESPONSE FORMAT:
Return ONLY the number (1-{len(articles)}) of your selection, nothing else."""
                }]
            )
            
            selection_text = message.content[0].text.strip()
            
            try:
                selection = int(selection_text)
                if 1 <= selection <= len(articles):
                    selected = articles[selection - 1]
                    print(f"✅ Selected: {selected.title}")
                    return selected
            except ValueError:
                pass
            
            # Fallback to first article
            print("⚠️  Using first article as fallback")
            return articles[0]
            
        except Exception as e:
            print(f"❌ Selection failed: {e}, using first article")
            return articles[0]
    
    def generate_social_posts(self, article: Article) -> SocialPosts:
        """Generate social media posts using Anthropic."""
        print(f"📱 Generating social media posts for: {article.title}")
        
        # Get full content
        article = self.get_full_article_content(article)
        
        try:
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Create highly engaging, platform-optimized social media posts for this article:

📋 ARTICLE DETAILS:
Title: {article.title}
Author: {article.author or 'Unknown'}
Link: {article.link}
Content: {article.description}

🎯 PLATFORM-SPECIFIC REQUIREMENTS:

📌 LINKEDIN POST (150-200 words):
- Professional, thought-provoking tone
- Start with a compelling hook/question
- Include 2-3 key insights from the article
- End with a call-to-action encouraging discussion
- Use 3-5 relevant hashtags (#AI #Technology #Innovation #Business #Learning)
- Include the article link
- Focus on professional value and industry insights

🐦 TWITTER POST (MAXIMUM 250 characters):
- Punchy, attention-grabbing opening
- Include 1-2 emojis for visual appeal
- Essential insight in under 200 chars
- Include article link
- Use 2-3 hashtags (#AI #Tech #Innovation)
- Create urgency or curiosity
- CRITICAL: Total character count MUST be under 250!

📸 INSTAGRAM POST (100-150 words):
- Visual-first storytelling approach
- Start with emoji hook
- Focus on lifestyle/inspiration angle
- Break into short, scannable paragraphs
- Use 5-8 hashtags including trending ones
- Include "Link in bio" instead of direct link
- Emphasize visual appeal and personal growth

Return as valid JSON:
{{
    "linkedin_post": "...",
    "twitter_post": "...",
    "instagram_post": "..."
}}"""
                }]
            )
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                posts_data = json.loads(json_str)
                
                # Ensure Twitter post is under 280 characters
                twitter_post = posts_data.get('twitter_post', '')
                if len(twitter_post) > 280:
                    print(f"⚠️  Twitter post too long ({len(twitter_post)} chars), truncating...")
                    twitter_post = twitter_post[:270] + "... #AI"
                
                return SocialPosts(
                    linkedin_post=posts_data.get('linkedin_post', ''),
                    twitter_post=twitter_post,
                    instagram_post=posts_data.get('instagram_post', ''),
                )
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"❌ Failed to generate posts: {e}")
            # Create fallback posts
            twitter_text = f"📰 {article.title[:100]}... {article.link} #AI #Tech"
            if len(twitter_text) > 280:
                available_chars = 280 - len(f"... {article.link} #AI #Tech")
                truncated_title = article.title[:available_chars-10]
                twitter_text = f"📰 {truncated_title}... {article.link} #AI #Tech"
            
            return SocialPosts(
                linkedin_post=f"Check out this insightful article about {self.selection_criteria}: {article.title}\n\n{article.link}\n\n#AI #Technology #Innovation",
                twitter_post=twitter_text,
                instagram_post=f"New article alert! 🚀\n\n{article.title}\n\nLink in bio.\n\n#AI #Technology #Innovation #Learning",
            )
    def generate_image_prompt(self, linkedin_post: str) -> str:
        """Generate prompt for image generation"""
        print(f"Linkedin post used for generation of image generation prompt: {linkedin_post}")
        full_prompt = f"Create an image generation prompt for this LinkedIn post: {linkedin_post}. Style: {self.image_style}. Return only the prompt."

        try:
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )
            
            generated_prompt = message.content[0].text.strip()
            self.image_prompt = f"{generated_prompt}. Please follow this stylistic guidelines: {self.image_style}"
            
        except Exception as e:
            print(f"❌ Failed to generate image prompt: {e}")
            self.image_prompt = f"Modern technology illustration representing {self.selection_criteria}. Please follow this stylistic guidelines: {self.image_style}" 
    
    def generate_image(self, prompt: str, output_dir: Path) -> Optional[str]:
        """Generate image using Stability AI API."""
        print(f"🎨 Generating image for: {prompt}")
        
        # Generate image filename
        timestamp = int(time.time())
        image_path = output_dir / f"generated_image_{timestamp}.png"
        
        try:
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/ultra",
                headers={
                    "authorization": f"Bearer {self.stability_api_key}",
                    "accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": prompt,
                    "output_format": "png",
                },
                timeout=60
            )
            
            if response.status_code == 200:
                with open(image_path, 'wb') as file:
                    file.write(response.content)
                
                print(f"🖼️  Image saved: {image_path}")
                return str(image_path)
            else:
                print(f"❌ Image generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to generate image: {e}")
            return None
    
    def save_outputs(self, article: Article, posts: SocialPosts) -> str:
        """Save social media posts to date-based output folder."""
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = Path(f"outputs/{today}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate image
        image_path = None
        self.generate_image_prompt(posts.linkedin_post)
        if self.image_prompt:
            image_path = self.generate_image(self.image_prompt, output_dir)
        
        # Save posts as JSON
        output_data = {
            "article": {
                "title": article.title,
                "author": article.author,
                "date": article.date,
                "link": article.link
            },
            "social_posts": {
                "linkedin_post": posts.linkedin_post,
                "twitter_post": posts.twitter_post,
                "instagram_post": posts.instagram_post,
                "image_prompt": self.image_prompt
            },
            "image_path": image_path,
            "generated_at": datetime.now().isoformat(),
            "criteria": self.selection_criteria
        }
        
        output_file = output_dir / f"social_posts_{int(time.time())}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Save individual platform files (overwrite if exists)
        with open(output_dir / "linkedin.txt", 'w', encoding='utf-8') as f:
            f.write(posts.linkedin_post)
        
        with open(output_dir / "twitter.txt", 'w', encoding='utf-8') as f:
            f.write(posts.twitter_post)
            
        with open(output_dir / "instagram.txt", 'w', encoding='utf-8') as f:
            f.write(posts.instagram_post)
            
        with open(output_dir / "image_prompt.txt", 'w', encoding='utf-8') as f:
            f.write(self.image_prompt)
        
        print(f"💾 Saved individual files: linkedin.txt, twitter.txt, instagram.txt, image_prompt.txt")
        
        # Also save as readable text
        text_file = output_dir / f"social_posts_{int(time.time())}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Article: {article.title}\n")
            f.write(f"Author: {article.author or 'Unknown'}\n")
            f.write(f"Date: {article.date or 'Unknown'}\n")
            f.write(f"Link: {article.link}\n\n")
            f.write("=" * 60 + "\n")
            f.write("LINKEDIN POST:\n")
            f.write("=" * 60 + "\n")
            f.write(posts.linkedin_post + "\n\n")
            f.write("=" * 60 + "\n")
            f.write("TWITTER POST:\n")
            f.write("=" * 60 + "\n")
            f.write(posts.twitter_post + "\n\n")
            f.write("=" * 60 + "\n")
            f.write("INSTAGRAM POST:\n")
            f.write("=" * 60 + "\n")
            f.write(posts.instagram_post + "\n\n")
            f.write("=" * 60 + "\n")
            f.write("IMAGE PROMPT:\n")
            f.write("=" * 60 + "\n")
            f.write(self.image_prompt + "\n")
            if image_path:
                f.write(f"\nGenerated Image: {image_path}\n")
        
        print(f"💾 Saved outputs to: {output_file}")
        return str(output_file)
    
    def run(self) -> Dict[str, Any]:
        """Execute the complete workflow."""
        start_time = time.time()
        
        print("\n" + "=" * 60)
        print("🚀 Starting Web Scraper Workflow")
        print("=" * 60)
        
        # Step 1: Scrape articles from all URLs
        print(f"\n📥 Step 1: Scraping {len(self.urls)} URLs...")
        scraped_articles = []
        
        for url in self.urls:
            article = self.scrape_article_from_url(url)
            if article:
                scraped_articles.append(article)
        
        print(f"✅ Scraped {len(scraped_articles)} articles")
        
        if not scraped_articles:
            print("❌ No articles found!")
            return {"status": "error", "message": "No articles found"}
        
        # Step 2: Filter out duplicates
        print(f"\n🔍 Step 2: Checking for duplicates...")
        new_articles = []
        for article in scraped_articles:
            if article.link not in self.processed_articles:
                new_articles.append(article)
            else:
                print(f"⏭️  Skipping duplicate: {article.title}")
        
        print(f"✅ Found {len(new_articles)} new articles")
        
        if not new_articles:
            print("ℹ️  No new articles to process")
            return {"status": "success", "message": "No new articles found", "new_articles": 0}
        
        # Step 3: Select best article
        print(f"\n🎯 Step 3: Selecting best article...")
        selected_article = self.select_best_article(new_articles)
        
        if not selected_article:
            print("❌ No article selected!")
            return {"status": "error", "message": "No article selected"}
        
        # Step 4: Generate social media posts
        print(f"\n📱 Step 4: Generating social media posts...")
        social_posts = self.generate_social_posts(selected_article)
        
        # Step 5: Save outputs
        print(f"\n💾 Step 5: Saving outputs...")
        output_path = self.save_outputs(selected_article, social_posts)
        
        # Step 6: Mark article as processed
        print(f"\n📝 Step 6: Marking article as processed...")
        self._save_processed_article(selected_article.link)
        
        end_time = time.time()
        
        print("\n" + "=" * 60)
        print("✅ Workflow Complete!")
        print("=" * 60)
        print(f"⏱️  Execution time: {end_time - start_time:.2f}s")
        print(f"📄 Selected article: {selected_article.title}")
        print(f"🔗 Article link: {selected_article.link}")
        print(f"💾 Output saved: {output_path}")
        
        return {
            "status": "success",
            "execution_time": end_time - start_time,
            "scraped_articles": len(scraped_articles),
            "new_articles": len(new_articles),
            "selected_article": {
                "title": selected_article.title,
                "link": selected_article.link,
                "author": selected_article.author,
                "date": selected_article.date
            },
            "output_path": output_path
        }


def main():
    """Main entry point."""
    try:
        workflow = WebScraperWorkflow()
        results = workflow.run()
        
        print(f"\n📊 Final Results:")
        print(json.dumps(results, indent=2))
        
        return results
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    main()
