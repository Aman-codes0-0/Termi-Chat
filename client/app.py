from textual.app import App
from screens import LoginScreen, MainChatScreen, SearchUsersScreen, PendingRequestsScreen
from theme_screen import ThemeSelectionScreen
from emoji_screen import EmojiPickerScreen
from websocket_handler import WebSocketClient, ChatMessageReceived

class TUIChatApp(App):
    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("ctrl+t", "push_screen('theme_selection')", "Themes"),
        ("ctrl+e", "push_screen('emoji_picker')", "Emoji")
    ]
    
    SCREENS = {
        "login": LoginScreen,
        "main_chat": MainChatScreen,
        "theme_selection": ThemeSelectionScreen,
        "emoji_picker": EmojiPickerScreen,
        "search_users": SearchUsersScreen,
        "pending_requests": PendingRequestsScreen
    }
    
    def __init__(self):
        super().__init__()
        self.token = None
        self.username = None
        self.target_username = None
        self.ws_client = None
        self.current_theme = "default"

    def set_theme(self, theme_name: str) -> None:
        """Switch the application theme by changing the CSS class on the App."""
        if self.current_theme != "default":
            self.remove_class(f"theme-{self.current_theme}")
        
        self.current_theme = theme_name
        
        if theme_name != "default":
            self.add_class(f"theme-{theme_name}")

    async def save_theme_to_server(self, theme_name: str) -> None:
        """Call the API to persist the theme preference for the user."""
        import httpx
        if self.token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "http://localhost:8000/update-theme",
                        json={"theme": theme_name},
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
            except Exception as e:
                self.log(f"Failed to save theme: {e}")

    async def upload_file(self, file_path: str) -> None:
        """Upload a local file to the server and broadcast its info."""
        import httpx
        import os
        if not os.path.exists(file_path):
            self.notify("File not found!", severity="error")
            return

        filename = os.path.basename(file_path)
        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f)}
                    response = await client.post(
                        "http://localhost:8000/upload",
                        files=files,
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=60.0
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    await self.ws_client.send_message({
                        "type": "file",
                        "file_id": data["file_id"],
                        "filename": data["filename"],
                        "text": f"sent a file: {data['filename']}"
                    })
                else:
                    self.notify(f"Upload failed: {response.text}", severity="error")
        except Exception as e:
            self.notify(f"Error uploading file: {e}", severity="error")

    async def download_file(self, file_id: str, filename: str) -> None:
        """Download a file from the server and save it locally."""
        import httpx
        import os
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/download/{file_id}", timeout=60.0)
                if response.status_code == 200:
                    # Save to current directory
                    save_path = os.path.join(os.getcwd(), filename)
                    # Handle duplicate filenames
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(save_path):
                        save_path = os.path.join(os.getcwd(), f"{base}_{counter}{ext}")
                        counter += 1
                        
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    self.notify(f"File downloaded to {os.path.basename(save_path)}", severity="information")
                else:
                    self.notify(f"Download failed: {response.text}", severity="error")
        except Exception as e:
            self.notify(f"Error downloading file: {e}", severity="error")

    def on_mount(self) -> None:
        self.push_screen("login")
        # Start a background polling timer every 5 seconds
        self.set_interval(5.0, self.poll_updates)

    async def poll_updates(self) -> None:
        if not self.token: return
        
        # Only poll if we are on MainChatScreen
        if isinstance(self.screen, MainChatScreen):
            await self.screen.action_refresh_friends()
            # We could also check pending requests and notify the user
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "http://localhost:8000/pending-requests",
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
                    if response.status_code == 200:
                        reqs = response.json().get("requests", [])
                        if reqs:
                            error_label = self.screen.query_one("#selection-error")
                            if not error_label.renderable:  # Only overwrite if no other error
                                error_label.update(f"[yellow]You have {len(reqs)} pending request(s)! Press 'P' to view.[/yellow]")
            except Exception:
                pass

    async def connect_websocket(self):
        self.ws_client = WebSocketClient(self, self.token, self.target_username)
        success = await self.ws_client.connect()
        if not success:
            self.notify("Failed to connect to chat server", severity="error")

    def on_chat_message_received(self, message: ChatMessageReceived) -> None:
        if isinstance(self.screen, MainChatScreen):
            self.screen.add_message(
                message.sender, 
                message.text, 
                message.time, 
                message.msg_type, 
                message.file_id, 
                message.filename
            )


    async def on_unmount(self) -> None:
        if self.ws_client:
            await self.ws_client.disconnect()

if __name__ == "__main__":
    app = TUIChatApp()
    app.run()
