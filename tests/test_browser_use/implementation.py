"""
Simple test script to verify that the browser use tool implementation is working correctly
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_browser_use_implementation():
    try:
        # Test importing the browser use tool function
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        print("SUCCESS: Successfully imported browser_use_tool function")
        
        # Test importing the BrowserUseCompatibleLLM class
        from src.tools.lggraph_tools.tools.browser_use import BrowserUseCompatibleLLM
        print("SUCCESS: Successfully imported BrowserUseCompatibleLLM class")
        
        # Test importing ModelManager and settings
        from src.utils.model_manager import ModelManager
        from src.config import settings
        print("SUCCESS: Successfully imported ModelManager and settings")
        
        # Test creating BrowserUseCompatibleLLM instance
        print(f"Using KIMI_MODEL: {settings.KIMI_MODEL}")
        model_manager = ModelManager(model=settings.KIMI_MODEL)
        browser_llm = BrowserUseCompatibleLLM(model_manager)
        print("SUCCESS: Successfully created BrowserUseCompatibleLLM instance")
        
        # Test accessing properties
        print(f"  - Model: {browser_llm.model}")
        print(f"  - Provider: {browser_llm.provider}")
        print(f"  - Name: {browser_llm.name}")
        
        print("SUCCESS: All tests passed!")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_browser_use_implementation()