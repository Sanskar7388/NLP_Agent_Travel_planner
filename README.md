# Pathfinder - Intelligent Travel Route Planning Agent

A multi-step LLM agent that generates personalized travel routes by reasoning across four sequential steps, integrating real weather data and flexible preference matching.

## Overview

This agent demonstrates the power of multi-step LLM reasoning. Rather than asking "generate a travel itinerary" in a single prompt (which would hallucinate data), the agent:

1. **Extracts** structured preferences from the user's request
2. **Fetches** real weather forecasts and attraction data
3. **Matches** activities based on weather conditions and preferences
4. **Synthesizes** a practical day-by-day itinerary

Each step feeds its structured output directly into the next, creating explicit data dependencies that prevent hallucination and ensure the itinerary reflects real-world constraints.

## Chain Architecture

### Step 1: Extract Preferences (LLM)
**Input:** User's free-form travel request  
**Output:** Structured preferences object

```json
{
  "destination": "Paris",
  "start_date": "2024-06-15",
  "end_date": "2024-06-20",
  "num_days": 5,
  "budget_category": "medium",
  "interests": ["culture", "museums", "food"],
  "constraints": ["prefer morning activities"],
  "traveling_with": "family with 2 kids"
}
```

The prompt is constrained to output valid JSON with specific keys. This structure is essential for Step 2.

---

### Step 2: Fetch Weather & Attractions (TOOL CALL)
**Input:** Destination from Step 1  
**Output:** Real-world data

- **Weather API:** Open-Meteo API returns 5-day forecast with temperature, precipitation, conditions
- **Attractions API:** Database of popular attractions matching destination

**Why a separate step?** LLMs cannot access real-time weather. The tool retrieves actual data, preventing hallucination. This data enters the chain as structured context for Step 3.

```json
{
  "weather_forecast": [
    {
      "date": "2024-06-15",
      "temp_max": 72,
      "temp_min": 58,
      "precipitation_mm": 0,
      "weather_description": "Clear sky"
    }
  ],
  "attractions": [
    {
      "name": "Eiffel Tower",
      "category": "landmark",
      "duration_hours": 2,
      "best_time": "morning",
      "rating": 4.8
    }
  ]
}
```

---

### Step 3: Match Activities (LLM)
**Input:**
- User preferences from Step 1
- Weather data from Step 2
- Available attractions from Step 2

**Output:** Prioritized, weather-aware activity list

```json
[
  {
    "name": "Eiffel Tower",
    "priority": 1,
    "suggested_time": "morning",
    "weather_suitability": "excellent - clear skies ideal for outdoor visits",
    "reason": "Top-rated landmark matching cultural interests"
  }
]
```

**Why a separate step?** The LLM must reason about weather constraints (outdoor activities in rain vs. indoor museums on rainy days) and match activities to user interests. This filtering is context-dependent and must happen before itinerary generation.

---

### Step 4: Generate Itinerary (LLM)
**Input:**
- Matched activities from Step 3
- Preferences from Step 1
- Weather context from Step 2

**Output:** Day-by-day itinerary with times, meals, transportation

```json
{
  "destination": "Paris",
  "daily_itineraries": [
    {
      "day": 1,
      "date": "2024-06-15",
      "schedule": [
        {
          "time": "09:00 AM",
          "activity": "Eiffel Tower visit",
          "duration": "2 hours",
          "notes": "Book tickets online. Visit observation deck for city views."
        },
        {
          "time": "12:00 PM",
          "activity": "Lunch at local bistro",
          "duration": "1 hour",
          "notes": "Try traditional French cuisine"
        }
      ],
      "daily_budget_estimate": "$150",
      "tips": "Start early to avoid crowds. Bring water and sunscreen."
    }
  ],
  "total_estimated_cost": "$750",
  "packing_suggestions": ["light layers", "comfortable walking shoes", "sunscreen"],
  "final_notes": "This itinerary balances cultural immersion with relaxation..."
}
```

**Why a separate step?** Synthesizing a practical, timed schedule requires reasoning about:
- Activity duration and sequencing
- Travel time between locations
- Meal times and rest periods
- Budget allocation across days

This requires final LLM reasoning across all previous outputs.

---

## Why This Chain Cannot Be Collapsed

Each step is essential. Removing any step breaks the chain:

- **Without Step 1:** Can't extract destination → Step 2 fails
- **Without Step 2:** Can't avoid hallucinating weather → Step 3 makes poor decisions (suggests outdoor hiking in forecast rain)
- **Without Step 3:** Can't reason about weather constraints → itinerary may be impractical
- **Without Step 4:** Can't synthesize practical timings and sequencing

## Installation

### Prerequisites
- Python 3.8+
- Groq API key (from console.groq.com)

### Setup

1. **Clone/download the repo**
   ```bash
   cd NLP_Project
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API key**
   
   The `.env` file already contains your Grok API key. Verify it's set:
   ```
   apikey="your_grok_api_key_here"
   ```

## Usage

### Run the Agent

```bash
python agent/main.py
```

**Interactive mode:**
- Choose from example inputs (1-3) or paste your own travel request
- Agent processes through 4 steps
- Output saved to `output/` folder (JSON + Markdown)

### Run Programmatically

```python
from agent.main import run_agent
from agent.output_formatter import save_output

# Run agent
final_state = run_agent("5-day trip to Tokyo, medium budget, interested in food and culture")

# Access results
print(final_state.itinerary)
print(final_state.preferences)

# Save output
save_output(final_state)
```

## Output Files

For each run, two files are generated in `output/`:

1. **`itinerary_[destination]_[timestamp].json`**
   - Complete structured output
   - Contains all step outputs for inspection
   - Useful for programmatic processing

2. **`itinerary_[destination]_[timestamp].md`**
   - Human-readable Markdown report
   - Day-by-day schedule with times
   - Budget estimates and packing suggestions
   - Print-friendly format

## Code Structure

```
NLP_Project/
├── agent/
│   ├── __init__.py
│   ├── config.py              # API configuration
│   ├── state.py               # Shared state object
│   ├── steps.py               # 4 LLM steps + logic
│   ├── output_formatter.py    # Output generation
│   └── main.py                # Orchestrator
├── tools/
│   ├── __init__.py
│   └── weather.py             # Weather API integration
├── output/                    # Generated itineraries
├── .env                       # API keys
├── requirements.txt
└── README.md
```

### Key Design Decisions

1. **Explicit Step Functions:** Each step is a separate function with clear inputs/outputs. This makes the dependency graph explicit and testable.

2. **State Object:** `TravelState` accumulates outputs across steps. Each step reads what it needs and writes its results. Easy to inspect and debug.

3. **Tool Integration:** Step 2 is the only tool call. It fetches real data that feeds into LLM reasoning in Step 3 and 4.

4. **Structured Outputs:** Every LLM step returns valid JSON with a specific schema. This enables reliable downstream processing.

5. **No Framework Abstractions:** Built from scratch using raw `openai` library. The chain logic is explicit and transparent.

## Example Run

```
User Input: "4-day trip to Barcelona, high budget, love food and architecture, traveling with my partner"

Step 1: Extract preferences
  ✓ Extracted preferences for: Barcelona
    - Interests: food, architecture, romance
    - Budget: high
    - Duration: 4 days

Step 2: Fetch weather and attractions
  ✓ Weather forecast retrieved: 4 days
  ✓ Attractions found: 5 options

Step 3: Match activities
  ✓ Activities matched: 8 selected

Step 4: Generate itinerary
  ✓ Itinerary created: 4 days

💾 Saving output files...
  ✓ JSON saved: output/itinerary_barcelona_20240515_143022.json
  ✓ Markdown saved: output/itinerary_barcelona_20240515_143022.md
```

## Handling Edge Cases

### Unexpected Inputs
- **Destination not in database:** Agent falls back to default attractions
- **Invalid date format:** Step 1 LLM parses flexibly; Step 4 handles missing dates gracefully
- **No interests specified:** Agent suggests diverse mix of activities

### Tool Failures
- **Weather API down:** Step 2 caches response with error flag; Step 3 proceeds with generic weather assumptions
- **Empty attractions list:** Step 3 filters available activities; Step 4 generates practical itinerary with available options

### LLM Parsing Failures
- Each step includes try/catch JSON parsing with fallback
- Errors logged to `state.errors`
- Processing continues (graceful degradation)

## Limitations & Future Work

1. **Geocoding:** Currently uses hardcoded coordinates for ~8 cities. A real implementation would use a geocoding API.

2. **Attractions Data:** Sample attractions are curated. A production system would query a real database (Google Places, TripAdvisor API, etc.).

3. **Currency & Language:** All prices in USD, all text in English. Could be extended with localization.

4. **Group Size Constraints:** Budget and activity durations not yet adjusted for group size beyond description.

5. **Flight/Transport:** Itinerary assumes user is already at destination. Could add flight/train recommendations with Step 2.

## Testing & Validation

Try these inputs to test the agent:

1. **Simple request:** "5 days in Paris"
   - Tests default behavior

2. **Complex constraints:** "3 days Tokyo, low budget, vegetarian, physically limited mobility"
   - Tests constraint handling and Step 3 filtering

3. **Unusual destination:** "1 week in Reykjavik"
   - Tests edge cases and graceful degradation

4. **Vague input:** "somewhere warm and relaxing"
   - Tests Step 1 preference extraction with missing data

## Questions During Evaluation

**Q: Show me what Step 3 received as input and what it returned.**  
A: Run the agent and open the `.json` output file. `weather_data` and `attractions_data` show Step 2's output. `matched_activities` shows Step 3's result.

**Q: What happens if Step 2 fails?**  
A: Error logged to `state.errors`. Step 3 proceeds with empty weather/attractions. Step 4 generates generic itinerary. System degrades gracefully.

**Q: Why is Step 3 separate from Step 1?**  
A: Step 1 parses user input; Step 3 reasons about constraints. They have different purposes. Step 3 needs real weather data (Step 2) to function correctly.

**Q: Where does this break?**  
A: Unknown destinations with no coordinates. Unusual interest combinations. Very large groups with budget constraints. These would be addressed with better data APIs and more sophisticated constraint solving.

## References

- [Groq API Documentation](https://console.groq.com/docs)
- [Open-Meteo Weather API](https://open-meteo.com/)
- [OpenAI Python Client](https://github.com/openai/openai-python)
