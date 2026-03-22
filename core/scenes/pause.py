import pygame

from core.config.game_settings import settings
from core.gui import Button, Divider, Label, Panel
from core.scene import Scene, SceneManager


class Pause(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        self.title = Label("Paused", size=30)
        self.divider_left = Divider(scale=0.6, style=3, fade=True)
        self.divider_right = Divider(scale=0.6, style=3, fade=True)
        self.divider_right.image = pygame.transform.flip(self.divider_right.image, True, False)

        self.resume_btn = Button("Resume", width=230, height=54, font_size=22, variant="primary")
        self.resume_btn.callback = self._on_resume

        self.settings_btn = Button(
            "Settings", width=200, height=48, font_size=20, variant="secondary"
        )
        self.settings_btn.callback = self._on_settings

        self.quit_btn = Button("Quit to Menu", width=200, height=48, font_size=18, variant="danger")
        self.quit_btn.callback = self._on_quit

        self.buttons = [self.resume_btn, self.settings_btn, self.quit_btn]
        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.bg_panel = Panel(380, 340, style=6, transparent=True)
        self.bg_x = (sw - 380) // 2
        self.bg_y = cy - 170

        self.resume_btn.set_position(cx, cy - 30)
        self.settings_btn.set_position(cx, cy + 40)
        self.quit_btn.set_position(cx, cy + 110)

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _on_resume(self) -> None:
        self.manager.pop()

    def _on_settings(self) -> None:
        from core.scenes.settings import Settings

        self.manager.push(Settings(self.manager))

    def _on_quit(self) -> None:
        from core.scenes.main_menu import MainMenu

        self.manager.stack.clear()
        self.manager.push(MainMenu(self.manager))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_resume()
            return
        for btn in self.buttons:
            btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        cx = sw // 2
        title_y = self.bg_y + 50

        self.bg_panel.draw(surface, self.bg_x, self.bg_y)
        title_gap = self.title.rect.width // 2 + 70
        self.divider_left.draw(surface, cx - title_gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.divider_right.draw(surface, cx + title_gap, title_y)

        for btn in self.buttons:
            btn.draw(surface)
