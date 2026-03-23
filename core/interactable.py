from pathlib import Path

import pygame

from core.gui import Label, Panel

INTERACT_RADIUS = 60
PRESSURE_PLATE_PATH = Path("assets/adve/pressure_plate.png")
PRESSURE_FRAME_SIZE = (8, 8)
PRESSURE_FRAME_COUNT = 3
PRESSURE_FPS = 6


class Sign:
    def __init__(self, rect: pygame.Rect, text: str) -> None:
        self.rect = rect
        self.text = text

    def in_range(self, player_rect: pygame.Rect) -> bool:
        cx, cy = self.rect.center
        px, py = player_rect.center
        dx = abs(cx - px)
        dy = abs(cy - py)
        return dx < INTERACT_RADIUS and dy < INTERACT_RADIUS


class SignManager:
    def __init__(self, sign_rects: list[pygame.Rect], texts: dict[int, str]) -> None:
        self._texts = texts
        self.signs: list[Sign] = []
        for i, rect in enumerate(sign_rects):
            text = texts.get(i, "...")
            self.signs.append(Sign(rect, text))

    def get_active_text(self, *player_rects: pygame.Rect) -> str | None:
        for sign in self.signs:
            for pr in player_rects:
                if sign.in_range(pr):
                    return sign.text
        return None


class SignDialog:
    FADE_SPEED = 6.0

    def __init__(self) -> None:
        self.current_text = ""
        self.alpha = 0.0
        self.visible = False

        self.panel = Panel(
            400,
            80,
            style=6,
            fill_color=(20, 15, 30),
            border_color=(120, 115, 100),
        )
        self.label = Label("", size=20)

    def show(self, text: str) -> None:
        if text != self.current_text:
            self.current_text = text
            self.label.set_text(text)

            text_w = self.label.rect.width
            panel_w = max(text_w + 100, 300)
            self.panel = Panel(
                panel_w,
                80,
                style=6,
                fill_color=(20, 15, 30),
                border_color=(120, 115, 100),
            )
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def update(self, dt: float) -> None:
        target = 1.0 if self.visible else 0.0
        if self.alpha < target:
            self.alpha = min(self.alpha + self.FADE_SPEED * dt, 1.0)
        elif self.alpha > target:
            self.alpha = max(self.alpha - self.FADE_SPEED * dt, 0.0)

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        self.draw_at(surface, sw // 2, int(sh * 0.78))

    def draw_at(self, surface: pygame.Surface, cx: int, y: int) -> None:
        if self.alpha <= 0.01:
            return

        sw, sh = surface.get_size()

        temp = pygame.Surface((sw, sh), pygame.SRCALPHA)

        pw = self.panel.image.get_width()
        self.panel.draw(temp, cx - pw // 2, y - 40)
        self.label.draw(temp, cx, y)

        temp.set_alpha(int(255 * self.alpha))
        surface.blit(temp, (0, 0))


def _load_pressure_frames(scale: float) -> list[pygame.Surface]:
    sheet = pygame.image.load(PRESSURE_PLATE_PATH).convert_alpha()
    frames: list[pygame.Surface] = []
    w, h = PRESSURE_FRAME_SIZE
    scaled = (int(w * scale), int(h * scale))
    for i in range(PRESSURE_FRAME_COUNT):
        frame = sheet.subsurface(pygame.Rect(i * w, 0, w, h))
        frames.append(pygame.transform.scale(frame, scaled))
    return frames


class PressurePlate:
    def __init__(self, rect: pygame.Rect, frames: list[pygame.Surface]) -> None:
        self.rect = rect
        self.frames = frames
        self.pressed = False
        self.frame_index = 0.0
        self.activated = False

    def update(self, dt: float, *player_rects: pygame.Rect) -> None:
        was_pressed = self.pressed
        self.pressed = any(self.rect.colliderect(pr) for pr in player_rects)

        if self.pressed and not was_pressed:
            self.frame_index = 0.0
            self.activated = True

        if self.pressed:
            self.frame_index = min(
                self.frame_index + dt * PRESSURE_FPS,
                PRESSURE_FRAME_COUNT - 1,
            )
        elif self.frame_index > 0:
            self.frame_index = max(self.frame_index - dt * PRESSURE_FPS, 0.0)
            if self.frame_index == 0.0:
                self.activated = False

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        ox, oy = camera_offset
        frame = self.frames[int(self.frame_index)]
        pos = (self.rect.x - ox, self.rect.y - oy)
        surface.blit(frame, pos)


BREAKABLE_TIMER = 0.5  # seconds before breaking


class BreakablePlatform:
    def __init__(self, rect: pygame.Rect, image: pygame.Surface) -> None:
        self.rect = rect
        self.image = image
        self.timer = 0.0
        self.triggered = False
        self.broken = False

    @property
    def shake_amount(self) -> float:
        if self.triggered and not self.broken:
            return min(self.timer / BREAKABLE_TIMER, 1.0) * 3.0
        return 0.0

    def update(self, dt: float, *player_rects: pygame.Rect) -> None:
        if self.broken:
            return

        # Trigger on overlap OR standing on top (feet at platform top)
        touching = any(
            pr.colliderect(self.rect)
            or (
                pr.bottom >= self.rect.top
                and pr.bottom <= self.rect.top + 4
                and pr.right > self.rect.left
                and pr.left < self.rect.right
            )
            for pr in player_rects
        )

        if touching and not self.triggered:
            self.triggered = True
            self.timer = 0.0

        if self.triggered:
            self.timer += dt
            if self.timer >= BREAKABLE_TIMER:
                self.broken = True

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        if self.broken:
            return
        ox, oy = camera_offset
        x = self.rect.x - ox
        y = self.rect.y - oy
        # Shake when about to break
        if self.shake_amount > 0:
            import random

            x += random.randint(int(-self.shake_amount), int(self.shake_amount))
            y += random.randint(int(-self.shake_amount), int(self.shake_amount))
        surface.blit(self.image, (x, y))


class BreakableManager:
    def __init__(self, tiles: list[tuple[pygame.Rect, pygame.Surface]]) -> None:
        self.platforms = [BreakablePlatform(rect, img) for rect, img in tiles]

    def active_rects(self) -> list[pygame.Rect]:
        return [p.rect for p in self.platforms if not p.broken]

    def update(self, dt: float, *player_rects: pygame.Rect) -> None:
        for p in self.platforms:
            p.update(dt, *player_rects)

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        for p in self.platforms:
            p.draw(surface, camera_offset)


class PressurePlateManager:
    def __init__(self, rects: list[pygame.Rect], scale: float) -> None:
        self.frames = _load_pressure_frames(scale)
        self.plates = [PressurePlate(r, self.frames) for r in rects]

    def update(self, dt: float, *player_rects: pygame.Rect) -> None:
        for plate in self.plates:
            plate.update(dt, *player_rects)

    def any_activated(self) -> bool:
        return any(p.activated for p in self.plates)

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        for plate in self.plates:
            plate.draw(surface, camera_offset)
