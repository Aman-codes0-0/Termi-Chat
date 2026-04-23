from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Input
from textual.containers import Vertical, Horizontal, Grid, Center

EMOJI_DATA = [
    ("😀", ":smile:"), ("😂", ":laugh:"), ("🤣", ":rofl:"), ("😊", ":blush:"),
    ("😎", ":cool:"), ("😍", ":heart_eyes:"), ("🥰", ":smiling_face_with_3_hearts:"), ("😘", ":kiss:"),
    ("🤔", ":thinking:"), ("🤨", ":raised_eyebrow:"), ("😐", ":neutral:"), ("😑", ":expressionless:"),
    ("🙄", ":rolling_eyes:"), ("😏", ":smirk:"), ("😮", ":open_mouth:"), ("😴", ":sleeping:"),
    ("🤢", ":nauseated:"), ("🤮", ":vomit:"), ("😡", ":rage:"), ("🥺", ":pleading:"),
    ("👍", ":thumb:"), ("👎", ":thumbsdown:"), ("👌", ":ok:"), ("✌️", ":peace:"),
    ("👊", ":punch:"), ("👏", ":clap:"), ("🙌", ":raised_hands:"), ("🙏", ":pray:"),
    ("❤️", ":heart:"), ("💔", ":broken_heart:"), ("🔥", ":fire:"), ("✨", ":sparkles:"),
    ("🚀", ":rocket:"), ("💯", ":100:"), ("🎉", ":tada:"), ("🎁", ":gift:"),
    ("⭐", ":star:"), ("🌟", ":glowing_star:"), ("☁️", ":cloud:"), ("☀️", ":sun:"),
]

class EmojiPickerScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="emoji-container"):
                yield Static("Pick an Emoji", id="title")
                with Grid(id="emoji-grid"):
                    for emoji, code in EMOJI_DATA:
                        yield Button(emoji, id=f"emoji-{code[1:-1]}", classes="emoji-btn")
                yield Button("Close", id="btn-close-emoji", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-emoji":
            self.app.pop_screen()
        elif event.button.id.startswith("emoji-"):
            emoji_char = str(event.button.label)
            # Find the active input and append the emoji
            chat_screen = self.app.get_screen("chat")
            try:
                input_widget = chat_screen.query_one("#message-input", Input)
                input_widget.value += emoji_char
                input_widget.focus()
            except:
                pass
            self.app.pop_screen()

# Add missing import for Input in screens.py later
