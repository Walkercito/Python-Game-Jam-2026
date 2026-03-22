from pathlib import Path

import pygame

from core.config.constants import (
    PLAYER_ACCELERATION,
    PLAYER_ANIMATION_SPEED,
    PLAYER_FAST_FALL,
    PLAYER_FRICTION,
    PLAYER_GRAVITY,
    PLAYER_JUMP_FORCE,
    PLAYER_MAX_SPEED,
    PLAYER_SCALE,
)

SPRITE_DIR = Path("assets/characters/green")
FRAME_SIZE = (8, 8)
FRAME_COUNT = 5
OUTLINE_COLOR = (255, 255, 255)


def _load_spritesheet(filename: str, scale: float) -> list[pygame.Surface]:
    sheet = pygame.image.load(SPRITE_DIR / filename).convert_alpha()
    frames: list[pygame.Surface] = []
    w, h = FRAME_SIZE
    scaled = (int(w * scale), int(h * scale))
    for i in range(FRAME_COUNT):
        frame = sheet.subsurface(pygame.Rect(i * w, 0, w, h))
        frames.append(pygame.transform.scale(frame, scaled))
    return frames


def _add_outline(surface: pygame.Surface) -> pygame.Surface:
    w, h = surface.get_size()
    outlined = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)

    mask = pygame.mask.from_surface(surface)
    mask_surface = mask.to_surface(setcolor=OUTLINE_COLOR, unsetcolor=(0, 0, 0, 0))

    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        outlined.blit(mask_surface, (1 + dx, 1 + dy))

    outlined.blit(surface, (1, 1))
    return outlined


class Player:
    def __init__(self, x: float, y: float) -> None:
        raw_anims = {
            "idle": _load_spritesheet("green_idle.png", PLAYER_SCALE),
            "walk": _load_spritesheet("green_walk.png", PLAYER_SCALE),
            "jump": _load_spritesheet("green_jump.png", PLAYER_SCALE),
            "die": _load_spritesheet("green_die.png", PLAYER_SCALE),
        }
        self.animations: dict[str, list[pygame.Surface]] = {
            name: [_add_outline(f) for f in frames]
            for name, frames in raw_anims.items()
        }

        self.state = "idle"
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0)

        self.on_ground = False
        self.was_airborne = False
        self.just_landed = False
        self.in_water = False
        self.has_double_jump = False
        self.facing_right = True

        self.frame_index = 0.0
        self.image = self.animations[self.state][0]
        self.rect = self.image.get_rect(topleft=(int(x), int(y)))

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        self.acceleration.x = 0

        if keys[pygame.K_a]:
            self.acceleration.x = -PLAYER_ACCELERATION
            self.facing_right = False
        if keys[pygame.K_d]:
            self.acceleration.x = PLAYER_ACCELERATION
            self.facing_right = True

        if keys[pygame.K_w]:
            if self.in_water:
                self.velocity.y = PLAYER_JUMP_FORCE * 0.6
            elif self.on_ground:
                self.velocity.y = PLAYER_JUMP_FORCE
                self.on_ground = False
                self.has_double_jump = True
            elif self.has_double_jump and self._near_apex():
                self.velocity.y = PLAYER_JUMP_FORCE
                self.has_double_jump = False

        if keys[pygame.K_s] and not self.on_ground:
            self.velocity.y += PLAYER_FAST_FALL

    def update(
        self,
        dt: float,
        collision_rects: list[pygame.Rect],
        water_rects: list[pygame.Rect],
    ) -> None:
        self.in_water = any(self.rect.colliderect(w) for w in water_rects)
        speed_mod = 0.4 if self.in_water else 1.0
        gravity_mod = 0.3 if self.in_water else 1.0

        self.handle_input()

        # Horizontal
        self.velocity.x += self.acceleration.x * speed_mod * dt
        self.velocity.x -= self.velocity.x * PLAYER_FRICTION * dt

        max_speed = PLAYER_MAX_SPEED * speed_mod
        if abs(self.velocity.x) > max_speed:
            self.velocity.x = max_speed if self.velocity.x > 0 else -max_speed

        if abs(self.velocity.x) < 1.0:
            self.velocity.x = 0

        self.pos.x += self.velocity.x * dt
        self.rect.x = int(self.pos.x)
        self._collide_x(collision_rects)

        # Vertical
        self.velocity.y += PLAYER_GRAVITY * gravity_mod * dt

        if self.in_water:
            max_fall = PLAYER_MAX_SPEED * 0.5
            if self.velocity.y > max_fall:
                self.velocity.y = max_fall

        self.pos.y += self.velocity.y * dt
        self.rect.y = int(self.pos.y)
        self._collide_y(collision_rects)

        self._check_ground(collision_rects)

        self.just_landed = self.on_ground and self.was_airborne
        self.was_airborne = not self.on_ground

        self._animate(dt)

    def _collide_x(self, rects: list[pygame.Rect]) -> None:
        for wall in rects:
            if self.rect.colliderect(wall):
                if self.velocity.x > 0:
                    self.rect.right = wall.left
                elif self.velocity.x < 0:
                    self.rect.left = wall.right
                self.pos.x = float(self.rect.x)
                self.velocity.x = 0

    def _collide_y(self, rects: list[pygame.Rect]) -> None:
        self.on_ground = False
        for wall in rects:
            if self.rect.colliderect(wall):
                if self.velocity.y > 0:
                    self.rect.bottom = wall.top
                    self.on_ground = True
                    self.has_double_jump = False
                elif self.velocity.y < 0:
                    self.rect.top = wall.bottom
                self.pos.y = float(self.rect.y)
                self.velocity.y = 0

    def _check_ground(self, rects: list[pygame.Rect]) -> None:
        if self.on_ground:
            return
        probe = pygame.Rect(self.rect.x, self.rect.y + 1, self.rect.width, self.rect.height)
        for wall in rects:
            if probe.colliderect(wall) and self.velocity.y >= 0:
                self.on_ground = True
                return

    def _near_apex(self) -> bool:
        threshold = abs(PLAYER_JUMP_FORCE) * 0.2
        return abs(self.velocity.y) <= threshold

    def _get_state(self) -> str:
        if not self.on_ground:
            return "jump"
        if abs(self.velocity.x) > 1.0:
            return "walk"
        return "idle"

    def _animate(self, dt: float) -> None:
        new_state = self._get_state()
        if new_state != self.state:
            self.state = new_state
            self.frame_index = 0.0

        anim_speed = PLAYER_ANIMATION_SPEED
        if self.in_water:
            anim_speed *= 2.5

        frames = self.animations[self.state]
        self.frame_index += dt / anim_speed
        if self.frame_index >= len(frames):
            self.frame_index = 0.0

        frame = frames[int(self.frame_index)]
        self.image = pygame.transform.flip(frame, True, False) if not self.facing_right else frame

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, self.rect)
