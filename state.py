"""
State management for the travel itinerary agent.
All steps read from and write to this shared state object.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any


@dataclass
class TravelState:
    """Accumulated state across the agent chain."""
    
    # User input
    user_input: str = ""
    
    # Step 1 output: Extracted preferences
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Step 2 output: Weather and attraction data
    weather_data: Dict[str, Any] = field(default_factory=dict)
    attractions_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # Step 3 output: Matched activities
    matched_activities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Step 4 output: Final itinerary
    itinerary: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return asdict(self)
    
    def add_error(self, error: str):
        """Log an error that occurred during processing."""
        self.errors.append(error)
    
    def summary(self) -> str:
        """Return a human-readable summary of the state."""
        lines = [
            "=== TRAVEL ITINERARY AGENT STATE ===",
            f"User Input: {self.user_input[:100]}..." if len(self.user_input) > 100 else f"User Input: {self.user_input}",
            f"Preferences Extracted: {bool(self.preferences)}",
            f"Weather Data Retrieved: {bool(self.weather_data)}",
            f"Attractions Found: {len(self.attractions_data)}",
            f"Activities Matched: {len(self.matched_activities)}",
            f"Itinerary Generated: {bool(self.itinerary)}",
        ]
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        return "\n".join(lines)
