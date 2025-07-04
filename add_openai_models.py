#!/usr/bin/env python3
"""
Add OpenAI models from config templates to the database
"""

import sys
sys.path.append('src')

from pymongo import MongoClient
from config import MONGO_LOCAL_URI, MONGO_LOCAL_DB_NAME, MODEL_TEMPLATES
from datetime import datetime

def add_openai_models_to_db():
    """Add OpenAI models from MODEL_TEMPLATES to database"""
    
    # Connect to database
    print("🔌 Connecting to MongoDB...")
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    # Get OpenAI models from templates
    openai_models = {k: v for k, v in MODEL_TEMPLATES.items() if v.get('provider') == 'openai'}
    
    print(f"📋 Found {len(openai_models)} OpenAI models in templates:")
    for name, config in openai_models.items():
        print(f"   - {name}: {config['name']}")
    
    # Check existing OpenAI models in database
    existing_openai = list(db.models.find({"provider": "openai"}))
    print(f"\n📊 Current OpenAI models in database: {len(existing_openai)}")
    
    # Add models to database
    added_count = 0
    updated_count = 0
    
    for display_name, template_config in openai_models.items():
        model_name = template_config["name"]
        
        # Check if model already exists
        existing = db.models.find_one({"name": model_name, "provider": "openai"})
        
        # Prepare model document
        model_doc = {
            "name": model_name,
            "provider": "openai",
            "display_name": display_name,
            "temperature": template_config.get("temperature", 0.7),
            "top_p": template_config.get("top_p", 0.9),
            "max_output_tokens": template_config.get("max_output_tokens", 16384),
            "max_input_tokens": template_config.get("max_input_tokens", 128000),
            "input_price": template_config.get("input_price", 0.0),
            "output_price": template_config.get("output_price", 0.0),
            "capabilities": [],
            "system_prompt": "You are a helpful, harmless, and honest AI assistant.",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Add capabilities based on template
        if template_config.get("text_input", False):
            model_doc["capabilities"].append("text_input")
        if template_config.get("image_input", False):
            model_doc["capabilities"].append("image_input")
        if template_config.get("text_output", False):
            model_doc["capabilities"].append("text_output")
        if template_config.get("tools", False):
            model_doc["capabilities"].append("function_calling")
        if template_config.get("functions", False):
            model_doc["capabilities"].append("function_calling")
        
        if existing:
            # Update existing model
            db.models.update_one(
                {"_id": existing["_id"]},
                {"$set": {**model_doc, "updated_at": datetime.utcnow()}}
            )
            print(f"✅ Updated: {display_name} ({model_name})")
            updated_count += 1
        else:
            # Insert new model
            result = db.models.insert_one(model_doc)
            print(f"➕ Added: {display_name} ({model_name})")
            added_count += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   ➕ Added: {added_count} models")
    print(f"   ✅ Updated: {updated_count} models")
    
    # Verify final count
    final_openai_count = db.models.count_documents({"provider": "openai"})
    total_models = db.models.count_documents({})
    
    print(f"   📋 Total OpenAI models in DB: {final_openai_count}")
    print(f"   📊 Total models in DB: {total_models}")
    
    print(f"\n🎉 OpenAI models successfully added to database!")
    
    return final_openai_count

def list_all_models():
    """List all models in database by provider"""
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    # Get all models grouped by provider
    pipeline = [
        {"$group": {
            "_id": "$provider",
            "models": {"$push": {"name": "$name", "display_name": "$display_name"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    providers = list(db.models.aggregate(pipeline))
    
    print(f"\n📋 ALL MODELS IN DATABASE:")
    print("=" * 50)
    
    total_models = 0
    for provider in providers:
        provider_name = provider["_id"]
        count = provider["count"]
        models = provider["models"]
        total_models += count
        
        print(f"\n{provider_name.upper()}: {count} models")
        for model in models:
            display_name = model.get("display_name", model["name"])
            print(f"   - {display_name} ({model['name']})")
    
    print(f"\n📊 TOTAL: {total_models} models across all providers")

if __name__ == "__main__":
    print("🚀 Adding OpenAI Models to Database")
    print("=" * 40)
    
    # Add the models
    openai_count = add_openai_models_to_db()
    
    # Show all models
    list_all_models()
    
    print(f"\n✅ OpenAI integration complete!")
    print(f"💡 You can now select OpenAI models in your chat interface")