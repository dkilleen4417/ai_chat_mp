#!/usr/bin/env python3
"""
Test if the PWS tools are properly registered and callable
"""

import sys
sys.path.append('./src')

def test_tool_registry():
    print("=== Tool Registry Test ===\n")
    
    try:
        from tools import tool_registry, get_pws_current_conditions
        
        print("✅ Successfully imported tool_registry and get_pws_current_conditions")
        
        # Check if tool is registered
        configs = tool_registry.list_tool_configs()
        print(f"📊 Total tools registered: {len(configs)}")
        
        pws_tool_found = False
        for config in configs:
            for decl in config.get('function_declarations', []):
                name = decl.get('name', 'Unknown')
                if name == 'get_pws_current_conditions':
                    pws_tool_found = True
                    print(f"✅ PWS tool found: {name}")
                    print(f"   Description: {decl.get('description', 'No description')}")
                    print(f"   Parameters: {decl.get('parameters', {})}")
                else:
                    print(f"   Other tool: {name}")
        
        if not pws_tool_found:
            print("❌ PWS tool NOT found in registry!")
        
        # Test if the function is callable
        print(f"\n🧪 Testing get_pws_current_conditions function...")
        try:
            # This will fail due to missing secrets, but should show it's callable
            result = get_pws_current_conditions()
            print(f"Function result: {result[:100]}...")
        except Exception as e:
            print(f"Function call error (expected): {e}")
        
        print("\n=== Test Complete ===")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_tool_registry()