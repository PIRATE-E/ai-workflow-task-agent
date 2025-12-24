#!/usr/bin/env python3
"""
Test script to demonstrate the system_logging system
Run this after starting the log server: python utils/error_transfer.py
"""

import os
import sys
import time

# Add the project root to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.socket_manager import socket_manager


def test_logging():
    """Test the socket-based system_logging system"""
    print("🧪 Testing the system_logging system...")

    # Get the socket connection
    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        print("✅ Connected to log server!")

        # Send some test messages
        messages = [
            "🚀 Application started",
            "📊 Processing data...",
            "⚠️ Warning: This is a test warning",
            "❌ Error: This is a test error",
            "💾 Saving data to database...",
            "🔍 Searching knowledge graph...",
            "🌐 Making web request...",
            "✅ Process completed successfully",
        ]

        print(f"📤 Sending {len(messages)} test messages to log server...")

        for i, message in enumerate(messages, 1):
            print(f"  Sending message {i}/{len(messages)}: {message[:30]}...")
            socket_con.send_error(f"[TEST {i:02d}] {message}")
            time.sleep(0.5)  # Wait 0.5 seconds between messages

        print("✅ All test messages sent!")
        print("📋 Check the log server terminal to see the received messages")

    else:
        print("❌ Could not connect to log server")
        print("📝 Instructions:")
        print("   1. First run: python utils/error_transfer.py")
        print("   2. Then run this test again")
        print("   3. Check your config.py for ENABLE_SOCKET_LOGGING=true")


def test_error_scenarios():
    """Test various error scenarios"""
    print("\n🧪 Testing error scenarios...")

    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        error_scenarios = [
            "FileNotFoundError: Could not find config.json",
            "ConnectionError: Failed to connect to Neo4j database",
            "TimeoutError: RAG search timed out after 30 seconds",
            "ValueError: Invalid JSON format in API response",
            "MemoryError: Not enough memory to process large document",
            "KeyError: Missing required field 'cypher_query' in response",
        ]

        print(f"📤 Sending {len(error_scenarios)} error scenarios...")

        for i, error in enumerate(error_scenarios, 1):
            print(f"  Sending error {i}/{len(error_scenarios)}: {error[:40]}...")
            socket_con.send_error(f"[ERROR {i:02d}] {error}")
            time.sleep(0.3)

        print("✅ All error scenarios sent!")
    else:
        print("❌ Could not connect to log server for error testing")


def test_socket_manager_singleton():
    """Test that socket manager follows singleton pattern"""
    print("\n🧪 Testing singleton pattern...")

    # Create multiple instances
    manager1 = socket_manager
    manager2 = socket_manager.__class__()

    # They should be the same object
    if manager1 is manager2:
        print("✅ Singleton pattern working correctly")
        if manager1.get_socket_connection():
            manager1.send_error(
                "[SINGLETON TEST] Both managers use the same connection"
            )
    else:
        print("❌ Singleton pattern failed - different objects created")


def run_all_tests():
    """Run all system_logging system tests"""
    print("=" * 60)
    print("🧪 LOGGING SYSTEM TEST SUITE")
    print("=" * 60)

    test_logging()
    test_error_scenarios()
    test_socket_manager_singleton()

    print("\n" + "=" * 60)
    print("✅ TEST SUITE COMPLETED")
    print("=" * 60)
    print("\n📋 Instructions:")
    print("   1. Make sure log server is running: python utils/error_transfer.py")
    print("   2. Check the server terminal for all received messages")
    print("   3. Verify that messages appear in chronological order")


if __name__ == "__main__":
    run_all_tests()
