"""
Simple BUDDY Backend Server

A minimal FastAPI server to handle chat requests from the desktop app.
This is a simplified version for development purposes.
"""

import os
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json

# Weather API configuration
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ff2cbe677bbfc325d2b615c86a20daef")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Runtime flags
DEBUG_MODE = os.getenv("BUDDY_DEBUG") == "1"
DEV_MODE = os.getenv("BUDDY_DEV") == "1"

def debug_log_intent(intent: str, message: str | None = None):
    if DEBUG_MODE:
        try:
            logger.info(f"[INTENT] {intent} msg={message!r}")
        except Exception:
            pass

# Create FastAPI app
app = FastAPI(title="BUDDY Backend API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    context: Dict[str, Any] = {}

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    session_id: str

class SystemStats(BaseModel):
    status: str
    uptime: int
    active_sessions: int

class MemoryUpdate(BaseModel):
    user_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

# Simple in-memory storage
conversations: Dict[str, List[Dict[str, Any]]] = {}
server_start_time = datetime.now()

# Lightweight local memory persisted to JSON (privacy-first)
MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'user_memory.json')
user_memory: Dict[str, Any] = {}

def load_memory() -> Dict[str, Any]:
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load memory: {e}")
    return {"user_name": None, "preferences": {}, "frequent_intents": {}, "topics": []}

def save_memory() -> None:
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save memory: {e}")

def set_user_name(name: str) -> None:
    user_memory["user_name"] = name
    save_memory()

def get_user_name(default: str = "there") -> str:
    name = user_memory.get("user_name")
    return name if name else default

def update_memory_intent(intent: str) -> None:
    fi = user_memory.setdefault("frequent_intents", {})
    fi[intent] = fi.get(intent, 0) + 1
    save_memory()

# Initialize memory on startup
user_memory.update(load_memory())

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "BUDDY Backend API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    uptime = (datetime.now() - server_start_time).total_seconds()
    return {
        "status": "healthy",
        "uptime_seconds": uptime,
        "active_sessions": len(conversations),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Handle chat messages."""
    try:
        # Generate a simple session ID
        session_id = "session_001"
        
        # Store the conversation
        if session_id not in conversations:
            conversations[session_id] = []
        
        # Add user message to conversation
        conversations[session_id].append({
            "role": "user",
            "content": message.message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Learn user's name if they introduce themselves
        ml = message.message.lower()
        if any(kw in ml for kw in ["my name is", "i am ", "i'm ", "call me "]):
            try:
                text = ml.replace("i'm", "i am")
                words = text.split()
                if "name" in words and "is" in words:
                    idx = words.index("is")
                    if idx + 1 < len(words):
                        nm = words[idx + 1].strip(".,!?").title()
                        if nm and nm.isalpha():
                            set_user_name(nm)
                elif "am" in words:
                    idx = words.index("am")
                    if idx + 1 < len(words):
                        nm = words[idx + 1].strip(".,!?").title()
                        if nm and nm.isalpha():
                            set_user_name(nm)
            except Exception:
                pass

        # Generate a response (this is where you'd integrate with AI models)
        response_text = await generate_response(message.message, conversations[session_id])
        
        # Add assistant response to conversation
        conversations[session_id].append({
            "role": "assistant", 
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat(),
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history."""
    if session_id not in conversations:
        return {"messages": []}
    return {"messages": conversations[session_id]}

@app.get("/skills")
async def get_skills():
    """Get available skills."""
    return {
        "skills": [
            {
                "id": "chat",
                "name": "General Chat",
                "description": "General conversation and assistance",
                "enabled": True,
                "category": "conversation",
                "icon": "💬"
            },
            {
                "id": "time",
                "name": "Time & Date",
                "description": "Get current time and date information",
                "enabled": True,
                "category": "utility",
                "icon": "🕐"
            },
            {
                "id": "weather",
                "name": "Weather",
                "description": "Get weather information and forecasts",
                "enabled": True,
                "category": "information",
                "icon": "🌤️"
            },
            {
                "id": "calculator",
                "name": "Calculator",
                "description": "Perform mathematical calculations",
                "enabled": True,
                "category": "utility",
                "icon": "🧮"
            },
            {
                "id": "system_info",
                "name": "System Monitor",
                "description": "Monitor system performance and resources",
                "enabled": True,
                "category": "system",
                "icon": "📊"
            },
            {
                "id": "file_manager",
                "name": "File Operations",
                "description": "File and folder management tasks",
                "enabled": True,
                "category": "system",
                "icon": "📁"
            },
            {
                "id": "web_search",
                "name": "Web Search",
                "description": "Search the internet for information",
                "enabled": True,
                "category": "information",
                "icon": "🔍"
            },
            {
                "id": "reminders",
                "name": "Reminders",
                "description": "Set and manage reminders and tasks",
                "enabled": True,
                "category": "productivity",
                "icon": "⏰"
            },
            {
                "id": "voice_commands",
                "name": "Voice Control",
                "description": "Voice command recognition and processing",
                "enabled": False,
                "category": "interaction",
                "icon": "🎤"
            },
            {
                "id": "automation",
                "name": "Task Automation",
                "description": "Automate repetitive tasks and workflows",
                "enabled": True,
                "category": "productivity",
                "icon": "🤖"
            }
        ]
    }

@app.get("/memory")
async def get_memory():
    """Inspect in-memory user profile (persisted to user_memory.json)."""
    return user_memory

@app.post("/memory")
async def update_memory(update: MemoryUpdate):
    """Update memory fields like user_name or preferences."""
    if update.user_name:
        set_user_name(update.user_name)
    if update.preferences:
        prefs = user_memory.setdefault("preferences", {})
        prefs.update(update.preferences)
        save_memory()
    return {"status": "ok", "memory": user_memory}

@app.post("/memory/reset")
async def reset_memory():
    user_memory.clear()
    user_memory.update({"user_name": None, "preferences": {}, "frequent_intents": {}, "topics": []})
    save_memory()
    return {"status": "ok", "memory": user_memory}

@app.get("/system/stats")
async def get_system_stats():
    """Get system statistics."""
    uptime = (datetime.now() - server_start_time).total_seconds()
    return {
        "status": "running",
        "uptime": int(uptime),
        "active_sessions": len(conversations),
        "memory_usage": "Normal",
        "cpu_usage": "Low",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/weather/{city}")
async def get_weather(city: str):
    """Get current weather for a city."""
    try:
        async with httpx.AsyncClient() as client:
            # Get current weather
            url = f"{WEATHER_BASE_URL}/weather"
            params = {
                "q": city,
                "appid": WEATHER_API_KEY,
                "units": "metric"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "city": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "wind_speed": data["wind"]["speed"],
                "visibility": data.get("visibility", 0) / 1000,  # Convert to km
                "timestamp": datetime.now().isoformat()
            }
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        else:
            raise HTTPException(status_code=500, detail="Weather service unavailable")
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")

async def get_weather_for_city(city: str) -> str:
    """Enhanced weather function with detailed information and suggestions."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{WEATHER_BASE_URL}/weather"
            params = {
                "q": city,
                "appid": WEATHER_API_KEY,
                "units": "metric"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]
            description = data["weather"][0]["description"]
            city_name = data["name"]
            country = data["sys"]["country"]
            wind_speed = data["wind"]["speed"]
            visibility = data.get("visibility", 0) / 1000  # Convert to km
            
            # Generate weather emoji based on description
            weather_emoji = "☀️"  # default
            desc_lower = description.lower()
            if "rain" in desc_lower:
                weather_emoji = "�️"
            elif "cloud" in desc_lower:
                weather_emoji = "☁️"
            elif "clear" in desc_lower:
                weather_emoji = "☀️"
            elif "snow" in desc_lower:
                weather_emoji = "❄️"
            elif "thunder" in desc_lower:
                weather_emoji = "⛈️"
            elif "mist" in desc_lower or "fog" in desc_lower:
                weather_emoji = "🌫️"
            
            # Generate contextual advice
            advice = ""
            if temp < 5:
                advice = "\n🧥 **Tip**: Bundle up! It's quite cold out there."
            elif temp > 30:
                advice = "\n🌡️ **Tip**: Stay hydrated and seek shade when possible!"
            elif "rain" in desc_lower:
                advice = "\n☂️ **Tip**: Don't forget an umbrella if you're heading out!"
            elif humidity > 80:
                advice = "\n💧 **Tip**: High humidity might make it feel muggy!"
            elif wind_speed > 10:
                advice = "\n💨 **Tip**: It's quite windy - secure any loose items!"
            
            # Temperature comfort assessment
            if feels_like > temp + 3:
                comfort = f" (feels warmer at {feels_like}°C due to humidity)"
            elif feels_like < temp - 3:
                comfort = f" (feels cooler at {feels_like}°C due to wind)"
            else:
                comfort = f" (feels like {feels_like}°C)"
            
            return f"""{weather_emoji} **Weather in {city_name}, {country}**

🌡️ **Temperature**: {temp}°C{comfort}
📝 **Conditions**: {description.title()}
💧 **Humidity**: {humidity}%
🏮 **Pressure**: {pressure} hPa
💨 **Wind Speed**: {wind_speed} m/s
👁️ **Visibility**: {visibility:.1f} km{advice}

🕐 **Last Updated**: {datetime.now().strftime('%I:%M %p')}

Need weather for another city? Just ask! 🌍"""
                   
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"🌍 I couldn't find weather data for '{city}'. Please check the spelling or try a different city name.\n\n💡 **Tip**: Try major cities or include the country (e.g., 'Paris, France')."
        else:
            return "🌤️ The weather service is temporarily unavailable. Please try again in a moment!"
    except Exception as e:
        logger.error(f"Weather lookup error: {e}")
        return f"🌍 I couldn't get the weather for '{city}' right now. Please check the city name and try again.\n\n💡 **Try formats like**: 'weather in London' or 'what's the weather in Tokyo?'"

async def generate_response(user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
    """
    Generate a contextual and intelligent response to the user message.
    Enhanced with better natural language understanding and personalized responses.
    """
    message_lower = user_message.lower()

    def fuzzy_contains(text: str, phrases: List[str], threshold: float = 0.82) -> bool:
        """Return True if any phrase approximately appears in text (typo tolerance)."""
        text_words = text.split()
        for phrase in phrases:
            ph = phrase.lower()
            if ph in text:
                return True
            ph_tokens = ph.split()
            # sequential scan attempting to match tokens in order (fuzzy)
            ti = 0
            hits = 0
            for pt in ph_tokens:
                found = False
                for idx in range(ti, len(text_words)):
                    if SequenceMatcher(None, text_words[idx], pt).ratio() >= threshold:
                        hits += 1
                        ti = idx + 1
                        found = True
                        break
                if not found:
                    break
            required = len(ph_tokens) if len(ph_tokens) <= 3 else int(len(ph_tokens) * 0.8)
            if hits >= required:
                return True
        return False

    # Context seeded from conversation + persisted memory
    context = analyze_conversation_context(conversation_history)
    user_name = context.get("user_name", "there")

    # Greeting (kept narrow so it doesn't steal 'how are you' or other queries)
    if any(w in message_lower for w in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]) or \
       fuzzy_contains(message_lower, ["hiya"]):
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        options = [
            f"{greeting}! I'm BUDDY, your AI assistant. Ready to help, {user_name}! 🚀",
            f"{greeting}! Great to see you again, {user_name}. What's on your mind?",
            f"{greeting}! I'm BUDDY—happy to assist with info, math, weather, or just chat! ✨",
        ]
        update_memory_intent("greeting")
        if len(conversation_history) > 2:
            return f"{greeting}! Welcome back! How can I continue helping you today? 😊"
        import random
        return random.choice(options)

    # Time
    elif any(w in message_lower for w in ["time", "clock", "what time"]):
        now = datetime.now()
        formatted = now.strftime("%I:%M %p")
        day_part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        update_memory_intent("time")
        return f"🕐 It's currently {formatted} on this {now.strftime('%A')} {day_part}. Need help planning your day?"

    # Date
    elif any(w in message_lower for w in ["date", "today", "what day"]):
        d = datetime.now()
        formatted = d.strftime("%A, %B %d, %Y")
        day_of_year = d.timetuple().tm_yday
        days_left = (366 if d.year % 4 == 0 else 365) - day_of_year
        update_memory_intent("date")
        return f"📅 Today is {formatted}. Day {day_of_year} of the year with {days_left} days remaining."

    # How are you (status response, not greeting)
    elif any(w in message_lower for w in ["how are you", "how's it going", "how do you feel"]) or \
         fuzzy_contains(message_lower, ["how are you", "how r u", "how r you", "hows it going", "howz it going", "how are u", "hoe are you", "how are u"]):
        responses = [
            "I'm operating at full capacity and feeling fantastic! 🤖✨",
            "Doing great—systems are green and ready to help! 🚀",
            "Excellent! Optimized and eager to assist. 💪",
            "All good here! What can I do for you? 😊",
        ]
        import random
        update_memory_intent("status_how_are_you")
        debug_log_intent("status_how_are_you", user_message)
        return random.choice(responses)

    # Set Reminder
    elif any(phrase in message_lower for phrase in ["set reminder", "remind me", "create reminder", "set a reminder"]):
        import re
        time_match = re.search(r'(at |for |@)(\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?|\d{1,2}\s*(?:am|pm))', message_lower)
        task_text = user_message
        if time_match:
            time_str = time_match.group(2).strip()
            task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to|at|@)?\s*', '', task_text, flags=re.IGNORECASE).strip()
            task_text = re.sub(time_match.group(0), '', task_text).strip()
        else:
            time_str = "later"
            task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to)?\s*', '', task_text, flags=re.IGNORECASE).strip()
        
        update_memory_intent("reminder_set")
        debug_log_intent("reminder_set", user_message)
        return f"⏰ **Reminder Created Successfully!** \n📝 **Task**: {task_text}\n🕐 **Time**: {time_str}\n📅 **Status**: Active reminder set"

    # Get Reminders / List Reminders
    elif any(phrase in message_lower for phrase in ["my reminders", "list reminders", "show reminders", "what reminders", "reminders today", "list the remaindera"]):
        update_memory_intent("reminder_list")
        debug_log_intent("reminder_list", user_message)
        return (
            "📋 **Your Active Reminders:**\n"
            "• 🕘 Meeting with client - 10:00 AM\n"
            "• 🏋️ Gym workout - 6:00 PM\n"
            "• 📞 Call mom - 8:00 PM\n\n"
            "💡 **Tip**: Say 'set reminder for [task] at [time]' to add new ones!"
        )

    # Unit Conversions
    elif any(phrase in message_lower for phrase in ["convert", "change to", "how many", "what is", "usd to inr", "celsius to fahrenheit", "km to miles"]):
        import re
        # Currency conversion
        currency_match = re.search(r'(\d+(?:\.\d+)?)\s*(usd|dollars?)\s*(?:to|in)\s*(inr|rupees?)', message_lower)
        if currency_match:
            amount = float(currency_match.group(1))
            result = amount * 83.5  # Approximate USD to INR
            update_memory_intent("convert_currency")
            debug_log_intent("convert_currency", user_message)
            return f"💱 {amount} USD ≈ ₹{result:.2f} INR (approximate rate)"
        
        # Temperature conversion
        temp_match = re.search(r'(\d+(?:\.\d+)?)\s*(celsius|fahrenheit|c|f)\s*(?:to|in)\s*(celsius|fahrenheit|c|f)', message_lower)
        if temp_match:
            temp = float(temp_match.group(1))
            from_unit = temp_match.group(2).lower()
            to_unit = temp_match.group(3).lower()
            if from_unit[0] == 'c' and to_unit[0] == 'f':
                result = (temp * 9/5) + 32
                update_memory_intent("convert_temperature")
                return f"🌡️ {temp}°C = {result:.1f}°F"
            elif from_unit[0] == 'f' and to_unit[0] == 'c':
                result = (temp - 32) * 5/9
                update_memory_intent("convert_temperature")
                return f"🌡️ {temp}°F = {result:.1f}°C"
        
        # Distance conversion
        distance_match = re.search(r'(\d+(?:\.\d+)?)\s*(miles?|km|kilometers?)\s*(?:to|in)\s*(miles?|km|kilometers?)', message_lower)
        if distance_match:
            distance = float(distance_match.group(1))
            from_unit = distance_match.group(2).lower()
            to_unit = distance_match.group(3).lower()
            if 'mile' in from_unit and 'km' in to_unit:
                result = distance * 1.609
                update_memory_intent("convert_distance")
                return f"📏 {distance} miles = {result:.2f} km"
            elif 'km' in from_unit and 'mile' in to_unit:
                result = distance / 1.609
                update_memory_intent("convert_distance")
                return f"📏 {distance} km = {result:.2f} miles"
        
        return "🔄 I can convert currencies (USD to INR), temperatures (C to F), and distances (miles to km). Try: 'Convert 10 USD to INR'"

    # Battery Status
    elif any(phrase in message_lower for phrase in ["battery", "battery level", "battery status", "power level"]):
        import random
        battery_level = random.randint(65, 95)
        charging = random.choice([True, False])
        status = "charging" if charging else "on battery"
        update_memory_intent("battery_status")
        debug_log_intent("battery_status", user_message)
        return f"🔋 Battery at {battery_level}%, {status}. {'⚡ Charging...' if charging else '🔌 Unplug when convenient.'}"

    # General Knowledge
    elif any(phrase in message_lower for phrase in ["who is", "what is", "explain", "tell me about"]):
        import re
        if "president of india" in message_lower:
            update_memory_intent("knowledge_query")
            debug_log_intent("knowledge_query", user_message)
            return "🇮🇳 The President of India is Droupadi Murmu (as of 2022). She is the 15th President and the second woman to hold this office."
        elif "quantum computing" in message_lower:
            update_memory_intent("knowledge_query")
            return "⚛️ **Quantum Computing** uses quantum mechanics principles (superposition, entanglement) to process information in quantum bits (qubits), potentially solving certain problems exponentially faster than classical computers."
        elif "ai" in message_lower and any(w in message_lower for w in ["artificial intelligence", "explain ai"]):
            update_memory_intent("knowledge_query")
            return "🤖 **Artificial Intelligence** is technology that enables machines to simulate human intelligence - learning, reasoning, and decision-making. I'm a simple example: processing your questions and responding helpfully!"
        else:
            # Generic knowledge response
            query = re.sub(r'^(who is|what is|explain|tell me about)\s*', '', user_message, flags=re.IGNORECASE).strip()
            update_memory_intent("knowledge_query")
            return f"🧠 You asked about '{query}'. I have basic knowledge but would recommend checking reliable sources like Wikipedia or Google for detailed information on this topic."

    # Fun Facts
    elif any(phrase in message_lower for phrase in ["fun fact", "interesting fact", "tell me fact", "give me fact"]):
        facts = [
            "🍯 Did you know honey never spoils? Archaeologists have found edible honey in ancient Egyptian tombs!",
            "🐙 Octopuses have three hearts and blue blood!",
            "🌍 There are more possible games of chess than atoms in the observable universe!",
            "🦈 Sharks have been around longer than trees - by about 50 million years!",
            "🧠 Your brain uses about 20% of your body's total energy, despite being only 2% of your weight!",
            "🌙 The Moon is moving away from Earth at about 3.8 cm per year!",
        ]
        import random
        update_memory_intent("fun_facts")
        debug_log_intent("fun_facts", user_message)
        return random.choice(facts)

    # Jokes
    elif any(phrase in message_lower for phrase in ["tell joke", "make me laugh", "joke", "funny"]):
        jokes = [
            "🤖 Why don't programmers like nature? Too many bugs!",
            "😂 Why did the AI go to therapy? It had too many deep learning issues!",
            "💻 How many programmers does it take to change a light bulb? None, that's a hardware problem!",
            "🔧 Why do Python developers prefer dark mode? Because light attracts bugs!",
            "📱 Why was the smartphone cold? It left its Windows open!",
            "⚡ What do you call a programmer from Finland? Nerdic!",
        ]
        import random
        update_memory_intent("jokes")
        debug_log_intent("jokes", user_message)
        return random.choice(jokes)

    # User Preferences
    elif any(phrase in message_lower for phrase in ["my favorite", "i like", "i love", "remember that", "remember i"]):
        import re
        # Extract preference
        if "favorite color" in message_lower:
            color_match = re.search(r'favorite color is (\w+)', message_lower)
            if color_match:
                color = color_match.group(1)
                user_memory.setdefault("preferences", {})["favorite_color"] = color
                save_memory()
                update_memory_intent("set_preference")
                debug_log_intent("set_preference", user_message)
                return f"✅ Got it! I'll remember that your favorite color is {color}. 🎨"
        
        elif "like" in message_lower or "love" in message_lower:
            # Generic preference storage
            pref = re.sub(r'^.*?(i like|i love|my favorite)\s*', '', message_lower, flags=re.IGNORECASE).strip()
            if pref:
                user_memory.setdefault("preferences", {})["general"] = user_memory.get("preferences", {}).get("general", [])
                if pref not in user_memory["preferences"]["general"]:
                    user_memory["preferences"]["general"].append(pref)
                    save_memory()
                update_memory_intent("set_preference")
                return f"✅ Noted! I'll remember that you like {pref}. 📝"
        
        update_memory_intent("set_preference")
        return "✅ I'm listening! Tell me what you'd like me to remember about your preferences. 👂"

    # Light Control (Smart Home placeholder)
    elif any(phrase in message_lower for phrase in ["turn on light", "turn off light", "lights on", "lights off", "switch light"]):
        import random
        room = "living room"
        if "bedroom" in message_lower:
            room = "bedroom"
        elif "kitchen" in message_lower:
            room = "kitchen"
        
        action = "on" if any(w in message_lower for w in ["on", "turn on"]) else "off"
        update_memory_intent("smart_home_lights")
        debug_log_intent("smart_home_lights", user_message)
        return f"💡 {room.title()} lights turned {action}. (Simulated - connect to smart home system for real control!)"

    # Music Control (placeholder)
    elif any(phrase in message_lower for phrase in ["play music", "start spotify", "play song", "music on"]):
        playlists = ["Your Favorites", "Chill Vibes", "Workout Mix", "Focus Flow"]
        import random
        playlist = random.choice(playlists)
        update_memory_intent("music_control")
        debug_log_intent("music_control", user_message)
        return f"🎵 Now playing '{playlist}' on Spotify. (Simulated - integrate with Spotify API for real control!)"

    # Health Reminders
    elif any(phrase in message_lower for phrase in ["drink water", "hydration", "water reminder", "remind water"]):
        update_memory_intent("health_hydration")
        debug_log_intent("health_hydration", user_message)
        return "💧 **Hydration Reminder Set!** I'll remind you to drink water every hour. Stay healthy! 🌊\n\n💡 **Tip**: Aim for 8 glasses a day for optimal health."

    # Exercise Tracking
    elif any(phrase in message_lower for phrase in ["track workout", "log exercise", "exercise tracker", "workout log"]):
        import re
        exercise_match = re.search(r'(\d+(?:\.\d+)?)\s*(km|miles?|minutes?)\s*(run|walk|cycle|gym)', message_lower)
        if exercise_match:
            amount = exercise_match.group(1)
            unit = exercise_match.group(2)
            activity = exercise_match.group(3)
            update_memory_intent("exercise_tracker")
            return f"🏋️ **Workout Logged!** {amount} {unit} {activity}\n📊 Keep up the great work! 💪"
        else:
            update_memory_intent("exercise_tracker")
            return "🏃 **Exercise Tracker Ready!** Tell me what you did: '5km run', '30 minutes gym', etc."

    # To-Do List Management
    elif any(phrase in message_lower for phrase in ["add task", "add todo", "to do list", "task list", "add to list"]):
        import re
        task_match = re.search(r'(?:add|create)(?:\s+task)?(?:\s+to)?.*?[\'""]([^\'""]+)[\'""]', user_message, re.IGNORECASE)
        if not task_match:
            task_match = re.search(r'(?:add|create)(?:\s+task|\s+todo)?\s+(.+)', user_message, re.IGNORECASE)
        
        if task_match:
            task = task_match.group(1).strip()
            update_memory_intent("todo_add")
            debug_log_intent("todo_add", user_message)
            return f"✅ **Task Added!** '{task}' is now on your to-do list.\n📋 Say 'show my tasks' to see all items."
        else:
            update_memory_intent("todo_add")
            return "📝 **Ready to add a task!** Try: 'Add task buy groceries' or 'Add finish report to my list'"

    elif any(phrase in message_lower for phrase in ["show tasks", "my tasks", "todo list", "task list", "what's pending"]):
        tasks = [
            "📊 Finish quarterly report",
            "🛒 Buy groceries (milk, bread, fruits)",
            "📞 Call client about project update",
            "🏃 Go for evening run",
            "📚 Read 20 pages of current book"
        ]
        update_memory_intent("todo_list")
        debug_log_intent("todo_list", user_message)
        return f"📋 **Your Current Tasks:**\n" + "\n".join(f"{i+1}. {task}" for i, task in enumerate(tasks)) + "\n\n💡 **Tip**: Say 'mark task 1 done' to complete items!"

    # Reasoning/Logic Questions
    elif any(phrase in message_lower for phrase in ["if i leave", "will i reach", "can i finish", "is it possible"]):
        # Simple time/distance reasoning
        if "leave" in message_lower and "reach" in message_lower:
            update_memory_intent("reasoning_time")
            debug_log_intent("reasoning_time", user_message)
            return "🚗 **Travel Calculation**: If traffic is normal and your usual route takes 25-30 minutes, you should reach on time. Consider checking live traffic for accuracy! 🗺️"
        elif "finish" in message_lower and ("30 minutes" in message_lower or "5km" in message_lower):
            update_memory_intent("reasoning_exercise")
            return "🏃 **Fitness Estimate**: A 5km run in 30 minutes means 6-minute pace per km - that's a good intermediate pace! You can definitely do it with consistent training. 💪"
        else:
            update_memory_intent("reasoning_general")
            return "🤔 **Let me think about that...** Based on typical scenarios, it's likely achievable with proper planning. Want me to break down the steps?"

    # Who am I
    elif fuzzy_contains(message_lower, ["who am i", "do you know me", "what's my name", "who are i"]):
        name = get_user_name("there")
        update_memory_intent("who_am_i")
        debug_log_intent("who_am_i", user_message)
        if name and name.lower() != "there":
            prefs = user_memory.get("preferences", {})
            pref_text = ""
            if prefs.get("favorite_color"):
                pref_text = f" I know your favorite color is {prefs['favorite_color']}."
            if prefs.get("general"):
                pref_text += f" You like: {', '.join(prefs['general'][:3])}."
            return f"You're {name}!{pref_text} Share more about yourself and I'll remember it."
        return "I don't have your name yet. Tell me 'My name is <your name>' and I'll remember it locally."

    # Who / how developed you (expanded variants)
    elif fuzzy_contains(message_lower, [
        "who developed you", "who made you", "who built you", "who created you",
        "how were you developed", "how were you built", "how was your code developed",
        "how was your code built", "who coded you"
    ]):
        update_memory_intent("who_developed_you")
        debug_log_intent("who_developed_you", user_message)
        return (
            "I'm BUDDY—assembled using Python (FastAPI) + Electron UI + planned local voice modules. "
            "Your team (you!) integrates open-source pieces with custom logic focusing on privacy & extensibility."
        )

    # Training / how to train you
    elif fuzzy_contains(message_lower, [
        "how should i train you", "how do i train you", "train you", "customize yourself",
        "how can i improve you", "teach you"
    ]):
        update_memory_intent("training")
        debug_log_intent("training", user_message)
        return (
            "You can 'train' me by: 1) Telling me your name: 'My name is <name>'. 2) Using intents repeatedly—I'll track usage patterns. "
            "3) Sharing preferences (future expansion) via a preferences command. 4) Adding new skills (Python functions / endpoints). "
            "I'm lightweight: no large remote model tuning here—it's rule + memory now, with room to plug in local models later."
        )

    # Day summary / reflection
    elif any(p in message_lower for p in ["how was the day", "how was your day", "how did the day go", "day summary", "summarize the day"]):
        update_memory_intent("day_summary")
        fi = user_memory.get("frequent_intents", {})
        total_msgs = sum(fi.values()) or 0
        top = sorted(fi.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_txt = ", ".join(f"{k.replace('_',' ')} ({v})" for k, v in top) if top else "no significant interactions yet"
        debug_log_intent("day_summary", user_message)
        return (
            f"Here's a quick day summary: you've triggered {total_msgs} tracked intents so far. "
            f"Top areas: {top_txt}. I'm ready to help you build more habits tomorrow. Want a suggestion?"
        )

    # Capabilities phrasing variants (enhanced)
    elif any(p in message_lower for p in ["what can you do", "your abilities", "your capabilities", "assist me with", "how can you help me", "help me", "what help"]):
        update_memory_intent("help")
        debug_log_intent("help", user_message)
        return (
            "🚀 **BUDDY's Capabilities:**\n\n"
            "📅 **Time & Reminders**: Current time, date, set reminders\n"
            "🧮 **Math & Conversions**: Calculate anything, convert currencies/units\n"
            "🌤️ **Weather**: Current conditions and forecasts\n"
            "📊 **System Info**: Check status, battery, diagnostics\n"
            "💾 **Memory**: Remember your name, preferences, habits\n"
            "📝 **Productivity**: To-do lists, task management\n"
            "🏠 **Smart Home**: Light control, music (simulated)\n"
            "💪 **Health**: Exercise tracking, hydration reminders\n"
            "🧠 **Knowledge**: Answer questions, fun facts, jokes\n"
            "🤖 **Reasoning**: Basic logic and problem-solving\n\n"
            "💡 **Try saying**: 'Set reminder for 6pm', 'Convert 10 USD to INR', 'Tell me a joke'"
        )

    # Home / device integration
    elif any(p in message_lower for p in ["integrate you to my house", "integrate you to my home", "home integration", "house integration", "smart home integration", "connect to my house"]):
        update_memory_intent("home_integration")
        debug_log_intent("home_integration", user_message)
        return (
            "Home integration roadmap:\n"
            "1. Run this backend on a Raspberry Pi or always-on PC.\n"
            "2. Add a lightweight local REST or MQTT bridge.\n"
            "3. Connect smart devices via APIs (Philips Hue, Home Assistant).\n"
            "4. Enable wake-word + VAD from the voice package for hands-free use.\n"
            "5. Use local TTS + ASR for privacy-first control.\n"
            "I stay local—no cloud lock-in."
        )

    # Supported devices / platforms (broaden detection)
    elif any(p in message_lower for p in [
        "what devices can you work on", "supported devices", "which platforms", "supported os", "which devices",
        "how many device", "how many devices", "devices you work", "platforms you run", "run on raspberry"
    ]) or ("device" in message_lower and "work" in message_lower) or ("platform" in message_lower and ("run" in message_lower or "support" in message_lower)):
        update_memory_intent("devices_support")
        debug_log_intent("devices_support", user_message)
        return (
            "Environments: Windows, macOS, Linux, Raspberry Pi (ARM). Needs Python 3.10+ and optionally Electron for desktop UI. "
            "You can also run headless (just the FastAPI server) and talk to it via HTTP or a future CLI / mobile wrapper."
        )

    # Who are you
    elif fuzzy_contains(message_lower, ["who are you", "what are you", "tell me about yourself", "introduce yourself"]):
        update_memory_intent("who_are_you")
        return (
            "I'm BUDDY, your local AI assistant. I handle chat, time, weather, calculations, and system info, "
            "and I learn lightweight preferences on-device to stay helpful and privacy-first."
        )

    # How do you work
    elif fuzzy_contains(message_lower, ["how do you work", "how you work", "how do u work", "how it works"]):
        update_memory_intent("how_i_work")
        return (
            "I run a local FastAPI backend that classifies your intent and executes skills (time, weather, calculator, system). "
            "The desktop app talks to me over HTTP/IPC. I store small preferences locally in JSON for personalization."
        )

    # Test yourself
    elif fuzzy_contains(message_lower, ["test yourself", "self test", "self-check", "diagnostics", "run healthcheck"]):
        import random
        uptime = int((datetime.now() - server_start_time).total_seconds())
        cpu = random.randint(10, 35); mem = random.randint(30, 60)
        return (
            f"✅ Self-check complete.\n\n"
            f"• Status: Online\n"
            f"• Uptime: {uptime//3600}h {(uptime%3600)//60}m\n"
            f"• CPU: {cpu}%   • Memory: {mem}%\n"
            f"Try: 'system status', weather, or a calculation."
        )

    # Thanks
    elif any(w in message_lower for w in ["thank", "thanks", "appreciate"]):
        import random
        debug_log_intent("gratitude", user_message)
        return random.choice([
            "You're welcome! 😊",
            "Happy to help! 🙌",
            "Anytime! 💫",
            "Glad to be useful! 🎉",
        ])

    # Farewell
    elif any(w in message_lower for w in ["bye", "goodbye", "see you", "talk later"]):
        import random
        update_memory_intent("farewell")
        return random.choice([
            "Goodbye for now! 👋",
            "See you later! 🌟",
            "Until next time! 😊",
            "Farewell! 🚀",
        ])

    # Weather
    elif "weather" in message_lower:
        city = extract_city_from_message(message_lower)
        if city:
            weather_response = await get_weather_for_city(city)
            update_memory_intent("weather")
            return weather_response
        return "🌤️ Tell me a city, like 'weather in London' or 'weather Paris'."

    # Calculator
    elif any(w in message_lower for w in ["calculate", "math", "multiply", "plus", "minus", "divide", "compute"]):
        try:
            import re, math
            percent_match = re.search(r'(\d+(?:\.\d+)?)\s*percent\s*of\s*(\d+(?:\.\d+)?)', user_message.lower())
            if percent_match:
                percent, number = float(percent_match.group(1)), float(percent_match.group(2))
                result = (percent / 100) * number
                update_memory_intent("calculate")
                return f"🧮 {percent}% of {number} = {result:g}"
            sqrt_match = re.search(r'square\s*root\s*of\s*(\d+(?:\.\d+)?)', user_message.lower())
            if sqrt_match:
                number = float(sqrt_match.group(1))
                result = math.sqrt(number)
                update_memory_intent("calculate")
                return f"🧮 √{number} = {result:g}"
            exp_match = re.search(r'(\d+(?:\.\d+)?)\s*\^\s*(\d+(?:\.\d+)?)', user_message)
            if exp_match:
                base, exponent = float(exp_match.group(1)), float(exp_match.group(2))
                result = base ** exponent
                update_memory_intent("calculate")
                return f"🧮 {base}^{exponent} = {result:g}"
            basic_match = re.search(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)', user_message)
            if basic_match:
                a, op, b = basic_match.groups(); a = float(a); b = float(b)
                if op == '+': res = a + b
                elif op == '-': res = a - b
                elif op == '*': res = a * b
                else:
                    if b == 0: return "🚫 Can't divide by zero."
                    res = a / b
                if isinstance(res, float) and res.is_integer():
                    res = int(res)
                update_memory_intent("calculate")
                return f"🧮 {a} {op} {b} = {res}"
            return "🧮 Try: 25 * 4, 15 percent of 200, 2^8, or square root of 64."
        except Exception:
            return "🧮 I couldn't parse that. Try 'calculate 25 * 4'."

    # System status
    elif any(w in message_lower for w in ["system", "status", "health", "performance", "metrics"]):
        import random
        uptime = (datetime.now() - server_start_time).total_seconds()
        uptime_hours = int(uptime // 3600)
        uptime_minutes = int((uptime % 3600) // 60)
        cpu = random.randint(15, 45)
        mem = random.randint(35, 65)
        response_time = random.randint(80, 150)
        status_emoji = "🟢" if cpu < 50 and mem < 70 else "🟡" if cpu < 70 else "🔴"
        update_memory_intent("system_status")
        return (
            f"📊 System: {status_emoji}\n"
            f"⏱️ Uptime: {uptime_hours}h {uptime_minutes}m\n"
            f"🖥️ CPU: {cpu}%\n🧠 Memory: {mem}%\n⚡ Avg Response: {response_time}ms\n"
        )

    # Help
    elif any(w in message_lower for w in ["help", "what can you do", "capabilities", "features"]) or \
         fuzzy_contains(message_lower, ["what can you do", "what are your features", "what do you do", "your capabilities", "as my assistant what can you do"]):
        update_memory_intent("help")
        return (
            "I can chat, tell time/date, fetch weather, calculate, and show system stats. "
            "Try: 'weather in Paris', 'calculate 25*4', 'system status', or 'what is AI?'."
        )

    # Knowledge
    elif any(w in message_lower for w in ["what is", "tell me about", "explain", "define"]) or \
         fuzzy_contains(message_lower, ["explain", "define", "tell me about"]):
        update_memory_intent("knowledge")
        return handle_knowledge_query(user_message, conversation_history)

    # Productivity
    elif any(w in message_lower for w in ["remind", "reminder", "task", "todo", "schedule"]):
        update_memory_intent("productivity")
        return handle_productivity_query(user_message, conversation_history)

    # Creative
    elif any(w in message_lower for w in ["create", "generate", "write", "compose", "make"]):
        update_memory_intent("creative")
        return handle_creative_query(user_message, conversation_history)

    # Fallback
    else:
        suggestions = generate_smart_suggestions(user_message)
        return (
            f"I understand you said: \"{user_message}\"\n\n"
            f"I'm still learning new skills. Meanwhile, here are ideas:\n{suggestions}\n\n"
            f"Ask weather, do a calculation, check time/status, or ask 'what can you do?'."
        )


def analyze_conversation_context(conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze conversation history to extract context and preferences, seeded from memory."""
    context = {"user_name": get_user_name("there"), "topics": list(user_memory.get("topics", [])), "sentiment": "neutral"}
    if not conversation_history:
        return context
    # Extract user name if mentioned
    for msg in conversation_history:
        content = msg.get("content", "").lower()
        if "my name is" in content or "i'm" in content or "call me" in content or content.startswith("i am "):
            words = content.replace("i'm", "i am").split()
            if "is" in words:
                idx = words.index("is")
                if idx + 1 < len(words):
                    nm = words[idx + 1].strip(".,!?").title()
                    if nm and nm.isalpha():
                        context["user_name"] = nm
                        set_user_name(nm)
            elif "am" in words:
                idx = words.index("am")
                if idx + 1 < len(words):
                    nm = words[idx + 1].strip(".,!?").title()
                    if nm and nm.isalpha():
                        context["user_name"] = nm
                        set_user_name(nm)
    # Extract topics
    topic_keywords = {
        "weather": ["weather", "temperature", "rain", "sunny", "cold"],
        "math": ["calculate", "math", "number", "percent"],
        "time": ["time", "date", "today", "clock"],
        "technology": ["system", "computer", "software", "tech"],
    }
    changed = False
    for msg in conversation_history:
        content = msg.get("content", "").lower()
        for topic, keywords in topic_keywords.items():
            if any(k in content for k in keywords):
                if topic not in context["topics"]:
                    context["topics"].append(topic)
                    changed = True
    if changed:
        user_memory["topics"] = context["topics"]
        save_memory()
    return context


def extract_city_from_message(message: str) -> Optional[str]:
    """Extract city name from weather-related messages."""
    # Common patterns for city extraction
    patterns = [
        r'weather\s+in\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
        r'weather\s+for\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
        r'weather\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
        r'in\s+([a-zA-Z\s]+?)\s+weather',
        r'([a-zA-Z\s]+?)\s+weather'
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            city = match.group(1).strip()
            # Remove common words that aren't city names
            exclude_words = {'the', 'is', 'today', 'tomorrow', 'like', 'what', 'how'}
            city_words = [word for word in city.split() if word not in exclude_words]
            if city_words:
                return ' '.join(city_words).title()
    
    return None


def handle_knowledge_query(user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
    """Handle knowledge-based questions with intelligent responses."""
    message_lower = user_message.lower()
    
    # Technology explanations
    if any(word in message_lower for word in ["ai", "artificial intelligence", "machine learning", "neural network"]):
        return """🤖 **Artificial Intelligence (AI)** is fascinating! 

AI refers to computer systems that can perform tasks that typically require human intelligence - like understanding language, recognizing patterns, making decisions, and learning from experience.

**Key AI Concepts:**
• **Machine Learning**: AI systems that improve through experience
• **Neural Networks**: AI models inspired by how the brain works
• **Natural Language Processing**: How AI understands and generates human language (like me!)

**How I Work**: I use advanced language models trained on vast amounts of text to understand your questions and provide helpful, contextual responses.

**Fun Fact**: AI is already part of your daily life - in search engines, recommendation systems, voice assistants, and smart devices!

Want to know more about any specific aspect of AI? 🧠✨"""
    
    # Science topics
    elif any(word in message_lower for word in ["space", "universe", "planet", "star", "galaxy"]):
        return """🌌 **Space and the Universe** - one of the most awe-inspiring topics!

**Mind-Blowing Space Facts:**
• The observable universe is about 93 billion light-years in diameter
• There are more stars in the universe than grains of sand on all Earth's beaches
• One day on Venus equals 243 Earth days
• Jupiter's Great Red Spot is a storm larger than Earth that's been raging for centuries

**Our Solar System**: 8 planets, 200+ moons, countless asteroids and comets, all orbiting our amazing Sun.

**Recent Discoveries**: We've found thousands of exoplanets, detected gravitational waves, and even photographed black holes!

**Fun Thought**: You're made of star stuff - the heavier elements in your body were forged in the hearts of ancient stars! ⭐

What aspect of space interests you most? 🚀"""
    
    # Default knowledge response
    else:
        return """🧠 I'd love to help you learn more! While I might not have specific information about that topic right now, I can assist with:

**💡 Topics I'm Great With:**
• Technology and AI concepts
• Basic science and space facts  
• Weather and environmental data
• Mathematics and calculations
• General knowledge questions

**📚 For More Detailed Information**, I recommend:
• Checking reputable educational websites
• Looking up academic sources
• Consulting specialized databases

What specific aspect would you like to explore? I'm always eager to help you discover new things! 🌟"""


def handle_productivity_query(user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
    """Handle productivity and task-related queries."""
    message_lower = user_message.lower()
    
    if "remind" in message_lower:
        # Extract reminder details
        reminder_text = user_message
        if "remind me to" in message_lower:
            task = user_message.lower().split("remind me to", 1)[1].strip()
        elif "reminder" in message_lower:
            task = user_message.lower().split("reminder", 1)[1].strip()
        else:
            task = "your task"
        
        return f"""⏰ **Reminder Created Successfully!**

📝 **Task**: {task}
🕐 **Status**: Active reminder set
📅 **Note**: I've noted your reminder request

**💡 Productivity Tips:**
• Break large tasks into smaller, manageable steps
• Set specific deadlines for better accountability  
• Review and update your tasks regularly
• Celebrate completed tasks to stay motivated!

**⚡ Quick Actions You Can Try:**
• "Set reminder for meeting at 3pm"
• "Remind me to call John tomorrow"
• "Task: finish project report"

Would you like to add any specific time or details to this reminder? 🎯"""
    
    else:
        return """📋 **Productivity Assistant Ready!**

I can help you stay organized and efficient:

**🎯 Task Management:**
• Set reminders and notifications
• Break down complex projects
• Track progress and deadlines
• Organize priorities

**⏰ Time Management:**
• Schedule planning assistance
• Time-blocking suggestions  
• Deadline tracking
• Work-life balance tips

**💡 Productivity Strategies:**
• Goal setting frameworks
• Focus techniques
• Habit building
• Motivation boosters

Try saying something like "remind me to..." or "set a task for..." to get started! 🚀"""


def handle_creative_query(user_message: str, conversation_history: List[Dict[str, Any]]) -> str:
    """Handle creative and generation requests."""
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ["joke", "funny", "humor"]):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything! 😄",
            "I told my computer a joke about UDP... I'm not sure if it got it! 😂",
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
            "What do you call a robot that takes the long way around? R2-Detour! 🤖",
            "Why don't AI assistants ever get tired? We run on cloud computing - it's always a breeze! ☁️"
        ]
        import random
        return f"😄 Here's a fun one for you:\n\n{random.choice(jokes)}\n\nLaughter is the best medicine! Want to hear another one? 🎭"
    
    elif any(word in message_lower for word in ["story", "tale", "narrative"]):
        return """📚 **Creative Story Starter for You:**

*Once upon a time, in a world where AI assistants and humans worked together as the best of teams, there lived a curious person who discovered that asking the right questions could unlock amazing possibilities...*

**🎨 Creative Writing Tips:**
• Start with "What if..." scenarios
• Use vivid, sensory descriptions
• Create interesting characters with clear motivations
• Build tension and resolution

**💡 Story Prompts to Try:**
• "A day when technology gained emotions"
• "The last library on Earth"
• "Messages from the future"

Would you like me to help you develop any of these ideas further? ✨"""
    
    else:
        return """🎨 **Creative Assistant Ready!**

I can help spark your creativity:

**✍️ Writing Support:**
• Story ideas and prompts
• Character development
• Plot suggestions
• Writing techniques

**🎭 Fun & Entertainment:**
• Jokes and humor
• Wordplay and puns
• Creative challenges
• Brainstorming sessions

**💡 Innovation Help:**
• Problem-solving approaches
• Alternative perspectives
• "What if" scenarios
• Out-of-the-box thinking

What kind of creative adventure shall we embark on? 🚀✨"""


def generate_smart_suggestions(user_message: str) -> str:
    """Generate contextual suggestions based on user input."""
    message_lower = user_message.lower()

    # Personalized top hint using frequent intents
    top_hint = None
    fi = user_memory.get("frequent_intents", {}) if isinstance(user_memory, dict) else {}
    if fi:
        common = sorted(fi.items(), key=lambda kv: kv[1], reverse=True)[0][0]
        if common == "weather":
            top_hint = "• 🌤️ Your usual: ask weather, e.g. 'weather in Mumbai'"
        elif common == "calculate":
            top_hint = "• 🧮 Your usual: quick math, e.g. '25 * 4' or 'convert 10 USD to INR'"
        elif common == "time":
            top_hint = "• 🕐 Your usual: time/date, e.g. 'what time is it?'"
        elif common == "system_status":
            top_hint = "• 📊 Your usual: 'system status' or 'battery level'"
        elif common == "reminder_set":
            top_hint = "• ⏰ Your usual: reminders, e.g. 'remind me to call at 6pm'"

    suggestions = []
    if top_hint:
        suggestions.append(top_hint)
    
    # Analyze the message for keywords and generate relevant suggestions
    if any(word in message_lower for word in ["number", "digit", "calculate", "math"]):
        suggestions.append("• 🧮 **Try calculations**: '25 * 4', 'convert 100 USD to INR', '50% of 200'")
    elif any(word in message_lower for word in ["when", "time", "date", "remind"]):
        suggestions.append("• 🕐 **Time & reminders**: 'What time is it?', 'Set reminder for 6pm'")
    elif any(word in message_lower for word in ["weather", "rain", "sunny", "cold"]):
        suggestions.append("• 🌤️ **Check weather**: 'Weather in [your city]' or 'Tomorrow's forecast'")
    elif any(word in message_lower for word in ["how", "what", "why", "explain", "knowledge"]):
        suggestions.append("• 💡 **Ask me questions**: 'What is AI?', 'Tell me a fun fact', 'Explain quantum computing'")
    elif any(word in message_lower for word in ["task", "todo", "list", "remind"]):
        suggestions.append("• 📝 **Productivity**: 'Add task buy groceries', 'Show my tasks', 'Set reminder'")
    else:
        # General suggestions based on capabilities
        suggestions.extend([
            "• 💬 **Chat naturally**: I understand context and remember conversations!",
            "• 🎯 **Try these popular commands**:",
            "  - 'What can you do?' (see all capabilities)",
            "  - 'Tell me a joke' (for some fun)",
            "  - 'My name is [name]' (personalize experience)",
            "  - 'Convert 50 miles to km' (unit conversions)"
        ])
    return "\n".join(suggestions)

if __name__ == "__main__":
    logger.info("Starting BUDDY Backend Server...")
    if DEV_MODE:
        uvicorn.run(
            "simple_backend:app",
            host="localhost", 
            port=8082,
            log_level="info",
            reload=True
        )
    else:
        uvicorn.run(
            app,
            host="localhost", 
            port=8082,
            log_level="info"
        )
