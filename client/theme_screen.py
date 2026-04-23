from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, Static, Button
from textual.containers import Vertical, Center
from textual.widgets.option_list import Option

class ThemeSelectionScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    THEMES = [
        ("Default Cyan", "default"),
        ("Dracula", "dracula"),
        ("Nord", "nord"),
        ("Gruvbox", "gruvbox"),
        ("Monokai", "monokai"),
        ("Solarized Dark", "solarized-dark"),
        ("Solarized Light", "solarized-light"),
        ("Midnight", "midnight"),
        ("Emerald", "emerald"),
        ("Crimson", "crimson"),
        ("Lavender", "lavender"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="theme-container"):
                yield Static("Select a Theme", id="title")
                yield OptionList(
                    *[Option(label, id=theme_id) for label, theme_id in self.THEMES],
                    id="theme-list"
                )
                yield Button("Close", id="btn-close", variant="primary")
        yield Footer()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        theme_id = event.option.id
        self.app.set_theme(theme_id)
        await self.app.save_theme_to_server(theme_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.app.pop_screen()
