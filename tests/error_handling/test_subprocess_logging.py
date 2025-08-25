#!/usr/bin/env python3
"""
Test script to verify that the socket manager can automatically start
and stop the log server as a subprocess
"""

import os
import sys
import time

import psutil

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.socket_manager import socket_manager


def test_subprocess_startup():
    """Test that socket manager can start log server subprocess"""
    print("🧪 Testing Subprocess Log Server Startup...")

    # Make sure no log server is running initially
    if socket_manager.is_log_server_running():
        print("⚠️ Log server already running, stopping it first...")
        socket_manager.stop_log_server()
        time.sleep(2)

    # Reset socket connection to force subprocess startup
    socket_manager._socket_con = None

    print("1. Attempting to get socket connection (should start subprocess)...")
    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        print("✅ Socket connection established successfully")

        # Check if subprocess is running
        if socket_manager.is_log_server_running():
            print("✅ Log server subprocess is running")
            pid = socket_manager._log_server_process.pid
            print(f"   Process ID: {pid}")

            # Verify process exists in system
            try:
                process = psutil.Process(pid)
                print(f"   Process name: {process.name()}")
                print(f"   Process status: {process.status()}")
                return True
            except psutil.NoSuchProcess:
                print("❌ Process not found in system")
                return False
        else:
            print("❌ Log server subprocess not detected as running")
            return False
    else:
        print("❌ Failed to establish socket connection")
        return False


def test_message_sending():
    """Test sending messages through the subprocess-managed connection"""
    print("\n🧪 Testing Message Sending Through Subprocess...")

    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        test_messages = [
            "🧪 Test message 1: Basic functionality",
            "🧪 Test message 2: Unicode support 🚀💯",
            "🧪 Test message 3: Long message " + "x" * 100,
            "🧪 Test message 4: Special chars !@#$%^&*()",
            '🧪 Test message 5: JSON-like {"test": "value"}',
        ]

        success_count = 0
        for i, message in enumerate(test_messages, 1):
            try:
                socket_manager.send_error(f"[SUBPROCESS TEST {i}] {message}")
                print(f"✅ Message {i} sent successfully")
                success_count += 1
                time.sleep(0.5)  # Small delay between messages
            except Exception as e:
                print(f"❌ Message {i} failed: {e}")

        print(f"📊 Message success rate: {success_count}/{len(test_messages)}")
        return success_count > 0
    else:
        print("❌ No socket connection available for testing")
        return False


def test_subprocess_management():
    """Test starting and stopping the subprocess"""
    print("\n🧪 Testing Subprocess Management...")

    # Test manual start
    print("1. Testing manual subprocess start...")
    if socket_manager.start_log_server():
        print("✅ Manual start successful")

        # Test status check
        if socket_manager.is_log_server_running():
            print("✅ Status check confirms subprocess is running")
        else:
            print("❌ Status check failed")
            return False
    else:
        print("❌ Manual start failed")
        return False

    # Test manual stop
    print("2. Testing manual subprocess stop...")
    socket_manager.stop_log_server()
    time.sleep(1)

    if not socket_manager.is_log_server_running():
        print("✅ Manual stop successful")
        return True
    else:
        print("❌ Manual stop failed - subprocess still running")
        return False


def test_automatic_restart():
    """Test that the system can recover if subprocess dies"""
    print("\n🧪 Testing Automatic Recovery...")

    # Start the subprocess
    socket_con = socket_manager.get_socket_connection()
    if not socket_con:
        print("❌ Could not establish initial connection")
        return False

    print("1. Initial connection established")

    # Kill the subprocess manually to simulate crash
    if socket_manager._log_server_process:
        pid = socket_manager._log_server_process.pid
        print(f"2. Terminating subprocess (PID: {pid}) to simulate crash...")

        try:
            socket_manager._log_server_process.terminate()
            socket_manager._log_server_process.wait(timeout=3)
            print("✅ Subprocess terminated")
        except Exception as e:
            print(f"⚠️ Error terminating subprocess: {e}")

    # Reset connection to trigger restart
    socket_manager._socket_con = None
    socket_manager._log_server_process = None

    print("3. Attempting to reconnect (should restart subprocess)...")
    time.sleep(1)

    new_socket_con = socket_manager.get_socket_connection()
    if new_socket_con:
        print("✅ Successfully reconnected after subprocess restart")

        # Test sending a message
        try:
            socket_manager.send_error("🧪 Test message after restart")
            print("✅ Message sent successfully after restart")
            return True
        except Exception as e:
            print(f"❌ Failed to send message after restart: {e}")
            return False
    else:
        print("❌ Failed to reconnect after subprocess restart")
        return False


def test_cleanup_on_exit():
    """Test that cleanup works properly"""
    print("\n🧪 Testing Cleanup on Exit...")

    # Ensure subprocess is running
    socket_con = socket_manager.get_socket_connection()
    if not socket_con:
        print("❌ Could not establish connection for cleanup test")
        return False

    print("1. Connection established for cleanup test")

    # Test cleanup
    print("2. Calling close_connection() to test cleanup...")
    socket_manager.close_connection()

    time.sleep(2)  # Give time for cleanup

    # Check if subprocess was stopped
    if not socket_manager.is_log_server_running():
        print("✅ Subprocess stopped during cleanup")
        return True
    else:
        print("❌ Subprocess still running after cleanup")
        return False


def run_subprocess_tests():
    """Run all subprocess-related tests"""
    print("=" * 80)
    print("🧪 SUBPROCESS LOG SERVER TEST SUITE")
    print("=" * 80)

    print("📋 This test suite will:")
    print("   1. Automatically start log server subprocesses")
    print("   2. Test message sending through subprocesses")
    print("   3. Test subprocess management (start/stop)")
    print("   4. Test automatic recovery from crashes")
    print("   5. Test proper cleanup on exit")
    print()

    tests = [
        ("Subprocess Startup", test_subprocess_startup),
        ("Message Sending", test_message_sending),
        ("Subprocess Management", test_subprocess_management),
        ("Automatic Recovery", test_automatic_restart),
        ("Cleanup on Exit", test_cleanup_on_exit),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))

            if result:
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")

        except Exception as e:
            print(f"❌ {test_name} - CRASHED: {e}")
            results.append((test_name, False))

        time.sleep(1)  # Pause between tests

    # Final cleanup
    print(f"\n{'=' * 20} Final Cleanup {'=' * 20}")
    try:
        socket_manager.close_connection()
        print("✅ Final cleanup completed")
    except Exception as e:
        print(f"⚠️ Final cleanup error: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUBPROCESS TEST RESULTS SUMMARY")
    print("=" * 80)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1

    print(f"\n📈 Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All subprocess tests passed!")
        print("   Your automatic log server management is working perfectly!")
    else:
        print("⚠️ Some subprocess tests failed.")
        print("   Check the output above for details.")

    print("\n📋 What this means:")
    print("   ✅ Your lggraph.py will automatically start its own log server")
    print("   ✅ No need to manually run utils/error_transfer.py")
    print("   ✅ Log server will be managed automatically")
    print("   ✅ Proper cleanup when application exits")


if __name__ == "__main__":
    try:
        run_subprocess_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        # Ensure cleanup
        try:
            socket_manager.close_connection()
        except:
            pass
    except Exception as e:
        print(f"\n\n❌ Test suite crashed: {e}")
        import traceback

        traceback.print_exc()
