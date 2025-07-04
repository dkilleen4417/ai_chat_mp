#!/usr/bin/env python3
"""
Convert Scratch Pad to use prompt reference instead of storing prompt text
"""

import sys
sys.path.append('src')

from pymongo import MongoClient
from config import MONGO_LOCAL_URI, MONGO_LOCAL_DB_NAME
from datetime import datetime

def fix_scratch_pad_prompt():
    """Convert Scratch Pad from system_prompt text to prompt_name reference"""
    
    print("🔧 Converting Scratch Pad to use prompt reference system")
    print("=" * 55)
    
    # Connect to database
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    # Find the Scratch Pad
    scratch_pad = db.chats.find_one({"name": "Scratch Pad"})
    
    if not scratch_pad:
        print("❌ No Scratch Pad chat found!")
        return False
    
    print("📋 Current Scratch Pad:")
    current_prompt = scratch_pad.get("system_prompt", "No prompt")
    print(f"   System Prompt: {current_prompt[:100]}...")
    print(f"   Length: {len(current_prompt)} characters")
    
    # Update to use prompt reference
    update_result = db.chats.update_one(
        {"name": "Scratch Pad"},
        {
            "$set": {
                "prompt_name": "Default System Prompt",  # Reference to prompt in prompts collection
                "updated_at": datetime.now().timestamp()
            },
            "$unset": {
                "system_prompt": ""  # Remove the old text field
            }
        }
    )
    
    if update_result.modified_count > 0:
        print("\n✅ Scratch Pad updated successfully!")
        print("   🔗 Now uses: prompt_name = 'Default System Prompt'")
        print("   🗑️  Removed: old system_prompt text field")
        
        # Verify the change
        updated_scratch_pad = db.chats.find_one({"name": "Scratch Pad"})
        prompt_name = updated_scratch_pad.get("prompt_name", "Not set")
        has_old_prompt = "system_prompt" in updated_scratch_pad
        
        print(f"\n🔍 Verification:")
        print(f"   Prompt Name: {prompt_name}")
        print(f"   Old prompt field present: {has_old_prompt}")
        
        if not has_old_prompt and prompt_name == "Default System Prompt":
            print("   ✅ Conversion successful!")
            return True
        else:
            print("   ⚠️  Conversion may have issues")
            return False
    else:
        print("\n❌ Update failed - no documents modified")
        return False

def verify_prompt_resolution():
    """Verify that the prompt can be resolved from the reference"""
    
    print(f"\n🧪 Testing Prompt Resolution...")
    
    client = MongoClient(MONGO_LOCAL_URI)
    db = client[MONGO_LOCAL_DB_NAME]
    
    # Get chat's prompt reference
    scratch_pad = db.chats.find_one({"name": "Scratch Pad"})
    prompt_name = scratch_pad.get("prompt_name")
    
    if not prompt_name:
        print("❌ No prompt_name found in Scratch Pad")
        return False
    
    # Resolve the prompt
    prompt_doc = db.prompts.find_one({"name": prompt_name})
    
    if prompt_doc:
        prompt_content = prompt_doc.get("content", "")
        print(f"✅ Prompt resolved successfully!")
        print(f"   Referenced prompt: '{prompt_name}'")
        print(f"   Content length: {len(prompt_content)} characters")
        print(f"   Preview: {prompt_content[:100]}...")
        return True
    else:
        print(f"❌ Could not resolve prompt: '{prompt_name}'")
        return False

if __name__ == "__main__":
    print("🚀 Scratch Pad Prompt Reference Conversion")
    print("Making the architecture cleaner, one chat at a time!")
    print("=" * 60)
    
    # Fix the Scratch Pad
    success = fix_scratch_pad_prompt()
    
    if success:
        # Test prompt resolution
        verify_prompt_resolution()
        
        print(f"\n🎉 SCRATCH PAD CONVERSION COMPLETE!")
        print(f"💡 Benefits:")
        print(f"   🔗 Clean reference architecture")
        print(f"   📱 Instant prompt updates for all chats")
        print(f"   💾 Reduced data duplication")
        print(f"   🧹 Cleaner database structure")
        
        print(f"\n📋 Next Steps:")
        print(f"   1. Update chat creation code to use prompt_name instead of system_prompt")
        print(f"   2. Update chat rendering to resolve prompt references")
        print(f"   3. Enjoy the cleaner architecture!")
        
    else:
        print(f"\n💥 Conversion failed - please check the database and try again")