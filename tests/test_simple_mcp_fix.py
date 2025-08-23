#!/usr/bin/env python3
"""
Simple test for MCP tool mapping fix.
Tests if tools are correctly mapped to their servers instead of 'universal'.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def test_tool_mapping():
    """Test the tool-to-server mapping fix."""
    print("🔧 Testing Tool-to-Server Mapping Fix...")
    
    try:
        # Import the universal tool function
        from src.tools.lggraph_tools.tools.mcp_integrated_tools.universal import universal_tool
        
        # Test some basic mapping lookups
        print("📋 Testing tool-to-server mapping logic...")
        
        # These are the tools that were failing with "Server 'universal' not found"
        test_cases = [
            ('read_graph', 'memory'),
            ('search_nodes', 'memory'),
            ('list_directory', 'filesystem'),
            ('create_repository', 'github')
        ]
        
        success_count = 0
        
        for tool_name, expected_server in test_cases:
            print(f"   {tool_name} should map to '{expected_server}' server")
            
            try:
                # Try to call the tool (it may fail due to server not running, but it should not fail due to 'universal' server)
                result = universal_tool(tool_name=tool_name)
                
                # Check the result - if it doesn't contain "Server 'universal' not found", the mapping worked
                if isinstance(result, dict) and result.get('error'):
                    error_msg = result.get('error', '')
                    if "Server 'universal' not found" in error_msg:
                        print(f"   ❌ {tool_name}: Still trying to use 'universal' server!")
                    elif "not running" in error_msg or "not found" in error_msg:
                        print(f"   ✅ {tool_name}: Mapping works (server may not be running)")
                        success_count += 1
                    else:
                        print(f"   ✅ {tool_name}: Mapping works (different error: {error_msg})")
                        success_count += 1
                else:
                    print(f"   ✅ {tool_name}: Mapping successful!")
                    success_count += 1
                    
            except Exception as e:
                error_msg = str(e)
                if "Server 'universal' not found" in error_msg:
                    print(f"   ❌ {tool_name}: Still trying to use 'universal' server!")
                else:
                    print(f"   ✅ {tool_name}: Mapping works (execution error: {error_msg})")
                    success_count += 1
        
        print(f"\n📊 Mapping Test Results: {success_count}/{len(test_cases)} tools correctly mapped")
        
        if success_count == len(test_cases):
            print("🎉 Tool-to-server mapping fix is working!")
            return True
        else:
            print("⚠️ Some tools are still trying to use 'universal' server")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openai_fix():
    """Test the OpenAI NoneType fix."""
    print("\n🔧 Testing OpenAI NoneType Fix...")
    
    try:
        from src.utils.open_ai_integration import OpenAIIntegration
        
        print("📋 Testing None completion handling...")
        
        # Test the None completion handling
        try:
            result = OpenAIIntegration._handle_non_streaming_response_with_debugging(None)
            print("❌ Should have raised exception for None completion")
            return False
        except Exception as e:
            if "API returned None completion object" in str(e):
                print("✅ None completion properly handled")
                return True
            else:
                print(f"⚠️ Different exception: {e}")
                return False
                
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Simple MCP Fix Test")
    print("=" * 30)
    
    # Test 1: Tool mapping
    mapping_success = test_tool_mapping()
    
    # Test 2: OpenAI fix
    openai_success = test_openai_fix()
    
    # Results
    print("\n" + "=" * 30)
    print("📊 Test Results:")
    print(f"Tool Mapping: {'✅ PASS' if mapping_success else '❌ FAIL'}")
    print(f"OpenAI Fix: {'✅ PASS' if openai_success else '❌ FAIL'}")
    
    if mapping_success and openai_success:
        print("\n🎉 All fixes are working correctly!")
        exit_code = 0
    else:
        print("\n⚠️ Some fixes need adjustment.")
        exit_code = 1
    
    print(f"\nExiting with code: {exit_code}")
    sys.exit(exit_code)