"""
Source capture utility for agents.
"""

from typing import Dict, List, Any


class SourceCapture:
    """Utility class for capturing and managing sources in agents."""
    
    def __init__(self):
        self.sources: List[Dict[str, Any]] = []
    
    def add_source(self, publisher: str, url: str, title: str = "", accessed_at_utc: str = "") -> None:
        """Add a source to the capture list."""
        source = {
            "publisher": publisher,
            "url": url,
            "title": title,
            "accessed_at_utc": accessed_at_utc
        }
        self.sources.append(source)
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """Get all captured sources."""
        return self.sources.copy()
    
    def clear(self) -> None:
        """Clear all captured sources."""
        self.sources.clear()