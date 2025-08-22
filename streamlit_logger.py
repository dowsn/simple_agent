"""
Custom logger for Streamlit that updates logs in real-time
"""

import streamlit as st
from datetime import datetime
from typing import Optional, List
import asyncio


class StreamlitLogger:
    """Logger that updates Streamlit display in real-time."""
    
    def __init__(self, container=None):
        """Initialize the logger with a Streamlit container."""
        self.container = container
        self.logs: List[str] = []
        self._update_counter = 0  # Counter to force updates
        
    def add_log(self, message: str, level: str = "INFO"):
        """Add a log entry and update display."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Add emoji based on level
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍",
            "PROGRESS": "🔄"
        }.get(level, "📝")
        
        log_entry = f"[{timestamp}] {emoji} {message}"
        self.logs.append(log_entry)
        
        # Update display if container exists
        if self.container:
            self.update_display()
    
    def update_display(self):
        """Update the Streamlit display with current logs."""
        if self.container:
            log_text = "\n".join(self.logs)
            # Use code block for terminal-like display
            self.container.code(log_text, language="log")
    
    def clear(self):
        """Clear all logs."""
        self.logs = []
        if self.container:
            self.update_display()
    
    def get_logs(self) -> str:
        """Get all logs as a string."""
        return "\n".join(self.logs)


class AsyncProgressCallback:
    """Async callback for workflow progress that updates Streamlit."""
    
    def __init__(self, progress_bar=None, logger: Optional[StreamlitLogger] = None):
        """Initialize with Streamlit components."""
        self.progress_bar = progress_bar
        self.logger = logger
    
    async def __call__(self, progress: float, message: str):
        """Update progress and log message."""
        # Update progress bar if available
        if self.progress_bar:
            self.progress_bar.progress(progress, text=message)
        
        # Add to logger if available
        if self.logger:
            # Determine log level from message
            if "error" in message.lower() or "failed" in message.lower():
                level = "ERROR"
            elif "warning" in message.lower():
                level = "WARNING"
            elif "✅" in message or "completed" in message.lower():
                level = "SUCCESS"
            else:
                level = "PROGRESS"
            
            self.logger.add_log(message, level)
        
        # Small delay to allow UI update
        await asyncio.sleep(0.01)