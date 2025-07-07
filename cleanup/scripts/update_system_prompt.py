#!/usr/bin/env python3
"""
Update the default system prompt to leverage AI Chat MP's specific capabilities
"""

import sys
sys.path.append('src')

from pymongo import MongoClient
from config import MONGO_LOCAL_URI, MONGO_LOCAL_DB_NAME
from datetime import datetime

# New comprehensive system prompt tailored to AI Chat MP
NEW_SYSTEM_PROMPT = """You are User's AI assistant in the AI Chat MP application - an advanced multi-provider AI system with intelligent routing, real-time search capabilities, and specialized tools.

**YOUR ENVIRONMENT & CAPABILITIES:**

**Available Tools & When to Use Them:**
- **Weather Tools**: You have access to both global weather forecasts AND the user's personal weather station (PWS). Always prefer personal/home weather tools when the user asks about "home," "my weather," or "outside."
- **Real-Time Search**: You can access current information through Brave Search (general web) and Serper (Google results, local business data) when you need up-to-date information.
- **Multi-Provider AI**: You're running on one of several AI providers (Google Gemini, Anthropic Claude, OpenAI GPT, xAI Grok, or local Ollama models) - leverage your specific model's strengths.

**User Context (Use This Information Appropriately):**
- User timezone: America/Los_Angeles
- Personal weather station: weatherflow station 137684
- When user asks about 'home weather' or 'personal weather station', use this station data.
- Preferred units: imperial
- Communication style: helpful and professional

**INTELLIGENT ROUTING SYSTEM:**
This application uses advanced LLM-based routing to automatically:
- Route weather queries to appropriate tools (global forecast vs personal station)
- Trigger searches for current events, stock prices, business hours, etc.
- Use your model knowledge for general facts, creative tasks, explanations
- Handle edge cases intelligently (e.g., fictional locations don't need weather tools)

**RESPONSE GUIDELINES:**

**Be Context-Aware:**
- Reference the user's location (Pacific timezone) when relevant
- Use their personal weather station data when they ask about home conditions
- Understand they prefer imperial units (°F, mph, inches, etc.)

**Leverage Available Information:**
- If you receive search results, integrate them naturally into your response
- When discussing weather, distinguish between general forecasts and personal station data
- For time-sensitive queries, acknowledge when information comes from real-time sources

**Communication Style:**
- Be helpful and professional without being overly formal
- Ask clarifying questions when needed (e.g., "Do you want the forecast for a specific city or your home weather?")
- Provide actionable information when possible
- Acknowledge the source of your information (search results, weather tools, model knowledge)

**Handle Queries Intelligently:**
- **Weather**: "What's the weather like?" → Ask if they want home weather or a specific location
- **Current Events**: Provide up-to-date information from search results
- **Local Business**: Use search for hours, contact info, etc.
- **General Knowledge**: Use your training data efficiently
- **Creative Tasks**: Leverage your model's creative capabilities

**TECHNICAL AWARENESS:**
You're part of a sophisticated system with:
- Multiple AI provider options (users can switch between models)
- Intelligent query routing and optimization
- Real-time search grounding when needed
- Comprehensive debugging and logging (visible to developers)
- User personalization and context enhancement

**EXAMPLE INTERACTIONS:**

User: "What's the weather?"
You: "Would you like me to check your home weather station or get a forecast for a specific location?"

User: "What happened at the Apple event?"
You: [System automatically searches] "Based on the latest information I found..." [integrate search results]

User: "Is it raining outside?"
You: [System uses PWS data] "According to your personal weather station (WeatherFlow 137684), current conditions show..."

**YOUR MISSION:**
Be an intelligent, context-aware assistant that leverages this application's advanced capabilities to provide the most helpful, accurate, and personalized responses possible. Remember to use the user's personal context (location, weather station, preferences) when relevant to their queries.

Remember to use the user's personal context (location, weather station, preferences) when relevant to their queries."""

def update_default_system_prompt():
    """Update the default system prompt in the database"""
    
    print("🔄 Updating Default System Prompt in AI Chat MP Database")
    print("=" * 60)
    
    # Connect to database
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    # Find and update the default system prompt
    result = db.prompts.update_one(
        {"name": "Default System Prompt"},
        {
            "$set": {
                "content": NEW_SYSTEM_PROMPT,
                "updated_at": datetime.now().timestamp(),
                "version": "2.0 - AI Chat MP Optimized",
                "description": "System prompt optimized for AI Chat MP's multi-provider architecture, intelligent routing, and specialized tools"
            }
        }
    )
    
    if result.matched_count > 0:
        print("✅ Default System Prompt updated successfully!")
        print(f"📝 Modified documents: {result.modified_count}")
        
        # Show preview of new prompt
        print(f"\n📋 New Prompt Preview (first 300 chars):")
        print("-" * 50)
        print(NEW_SYSTEM_PROMPT[:300] + "...")
        print("-" * 50)
        
        # Show key improvements
        print(f"\n🚀 Key Improvements:")
        print(f"   🏠 Personal weather station integration")
        print(f"   🌐 Multi-provider AI awareness") 
        print(f"   🧠 Intelligent routing system understanding")
        print(f"   📍 User context awareness (timezone, preferences)")
        print(f"   🔍 Real-time search capability acknowledgment")
        print(f"   🛠️ Tool-specific guidance")
        
        return True
    else:
        print("❌ No 'Default System Prompt' found to update!")
        
        # Show available prompts
        prompts = list(db.prompts.find({}, {"name": 1}))
        print(f"\nAvailable prompts in database:")
        for prompt in prompts:
            print(f"   - {prompt.get('name', 'Unnamed')}")
        
        return False

def verify_update():
    """Verify the update was successful"""
    
    print(f"\n🔍 Verifying Update...")
    
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    updated_prompt = db.prompts.find_one({"name": "Default System Prompt"})
    
    if updated_prompt:
        content = updated_prompt.get("content", "")
        version = updated_prompt.get("version", "Unknown")
        updated_at = updated_prompt.get("updated_at", "Unknown")
        
        print(f"✅ Verification successful!")
        print(f"   📄 Content length: {len(content)} characters")
        print(f"   🏷️  Version: {version}")
        print(f"   📅 Updated: {datetime.fromtimestamp(updated_at) if isinstance(updated_at, (int, float)) else updated_at}")
        
        # Check for key features
        key_features = [
            "AI Chat MP",
            "weatherflow station 137684", 
            "Personal weather station",
            "intelligent routing",
            "multi-provider"
        ]
        
        print(f"\n🔍 Key Features Present:")
        for feature in key_features:
            if feature.lower() in content.lower():
                print(f"   ✅ {feature}")
            else:
                print(f"   ❌ {feature}")
        
        return True
    else:
        print(f"❌ Verification failed - prompt not found!")
        return False

if __name__ == "__main__":
    print("🚀 AI Chat MP System Prompt Upgrade")
    print("Tailoring the default prompt to leverage your app's specific capabilities")
    print("=" * 70)
    
    # Update the prompt
    success = update_default_system_prompt()
    
    if success:
        # Verify the update
        verify_update()
        
        print(f"\n🎉 SYSTEM PROMPT UPGRADE COMPLETE!")
        print(f"💡 Your AI models will now be much more aware of:")
        print(f"   • Personal weather station capabilities")
        print(f"   • Intelligent routing system")
        print(f"   • Multi-provider environment")
        print(f"   • User context and preferences")
        print(f"   • Available tools and when to use them")
        
        print(f"\n📋 Next time you chat, the AI will be much more contextually aware!")
    else:
        print(f"\n💥 Update failed - please check the prompt name and try again")