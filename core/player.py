from pathlib import Path

import pygame

from core.config.constants import (
    DEATH_ANIM_DURATION,
    FALL_DEATH_AIRTIME,
    P1_KEYS,
    PLAYER_ACCELERATION,
    PLAYER_ANIMATION_SPEED,
    PLAYER_FAST_FALL,
    PLAYER_FRICTION,
    PLAYER_GRAVITY,
    PLAYER_JUMP_FORCE,
    PLAYER_MAX_SPEED,
    PLAYER_SCALE,
    SQUASH_DURATION,
    SQUASH_FACTOR,
    STRETCH_DURATION,
    STRETCH_FACTOR,
)

KEY_MAP = {
    "a": pygame.K_a,
    "d": pygame.K_d,
    "w": pygame.K_w,
    "s": pygame.K_s,
    "[1]": pygame.K_KP_1,
    "[2]": pygame.K_KP_2,
    "[3]": pygame.K_KP_3,
    "[5]": pygame.K_KP_5,
}

FRAME_SIZE = (8, 8)
FRAME_COUNT = 5
OUTLINE_COLOR = (255, 255, 255)


def _load_spritesheet(filepath: Path, scale: float) -> list[pygame.Surface]:
    sheet = pygame.image.load(filepath).convert_alpha()
    frames: list[pygame.Surface] = []
    w, h = FRAME_SIZE
    scaled = (int(w * scale), int(h * scale))
    for i in range(FRAME_COUNT):
        frame = sheet.subsurface(pygame.Rect(i * w, 0, w, h))
        frames.append(pygame.transform.scale(frame, scaled))
    return frames


def _add_outline(
    surface: pygame.Surface,
    color: tuple[int, int, int] = OUTLINE_COLOR,
) -> pygame.Surface:
    w, h = surface.get_size()
    outlined = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)

    mask = pygame.mask.from_surface(surface)
    mask_surface = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))

    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        outlined.blit(mask_surface, (1 + dx, 1 + dy))

    outlined.blit(surface, (1, 1))
    return outlined


ANIM_KEYS = ["idle", "walk", "jump", "die"]


def _build_animations(
    sprite_dir: Path,
    prefix: str,
    scale: float,
    outline_color: tuple[int, int, int] = OUTLINE_COLOR,
) -> dict[str, list[pygame.Surface]]:
    names = [sprite_dir / f"{prefix}_{key}.png" for key in ANIM_KEYS]
    raw = {key: _load_spritesheet(path, scale) for key, path in zip(ANIM_KEYS, names, strict=True)}
    return {key: [_add_outline(f, outline_color) for f in frames] for key, frames in raw.items()}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * min(t, 1.0)


class Player:
    def __init__(
        self,
        x: float,
        y: float,
        keys: dict[str, str] | None = None,
        outline_color: tuple[int, int, int] = OUTLINE_COLOR,
        character: str = "green",
        name: str = "Player",
    ) -> None:
        bindings = keys or P1_KEYS
        self.key_left = KEY_MAP[bindings["left"]]
        self.key_right = KEY_MAP[bindings["right"]]
        self.key_jump = KEY_MAP[bindings["jump"]]
        self.key_down = KEY_MAP[bindings["down"]]

        self.name = name
        self.outline_color = outline_color
        self.sprite_dir = Path(f"assets/characters/{character}")
        self.sprite_prefix = character
        self.current_scale = PLAYER_SCALE
        self.animations = _build_animations(
            self.sprite_dir, self.sprite_prefix, PLAYER_SCALE, outline_color
        )

        self.state = "idle"
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0)

        self.on_ground = False
        self.was_airborne = False
        self.just_landed = False
        self.in_water = False
        self.in_lava = False
        self.on_stairs = False
        self.dropping_through = False
        self.has_double_jump = False
        self.facing_right = True
        self.dead = False
        self._death_timer = 0.0
        self._airtime = 0.0

        self.frame_index = 0.0
        self.image = self.animations[self.state][0]
        self.rect = self.image.get_rect(topleft=(int(x), int(y)))

        # Squash & stretch
        self.scale_x = 1.0
        self.scale_y = 1.0
        self._squash_timer = 0.0
        self._stretch_timer = 0.0

    def rescale(self, new_scale: float) -> None:
        self.current_scale = new_scale
        self.animations = _build_animations(
            self.sprite_dir, self.sprite_prefix, new_scale, self.outline_color
        )
        self.image = self.animations[self.state][int(self.frame_index)]
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        self.pos.x = float(self.rect.x)
        self.pos.y = float(self.rect.y)

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        self.acceleration.x = 0

        if keys[self.key_left]:
            self.acceleration.x = -PLAYER_ACCELERATION
            self.facing_right = False
        if keys[self.key_right]:
            self.acceleration.x = PLAYER_ACCELERATION
            self.facing_right = True

        if keys[self.key_jump]:
            if self.in_water:
                self.velocity.y = PLAYER_JUMP_FORCE * 0.6
            elif self.on_stairs:
                self.velocity.y = PLAYER_JUMP_FORCE * 0.8
                self.on_stairs = False
            elif self.on_ground:
                self.velocity.y = PLAYER_JUMP_FORCE
                self.on_ground = False
                self.has_double_jump = True
                self._stretch_timer = STRETCH_DURATION
                self._squash_timer = 0.0
            elif self.has_double_jump and self._near_apex():
                self.velocity.y = PLAYER_JUMP_FORCE
                self.has_double_jump = False
                self._stretch_timer = STRETCH_DURATION
                self._squash_timer = 0.0

        if keys[self.key_down]:
            if self.on_ground and not self.on_stairs:
                self.dropping_through = True
            elif not self.on_ground:
                self.velocity.y += PLAYER_FAST_FALL
        else:
            self.dropping_through = False

    def update(
        self,
        dt: float,
        collision_rects: list[pygame.Rect],
        water_rects: list[pygame.Rect],
        stairs_rects: list[pygame.Rect] | None = None,
        lava_rects: list[pygame.Rect] | None = None,
        platform_rects: list[pygame.Rect] | None = None,
        breakable_rects: list[pygame.Rect] | None = None,
    ) -> None:
        if self.dead:
            self._death_timer += dt
            self._animate_death(dt)
            return

        self.in_water = any(self.rect.colliderect(w) for w in water_rects)
        self.in_lava = any(self.rect.colliderect(lv) for lv in (lava_rects or []))
        self.on_stairs = any(self.rect.colliderect(s) for s in (stairs_rects or []))
        speed_mod = 0.4 if self.in_water else 1.0
        gravity_mod = 0.3 if self.in_water else 1.0

        self.handle_input()

        # Stairs: climb up/down with jump/down keys, reduced gravity
        if self.on_stairs:
            keys = pygame.key.get_pressed()
            if keys[self.key_jump]:
                self.velocity.y = -PLAYER_MAX_SPEED * 0.5
            elif keys[self.key_down]:
                self.velocity.y = PLAYER_MAX_SPEED * 0.4
            else:
                self.velocity.y *= 0.85  # friction on stairs
            gravity_mod = 0.0  # no gravity while on stairs

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

        # Track airtime for fall damage
        if not self.on_ground and self.velocity.y > 0:
            self._airtime += dt
        else:
            self._airtime = 0.0

        self.pos.y += self.velocity.y * dt
        self.rect.y = int(self.pos.y)
        self._collide_y(collision_rects)

        # One-way platforms (Terraria-style): collide only from above, drop-through with down
        if not self.dropping_through:
            self._collide_platforms(platform_rects or [])
            self._collide_platforms(breakable_rects or [])

        self._check_ground(collision_rects)
        if not self.dropping_through:
            self._check_ground(platform_rects or [])
            self._check_ground(breakable_rects or [])

        self.just_landed = self.on_ground and self.was_airborne
        self.was_airborne = not self.on_ground

        if self.just_landed:
            # Fall damage check — only lethal after sustained falling
            if self._airtime >= FALL_DEATH_AIRTIME and not self.in_water:
                self.dead = True
                self._death_timer = 0.0
                self.state = "die"
                self.frame_index = 0.0
            self._airtime = 0.0
            self._squash_timer = SQUASH_DURATION
            self._stretch_timer = 0.0

        self._update_squash_stretch(dt)
        self._animate(dt)

    def _update_squash_stretch(self, dt: float) -> None:
        if self._squash_timer > 0:
            t = 1.0 - (self._squash_timer / SQUASH_DURATION)
            self.scale_x = _lerp(STRETCH_FACTOR, 1.0, t)
            self.scale_y = _lerp(SQUASH_FACTOR, 1.0, t)
            self._squash_timer -= dt
        elif self._stretch_timer > 0:
            t = 1.0 - (self._stretch_timer / STRETCH_DURATION)
            self.scale_x = _lerp(SQUASH_FACTOR, 1.0, t)
            self.scale_y = _lerp(STRETCH_FACTOR, 1.0, t)
            self._stretch_timer -= dt
        else:
            self.scale_x = 1.0
            self.scale_y = 1.0

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

    def _collide_platforms(self, rects: list[pygame.Rect]) -> None:
        for plat in rects:
            if not self.rect.colliderect(plat):
                continue
            # Only collide from above: player's feet were above the platform top
            if self.velocity.y > 0 and self.rect.bottom <= plat.top + self.velocity.y * 0.05 + 4:
                self.rect.bottom = plat.top
                self.on_ground = True
                self.has_double_jump = False
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

    def _animate_death(self, dt: float) -> None:
        frames = self.animations["die"]
        self.frame_index += dt / (PLAYER_ANIMATION_SPEED * 2)  # slower death anim
        if self.frame_index >= len(frames):
            self.frame_index = len(frames) - 1  # hold last frame
        frame = frames[int(self.frame_index)]
        self.image = pygame.transform.flip(frame, True, False) if not self.facing_right else frame

    @property
    def death_complete(self) -> bool:
        return self.dead and self._death_timer >= DEATH_ANIM_DURATION

    def respawn(self, x: float, y: float) -> None:
        self.dead = False
        self._death_timer = 0.0
        self._airtime = 0.0
        self.pos.x = x
        self.pos.y = y
        self.rect.x = int(x)
        self.rect.y = int(y)
        self.velocity.x = 0
        self.velocity.y = 0
        self.state = "idle"
        self.frame_index = 0.0

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

    def draw(
        self,
        surface: pygame.Surface,
        camera_offset: tuple[int, int] = (0, 0),
        show_nametag: bool = False,
    ) -> None:
        ox, oy = camera_offset
        if self.scale_x != 1.0 or self.scale_y != 1.0:
            w, h = self.image.get_size()
            new_w = int(w * self.scale_x)
            new_h = int(h * self.scale_y)
            scaled = pygame.transform.scale(self.image, (new_w, new_h))
            anchor = (self.rect.midbottom[0] - ox, self.rect.midbottom[1] - oy)
            draw_rect = scaled.get_rect(midbottom=anchor)
            surface.blit(scaled, draw_rect)
        else:
            surface.blit(self.image, (self.rect.x - ox, self.rect.y - oy))

        if show_nametag and self.name:
            self._draw_nametag(surface, ox, oy)

    _nametag_font: pygame.font.Font | None = None

    def _draw_nametag(self, surface: pygame.Surface, ox: int, oy: int) -> None:
        if Player._nametag_font is None:
            from core.gui import FONT_PATH

            Player._nametag_font = pygame.font.Font(FONT_PATH, 24)

        tag = Player._nametag_font.render(self.name, True, (255, 255, 255))
        tag_rect = tag.get_rect(midbottom=(self.rect.centerx - ox, self.rect.top - 6 - oy))
        surface.blit(tag, tag_rect)
