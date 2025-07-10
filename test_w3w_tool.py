#!/usr/bin/env python3
"""
Test the W3W tool function directly
Check if the tool itself works correctly
"""

import sys
sys.path.append('src')

from tools import get_what3words_address

def test_w3w_tool_direct():
    """Test the W3W tool function directly"""
    
    print("🧪 Testing W3W Tool Function Directly")
    print("=" * 50)
    
    test_addresses = [
        "Times Square, New York",
        "1600 Pennsylvania Avenue, Washington DC",
        "317 N Beaumont Ave, Catonsville, MD",
        "White House",
        "Central Park, New York"
    ]
    
    for i, address in enumerate(test_addresses):
        print(f"\n🧪 Test {i+1}: '{address}'")
        
        try:
            result = get_what3words_address(address)
            print(f"Result:")
            print(result)
            
            if "❌" in result:
                print(f"   ⚠️  Error detected in result")
            elif "///" in result:
                print(f"   ✅ SUCCESS: W3W address found!")
            else:
                print(f"   ❓ Unexpected result format")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n🎯 Direct W3W Tool Test Complete!")

if __name__ == "__main__":
    test_w3w_tool_direct()