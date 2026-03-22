import pygame

from core.config.constants import TITLE
from core.config.game_settings import settings
from core.gui import Button, Divider, Label, Panel
from core.scene import Scene, SceneManager

BG_COLOR = (14, 7, 27)


class MainMenu(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        # Title above panel — with flanking fade dividers
        self.title = Label(TITLE, size=44)
        self.title_div_l = Divider(scale=0.7, style=3, fade=True)
        self.title_div_r = Divider(scale=0.7, style=3, fade=True)
        self.title_div_r.image = pygame.transform.flip(self.title_div_r.image, True, False)
        self.title_w = self.title.rect.width

        self.subtitle = Label("Co-op Platformer", size=16, color=(140, 145, 160))

        # Buttons
        self.play_btn = Button(
            "Play", width=260, height=58, font_size=24, variant="primary",
        )
        self.play_btn.callback = self._on_play

        self.settings_btn = Button(
            "Settings", width=220, height=50, font_size=20, variant="secondary",
        )
        self.settings_btn.callback = self._on_settings

        self.quit_btn = Button(
            "Quit", width=220, height=50, font_size=20, variant="secondary",
        )
        self.quit_btn.callback = self._on_quit

        self.buttons = [self.play_btn, self.settings_btn, self.quit_btn]

        # Divider between play and secondary buttons
        self.btn_divider_l = Divider(scale=0.6, style=2, fade=True)
        self.btn_divider_r = Divider(scale=0.6, style=2, fade=True)
        self.btn_divider_r.image = pygame.transform.flip(self.btn_divider_r.image, True, False)

        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.bg_panel = Panel(420, 280, style=6, transparent=True)
        self.bg_x = (sw - 420) // 2
        self.bg_y = cy - 80

        self.play_btn.set_position(cx, cy - 30)
        self.settings_btn.set_position(cx, cy + 60)
        self.quit_btn.set_position(cx, cy + 130)

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _on_play(self) -> None:
        from core.scenes.gameplay import Gameplay

        self.manager.replace(Gameplay(self.manager))

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

        sw, sh = surface.get_size()
        cx = sw // 2
        cy = sh // 2

        # Title block — above the panel
        title_y = self.bg_y - 50
        gap = self.title_w // 2 + 80
        self.title_div_l.draw(surface, cx - gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.title_div_r.draw(surface, cx + gap, title_y)
        self.subtitle.draw(surface, cx, title_y + 30)

        # Panel with buttons
        self.bg_panel.draw(surface, self.bg_x, self.bg_y)

        self.play_btn.draw(surface)

        # Divider pair between play and secondary buttons
        div_y = cy + 15
        self.btn_divider_l.draw(surface, cx - 60, div_y)
        self.btn_divider_r.draw(surface, cx + 60, div_y)

        self.settings_btn.draw(surface)
        self.quit_btn.draw(surface)
