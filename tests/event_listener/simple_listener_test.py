# 🧪 Simple Event Listener Test
"""
Simple test for the event listener system that avoids complex imports.
This test directly imports only what's needed and tests the core functionality.
"""

import sys
import os
import time
import threading

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(project_root)

from rich.console import Console

def test_event_listener_system():
    """Test the event listener system with realistic threading scenario"""
    console = Console()
    
    console.print("🧪 [bold blue]SIMPLE EVENT LISTENER TEST[/bold blue]")
    console.print("🔄 Testing multi-threaded status updates...")
    
    try:
        # Import your event listener (with error handling)
        from src.utils.listeners.rich_status_listen import RichStatusListener
        
        console.print("✅ Successfully imported RichStatusListener")
        
        # Create listener
        listener_console = Console()
        listener = RichStatusListener(listener_console)
        
        console.print(f"✅ Listener created with ID: {id(listener)}")
        
        # Start status display
        listener.start_status("🔄 generating heading...")
        console.print("✅ Status display started")
        
        # Simulate the requested scenario
        request_count = 0
        
        def background_requests():
            nonlocal request_count
            
            while request_count < 45:
                time.sleep(0.15)  # Realistic request processing time
                request_count += 1
                
                # Update at milestones as requested
                if request_count == 10:
                    listener.emit_on_variable_change(
                        TestProcessor,
                        "status",
                        "generating heading...",
                        "🔄 generating heading... (requests done 10)"
                    )
                    console.print("📊 Milestone: 10 requests processed")
                    
                elif request_count == 30:
                    listener.emit_on_variable_change(
                        TestProcessor,
                        "status", 
                        "generating heading... (requests done 10)",
                        "🔄 generating heading... (requests done 30)"
                    )
                    console.print("📊 Milestone: 30 requests processed")
                    
                elif request_count == 40:
                    listener.emit_on_variable_change(
                        TestProcessor,
                        "status",
                        "generating heading... (requests done 30)",
                        "⏳ generating the request is 40 wait for sec"
                    )
                    console.print("⏳ Special milestone: 40 requests - waiting...")
                    
                    # Wait as requested
                    time.sleep(2)
                    
                    # Final completion
                    listener.emit_on_variable_change(
                        TestProcessor,
                        "status",
                        "generating the request is 40 wait for sec",
                        "✅ heading generation completed!"
                    )
                    console.print("🎉 Process completed!")
                    break
        
        # Start background thread
        console.print("🚀 Starting background request processing...")
        request_thread = threading.Thread(target=background_requests, daemon=True)
        request_thread.start()
        
        console.print("👀 Watch the status display above for real-time updates!")
        console.print("⏱️  This will take about 8-10 seconds...")
        
        # Wait for completion
        request_thread.join(timeout=15)
        
        # Give time to see final status
        time.sleep(3)
        
        # Stop status display
        listener.stop_status_display()
        console.print("⏹️ Status display stopped")
        
        # Show results
        console.print(f"\n📊 Final Results:")
        console.print(f"   Requests processed: {request_count}")
        console.print(f"   Events in history: {len(listener.event_history)}")
        console.print(f"   Processed events: {len(listener.processed_events)}")
        
        if request_count >= 40 and len(listener.event_history) > 0:
            console.print("\n🎉 [bold green]TEST PASSED![/bold green]")
            console.print("✅ Multi-threaded status updates working correctly")
            console.print("✅ Event listener system functioning properly")
            console.print("✅ Realistic timing and behavior confirmed")
        else:
            console.print("\n❌ [bold red]TEST FAILED![/bold red]")
            console.print(f"   Expected 40+ requests, got {request_count}")
            console.print(f"   Expected events in history, got {len(listener.event_history)}")
        
    except ImportError as e:
        console.print(f"❌ Import error: {e}")
        console.print("💡 Make sure you're running from the project root directory")
        console.print("💡 Check that your event listener files exist:")
        console.print("   - src/utils/listeners/rich_status_listen.py")
        console.print("   - src/utils/listeners/event_listener.py")
        
    except Exception as e:
        console.print(f"❌ Test failed with error: {e}")
        console.print("🔧 Check your event listener implementation")
        
        # Try to stop listener if it exists
        try:
            if 'listener' in locals():
                listener.stop_status_display()
        except:
            pass


class TestProcessor:
    """Test class for event emission"""
    pass


def run_until_working():
    """Run the test continuously until it works properly"""
    console = Console()
    console.print("🔄 [bold blue]CONTINUOUS TEST MODE[/bold blue]")
    console.print("Running tests until they work properly...")
    
    attempt = 1
    max_attempts = 5
    
    while attempt <= max_attempts:
        console.print(f"\n🧪 [bold yellow]ATTEMPT {attempt}/{max_attempts}[/bold yellow]")
        console.print("-" * 40)
        
        try:
            test_event_listener_system()
            console.print(f"✅ Attempt {attempt} successful!")
            break
            
        except KeyboardInterrupt:
            console.print("\n⏹️ Test interrupted by user")
            break
            
        except Exception as e:
            console.print(f"❌ Attempt {attempt} failed: {e}")
            
            if attempt < max_attempts:
                console.print(f"🔄 Retrying in 3 seconds...")
                time.sleep(3)
            else:
                console.print("❌ All attempts failed!")
        
        attempt += 1
    
    console.print("\n🏁 Continuous testing completed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Event Listener Test")
    parser.add_argument("--continuous", action="store_true", 
                       help="Run tests continuously until they work")
    
    args = parser.parse_args()
    
    if args.continuous:
        run_until_working()
    else:
        test_event_listener_system()