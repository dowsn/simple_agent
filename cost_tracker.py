"""
Cost tracking for API usage in the workflow
"""

from typing import Dict, List
from datetime import datetime


class CostTracker:
    """Track API usage costs for the workflow."""
    
    # Pricing as of 2024 (adjust as needed)
    PRICING = {
        'anthropic': {
            'claude-3-opus': {'input': 15.00, 'output': 75.00},  # per 1M tokens
            'claude-3-sonnet': {'input': 3.00, 'output': 15.00},  # per 1M tokens
            'claude-3-haiku': {'input': 0.25, 'output': 1.25},    # per 1M tokens
        },
        'firecrawl': {
            'extract': 0.01,  # per URL
            'scrape': 0.01,   # per URL
        },
        'zapier': {
            'action': 0.01,   # per action (estimate)
        }
    }
    
    def __init__(self):
        """Initialize cost tracker."""
        self.usage = {
            'anthropic_tokens': {'input': 0, 'output': 0},
            'firecrawl_calls': 0,
            'zapier_actions': 0,
            'start_time': datetime.now(),
            'end_time': None
        }
    
    def track_llm_usage(self, input_tokens: int, output_tokens: int):
        """Track LLM token usage."""
        self.usage['anthropic_tokens']['input'] += input_tokens
        self.usage['anthropic_tokens']['output'] += output_tokens
    
    def track_firecrawl(self, count: int = 1):
        """Track Firecrawl API calls."""
        self.usage['firecrawl_calls'] += count
    
    def track_zapier(self, count: int = 1):
        """Track Zapier actions."""
        self.usage['zapier_actions'] += count
    
    def calculate_costs(self, model: str = 'claude-3-sonnet') -> Dict[str, float]:
        """Calculate total costs based on usage."""
        costs = {}
        
        # Anthropic costs (convert tokens to millions)
        if model in self.PRICING['anthropic']:
            pricing = self.PRICING['anthropic'][model]
            input_cost = (self.usage['anthropic_tokens']['input'] / 1_000_000) * pricing['input']
            output_cost = (self.usage['anthropic_tokens']['output'] / 1_000_000) * pricing['output']
            costs['anthropic'] = round(input_cost + output_cost, 4)
        else:
            # Estimate based on average
            costs['anthropic'] = round(
                (self.usage['anthropic_tokens']['input'] + self.usage['anthropic_tokens']['output']) * 0.00001, 4
            )
        
        # Firecrawl costs
        costs['firecrawl'] = round(self.usage['firecrawl_calls'] * self.PRICING['firecrawl']['extract'], 4)
        
        # Zapier costs
        costs['zapier'] = round(self.usage['zapier_actions'] * self.PRICING['zapier']['action'], 4)
        
        # Total
        costs['total'] = round(sum(costs.values()), 4)
        
        return costs
    
    def get_summary(self, model: str = 'claude-3-sonnet') -> Dict[str, any]:
        """Get complete usage and cost summary."""
        self.usage['end_time'] = datetime.now()
        duration = (self.usage['end_time'] - self.usage['start_time']).total_seconds()
        
        costs = self.calculate_costs(model)
        
        return {
            'duration_seconds': round(duration, 2),
            'usage': {
                'llm_tokens': {
                    'input': self.usage['anthropic_tokens']['input'],
                    'output': self.usage['anthropic_tokens']['output'],
                    'total': self.usage['anthropic_tokens']['input'] + self.usage['anthropic_tokens']['output']
                },
                'firecrawl_calls': self.usage['firecrawl_calls'],
                'zapier_actions': self.usage['zapier_actions']
            },
            'costs': costs,
            'cost_breakdown': {
                'anthropic': f"${costs['anthropic']:.4f}",
                'firecrawl': f"${costs['firecrawl']:.4f}",
                'zapier': f"${costs['zapier']:.4f}",
                'total': f"${costs['total']:.4f}"
            }
        }
    
    def estimate_workflow_cost(self, num_urls: int, num_articles: int) -> float:
        """Estimate cost for a workflow run."""
        estimated_costs = {
            'firecrawl': num_urls * self.PRICING['firecrawl']['extract'],
            'firecrawl_content': self.PRICING['firecrawl']['scrape'],  # One article content
            'zapier': 5 * self.PRICING['zapier']['action'],  # Estimate 5 actions
            'anthropic': 0.05  # Rough estimate for typical workflow
        }
        
        return round(sum(estimated_costs.values()), 4)