#!/usr/bin/env python3
"""
Test script to verify the socket manager is working correctly
Tests the singleton pattern, connection handling, and error scenarios
"""

import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.socket_manager import socket_manager


def test_socket_manager_creation():
    """Test socket manager creation and singleton pattern"""
    print("🧪 Testing Socket Manager Creation...")

    # Test 1: Get socket connection
    print("\n1. Testing socket connection...")
    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        print("✅ Socket connection established successfully")

        # Test 2: Send a test message
        print("\n2. Testing message sending...")
        try:
            socket_manager.send_error("🧪 Test message from socket manager")
            print("✅ Message sent successfully")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
    else:
        print("⚠️ Socket connection not available")
        print("   This is normal if:")
        print("   - Logging is disabled in config")
        print("   - Log server is not running")

    return socket_con is not None


def test_singleton_pattern():
    """Test that singleton pattern works correctly"""
    print("\n🧪 Testing Singleton Pattern...")

    # Create multiple instances
    manager1 = socket_manager
    manager2 = socket_manager.__class__()
    manager3 = socket_manager.__class__()

    # Test that they're all the same object
    if manager1 is manager2 is manager3:
        print("✅ Singleton pattern working correctly")
        print(f"   All managers have same ID: {id(manager1)}")
        return True
    else:
        print("❌ Singleton pattern failed")
        print(f"   manager1 ID: {id(manager1)}")
        print(f"   manager2 ID: {id(manager2)}")
        print(f"   manager3 ID: {id(manager3)}")
        return False


def test_connection_status():
    """Test connection status checking"""
    print("\n🧪 Testing Connection Status...")

    is_connected = socket_manager.is_connected()
    print(
        f"Connection status: {'🟢 Connected' if is_connected else '🔴 Not connected'}"
    )

    return True


def test_error_handling():
    """Test error handling scenarios"""
    print("\n🧪 Testing Error Handling...")

    # Test sending messages when connection might fail
    test_messages = [
        "Testing normal message",
        "Testing message with special chars: àáâãäå",
        "Testing long message: " + "x" * 1000,
        "Testing empty message: ",
        "Testing unicode: 🚀🔥💯🎉",
    ]

    success_count = 0
    for i, message in enumerate(test_messages, 1):
        try:
            socket_manager.send_error(f"[ERROR TEST {i}] {message}")
            success_count += 1
            print(f"✅ Message {i} sent successfully")
        except Exception as e:
            print(f"❌ Message {i} failed: {e}")

        time.sleep(0.1)  # Small delay between messages

    print(f"📊 Success rate: {success_count}/{len(test_messages)} messages")
    return success_count > 0


def test_cleanup():
    """Test connection cleanup"""
    print("\n🧪 Testing Connection Cleanup...")

    try:
        socket_manager.close_connection()
        print("✅ Connection cleanup completed")

        # Test that we can still get connection after cleanup
        new_connection = socket_manager.get_socket_connection()
        if new_connection:
            print("✅ New connection established after cleanup")
            socket_manager.send_error("🧪 Test message after reconnection")
        else:
            print("⚠️ No new connection after cleanup (normal if server not running)")

        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


def run_comprehensive_test():
    """Run all socket manager tests"""
    print("=" * 70)
    print("🧪 SOCKET MANAGER COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    tests = [
        ("Socket Manager Creation", test_socket_manager_creation),
        ("Singleton Pattern", test_singleton_pattern),
        ("Connection Status", test_connection_status),
        ("Error Handling", test_error_handling),
        ("Connection Cleanup", test_cleanup),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1

    print(f"\n📈 Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Socket manager is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

    print("\n📋 Next Steps:")
    print("   1. If tests failed, make sure log server is running:")
    print("      python utils/error_transfer.py")
    print("   2. Check your config.py for correct socket settings")
    print("   3. Verify ENABLE_SOCKET_LOGGING=true in config")


if __name__ == "__main__":
    run_comprehensive_test()
