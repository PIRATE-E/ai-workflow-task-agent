"""
Test to verify that the headless mode parameter handling is correct
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_headless_mode_parameter():
    """Test that the headless mode parameter is correctly handled"""
    try:
        print("Testing headless mode parameter handling...")
        
        # Import the browser use tool function
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        
        # Check the function signature
        import inspect
        sig = inspect.signature(browser_use_tool)
        params = sig.parameters
        
        print(f"Function signature: {sig}")
        
        # Verify the headless mode parameter exists and has correct name
        if 'head_less_mode' in params:
            param = params['head_less_mode']
            print(f"SUCCESS: Found parameter 'head_less_mode'")
            print(f"  - Default value: {param.default}")
            print(f"  - Annotation: {param.annotation}")
            
            # Check if default is True (headless by default)
            if param.default is True:
                print("SUCCESS: head_less_mode defaults to True (headless mode enabled)")
            else:
                print("INFO: head_less_mode default is not True")
                
            # Check if it's a boolean parameter
            if param.annotation == bool:
                print("SUCCESS: head_less_mode is correctly typed as bool")
            else:
                print(f"INFO: head_less_mode is typed as {param.annotation}")
        else:
            print("ERROR: Parameter 'head_less_mode' not found!")
            print("Available parameters:", list(params.keys()))
            return False
            
        # Test that there's no parameter with incorrect naming
        incorrect_names = ['headless_mode', 'headlessmode', 'head_lessmode']
        for incorrect_name in incorrect_names:
            if incorrect_name in params:
                print(f"WARNING: Found incorrectly named parameter '{incorrect_name}'")
                return False
                
        print("SUCCESS: Headless mode parameter naming is correct")
        print("  - Using 'head_less_mode' (with underscore)")
        print("  - Matches what LLM generates in error logs")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_consistency():
    """Test that parameter names are consistent with LLM expectations"""
    try:
        print("\nTesting parameter consistency with LLM expectations...")
        
        # Based on the error logs we saw, the LLM generates:
        # {"query": "...", "head_less_mode": false}
        
        expected_params = ['query', 'head_less_mode']
        print(f"Expected parameters from LLM: {expected_params}")
        
        # Import and check the actual function
        from src.tools.lggraph_tools.tools.browser_use import browser_use_tool
        import inspect
        sig = inspect.signature(browser_use_tool)
        actual_params = list(sig.parameters.keys())
        
        print(f"Actual function parameters: {actual_params}")
        
        # Check if all expected parameters are present
        for expected in expected_params:
            if expected in actual_params:
                print(f"SUCCESS: Expected parameter '{expected}' is present")
            else:
                print(f"ERROR: Expected parameter '{expected}' is missing")
                return False
                
        print("SUCCESS: All expected parameters are present in function")
        print("  - No parameter name mismatches that would cause LLM errors")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("HEADLESS MODE PARAMETER VERIFICATION TEST")
    print("=" * 60)
    
    success1 = test_headless_mode_parameter()
    success2 = test_parameter_consistency()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("OVERALL RESULT: SUCCESS")
        print("  - Headless mode parameter handling is CORRECT")
        print("  - Parameter names match LLM expectations")
        print("  - No naming mismatches that would cause errors")
    else:
        print("OVERALL RESULT: FAILURE")
        print("  - There are issues with parameter handling")
    print("=" * 60)