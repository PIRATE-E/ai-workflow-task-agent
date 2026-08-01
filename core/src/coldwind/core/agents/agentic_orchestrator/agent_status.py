# 🎭 User-friendly status updates with funny quotes
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry


class AgentStatusUpdater:
    """Provides user-friendly status updates with funny quotes like Gemini CLI"""

    FUNNY_QUOTES = {
        "initial_planning": [
            " Putting on my thinking cap... Time to break down your request into bite-sized tasks!",
            "🎯 Analyzing your request like a detective with a magnifying glass...",
            "🔍 Dissecting your goal with surgical precision... Don't worry, no anesthesia needed!",
            "📋 Creating a master plan... Even Napoleon would be impressed!",
            "🎨 Crafting a strategy so elegant, it belongs in a museum!",
        ],
        "task_execution": [
            "⚡ Rolling up my sleeves and getting to work... This is where the magic happens!",
            "🛠️ Executing tasks with the precision of a Swiss watch... Tick tock!",
            "🎪 Time for the main event! Let's see what this tool can do...",
            "🚀 Launching into action... Houston, we have liftoff!",
            "⚙️ Turning gears and making things happen... Like a well-oiled machine!",
        ],
        "parameter_generation": [
            "🎛️ Fine-tuning parameters like a DJ mixing the perfect beat...",
            "🧪 Mixing the perfect cocktail of parameters... Shaken, not stirred!",
            "🎯 Calibrating tools with laser precision... Pew pew!",
            "⚗️ Brewing up the perfect parameter potion... *bubble bubble*",
            "🔧 Adjusting knobs and dials... We're going full scientist mode!",
        ],
        "error_recovery": [
            "🩹 Oops! Time to channel my inner surgeon and fix this...",
            "🔄 Plot twist! Let's try a different approach... Adapt and overcome!",
            "🛠️ Houston, we have a problem... But don't worry, I'm like MacGyver with code!",
            "🎭 That didn't go as planned... Time for Plan B (or C, or D)!",
            "🔍 Detective mode activated! Let's solve this mystery...",
        ],
        "task_planning": [
            "📊 Orchestrating tasks like a symphony conductor... Maestro at work!",
            "🎯 Playing task Tetris... Finding the perfect fit for each piece!",
            "🎮 Level up! Moving to the next quest in our adventure...",
            "🧩 Connecting the dots... It's all coming together beautifully!",
            "📈 Managing workflow like a boss... CEO of task execution!",
        ],
        "finalizing": [
            "🎉 Grand finale time! Putting together the masterpiece...",
            "🎭 The curtain falls... Time to reveal what we've accomplished!",
            "📝 Weaving together all the threads into a beautiful tapestry...",
            "🏆 Victory lap! Let's see what we've achieved together...",
            "✨ Ta-da! The moment you've been waiting for...",
        ],
        "complexity_analysis": [
            "🤔 Hmm, is this task simple or does it need the full treatment?",
            "🔬 Putting this under the microscope... Complex or atomic?",
            "⚖️ Weighing the complexity... Simple Simon or rocket science?",
            "🎭 To spawn or not to spawn... That is the question!",
            "🧩 Solving the complexity puzzle... Piece by piece!",
        ],
        "tool_recommendation": [
            "🛍️ Shopping for the perfect tools... Only the finest for you!",
            "🎯 Handpicking tools like a master craftsman choosing their instruments...",
            "🔧 Building the ultimate toolkit... Batman would be jealous!",
            "⚡ Assembling my dream team of tools... Avengers, assemble!",
            "🎪 Selecting the star performers for this show...",
        ],
    }

    @classmethod
    def update_status(cls, category: str, task_id: int = None, extra_info: str = ""):
        """Update user status with funny quotes and request count info"""
        try:
            # The eval listener lives on the active context's listener slot
            # (previously: settings.listeners). The listener itself is a desktop
            # runtime object, accessed through the platform-neutral context.
            eval_listener = ContextRegistry.get().get_listeners().get("eval", None)
            if eval_listener is None:
                return

            # Get a random funny quote for the category
            import random

            quotes = cls.FUNNY_QUOTES.get(category, ["🤖 Working on it..."])
            base_message = random.choice(quotes)

            # Add task info if provided
            if task_id is not None:
                base_message += f" [Task {task_id}]"

            # Add extra info if provided
            if extra_info:
                base_message += f" {extra_info}"

            # Get current request count from OpenAI integration
            from ...utils.open_ai_integration import OpenAIIntegration

            current_requests = OpenAIIntegration.requests_count

            # Format final message with request count
            final_message = f"{base_message} @ API calls: {current_requests}"

            # Update status via the eval listener
            eval_listener.emit_on_variable_change(
                cls,
                "agent_status",
                (
                    eval_listener.get_last_event().meta_data.get("new_value", "")
                    if eval_listener.get_last_event()
                    else ""
                ),
                final_message,
            )

        except Exception as e:
            # Fail silently - status updates shouldn't break the workflow
            debug_warning(
                "Status Updater",
                f"Failed to update status: {e}",
                metadata={
                    "category": category,
                    "task_id": task_id,
                    "extra_info": extra_info,
                },
            )
