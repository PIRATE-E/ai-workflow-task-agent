# 🔍 Quick Validation Script
"""
Quick validation to ensure the event listener system is working correctly.
This script tests the basic functionality before running the full test suite.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


import sys
import os
import time

# Add project root to path

from rich.console import Console

console = Console()

try:
    from src.utils.listeners.rich_status_listen import RichStatusListener
    from src.utils.listeners.event_listener import EventListener

    console.print("🔍 [bold blue]QUICK VALIDATION[/bold blue]")

    # Test 1: Import validation
    console.print("✅ All imports successful")

    # Test 2: Listener creation
    listener = RichStatusListener(Console())
    console.print(f"✅ Listener created with ID: {id(listener)}")

    # Test 3: Status start
    listener.start_status("🧪 Validation test...")
    console.print("✅ Status display started")

    # Test 4: Event emission
    listener.emit_on_variable_change(
        type("TestClass", (), {}), "test_var", "old_value", "new_value"
    )
    console.print("✅ Event emission successful")

    time.sleep(2)

    # Test 5: Status stop
    listener.stop_status_display()
    console.print("✅ Status display stopped")

    console.print("\n🎉 [bold green]VALIDATION PASSED![/bold green]")
    console.print("✅ Event listener system is working correctly")
    console.print("🚀 Ready to run full test suite!")

except ImportError as e:
    console.print(f"❌ Import error: {e}")
    console.print("🔧 Check that your event listener files are in the correct location")
    console.print("💡 Try running from project root directory")

except Exception as e:
    console.print(f"❌ Validation failed: {e}")
    console.print("🔧 Check your event listener implementation")

console.print("\n📝 To run the full test suite:")
console.print("   python tests/run_listener_test.py")
console.print("   python tests/test_event_listener_realistic.py")
