#!/usr/bin/env python3
"""
Simple OpenAI provider functionality test
"""

import sys
import os
sys.path.append('src')

# Import required modules
import streamlit as st
from providers import OpenAIProvider
import json

def test_openai_provider():
    """Test OpenAI provider with a simple query"""
    print("🧪 Testing OpenAI Provider")
    print("=" * 40)
    
    # Get API key
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("❌ No OpenAI API key found in secrets or environment")
            print("💡 Make sure OPENAI_API_KEY is in your .streamlit/secrets.toml")
            return False
        
        print("✅ API key found")
    except Exception as e:
        print(f"❌ Error accessing API key: {e}")
        return False
    
    # Initialize provider
    try:
        provider = OpenAIProvider(api_key)
        print("✅ Provider initialized")
    except Exception as e:
        print(f"❌ Provider initialization failed: {e}")
        return False
    
    # Test with GPT-4o Mini (cheapest option)
    model_config = {
        "name": "gpt-4o-mini",
        "provider": "openai", 
        "temperature": 0.7,
        "max_output_tokens": 50,
        "system_prompt": "You are a helpful AI assistant."
    }
    
    # Simple test message
    messages = [
        {"role": "user", "content": "Hello! Please respond with exactly: 'OpenAI provider is working correctly!'"}
    ]
    
    print(f"\n🔄 Testing with {model_config['name']}")
    print(f"📤 Request: {messages[0]['content']}")
    
    # Make the API call
    try:
        print("⏳ Calling OpenAI API...")
        response = provider.generate_response(messages, model_config)
        
        print(f"📥 Raw response type: {type(response)}")
        
        if isinstance(response, dict):
            if "text" in response:
                response_text = response["text"]
                print(f"📥 Response: {response_text}")
                
                # Check metrics
                if "metrics" in response and response["metrics"]:
                    metrics = response["metrics"]
                    print(f"⏱️  Response time: {metrics.get('response_time', 0):.2f}s")
                    print(f"📊 Input tokens: {metrics.get('input_tokens', 0)}")
                    print(f"📊 Output tokens: {metrics.get('output_tokens', 0)}")
                    
                    # Calculate cost (GPT-4o Mini: $0.15/1K input, $0.60/1K output)
                    input_cost = (metrics.get('input_tokens', 0) / 1000) * 0.15
                    output_cost = (metrics.get('output_tokens', 0) / 1000) * 0.60
                    total_cost = input_cost + output_cost
                    print(f"💰 Estimated cost: ${total_cost:.6f}")
                
                print("✅ OpenAI provider working correctly!")
                return True
            else:
                print(f"❌ Missing 'text' key in response: {response}")
                return False
        else:
            print(f"❌ Unexpected response format: {response}")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_availability():
    """Test that OpenAI models are available in provider manager"""
    print(f"\n🔍 Testing OpenAI model availability")
    
    try:
        from providers import initialize_provider_manager
        import streamlit as st
        
        # Initialize session state simulation
        if not hasattr(st, 'session_state'):
            st.session_state = type('SessionState', (), {})()
        
        # Initialize provider manager
        initialize_provider_manager()
        
        if hasattr(st.session_state, 'provider_manager'):
            provider_manager = st.session_state.provider_manager
            
            if "openai" in provider_manager.providers:
                print("✅ OpenAI provider available in provider manager")
                
                # Test get_available_models
                openai_provider = provider_manager.providers["openai"]
                available_models = openai_provider.get_available_models()
                
                print(f"📋 Available OpenAI models:")
                for model in available_models:
                    print(f"   - {model['name']}: {model['description']}")
                
                return True
            else:
                print("❌ OpenAI provider not found in provider manager")
                print(f"Available providers: {list(provider_manager.providers.keys())}")
                return False
        else:
            print("❌ Provider manager not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model availability: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 OpenAI Provider Integration Test")
    print("=" * 50)
    
    # Test 1: Model availability
    model_test = test_model_availability()
    
    # Test 2: Basic functionality 
    if model_test:
        func_test = test_openai_provider()
        
        if func_test:
            print(f"\n🎉 SUCCESS: OpenAI provider is fully functional!")
            print(f"💡 Ready to include in LLM routing tests")
        else:
            print(f"\n💥 FAILED: OpenAI provider has issues")
    else:
        print(f"\n💥 FAILED: OpenAI models not properly configured")
    
    print(f"\n📋 Next steps:")
    print(f"   1. If successful: Add OpenAI to LLM routing tests")
    print(f"   2. If failed: Debug provider configuration")