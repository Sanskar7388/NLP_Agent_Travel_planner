"""
External tools for the travel itinerary agent.
Currently integrates: Open-Meteo Weather API (free, no key required)
"""
import requests
from typing import Dict, List, Any
from datetime import datetime, timedelta


def fetch_weather_forecast(
    latitude: float, 
    longitude: float, 
    destination: str,
    num_days: int = 5
) -> Dict[str, Any]:
    """
    Fetch weather forecast using Open-Meteo API (free, no authentication required).
    
    Args:
        latitude: Destination latitude
        longitude: Destination longitude
        destination: Destination name (for context)
        num_days: Number of days to forecast
    
    Returns:
        Dictionary with weather data for the destination
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        # Calculate date range
        today = datetime.now().date()
        end_date = today + timedelta(days=num_days)
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": str(today),
            "end_date": str(end_date),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse the forecast into readable format
        daily = data.get("daily", {})
        weather_forecast = []
        
        for i, date_str in enumerate(daily.get("time", [])):
            weather_forecast.append({
                "date": date_str,
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "weather_code": daily["weather_code"][i],
                "weather_description": _weather_code_to_description(daily["weather_code"][i])
            })
        
        return {
            "destination": destination,
            "latitude": latitude,
            "longitude": longitude,
            "forecast": weather_forecast,
            "retrieved_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "destination": destination,
            "error": f"Failed to fetch weather: {str(e)}",
            "forecast": []
        }


def get_sample_attractions(destination: str) -> List[Dict[str, Any]]:
    """
    Get sample attractions for common destinations.
    In a production system, this would query a real attraction API.
    
    Args:
        destination: Destination name
    
    Returns:
        List of attractions with details
    """
    attractions_db = {
        "paris": [
            {"name": "Eiffel Tower", "category": "landmark", "duration_hours": 2, "best_time": "morning", "rating": 4.8},
            {"name": "Louvre Museum", "category": "museum", "duration_hours": 3, "best_time": "morning", "rating": 4.7},
            {"name": "Notre-Dame", "category": "landmark", "duration_hours": 1.5, "best_time": "afternoon", "rating": 4.6},
            {"name": "Arc de Triomphe", "category": "landmark", "duration_hours": 1, "best_time": "sunset", "rating": 4.5},
            {"name": "Seine River Cruise", "category": "activity", "duration_hours": 2, "best_time": "evening", "rating": 4.6},
        ],
        "tokyo": [
            {"name": "Senso-ji Temple", "category": "landmark", "duration_hours": 2, "best_time": "morning", "rating": 4.7},
            {"name": "Shibuya Crossing", "category": "experience", "duration_hours": 1, "best_time": "evening", "rating": 4.6},
            {"name": "Tokyo National Museum", "category": "museum", "duration_hours": 3, "best_time": "morning", "rating": 4.5},
            {"name": "Meiji Shrine", "category": "landmark", "duration_hours": 1.5, "best_time": "morning", "rating": 4.4},
            {"name": "Tsukiji Outer Market", "category": "experience", "duration_hours": 2, "best_time": "morning", "rating": 4.6},
        ],
        "new york": [
            {"name": "Statue of Liberty", "category": "landmark", "duration_hours": 3, "best_time": "morning", "rating": 4.7},
            {"name": "Central Park", "category": "park", "duration_hours": 2, "best_time": "afternoon", "rating": 4.6},
            {"name": "Metropolitan Museum of Art", "category": "museum", "duration_hours": 3, "best_time": "morning", "rating": 4.7},
            {"name": "Times Square", "category": "experience", "duration_hours": 1, "best_time": "evening", "rating": 4.3},
            {"name": "Brooklyn Bridge", "category": "landmark", "duration_hours": 1.5, "best_time": "sunset", "rating": 4.5},
        ],
        "default": [
            {"name": "Local Museum", "category": "museum", "duration_hours": 2, "best_time": "morning", "rating": 4.5},
            {"name": "City Park", "category": "park", "duration_hours": 2, "best_time": "afternoon", "rating": 4.4},
            {"name": "Historic Landmark", "category": "landmark", "duration_hours": 1.5, "best_time": "morning", "rating": 4.5},
            {"name": "Local Restaurant", "category": "dining", "duration_hours": 2, "best_time": "evening", "rating": 4.6},
        ]
    }
    
    dest_lower = destination.lower().strip()
    attractions = attractions_db.get(dest_lower, attractions_db["default"])
    return attractions


def _weather_code_to_description(code: int) -> str:
    """Convert WMO weather code to human-readable description."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail"
    }
    return codes.get(code, "Unknown")
