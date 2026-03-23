import pygame

from core.config.constants import TITLE
from core.config.game_settings import settings
from core.gui import Button, Divider, Label
from core.scene import Scene, SceneManager

BG_COLOR = (14, 7, 27)


class MainMenu(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        self.title = Label(TITLE, size=64)
        self.title_div_l = Divider(scale=1.2, style=3, fade=True)
        self.title_div_r = Divider(scale=1.2, style=3, fade=True)
        self.title_div_r.image = pygame.transform.flip(self.title_div_r.image, True, False)
        self.title_w = self.title.rect.width

        self.subtitle = Label("Co-op Platformer", size=24, color=(160, 155, 140))

        self.local_btn = Button(
            "Local Co-op", width=360, height=72, font_size=32, variant="primary"
        )
        self.local_btn.callback = self._on_local

        self.host_btn = Button(
            "Host Party", width=320, height=66, font_size=28, variant="secondary"
        )
        self.host_btn.callback = self._on_host

        self.join_btn = Button(
            "Join Party", width=320, height=66, font_size=28, variant="secondary"
        )
        self.join_btn.callback = self._on_join

        self.sep_div_l = Divider(scale=0.7, style=2, fade=True, color=(120, 115, 100))
        self.sep_div_r = Divider(scale=0.7, style=2, fade=True, color=(120, 115, 100))
        self.sep_div_r.image = pygame.transform.flip(self.sep_div_r.image, True, False)

        self.settings_btn = Button(
            "Settings", width=260, height=58, font_size=24, variant="secondary"
        )
        self.settings_btn.callback = self._on_settings

        self.quit_btn = Button("Quit", width=260, height=58, font_size=24, variant="danger")
        self.quit_btn.callback = self._on_quit

        self.buttons = [
            self.local_btn,
            self.host_btn,
            self.join_btn,
            self.settings_btn,
            self.quit_btn,
        ]
        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.local_btn.set_position(cx, cy - 80)
        self.host_btn.set_position(cx, cy + 10)
        self.join_btn.set_position(cx, cy + 90)
        self.settings_btn.set_position(cx, cy + 200)
        self.quit_btn.set_position(cx, cy + 270)

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _on_local(self) -> None:
        from core.scenes.name_input import LocalNameInput

        self.manager.push(LocalNameInput(self.manager))

    def _on_host(self) -> None:
        from core.scenes.lobby import HostLobby

        self.manager.push(HostLobby(self.manager))

    def _on_join(self) -> None:
        from core.scenes.lobby import JoinLobby

        self.manager.push(JoinLobby(self.manager))

    def _on_settings(self) -> None:
        from core.scenes.settings import Settings

        self.manager.push(Settings(self.manager))

    def _on_quit(self) -> None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        sw, _sh = surface.get_size()
        cx = sw // 2
        cy = _sh // 2

        title_y = cy - 200
        gap = self.title_w // 2 + 130
        self.title_div_l.draw(surface, cx - gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.title_div_r.draw(surface, cx + gap, title_y)
        self.subtitle.draw(surface, cx, title_y + 42)

        self.local_btn.draw(surface)
        self.host_btn.draw(surface)
        self.join_btn.draw(surface)

        sep_y = self.join_btn.rect.bottom + 30
        self.sep_div_l.draw(surface, cx - 80, sep_y)
        self.sep_div_r.draw(surface, cx + 80, sep_y)

        self.settings_btn.draw(surface)
        self.quit_btn.draw(surface)
