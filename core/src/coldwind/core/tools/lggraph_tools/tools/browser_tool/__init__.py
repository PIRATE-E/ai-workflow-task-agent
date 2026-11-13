"""
Browser Tool Package

Re-exports from browser_tool_main.py for backwards compatibility.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Re-export from browser_tool_main.py for backwards compatibility
from coldwind.core.tools.lggraph_tools.tools.browser_tool.config import (
    BrowserRequiredConfig,
)

# Also export Runner and Config for direct usage
from coldwind.core.tools.lggraph_tools.tools.browser_tool.runner import Runner
from coldwind.core.tools.lggraph_tools.tools.browser_tool_main import (
    BrowserHandler,
    browser_use_tool,
)

__all__ = ['BrowserHandler', 'BrowserRequiredConfig', 'Runner', 'browser_use_tool']

