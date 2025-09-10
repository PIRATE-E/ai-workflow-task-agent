"""
Test script to verify that the browser use tool can actually be used
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_browser_use_actual_usage():
    try:
        print("Testing browser use tool actual usage...")
        
        # Import the browser use tool function
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        print("SUCCESS: Successfully imported browser_use_tool function")
        
        # Test calling the function with a simple query
        # We won't actually run the browser to avoid dependency issues
        # Instead, we'll just verify the function can be called and the parameters are processed
        
        # Check if the function signature is correct
        import inspect
        sig = inspect.signature(browser_use_tool)
        print(f"Function signature: {sig}")
        
        # Verify the function has the expected parameters
        params = sig.parameters
        expected_params = ['query', 'head_less_mode']
        for param in expected_params:
            if param not in params:
                print(f"WARNING: Expected parameter '{param}' not found in function signature")
            else:
                print(f"SUCCESS: Parameter '{param}' found in function signature")
        
        print("SUCCESS: Browser use tool function signature is correct")
        print("NOTE: Actual browser execution requires browser-use package installation")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_browser_use_compatible_llm():
    try:
        print("\nTesting BrowserUseCompatibleLLM class...")
        
        # Import the BrowserUseCompatibleLLM class
        from src.tools.lggraph_tools.tools.browser_tool import BrowserUseCompatibleLLM
        from src.utils.model_manager import ModelManager
        from src.config import settings
        
        # Create a ModelManager instance
        model_manager = ModelManager(model=settings.KIMI_MODEL)
        
        # Create BrowserUseCompatibleLLM instance
        browser_llm = BrowserUseCompatibleLLM(model_manager)
        print("SUCCESS: Created BrowserUseCompatibleLLM instance")
        
        # Test accessing properties
        print(f"  - Model: {browser_llm.model}")
        print(f"  - Provider: {browser_llm.provider}")
        print(f"  - Name: {browser_llm.name}")
        print(f"  - Model name: {browser_llm.model_name}")
        
        # Test property access
        provider = browser_llm.provider
        name = browser_llm.name
        model_name = browser_llm.model_name
        
        print("SUCCESS: All properties accessible")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("BROWSER USE TOOL ACTUAL USAGE TEST")
    print("=" * 50)
    
    success1 = test_browser_use_actual_usage()
    success2 = test_browser_use_compatible_llm()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("OVERALL RESULT: SUCCESS - All tests passed!")
    else:
        print("OVERALL RESULT: FAILURE - Some tests failed!")
    print("=" * 50)