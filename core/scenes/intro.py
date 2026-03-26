"""Intro narration cutscene with cinematic text animations synced to voice."""

import math

import pygame

from core.config.constants import BG_COLOR
from core.gui import FONT_PATH, Divider, Label
from core.resource import resource_path
from core.scene import Scene, SceneManager

VOICE_PATH = resource_path("assets/audio/voice/speach.mp3")

# Exact subtitle timings — offset by PRE_DELAY so audio doesn't start immediately
PRE_DELAY = 2.5
POST_DELAY = 3.0

NARRATION = [
    (0.176, 2.994, "Fig and Moss lost track of time"),
    (2.994, 4.703, "again."),
    (4.704, 6.879, "Now, in most places,"),
    (6.880, 8.798, "that would just mean a late dinner"),
    (8.798, 10.821, "and a mildly annoyed parent,"),
    (12.475, 15.284, "but this town isn't most places."),
    (15.285, 16.729, "Every night,"),
    (16.730, 19.001, "when the last light fades,"),
    (19.001, 21.442, "the portals close."),
    (21.442, 24.492, "Every single one of them."),
    (24.493, 27.214, "No warning. No exceptions."),
    (28.853, 29.672, "No one knows why."),
    (31.182, 33.310, "No one's ever really asked."),
    (33.310, 35.679, "If Fig and Moss don't make it"),
    (35.679, 37.631, "through before nightfall,"),
    (37.631, 39.583, "they sleep outside."),
    (41.928, 42.313, "Again."),
    (44.032, 44.746, "So,"),
    (44.747, 46.144, "two friends,"),
    (46.144, 48.465, "a town full of portals,"),
    (48.465, 50.810, "and the sun is already setting."),
    (52.545, 54.200, "Let's not make this weird."),
]

TYPEWRITER_SPEED = 40

# Dramatic lines that get special treatment
EMPHASIS_LINES = {"again.", "the portals close.", "Again.", "Let's not make this weird."}

# Character name colors
WORD_COLORS = {
    "Fig": (255, 100, 100),  # P1 red-ish
    "Moss": (100, 150, 255),  # P2 blue-ish
}


class Intro(Scene):
    def __init__(
        self,
        manager: SceneManager,
        p1_name: str = "Green",
        p2_name: str = "Orange",
        level_id: str = "tutorial_001",
    ) -> None:
        super().__init__(manager)
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.level_id = level_id

        self.font = pygame.font.Font(FONT_PATH, 24)
        self.emphasis_font = pygame.font.Font(FONT_PATH, 32)
        self.prev_font = pygame.font.Font(FONT_PATH, 14)
        self.timer = 0.0
        self.audio_timer = 0.0
        self.current_idx = -1
        self.prev_idx = -1
        self.finished = False
        self._started_audio = False
        self._fade_out = 0.0

        self._skip_label = Label("Press any key to skip", size=12, color=(60, 55, 50))
        self._div_l = Divider(scale=0.5, style=3, fade=True, color=(60, 55, 50))
        self._div_r = Divider(scale=0.5, style=3, fade=True, color=(60, 55, 50))
        self._div_r.image = pygame.transform.flip(self._div_r.image, True, False)

        self._vignette: pygame.Surface | None = None

    def _render_colored_text(
        self, text: str, font: pygame.font.Font, default_color: tuple[int, int, int]
    ) -> pygame.Surface:
        """Render text with Fig/Moss colored differently."""
        words = text.split(" ")
        word_surfs = []
        space_w = font.size(" ")[0]

        for word in words:
            # Check if the word (stripped of punctuation) matches a colored name
            clean = word.strip(".,!?;:'\"")
            color = WORD_COLORS.get(clean, default_color)
            word_surfs.append(font.render(word, True, color))

        total_w = sum(s.get_width() for s in word_surfs) + space_w * (len(word_surfs) - 1)
        max_h = max(s.get_height() for s in word_surfs)
        result = pygame.Surface((total_w, max_h), pygame.SRCALPHA)

        x = 0
        for ws in word_surfs:
            result.blit(ws, (x, (max_h - ws.get_height()) // 2))
            x += ws.get_width() + space_w

        return result

    def _get_vignette(self, sw: int, sh: int) -> pygame.Surface:
        if self._vignette is None or self._vignette.get_size() != (sw, sh):
            self._vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for radius_pct in range(100, 0, -2):
                alpha = int(60 * (1.0 - radius_pct / 100.0))
                r = int(max(sw, sh) * 0.7 * radius_pct / 100)
                pygame.draw.circle(self._vignette, (0, 0, 0, alpha), (sw // 2, sh // 2), r)
        return self._vignette

    def update(self, dt: float) -> None:
        if self.finished:
            return

        self.timer += dt

        if self.timer >= PRE_DELAY and not self._started_audio:
            pygame.mixer.music.load(VOICE_PATH)
            pygame.mixer.music.play()
            self._started_audio = True

        if self._started_audio:
            self.audio_timer = self.timer - PRE_DELAY

        old_idx = self.current_idx
        self.current_idx = -1
        for i, (start, end, _text) in enumerate(NARRATION):
            if start <= self.audio_timer <= end + 0.3:
                self.current_idx = i

        if self.current_idx != old_idx and old_idx >= 0:
            self.prev_idx = old_idx

        if self._started_audio and not pygame.mixer.music.get_busy() and self.audio_timer > 3.0:
            self._fade_out += dt
            if self._fade_out >= POST_DELAY:
                self._finish()

    def _finish(self) -> None:
        self.finished = True
        pygame.mixer.music.stop()

        from core.scenes.gameplay import Gameplay

        self.manager.replace(Gameplay(self.manager, self.level_id, self.p1_name, self.p2_name))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN or (
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        ):
            self._finish()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        sw, sh = surface.get_size()
        cx = sw // 2
        cy = sh // 2

        screen_alpha = min(self.timer / 1.5, 1.0)

        surface.blit(self._get_vignette(sw, sh), (0, 0))

        if self._fade_out > 0:
            fade_alpha = min(self._fade_out / POST_DELAY, 1.0)
            fade_surf = pygame.Surface((sw, sh))
            fade_surf.fill(BG_COLOR)
            fade_surf.set_alpha(int(255 * fade_alpha))
            surface.blit(fade_surf, (0, 0))
            return

        if self.current_idx < 0:
            if self.timer < PRE_DELAY:
                dots = "." * (1 + int(self.timer * 2) % 3)
                dot_surf = self.prev_font.render(dots, True, (60, 55, 50))
                dot_rect = dot_surf.get_rect(center=(cx, cy))
                dot_surf.set_alpha(int(150 * screen_alpha))
                surface.blit(dot_surf, dot_rect)

            self._skip_label.draw(surface, cx, sh - 30)
            return

        start, _end, text = NARRATION[self.current_idx]
        elapsed = self.audio_timer - start
        is_emphasis = text in EMPHASIS_LINES
        font = self.emphasis_font if is_emphasis else self.font

        chars_to_show = int(min(elapsed * TYPEWRITER_SPEED, len(text)))
        visible = text[:chars_to_show]

        if visible:
            line_age = elapsed
            slide_offset = max(0, 10 - line_age * 40)
            text_alpha = min(line_age * 4, 1.0)

            if is_emphasis:
                scale = 1.0 + 0.02 * math.sin(self.timer * 3)
                rendered = self._render_colored_text(visible, font, (255, 250, 240))
                if scale != 1.0:
                    new_w = int(rendered.get_width() * scale)
                    new_h = int(rendered.get_height() * scale)
                    rendered = pygame.transform.scale(rendered, (new_w, new_h))
            else:
                rendered = self._render_colored_text(visible, font, (200, 195, 185))

            rendered.set_alpha(int(255 * text_alpha * screen_alpha))
            rect = rendered.get_rect(center=(cx, cy + int(slide_offset)))
            surface.blit(rendered, rect)

            if is_emphasis and chars_to_show >= len(text):
                div_alpha = min((elapsed - len(text) / TYPEWRITER_SPEED) * 3, 1.0)
                if div_alpha > 0:
                    gap = rendered.get_width() // 2 + 80
                    div_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                    self._div_l.draw(div_surf, cx - gap, cy + int(slide_offset))
                    self._div_r.draw(div_surf, cx + gap, cy + int(slide_offset))
                    div_surf.set_alpha(int(180 * div_alpha * screen_alpha))
                    surface.blit(div_surf, (0, 0))

        if self.prev_idx >= 0:
            prev_text = NARRATION[self.prev_idx][2]
            prev_age = self.audio_timer - NARRATION[self.prev_idx][1]
            prev_alpha = max(0, 1.0 - prev_age * 1.5)

            if prev_alpha > 0.05:
                prev_slide = prev_age * 15
                prev_rendered = self._render_colored_text(prev_text, self.prev_font, (80, 75, 65))
                prev_rendered.set_alpha(int(200 * prev_alpha * screen_alpha))
                prev_rect = prev_rendered.get_rect(center=(cx, cy - 45 - int(prev_slide)))
                surface.blit(prev_rendered, prev_rect)

        skip_alpha = int(100 * screen_alpha)
        skip_surf = self._skip_label.image.copy()
        skip_surf.set_alpha(skip_alpha)
        sr = skip_surf.get_rect(center=(cx, sh - 30))
        surface.blit(skip_surf, sr)
