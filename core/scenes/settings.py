import pygame

from core.config.game_settings import settings
from core.gui import Button, Divider, Label, Panel, Slider, Toggle
from core.scene import Scene, SceneManager


class Settings(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        self.title = Label("Settings", size=32)
        self.divider_top = Divider(scale=0.7, style=3, fade=True)
        self.divider_bottom = Divider(scale=0.7, style=3, fade=True)
        self.divider_bottom.image = pygame.transform.flip(self.divider_bottom.image, True, False)

        self.fullscreen_label = Label("Fullscreen", size=18)
        self.fullscreen_toggle = Toggle(width=70, height=36, active=settings.is_fullscreen, style=6)
        self.fullscreen_toggle.on_change = self._on_fullscreen

        self.resolutions = [(1280, 720), (1920, 1080), (800, 600)]
        self.res_index = next(
            (i for i, r in enumerate(self.resolutions) if r == settings.screen_size), 0
        )
        self.res_label = Label("Resolution", size=18)
        self.res_value = Label(self._res_text(), size=16)
        self.res_left = Button("<", width=36, height=36, font_size=16, style=6, hover_style=1)
        self.res_left.callback = self._prev_res
        self.res_right = Button(">", width=36, height=36, font_size=16, style=6, hover_style=1)
        self.res_right.callback = self._next_res

        self.music_label = Label("Music", size=18)
        self.music_slider = Slider(width=200, height=36, value=settings.music_volume, style=6)
        self.music_slider.on_change = self._on_music

        self.sfx_label = Label("SFX", size=18)
        self.sfx_slider = Slider(width=200, height=36, value=settings.sfx_volume, style=6)
        self.sfx_slider.on_change = self._on_sfx

        self.back_btn = Button("Back", width=180, height=50, style=6, hover_style=1, font_size=22)
        self.back_btn.callback = self._on_back

        self.widgets = [
            self.fullscreen_toggle,
            self.res_left,
            self.res_right,
            self.music_slider,
            self.sfx_slider,
            self.back_btn,
        ]

        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.bg_panel = Panel(560, 460, style=6, transparent=True)
        self.bg_x = (sw - 560) // 2
        self.bg_y = cy - 230

        label_x = cx - 120
        control_x = cx + 100

        self.fullscreen_toggle.set_position(control_x, self.bg_y + 140)
        self.res_left.set_position(control_x - 70, self.bg_y + 200)
        self.res_right.set_position(control_x + 70, self.bg_y + 200)
        self.music_slider.set_position(control_x, self.bg_y + 270)
        self.sfx_slider.set_position(control_x, self.bg_y + 340)
        self.back_btn.set_position(cx, self.bg_y + 420)

        self._label_x = label_x
        self._control_x = control_x

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _res_text(self) -> str:
        w, h = self.resolutions[self.res_index]
        return f"{w}x{h}"

    def _prev_res(self) -> None:
        self.res_index = (self.res_index - 1) % len(self.resolutions)
        self._apply_resolution()

    def _next_res(self) -> None:
        self.res_index = (self.res_index + 1) % len(self.resolutions)
        self._apply_resolution()

    def _apply_resolution(self) -> None:
        w, h = self.resolutions[self.res_index]
        self.res_value.set_text(self._res_text())
        if not settings.is_fullscreen:
            settings.screen_width = w
            settings.screen_height = h
            settings.apply_display_mode()

    def _on_fullscreen(self, active: bool) -> None:
        settings.is_fullscreen = active
        if not active:
            w, h = self.resolutions[self.res_index]
            settings.screen_width = w
            settings.screen_height = h
        settings.apply_display_mode()

    def _on_music(self, value: float) -> None:
        settings.set_music_volume(value)

    def _on_sfx(self, value: float) -> None:
        settings.set_sfx_volume(value)

    def _on_back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        for widget in self.widgets:
            widget.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        cx = sw // 2
        title_y = self.bg_y + 55

        self.bg_panel.draw(surface, self.bg_x, self.bg_y)
        title_gap = self.title.rect.width // 2 + 80
        self.divider_top.draw(surface, cx - title_gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.divider_bottom.draw(surface, cx + title_gap, title_y)

        self.fullscreen_label.draw(surface, self._label_x, self.bg_y + 140)
        self.fullscreen_toggle.draw(surface)

        self.res_label.draw(surface, self._label_x, self.bg_y + 200)
        self.res_left.draw(surface)
        self.res_value.draw(surface, self._control_x, self.bg_y + 200)
        self.res_right.draw(surface)

        self.music_label.draw(surface, self._label_x, self.bg_y + 270)
        self.music_slider.draw(surface)

        self.sfx_label.draw(surface, self._label_x, self.bg_y + 340)
        self.sfx_slider.draw(surface)

        self.back_btn.draw(surface)
