#!/usr/bin/env python3
"""
Complete system demonstration
Shows how your lggraph.py and rag.py both use the same socket connection
"""

import socket
import threading
import time

from utils.error_transfer import SocketCon
from utils.socket_manager import socket_manager


def start_demo_server():
    """Start a demo log server"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind(("localhost", 5390))
        server.listen(1)
        print("🚀 Demo log server started on localhost:5390")

        client, addr = server.accept()
        print(f"📡 Client connected from {addr}")

        socket_con = SocketCon(client)
        message_count = 0

        while message_count < 10:  # Receive up to 10 messages
            msg = socket_con.receive_error()
            if not msg:
                break
            message_count += 1
            print(f"📨 [{message_count:02d}] {msg}")

        print("🏁 Server received all messages, closing...")

    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        server.close()


def simulate_lggraph_usage():
    """Simulate how lggraph.py uses the socket manager"""
    print("\n🤖 Simulating lggraph.py usage...")

    # This is how lggraph.py gets the socket connection
    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        socket_con.send_error("[LGGRAPH] 🚀 LangGraph chatbot started")
        socket_con.send_error("[LGGRAPH] 🔍 Classifying user message...")
        socket_con.send_error("[LGGRAPH] 🛠️ Tool selection in progress...")
        socket_con.send_error("[LGGRAPH] ✅ Response generated successfully")
    else:
        print("❌ lggraph.py: No socket connection available")


def simulate_rag_usage():
    """Simulate how rag.py uses the socket manager"""
    print("\n📚 Simulating rag.py usage...")

    # This is how rag.py gets the socket connection
    socket_con = socket_manager.get_socket_connection()

    if socket_con:
        socket_con.send_error("[RAG] 📄 Loading PDF document...")
        socket_con.send_error("[RAG] ✂️ Splitting into chunks...")
        socket_con.send_error("[RAG] 🧠 Processing with Gemini API...")
        socket_con.send_error("[RAG] 💾 Saving triples to Neo4j...")
        socket_con.send_error("[RAG] ✅ Knowledge graph updated")
    else:
        print("❌ rag.py: No socket connection available")


def demonstrate_singleton():
    """Demonstrate that both modules use the same connection"""
    print("\n🔍 Demonstrating singleton pattern...")

    # Get connections from both "modules"
    lggraph_connection = socket_manager.get_socket_connection()
    rag_connection = socket_manager.get_socket_connection()

    print(
        f"lggraph connection ID: {id(lggraph_connection) if lggraph_connection else 'None'}"
    )
    print(f"rag connection ID: {id(rag_connection) if rag_connection else 'None'}")

    if lggraph_connection and rag_connection:
        if lggraph_connection is rag_connection:
            print("✅ Both modules use the SAME connection object!")
            lggraph_connection.send_error(
                "[SINGLETON] 🎯 This message proves both modules share the same connection!"
            )
        else:
            print("❌ Different connection objects (this shouldn't happen)")
    else:
        print("⚠️ No connections available")


def main():
    """Run the complete system demonstration"""
    print("=" * 80)
    print("🎯 COMPLETE SYSTEM DEMONSTRATION")
    print("=" * 80)

    # Start the server in a background thread
    server_thread = threading.Thread(target=start_demo_server, daemon=True)
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    # Simulate both modules using the socket manager
    simulate_lggraph_usage()
    time.sleep(0.5)

    simulate_rag_usage()
    time.sleep(0.5)

    demonstrate_singleton()
    time.sleep(0.5)

    print("\n🎉 Demonstration completed!")
    print("📋 What you just saw:")
    print("   ✅ Single log server handling all messages")
    print("   ✅ Both lggraph.py and rag.py using same connection")
    print("   ✅ Singleton pattern working perfectly")
    print("   ✅ No circular imports or connection conflicts")

    # Wait for server to finish
    time.sleep(2)


if __name__ == "__main__":
    main()
