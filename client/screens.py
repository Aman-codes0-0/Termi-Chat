from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Static, RichLog, Label
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.message import Message
import httpx

class MessageWidget(Static):
    """A widget representing a single chat message."""
    def __init__(self, sender: str, text: str, time: str, msg_type: str = "text", file_id: str = None, filename: str = None, is_self: bool = False):
        self.sender_name = sender
        self.text = text
        self.time = time
        self.msg_type = msg_type
        self.file_id = file_id
        self.filename = filename
        self.is_self = is_self
        
        # Safety: If text looks like JSON, it means something went wrong in parsing
        if text.startswith("{") and "text" in text:
            import json
            try:
                parsed = json.loads(text)
                self.text = parsed.get("text", text)
                self.msg_type = parsed.get("type", self.msg_type)
                self.file_id = parsed.get("file_id", self.file_id)
                self.filename = parsed.get("filename", self.filename)
            except:
                pass
        super().__init__()

    def compose(self) -> ComposeResult:
        color = "green" if self.is_self else "cyan"
        if self.sender_name == "System":
            color = "yellow"
            
        with Horizontal(classes="message-row"):
            yield Label(f"[[dim]{self.time}[/dim]] [{color}]{self.sender_name}[/{color}]: ", classes="message-meta")
            if self.msg_type == "text":
                yield Label(self.text, classes="message-text")
            else:
                yield Label(f"📁 {self.filename}", classes="file-label")
                yield Button("Download", id=f"dl-{self.file_id}", classes="btn-download")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith("dl-"):
            self.app.download_file(self.file_id, self.filename)

class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="login-container"):
            yield Static("Welcome to TUI Chat!", id="title")
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            with Horizontal(id="button-container"):
                yield Button("Login", id="btn-login", variant="primary")
                yield Button("Register", id="btn-register")
            yield Static("", id="error-message")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        error_label = self.query_one("#error-message", Static)
        
        if not username or not password:
            error_label.update("Please enter username and password")
            return

        if event.button.id == "btn-register":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post("http://localhost:8000/register", json={"username": username, "password": password})
                    if response.status_code == 200:
                        error_label.update("[green]Registration successful! Please login.[/green]")
                    else:
                        error_label.update(f"[red]{response.json().get('detail', 'Registration failed')}[/red]")
            except Exception as e:
                error_label.update(f"[red]Error connecting to server: {e}[/red]")
        
        elif event.button.id == "btn-login":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post("http://localhost:8000/login", json={"username": username, "password": password})
                    if response.status_code == 200:
                        data = response.json()
                        self.app.token = data.get("access_token")
                        self.app.username = username
                        self.app.set_theme(data.get("theme", "default"))
                        self.app.push_screen("chat_selection")
                    else:
                        error_label.update(f"[red]{response.json().get('detail', 'Login failed')}[/red]")
            except Exception as e:
                error_label.update(f"[red]Error connecting to server: {e}[/red]")

class ChatSelectionScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="selection-container"):
            yield Static("Who do you want to chat with?", id="title")
            yield Input(placeholder="Target Username", id="target-username")
            yield Button("Start Chat", id="btn-start-chat", variant="success")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        target_username = self.query_one("#target-username", Input).value
        if target_username:
            self.app.target_username = target_username
            await self.app.connect_websocket()
            self.app.push_screen("chat")

EMOJI_MAP = {
    ":smile:": "😀", ":laugh:": "😂", ":rofl:": "🤣", ":blush:": "😊",
    ":cool:": "😎", ":heart_eyes:": "😍", ":kiss:": "😘", ":thinking:": "🤔",
    ":neutral:": "😐", ":sleeping:": "😴", ":rage:": "😡", ":thumb:": "👍",
    ":ok:": "👌", ":heart:": "❤️", ":fire:": "🔥", ":rocket:": "🚀",
    ":tada:": "🎉", ":star:": "⭐", ":100:": "💯"
}

class ChatScreen(Screen):
    BINDINGS = [
        ("ctrl+e", "app.push_screen('emoji_picker')", "Emoji"),
        ("ctrl+t", "app.push_screen('theme_selection')", "Themes")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield VerticalScroll(id="chat-messages")
            with Horizontal(id="input-container"):
                yield Input(placeholder="Type a message... (Ctrl+E for Emoji)", id="message-input")
                yield Button("Send", id="btn-send", variant="primary")
                yield Button("Attach", id="btn-attach", variant="warning")
            yield Label("[Ctrl+E] Emoji | [Ctrl+T] Themes", id="shortcut-hint")
        yield Footer()

    async def on_mount(self) -> None:
        self.message_list = self.query_one("#chat-messages", VerticalScroll)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Replace shortcodes like :smile: with emojis in real-time."""
        if event.input.id == "message-input":
            current_value = event.value
            new_value = current_value
            for code, emoji in EMOJI_MAP.items():
                if code in new_value:
                    new_value = new_value.replace(code, emoji)
            
            if new_value != current_value:
                event.input.value = new_value
                # Keep cursor at the end
                event.input.cursor_position = len(new_value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-send":
            await self.send_message()
        elif event.button.id == "btn-attach":
            self.app.push_screen(FileAttachScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.send_message()

    async def send_message(self):
        input_widget = self.query_one("#message-input", Input)
        message_text = input_widget.value
        if message_text:
            await self.app.ws_client.send_message({
                "type": "text",
                "text": message_text
            })
            input_widget.value = ""

    def add_message(self, sender: str, text: str, time: str, msg_type: str = "text", file_id: str = None, filename: str = None):
        is_self = sender == self.app.username
        new_msg = MessageWidget(sender, text, time, msg_type, file_id, filename, is_self)
        self.message_list.mount(new_msg)
        new_msg.scroll_visible()

class FileAttachScreen(Screen):
    """A simple screen to input the path of a file to attach."""
    def compose(self) -> ComposeResult:
        with Vertical(id="attach-container"):
            yield Static("Enter File Path to Attach", id="title")
            yield Input(placeholder="/path/to/your/file.jpg", id="file-path")
            with Horizontal(id="button-container"):
                yield Button("Send File", id="btn-send-file", variant="success")
                yield Button("Cancel", id="btn-cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-send-file":
            path = self.query_one("#file-path", Input).value
            if path:
                self.app.pop_screen()
                await self.app.upload_file(path)
        else:
            self.app.pop_screen()
