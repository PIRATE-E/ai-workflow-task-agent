"""
Simple test script to verify that the browser use tool is working correctly
"""

def test_browser_use():
    try:
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        
        # Test with a simple query
        result = browser_use_tool("Navigate to https://www.google.com", head_less_mode=True)
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_browser_use()