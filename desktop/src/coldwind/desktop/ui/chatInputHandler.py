"""
Modern CLI Input Handler with Stylish Autocomplete

Provides a beautiful, Cursor AI/Warp-style input experience with:
- Gradient-style colored prompt
- Stylish autocomplete dropdown
- Command history with auto-suggest
- Tab to accept completion (not cycle)
- Enter while completing → accept completion, not submit
"""

from typing import Iterable
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style

from coldwind.desktop.slash_commands.on_run_time_register import OnRunTimeRegistry


class ChatCompleter(Completer):
    """
    Autocomplete for slash commands.
    """

    def get_completions(
            self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # Get fresh reference to registry each time (it's a singleton)
        registry = OnRunTimeRegistry()

        # Get text before cursor
        text = document.text_before_cursor

        # Only complete if starts with /
        if not text.startswith("/"):
            return

        # Check if registry has commands
        if len(registry) == 0:
            return

        # Get the part after / for matching
        search_text = text[1:].lower()  # Skip the first "/"

        for slash_command in registry:
            cmd_name = slash_command.command.lower()

            # Check if command starts with what user typed
            if cmd_name.startswith(search_text):
                emoji = self._get_command_emoji(slash_command.command)

                yield Completion(
                    text=f"/{slash_command.command}",
                    start_position=-len(text),
                    display=f"{emoji} /{slash_command.command}",
                    display_meta=slash_command.description or "",
                )

    def _get_command_emoji(self, command: str) -> str:
        """Return an emoji for the command type."""
        emojis = {
            'help': '❓',
            'agent': '🤖',
            'clear': '🧹',
            'exit': '👋',
            'chat': '💬',
            'tool': '🔧',
        }
        return emojis.get(command.lower(), '⚡')


# ═══════════════════════════════════════════════════════════════════════════════
#                           MODERN CLI STYLE THEME
# ═══════════════════════════════════════════════════════════════════════════════

MODERN_STYLE = Style.from_dict({
    # Prompt
    'prompt': '#00d4aa bold',

    # Completion menu
    'completion-menu': 'bg:#1a1b26',
    'completion-menu.completion': 'bg:#1a1b26 #a9b1d6',
    'completion-menu.completion.current': 'bg:#7c3aed #ffffff bold',
    'completion-menu.meta.completion': 'bg:#1a1b26 #565f89',
    'completion-menu.meta.completion.current': 'bg:#7c3aed #e0e0e0',

    # Scrollbar
    'scrollbar.background': 'bg:#1a1b26',
    'scrollbar.button': 'bg:#7c3aed',

    # Auto-suggest ghost text
    'auto-suggest': '#4a5568',
})


# ═══════════════════════════════════════════════════════════════════════════════
#                           CUSTOM KEY BINDINGS
# ═══════════════════════════════════════════════════════════════════════════════

def create_key_bindings() -> KeyBindings:
    """
    Create custom key bindings for better autocomplete UX.
    
    TAB Behavior:
    - If dropdown open + suggestion exists → Insert suggestion
    - If dropdown open + NO suggestion → Move to next menu option
    - If NO dropdown + suggestion exists → Insert suggestion
    - If nothing → Start completion

    ENTER Behavior:
    - If dropdown open + option selected → Insert with space (don't submit yet)
    - If dropdown open + nothing selected + suggestion → Submit suggestion
    - If NO dropdown + suggestion exists → Submit suggestion
    - If NO dropdown + no suggestion + has text → Submit text
    """
    kb = KeyBindings()

    @kb.add(Keys.Tab)
    def handle_tab(event):
        """
        Tab key behavior:
        1. Suggestion exists → Insert it (priority!)
        2. Dropdown open, no suggestion → Move to next option
        3. Nothing → Start completion
        """
        buffer = event.app.current_buffer

        # Priority 1: If there's an auto-suggestion, insert it
        if buffer.suggestion:
            buffer.insert_text(buffer.suggestion.text)
            return

        # Priority 2: If dropdown is open
        if buffer.complete_state:
            # Move to next option in the menu
            buffer.complete_next()
            return

        # Priority 3: Nothing is happening, start completion
        buffer.start_completion(select_first=True)

    @kb.add(Keys.Enter)
    def handle_enter(event):
        """
        Enter key behavior:
        1. Dropdown open + item selected → Apply completion + space (continue typing)
        2. Dropdown open + nothing selected → Submit current text
        3. No dropdown + suggestion → Submit (suggestion already in auto-suggest, user sees it)
        4. No dropdown + text exists → Submit
        """
        buffer = event.app.current_buffer

        # Case 1: Dropdown is open
        if buffer.complete_state:
            completion = buffer.complete_state.current_completion
            if completion:
                # Apply the selected completion and add space
                buffer.apply_completion(completion)
                buffer.insert_text(' ')
                return
            else:
                # No item selected, just submit what's there
                buffer.validate_and_handle()
                return

        # Case 2: No dropdown - just submit the input
        buffer.validate_and_handle()


    @kb.add(Keys.Escape)
    def handle_escape(event):
        """Escape closes the completion menu."""
        buffer = event.app.current_buffer
        if buffer.complete_state:
            buffer.cancel_completion()

    @kb.add(Keys.Right)
    def handle_right_arrow(event):
        """
        Right arrow: Accept auto-suggestion if at end of line.
        """
        buffer = event.app.current_buffer

        # If we're at the end and there's a suggestion, accept it
        if buffer.cursor_position == len(buffer.text) and buffer.suggestion:
            buffer.insert_text(buffer.suggestion.text)
        else:
            # Normal right arrow behavior
            buffer.cursor_right()

    return kb


class InputHandler:
    """
    Modern CLI Input Handler with stylish autocomplete.
    Singleton pattern to ensure consistent session.
    """

    _instance = None
    _session = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(InputHandler, cls).__new__(cls)
            cls._instance._init_session()
        return cls._instance

    def _init_session(self):
        """Initialize the PromptSession once."""
        if InputHandler._session is None:
            InputHandler._session = PromptSession(
                completer=ChatCompleter(),
                style=MODERN_STYLE,
                history=InMemoryHistory(),
                auto_suggest=AutoSuggestFromHistory(),
                complete_while_typing=True,
                reserve_space_for_menu=8,
                key_bindings=create_key_bindings(),  # Custom key bindings!
            )

    def get_user_input(self, prompt_text=None, style=None) -> str:
        """
        Get user input with autocomplete.
        
        Usage:
            handler = InputHandler()
            user_input = handler.get_user_input()
            
        Custom prompt:
            user_input = handler.get_user_input("Ask me: ")
        """
        if prompt_text is None and style is None:
            prompt_text = [('class:prompt', 'you ➜ ')]
        elif prompt_text is not None and style is None:
            prompt_text = [('class:prompt', prompt_text)]
        elif prompt_text is None:
            prompt_text = [(style, 'you ➜ ')]

        # If we're not in an interactive terminal, prompt_toolkit can't work reliably.
        if not sys.stdin.isatty():
            try:
                # best-effort plain prompt
                return input('you ➜ ')
            except EOFError:
                return '/exit'

        try:
            return InputHandler._session.prompt(prompt_text)
        except EOFError:
            return '/exit'
        except Exception:
            # prompt_toolkit can throw when terminal state is odd; fall back.
            try:
                return input('you ➜ ')
            except EOFError:
                return '/exit'
