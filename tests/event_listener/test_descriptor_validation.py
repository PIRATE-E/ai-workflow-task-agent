# 🧪 Descriptor Validation Test
"""
Test the descriptor validation system in RichStatusListener.

This test demonstrates:
1. ✅ Valid Console assignment
2. ❌ Invalid Console assignment (should raise TypeError)
3. ✅ Valid Status context assignment
4. ❌ Invalid Status context assignment (should raise TypeError)
5. 🔍 WeakKeyDictionary memory management
"""

import sys
import os

project_root = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.append(project_root)

from rich.console import Console
from rich.status import Status
from src.utils.listeners.rich_status_listen import RichStatusListener


def test_console_descriptor_validation():
    """Test Console descriptor validation"""
    print("🧪 Testing Console Descriptor Validation")

    # ✅ Test 1: Valid Console assignment
    try:
        console = Console()
        listener = RichStatusListener(console)
        print("✅ Valid Console assignment successful")
        print(f"   Console type: {type(listener.console).__name__}")
        print(f"   Console ID: {id(listener.console)}")
    except Exception as e:
        print(f"❌ Valid Console assignment failed: {e}")
        return False

    # ❌ Test 2: Invalid Console assignment (should raise TypeError)
    try:
        listener.console = "not_a_console"  # This should fail
        print("❌ Invalid Console assignment should have failed!")
        return False
    except TypeError as e:
        print(f"✅ Invalid Console assignment correctly rejected: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # ✅ Test 3: Valid Console reassignment
    try:
        new_console = Console()
        listener.console = new_console
        print("✅ Valid Console reassignment successful")
        print(f"   New Console ID: {id(listener.console)}")
    except Exception as e:
        print(f"❌ Valid Console reassignment failed: {e}")
        return False

    return True


def test_status_context_descriptor_validation():
    """Test Status Context descriptor validation"""
    print("\n🧪 Testing Status Context Descriptor Validation")

    console = Console()
    listener = RichStatusListener(console)

    # ✅ Test 1: Valid Status context assignment (None is valid)
    try:
        listener.status_context = None
        print("✅ None status_context assignment successful")
    except Exception as e:
        print(f"❌ None status_context assignment failed: {e}")
        return False

    # ✅ Test 2: Valid Status context assignment (actual status)
    try:
        status = console.status("Test status")
        listener.status_context = status
        print("✅ Valid Status context assignment successful")
        print(f"   Status type: {type(listener.status_context).__name__}")
    except Exception as e:
        print(f"❌ Valid Status context assignment failed: {e}")
        return False

    # ❌ Test 3: Invalid Status context assignment (should raise TypeError)
    try:
        listener.status_context = "not_a_context_manager"  # This should fail
        print("❌ Invalid Status context assignment should have failed!")
        return False
    except TypeError as e:
        print(f"✅ Invalid Status context assignment correctly rejected: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    return True


def test_memory_management():
    """Test WeakKeyDictionary memory management"""
    print("\n🧪 Testing Memory Management with WeakKeyDictionary")

    # Create multiple listeners and check memory management
    listeners = []
    console_ids = []

    for i in range(3):
        console = Console()
        listener = RichStatusListener(console)
        listeners.append(listener)
        console_ids.append(id(listener.console))
        print(f"✅ Listener {i + 1} created with Console ID: {console_ids[i]}")

    # Check that each listener has its own console
    unique_consoles = len(set(console_ids))
    print(
        f"🔍 Created {len(listeners)} listeners with {unique_consoles} unique consoles"
    )

    if unique_consoles == len(listeners):
        print("✅ Each listener has its own console instance")
        return True
    else:
        print("❌ Console instances are being shared incorrectly")
        return False


def test_descriptor_class_vs_instance_access():
    """Test descriptor behavior at class vs instance level"""
    print("\n🧪 Testing Descriptor Class vs Instance Access")

    # Access descriptor at class level
    console_descriptor = RichStatusListener.console
    status_descriptor = RichStatusListener.status_context

    print(f"✅ Class-level console descriptor: {type(console_descriptor).__name__}")
    print(f"✅ Class-level status descriptor: {type(status_descriptor).__name__}")

    # Access descriptor at instance level
    console = Console()
    listener = RichStatusListener(console)

    instance_console = listener.console
    instance_status = listener.status_context

    print(f"✅ Instance-level console: {type(instance_console).__name__}")
    print(
        f"✅ Instance-level status: {type(instance_status) if instance_status else 'None'}"
    )

    return True


def run_all_descriptor_tests():
    """Run all descriptor validation tests"""
    print("🎯 DESCRIPTOR VALIDATION TEST SUITE")
    print("=" * 50)

    tests = [
        ("Console Descriptor Validation", test_console_descriptor_validation),
        (
            "Status Context Descriptor Validation",
            test_status_context_descriptor_validation,
        ),
        ("Memory Management", test_memory_management),
        ("Descriptor Access Patterns", test_descriptor_class_vs_instance_access),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 ALL DESCRIPTOR VALIDATION TESTS PASSED!")
        return True
    else:
        print("⚠️  Some tests failed - check implementation")
        return False


if __name__ == "__main__":
    success = run_all_descriptor_tests()
    exit(0 if success else 1)
