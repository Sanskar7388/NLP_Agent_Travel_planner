"""
LLM steps for the travel itinerary agent.
Each step is a separate function with clear inputs and outputs.
"""
import json
from typing import Dict, Any
from openai import OpenAI
from agent.config import GROQ_API_KEY, GROQ_MODEL, GROQ_API_URL
from agent.state import TravelState


# Initialize Groq client
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url=GROQ_API_URL
)


def _extract_json(response_text: str) -> str:
    """
    Extract JSON from response that may be wrapped in markdown code blocks.
    Groq often returns ```json ... ``` which breaks json.loads().
    """
    response_text = response_text.strip()
    
    # Remove markdown code block wrapper if present
    if response_text.startswith("```"):
        # Find the closing ```
        if "```" in response_text[3:]:
            response_text = response_text[3:]  # Remove opening ```
            response_text = response_text.rsplit("```", 1)[0]  # Remove closing ```
        response_text = response_text.strip()
        # Remove language specifier (e.g., "json\n")
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()
    
    return response_text


def step1_extract_preferences(state: TravelState) -> TravelState:
    """
    Step 1: Extract ALL user preferences from raw input - no fixed categories.
    
    Input: state.user_input (user's travel request)
    Output: state.preferences (ALL mentioned preferences, dynamically extracted)
    
    This step parses the user's request to extract ANYTHING they mention as a preference:
    - Standard fields: destination, dates, budget
    - Dynamic fields: weather constraints, activity restrictions, dietary needs, accessibility, etc.
    - Free-form: any other preference they mention
    """
    
    system_prompt = """You are a flexible travel preferences analyzer. Extract ALL preferences mentioned by the user.

Your task is to parse the user's input and extract EVERY preference they mention, not just predefined categories.

STANDARD FIELDS (extract if mentioned):
- destination (place name)
- start_date (YYYY-MM-DD format if mentioned, or "not specified")
- end_date (YYYY-MM-DD format if mentioned, or "not specified")
- num_days (number of days, inferred if dates given)
- budget (what they say about budget: e.g., "low budget", "expensive trip", "$1000/day")
- traveling_with (solo, couple, family, friends, etc.)

DYNAMIC PREFERENCES (extract everything they mention):
- weather_tolerance (avoid rain, avoid heat, avoid cold, any weather ok, etc.)
- interests (culture, food, adventure, relaxation, shopping, nightlife, nature, etc.)
- activities (specific things they want to do)
- constraints (mobility issues, dietary restrictions, allergies, time constraints)
- comfort_level (luxury, budget-friendly, mid-range, backpacker)
- pace (relaxed, moderate, fast-paced, mix)
- transportation_preference (public transport, driving, walking, any)
- accommodation (hotel, airbnb, hostel, resort, luxury, budget)
- dining_style (street food, fine dining, local restaurants, specific cuisine)
- risk_tolerance (adventure seeker, prefer safe, family-friendly)
- any other preference they mention

Return a valid JSON object with ALL preferences mentioned. If field not mentioned, use "not specified".
Focus on capturing what the user ACTUALLY said, not assumptions."""

    user_prompt = f"""Extract ALL travel preferences mentioned in this request. Capture everything, not just standard fields:

{state.user_input}

Return ONLY a valid JSON object with all preferences. No markdown, no extra text. Include EVERY preference they mention."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        if not response_text:
            state.add_error(f"Step 1: LLM returned empty response")
            state.preferences = {"error": "Empty response"}
            return state
        
        # Remove markdown wrapper if present
        response_text = _extract_json(response_text)
        
        # Parse JSON response
        preferences = json.loads(response_text)
        state.preferences = preferences
        
    except json.JSONDecodeError as e:
        state.add_error(f"Step 1: Failed to parse LLM response as JSON: {str(e)}")
        state.preferences = {"error": "Could not parse preferences"}
    except Exception as e:
        state.add_error(f"Step 1: {str(e)}")
        state.preferences = {"error": str(e)}
    
    return state


def step2_fetch_weather_and_attractions(state: TravelState) -> TravelState:
    """
    Step 2: Fetch real weather data and attraction information for the destination.
    
    Input: state.preferences (destination, dates, interests)
    Output: state.weather_data and state.attractions_data
    
    This is the TOOL CALL step. It retrieves real data that LLMs cannot hallucinate:
    - Weather forecast for the destination
    - Popular attractions matching the user's interests
    
    This data then enters the LLM chain to inform activity selection.
    """
    from tools.weather import fetch_weather_forecast, get_sample_attractions
    
    try:
        destination = state.preferences.get("destination", "").strip()
        
        if not destination:
            state.add_error("Step 2: No destination specified")
            return state
        
        # Hardcode coordinates for common destinations (in production, use geocoding API)
        destination_coords = {
            "paris": (48.8566, 2.3522),
            "tokyo": (35.6762, 139.6503),
            "new york": (40.7128, -74.0060),
            "london": (51.5074, -0.1278),
            "sydney": (-33.8688, 151.2093),
            "dubai": (25.2048, 55.2708),
            "barcelona": (41.3851, 2.1734),
        }
        
        dest_lower = destination.lower().strip()
        coords = destination_coords.get(dest_lower, (0, 0))  # Default to (0, 0) if not found
        
        # Fetch weather
        num_days = state.preferences.get("num_days", 5)
        state.weather_data = fetch_weather_forecast(
            latitude=coords[0],
            longitude=coords[1],
            destination=destination,
            num_days=num_days
        )
        
        # Fetch attractions
        state.attractions_data = get_sample_attractions(destination)
        
    except Exception as e:
        state.add_error(f"Step 2: {str(e)}")
    
    return state


def step3_match_activities(state: TravelState) -> TravelState:
    """
    Step 3: Match activities to weather conditions and user constraints.
    
    Input: 
    - state.preferences (interests, constraints)
    - state.weather_data (weather forecast)
    - state.attractions_data (available attractions)
    
    Output: state.matched_activities (filtered and prioritized activities)
    
    This step uses the LLM to reason about which activities are suitable given:
    - Current weather forecast
    - User interests and constraints
    - Activity duration and timing
    """
    
    system_prompt = """You are a travel activity matcher. Given user preferences, weather forecast, and available attractions, 
select and order activities that make sense.

Your task:
1. Filter attractions based on user interests
2. CRITICAL: Remove activities that conflict with user's weather tolerance
   - If user said "avoid rain", don't schedule outdoor activities on rainy days
   - If user said "avoid heat", don't schedule exposed outdoor activities on hot days
   - If user said "avoid cold", don't schedule outdoor activities on cold days
3. Suggest timing (morning/afternoon/evening) based on weather and activity requirements
4. Consider activity duration to fit in available time
5. Return activities in priority order (best first)

Weather constraints that override everything:
- User's weather_tolerance is a HARD CONSTRAINT, not a suggestion
- If user "avoid rain", outdoor activities on rainy days get priority 0 (excluded)
- If user "avoid heat", exposed activities on 80+ F days get deprioritized
- If user "avoid cold", outdoor activities on cold days get deprioritized

Return a JSON array with selected activities. Each has:
- name, category, priority (1-5, 1=most recommended), reason_for_selection, suggested_time, weather_suitability"""

    attractions_summary = json.dumps(state.attractions_data, indent=2)
    weather_summary = json.dumps(state.weather_data.get("forecast", []), indent=2)
    preferences_summary = json.dumps(state.preferences, indent=2)

    user_prompt = f"""Match activities based on:

PREFERENCES:
{preferences_summary}

WEATHER FORECAST:
{weather_summary}

AVAILABLE ATTRACTIONS:
{attractions_summary}

CRITICAL: User's weather_tolerance is a HARD CONSTRAINT. If user says "avoid rain", exclude outdoor activities on rainy days.
Select the best activities considering weather, interests, and ESPECIALLY weather constraints.
Return ONLY a valid JSON array. No markdown, no extra text."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=3000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        if not response_text:
            state.add_error(f"Step 3: LLM returned empty response")
            state.matched_activities = []
            return state
        
        # Remove markdown wrapper if present
        response_text = _extract_json(response_text)
        
        matched = json.loads(response_text)
        state.matched_activities = matched if isinstance(matched, list) else [matched]
        
    except json.JSONDecodeError as e:
        state.add_error(f"Step 3: Failed to parse activity matching response: {str(e)}")
    except Exception as e:
        state.add_error(f"Step 3: {str(e)}")
    
    return state


def step4_generate_itinerary(state: TravelState) -> TravelState:
    """
    Step 4: Generate a day-by-day itinerary with timings.
    
    Input: 
    - state.matched_activities (selected and prioritized activities)
    - state.preferences (travel dates, budget, group info)
    - state.weather_data (for context on daily conditions)
    
    Output: state.itinerary (structured day-by-day schedule)
    
    This final LLM step synthesizes everything into a practical, executable itinerary.
    It must:
    - Distribute activities across days
    - Account for travel time between locations
    - Include meals and rest time
    - Provide realistic timings
    - Stay within budget and constraints
    """
    
    system_prompt = """You are an itinerary planner. Create a practical, day-by-day travel schedule.

CRITICAL RULE: Respect the user's weather tolerance constraint.
- If user said "avoid rain", don't schedule outdoor activities on rainy days
- If user said "avoid heat", don't schedule exposed activities on hot days
- If user said "avoid cold", don't schedule outdoor activities on cold days

Your task:
1. Distribute selected activities across available days (respecting weather constraints)
2. Include realistic times for each activity (e.g., "10:00 AM - 12:30 PM")
3. Account for travel time between locations
4. Include meal times and rest periods
5. Suggest budget-appropriate dining and accommodation notes
6. Provide specific, actionable recommendations

For each day, create a schedule like:
- 08:00 AM: Breakfast at [place]
- 09:30 AM - 12:00 PM: Activity [name] - [reason]
- 12:00 PM - 01:00 PM: Lunch
- [etc]

Return a JSON object with this structure:
{
  "destination": "string",
  "trip_start": "YYYY-MM-DD",
  "trip_end": "YYYY-MM-DD",
  "daily_itineraries": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "weather": "description",
      "schedule": [
        {"time": "HH:MM AM/PM", "activity": "name", "duration": "X hours", "notes": "details"}
      ],
      "daily_budget_estimate": "$X",
      "tips": "specific advice"
    }
  ],
  "total_estimated_cost": "$X",
  "packing_suggestions": ["item1", "item2"],
  "final_notes": "overall summary and tips"
}"""

    activities_summary = json.dumps(state.matched_activities, indent=2)
    weather_summary = json.dumps(state.weather_data.get("forecast", []), indent=2)
    prefs = state.preferences

    user_prompt = f"""Create a day-by-day itinerary:

Destination: {prefs.get('destination', 'Unknown')}
Trip Duration: {prefs.get('num_days', 5)} days (from {prefs.get('start_date', 'not specified')} to {prefs.get('end_date', 'not specified')})
Budget: {prefs.get('budget_category', 'medium')}
Traveling With: {prefs.get('traveling_with', 'unknown')}
Weather Tolerance: {prefs.get('weather_tolerance', 'any weather ok')}

SELECTED ACTIVITIES:
{activities_summary}

WEATHER FORECAST:
{weather_summary}

CRITICAL: User's weather tolerance is "{prefs.get('weather_tolerance', 'any weather ok')}". 
If user avoids rain, do NOT schedule outdoor activities on rainy days.
If user avoids heat, do NOT schedule exposed activities on hot days.
If user avoids cold, do NOT schedule outdoor activities on cold days.

Create a realistic, actionable itinerary respecting weather constraints. Return ONLY valid JSON. No markdown, no extra text."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=8000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Debug: Print response if it's empty or looks wrong
        if not response_text:
            state.add_error(f"Step 4: LLM returned empty response")
            return state
        
        # Remove markdown wrapper if present
        response_text = _extract_json(response_text)
        
        itinerary = json.loads(response_text)
        state.itinerary = itinerary
        
    except json.JSONDecodeError as e:
        state.add_error(f"Step 4: Failed to parse itinerary response: {str(e)}")
        # Store raw response for debugging
        state.itinerary = {"error": f"JSON parse error: {str(e)}", "raw_response": response_text[:500] if response_text else "empty"}
    except Exception as e:
        state.add_error(f"Step 4: {str(e)}")
    
    return state
