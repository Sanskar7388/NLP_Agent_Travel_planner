"""
Main orchestrator for the Pathfinder Agent.
Runs the 4-step chain with clear state management.
"""
import sys
from pathlib import Path
from agent.state import TravelState
from agent.steps import (
    step1_extract_preferences,
    step2_fetch_weather_and_attractions,
    step3_match_activities,
    step4_generate_itinerary
)
from agent.output_formatter import save_output, print_summary


def run_agent(user_input: str) -> TravelState:
    """
    Run the complete travel itinerary agent chain.
    
    Args:
        user_input: User's travel request
    
    Returns:
        Final state after processing
    """
    
    print("\n" + "="*60)
    print("PATHFINDER - Travel Route Agent")
    print("="*60)
    
    # Initialize state
    state = TravelState(user_input=user_input)
    print(f"\n[*] User Input: {user_input[:100]}...")
    print("\nRunning 4-step agent chain...\n")
    
    # Step 1: Extract preferences
    print("Step 1: Extracting travel preferences...")
    state = step1_extract_preferences(state)
    print(f"  [*] Extracted preferences for: {state.preferences.get('destination', 'unknown')}")
    
    # Print ALL extracted preferences dynamically
    if state.preferences and "error" not in state.preferences:
        for key, value in state.preferences.items():
            if key != "destination" and value and value != "not specified":
                # Format the output nicely
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value)
                else:
                    value_str = str(value)
                # Pretty print the key
                pretty_key = key.replace("_", " ").title()
                print(f"    - {pretty_key}: {value_str}")
    print()
    
    # Step 2: Fetch weather and attractions (TOOL CALL)
    print("Step 2: Fetching weather forecast and attractions...")
    state = step2_fetch_weather_and_attractions(state)
    print(f"  [+] Weather forecast retrieved: {len(state.weather_data.get('forecast', []))} days")
    print(f"  [+] Attractions found: {len(state.attractions_data)} options\n")
    
    # Step 3: Match activities
    print("Step 3: Matching activities to preferences and weather...")
    state = step3_match_activities(state)
    print(f"  [+] Activities matched and prioritized: {len(state.matched_activities)} selected\n")
    
    # Step 4: Generate itinerary
    print("Step 4: Generating day-by-day itinerary...")
    state = step4_generate_itinerary(state)
    if state.itinerary:
        num_days = len(state.itinerary.get('daily_itineraries', []))
        print(f"  [+] Itinerary created: {num_days} days\n")
    else:
        print(f"  Failed to generate itinerary\n")
    
    # Print summary
    print_summary(state)
    
    return state


def main():
    """Main entry point for Pathfinder agent."""
    
    # Example user inputs (can be replaced with interactive input)
    examples = {
        "1": "I'm planning a 5-day trip to Paris in June. I have a medium budget and love museums and historical sites. I prefer morning activities and relaxing evenings. I'm traveling with my family.",
        "2": "3-day Tokyo visit, low budget, interested in food and shopping, going alone, want to experience local culture",
        "3": "New York, 4 days, high budget, want adventure activities and nightlife, traveling with a group of friends"
    }
    
    print("Pathfinder - Intelligent Travel Route Planning Agent")
    print("-" * 60)
    print("\nExample inputs available:")
    for key, example in examples.items():
        print(f"{key}: {example[:60]}...")
    
    # Get user input
    user_choice = input("\nEnter example number (1-3) or paste your own travel request: ").strip()
    
    if user_choice in examples:
        user_input = examples[user_choice]
    elif user_choice:
        user_input = user_choice
    else:
        user_input = examples["1"]  # Default
    
    # Run agent
    final_state = run_agent(user_input)
    
    # Save output
    print("\n Saving output files...")
    output_files = save_output(final_state, Path("output"))
    print(f"  [+] JSON saved: {output_files['json']}")
    print(f"  [+] Markdown saved: {output_files['markdown']}")
    
    # Display itinerary preview
    if final_state.itinerary:
        print("\n" + "="*60)
        print("ITINERARY PREVIEW")
        print("="*60)
        from agent.output_formatter import format_itinerary_markdown
        preview = format_itinerary_markdown(final_state)
        # Print first 2000 chars
        print(preview[:2000])
        if len(preview) > 2000:
            print("\n... (see full itinerary in output file)")
    
    print("\n[+] Agent complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAgent interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
