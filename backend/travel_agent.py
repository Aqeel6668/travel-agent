"""
Travel Planning Agent - FREE version (local model via Ollama, no API key).
1. Send the conversation + tool descriptions to the model.
2. If the model asks for a tool, run it and send the result back.
3. Repeat until the model answers in plain text.
"""

import json

import ollama
import requests

MODEL = "llama3.2"  # small local model that supports tool calling
MAX_STEPS = 6       # safety limit so a confused model can't loop forever

SYSTEM_PROMPT = """You are a friendly travel planning assistant.
- Call get_weather once for the destination before planning.
- Call find_attractions once and use those places in the plan.
- Call calculate_trip_cost once to estimate the total cost.
- The total in your final answer MUST be exactly the total_cost returned by the tool. Never use the user's budget as the total.
- If total_cost is higher than the user's budget, say it is over budget and suggest cheaper options.
- If destination, number of days, or budget is missing, ask the user.
- Then give a short day-by-day plan."""


# ---------- TOOLS (plain Python functions) ----------

def get_weather(city: str, days: int = 3) -> str:
    """Free forecast from Open-Meteo (no API key needed)."""
    days = int(days)  # small models sometimes send numbers as text
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    ).json()
    if not geo.get("results"):
        return f"Could not find city: {city}"
    place = geo["results"][0]

    daily = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": min(days, 16),
            "timezone": "auto",
        },
        timeout=10,
    ).json()["daily"]

    return "\n".join(
        f"{d}: {daily['temperature_2m_min'][i]}-{daily['temperature_2m_max'][i]}°C, "
        f"rain chance {daily['precipitation_probability_max'][i]}%"
        for i, d in enumerate(daily["time"])
    )


def calculate_trip_cost(days: int, hotel_per_night: float, food_per_day: float,
                        activities_per_day: float, transport_total: float) -> str:
    """Budget math so the model doesn't do arithmetic itself."""
    total = int(days) * (float(hotel_per_night) + float(food_per_day)
                         + float(activities_per_day)) + float(transport_total)
    return json.dumps({"days": int(days), "total_cost": round(total, 2)})


def find_attractions(city: str) -> str:
    """Real nearby attractions from Wikipedia (free, no key)."""
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    ).json()
    if not geo.get("results"):
        return f"Could not find city: {city}"
    place = geo["results"][0]

    data = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{place['latitude']}|{place['longitude']}",
            "gsradius": 5000,
            "gslimit": 10,
            "format": "json",
        },
        headers={"User-Agent": "travel-agent-student-project/1.0"},
        timeout=10,
    ).json()
    names = [p["title"] for p in data["query"]["geosearch"]]
    return "Nearby places: " + ", ".join(names)


TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate_trip_cost": calculate_trip_cost,
    "find_attractions": find_attractions,
}

# Descriptions the model reads to decide WHEN and HOW to call each tool
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the daily weather forecast for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Rome"},
                    "days": {"type": "integer", "description": "Number of forecast days"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_trip_cost",
            "description": "Calculate total trip cost from estimated daily costs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "hotel_per_night": {"type": "number"},
                    "food_per_day": {"type": "number"},
                    "activities_per_day": {"type": "number"},
                    "transport_total": {"type": "number", "description": "Flights/trains, whole trip"},
                },
                "required": ["days", "hotel_per_night", "food_per_day",
                             "activities_per_day", "transport_total"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_attractions",
            "description": "Find real attractions and landmarks near a city center.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Rome"},
                },
                "required": ["city"],
            },
        },
    },
]


def run_tool(name: str, args: dict) -> str:
    """Run a tool safely. Errors go back to the model so it can recover."""
    try:
        return str(TOOL_FUNCTIONS[name](**args))
    except Exception as e:
        return f"Tool error: {e}"


# ---------- THE AGENT LOOP ----------

def run_agent(messages: list) -> tuple[str, list[dict]]:
    """Returns (final_answer, list_of_tools_used) so the UI can show both."""
    tools_used: list[dict] = []
    for _ in range(MAX_STEPS):
        response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
        msg = response.message
        messages.append(msg)

        # No tool requested -> model is done, return its text
        if not msg.tool_calls:
            return msg.content or "", tools_used

        # Otherwise run every requested tool and feed results back
        for call in msg.tool_calls:
            name, args = call.function.name, dict(call.function.arguments)
            print(f"  [tool] {name}({args})")
            tools_used.append({"name": name, "args": args})
            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": run_tool(name, args),
            })
    return "Sorry, I got stuck. Please try rephrasing your request.", tools_used


def main():
    """Command-line mode (still works without the web UI)."""
    print("Travel Agent (free, local) ready. Type 'quit' to exit.\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]  # history = memory
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        reply, _ = run_agent(messages)
        print("\nAgent:", reply, "\n")


if __name__ == "__main__":
    main()
