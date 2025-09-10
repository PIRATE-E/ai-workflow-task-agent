"""
Example usage of the browser use tool
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def example_usage():
    """Example of how to use the browser use tool"""
    try:
        # Import the browser use tool function
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        
        print("Example 1: Basic usage with default headless mode")
        print("browser_use_tool('Navigate to https://www.google.com')")
        print("  - This would use headless=True by default")
        print()
        
        print("Example 2: Explicit headless mode")
        print("browser_use_tool('Navigate to https://www.google.com', head_less_mode=True)")
        print("  - This explicitly sets headless mode to True")
        print()
        
        print("Example 3: Visible browser mode")
        print("browser_use_tool('Navigate to https://www.google.com', head_less_mode=False)")
        print("  - This runs the browser in visible mode")
        print()
        
        print("Function signature:")
        import inspect
        sig = inspect.signature(browser_use_tool)
        print(f"  {sig}")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("BROWSER USE TOOL EXAMPLE USAGE")
    print("=" * 60)
    example_usage()
    print("=" * 60)