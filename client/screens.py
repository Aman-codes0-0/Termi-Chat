from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Static, Label, ListView, ListItem
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
                        self.app.push_screen("main_chat")
                    else:
                        error_label.update(f"[red]{response.json().get('detail', 'Login failed')}[/red]")
            except Exception as e:
                error_label.update(f"[red]Error connecting to server: {e}[/red]")

class MainChatScreen(Screen):
    BINDINGS = [
        ("s", "app.push_screen('search_users')", "Search Users"),
        ("p", "app.push_screen('pending_requests')", "Pending Requests"),
        ("r", "refresh_friends", "Refresh"),
        ("ctrl+e", "app.push_screen('emoji_picker')", "Emoji"),
        ("ctrl+t", "app.push_screen('theme_selection')", "Themes")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            # Sidebar for friends
            with Vertical(id="sidebar"):
                yield Static("Friends List", id="sidebar-title")
                yield ListView(id="friends-list")
                yield Static("[S] Search | [P] Pending", id="sidebar-hints")
                yield Static("", id="selection-error")
            
            # Main Chat Area
            with Vertical(id="chat-area"):
                yield Static("Select a friend to chat", id="chat-header")
                yield VerticalScroll(id="chat-messages")
                with Horizontal(id="input-container"):
                    yield Input(placeholder="Type a message... (Ctrl+E Emoji)", id="message-input", disabled=True)
                    yield Button("Send", id="btn-send", variant="primary", disabled=True)
                    yield Button("Attach", id="btn-attach", variant="warning", disabled=True)
                yield Label("[Ctrl+E] Emoji | [Ctrl+T] Themes", id="shortcut-hint")
        yield Footer()

    async def on_mount(self) -> None:
        self.message_list = self.query_one("#chat-messages", VerticalScroll)
        self.chat_header = self.query_one("#chat-header", Static)
        self.msg_input = self.query_one("#message-input", Input)
        self.btn_send = self.query_one("#btn-send", Button)
        self.btn_attach = self.query_one("#btn-attach", Button)
        await self.action_refresh_friends()

    async def action_refresh_friends(self) -> None:
        list_view = self.query_one("#friends-list", ListView)
        error_label = self.query_one("#selection-error", Static)
        
        # Keep track of currently selected index to restore it if possible
        current_index = list_view.index
        list_view.clear()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/friends",
                    headers={"Authorization": f"Bearer {self.app.token}"}
                )
                if response.status_code == 200:
                    friends = response.json().get("friends", [])
                    if not friends:
                        error_label.update("No friends yet.")
                    else:
                        error_label.update("")
                        for friend_obj in friends:
                            if isinstance(friend_obj, str):
                                friend = friend_obj
                                is_online = False
                                unread = 0
                            else:
                                friend = friend_obj.get("username")
                                is_online = friend_obj.get("is_online", False)
                                unread = friend_obj.get("unread_count", 0)
                                
                            if not friend: continue
                            
                            # Highlight the active friend
                            prefix = "💬 " if friend == self.app.target_username else "👤 "
                            status = "🟢" if is_online else "🔴"
                            
                            label_text = f"{status} {prefix}{friend}"
                            if unread > 0 and friend != self.app.target_username:
                                label_text += f" [bold red]({unread})[/bold red]"
                                
                            list_view.append(ListItem(Label(label_text), id=f"friend-{friend}"))
                        
                        # Restore selection if it's still valid
                        if current_index is not None and current_index < len(friends):
                            list_view.index = current_index
                else:
                    error_label.update(f"[red]Failed to load friends[/red]")
        except Exception as e:
            error_label.update(f"[red]Error: {e}[/red]")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item.id or not event.item.id.startswith("friend-"):
            return
            
        target_username = event.item.id.replace("friend-", "")
        
        # Don't reconnect if clicking the same user
        if target_username == self.app.target_username:
            return
            
        # Disconnect previous websocket if exists
        if self.app.ws_client:
            await self.app.ws_client.disconnect()
            self.app.ws_client = None
            
        self.app.target_username = target_username
        self.chat_header.update(f"Chatting with: {target_username}")
        self.message_list.remove_children()
        
        # Enable inputs
        self.msg_input.disabled = False
        self.btn_send.disabled = False
        self.btn_attach.disabled = False
        self.msg_input.focus()
        
        await self.app.connect_websocket()
        await self.action_refresh_friends() # Refresh to show active icon

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "message-input":
            current_value = event.value
            new_value = current_value
            for code, emoji in EMOJI_MAP.items():
                if code in new_value:
                    new_value = new_value.replace(code, emoji)
            
            if new_value != current_value:
                event.input.value = new_value
                event.input.cursor_position = len(new_value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-send":
            await self.send_message()
        elif event.button.id == "btn-attach":
            self.app.push_screen(FileAttachScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "message-input":
            await self.send_message()

    async def send_message(self):
        if not self.app.ws_client or not self.app.target_username:
            return
        message_text = self.msg_input.value
        if message_text:
            await self.app.ws_client.send_message({
                "type": "text",
                "text": message_text
            })
            self.msg_input.value = ""

    def add_message(self, sender: str, text: str, time: str, msg_type: str = "text", file_id: str = None, filename: str = None):
        is_self = sender == self.app.username
        new_msg = MessageWidget(sender, text, time, msg_type, file_id, filename, is_self)
        self.message_list.mount(new_msg)
        new_msg.scroll_visible()

class SearchUsersScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="search-container"):
            yield Static("Search for Users to Add", id="title")
            yield Input(placeholder="Type username and press Enter...", id="search-input")
            yield ListView(id="search-results-list")
            yield Static("", id="search-message")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            query = event.value.strip()
            if len(query) < 2: return
            
            list_view = self.query_one("#search-results-list", ListView)
            msg_label = self.query_one("#search-message", Static)
            list_view.clear()
            msg_label.update("Searching...")
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:8000/search-users?q={query}",
                        headers={"Authorization": f"Bearer {self.app.token}"}
                    )
                    if response.status_code == 200:
                        results = response.json().get("results", [])
                        if not results:
                            msg_label.update("No users found.")
                        else:
                            msg_label.update("Select a user to send a friend request.")
                            for res in results:
                                if res != self.app.username:
                                    list_view.append(ListItem(Label(f"✉️ {res}"), id=f"search-{res}"))
                    else:
                        msg_label.update(f"[red]Search failed[/red]")
            except Exception as e:
                msg_label.update(f"[red]Error: {e}[/red]")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id and event.item.id.startswith("search-"):
            target_user = event.item.id.replace("search-", "")
            msg_label = self.query_one("#search-message", Static)
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/send-request",
                        json={"to_user": target_user},
                        headers={"Authorization": f"Bearer {self.app.token}"}
                    )
                    if response.status_code == 200:
                        msg_label.update(f"[green]Request sent to {target_user}![/green]")
                    else:
                        msg_label.update(f"[red]Failed to send request[/red]")
            except Exception as e:
                msg_label.update(f"[red]Error: {e}[/red]")

class PendingRequestsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("r", "refresh_requests", "Refresh")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="pending-container"):
            yield Static("Pending Friend Requests", id="title")
            yield ListView(id="pending-list")
            yield Static("", id="pending-message")
        yield Footer()

    async def on_mount(self) -> None:
        await self.action_refresh_requests()

    async def action_refresh_requests(self) -> None:
        list_view = self.query_one("#pending-list", ListView)
        msg_label = self.query_one("#pending-message", Static)
        list_view.clear()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/pending-requests",
                    headers={"Authorization": f"Bearer {self.app.token}"}
                )
                if response.status_code == 200:
                    requests = response.json().get("requests", [])
                    if not requests:
                        msg_label.update("No pending requests.")
                    else:
                        msg_label.update("Select a user to accept their request.")
                        for req in requests:
                            list_view.append(ListItem(Label(f"✅ Accept: {req}"), id=f"req-{req}"))
                else:
                    msg_label.update(f"[red]Failed to load requests[/red]")
        except Exception as e:
            msg_label.update(f"[red]Error: {e}[/red]")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id and event.item.id.startswith("req-"):
            requester = event.item.id.replace("req-", "")
            msg_label = self.query_one("#pending-message", Static)
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/accept-request",
                        json={"requester": requester},
                        headers={"Authorization": f"Bearer {self.app.token}"}
                    )
                    if response.status_code == 200:
                        msg_label.update(f"[green]Accepted request from {requester}![/green]")
                        await self.action_refresh_requests() # Refresh list
                    else:
                        msg_label.update(f"[red]Failed to accept[/red]")
            except Exception as e:
                msg_label.update(f"[red]Error: {e}[/red]")

EMOJI_MAP = {
    ":smile:": "😀", ":laugh:": "😂", ":rofl:": "🤣", ":blush:": "😊",
    ":cool:": "😎", ":heart_eyes:": "😍", ":kiss:": "😘", ":thinking:": "🤔",
    ":neutral:": "😐", ":sleeping:": "😴", ":rage:": "😡", ":thumb:": "👍",
    ":ok:": "👌", ":heart:": "❤️", ":fire:": "🔥", ":rocket:": "🚀",
    ":tada:": "🎉", ":star:": "⭐", ":100:": "💯"
}

# ChatScreen has been merged into MainChatScreen
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
