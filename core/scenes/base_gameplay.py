import pygame

from core.camera import SplitScreen
from core.config.constants import (
    BASE_MAP_SCALE,
    BG_COLOR,
    DEATH_ANIM_DURATION,
    DEATH_FLASH_COLOR,
    DEATH_FLASH_MAX_ALPHA,
    LANDING_SHAKE_DURATION,
    LANDING_SHAKE_INTENSITY,
    LAVA_COUNTDOWN_COLOR,
    LAVA_COUNTDOWN_SIZE,
    LAVA_DEATH_SHAKE_DURATION,
    LAVA_DEATH_SHAKE_INTENSITY,
    LAVA_DEATH_TIME,
    LAVA_DECAY_RATE,
    LAVA_JOLT_BASE_INTENSITY,
    LAVA_JOLT_DURATION,
    LAVA_JOLT_INTERVAL,
    LAVA_JOLT_MULTIPLIER,
    LAVA_VIGNETTE_COLOR,
    LAVA_VIGNETTE_MAX_ALPHA,
    PLAYER_SCALE,
    PLAYER_SPAWN_OFFSET,
    SCALE_EPSILON,
    SIGN_DIALOG_Y_RATIO,
)
from core.config.levels import LEVELS
from core.hud import ZoneAnnouncement
from core.interactable import BreakableManager, PressurePlateManager, SignDialog, SignManager
from core.map_loader import TMXMap
from core.player import Player
from core.portal import Portal
from core.scene import Scene, SceneManager
from core.vfx import VFXAnimation, load_vfx_frames


class BaseGameplay(Scene):
    def __init__(self, manager: SceneManager, level_id: str = "tutorial_001") -> None:
        super().__init__(manager)
        self.level_id = level_id
        level = LEVELS[level_id]

        self.map = TMXMap(level["map"], zoom=level.get("zoom"))

        self.spawn_x = self.map.offset[0] + self.map.scaled_size[0] // 2
        self.spawn_y = self.map.offset[1] + self.map.scaled_size[1] // 2

        self.players: list[Player] = []  # subclass fills this

        self.landing_frames = load_vfx_frames("assets/vfx/landing", scale=self.map.scale)
        self.vfx_list: list[VFXAnimation] = []
        self.split_screen = SplitScreen()
        self.zone_announcement = ZoneAnnouncement(level["zone_subtitle"], level["zone_title"])

        self.sign_manager = SignManager(self.map.sign_rects, level.get("signs", {}))
        self.sign_dialogs = [SignDialog(), SignDialog()]

        self.pressure_plates = PressurePlateManager(self.map.pressure_rects, self.map.scale)
        self.breakables = BreakableManager(self.map.get_layer_tiles("BrakablePlatform"))

        portal_rects = self.map.portal_rects
        self.portal: Portal | None = None
        if portal_rects:
            self.portal = Portal(portal_rects[0], self.map.scale)
        self.next_level = level.get("next_level")
        self._portal_activated = False
        self._lava_timers = [0.0, 0.0]
        self._death_flash = [0.0, 0.0]

    def _sync_player_scales(self) -> None:
        new_scale = PLAYER_SCALE * (self.map.scale / BASE_MAP_SCALE)
        for p in self.players:
            if abs(new_scale - p.current_scale) > SCALE_EPSILON:
                p.rescale(new_scale)

    def _base_resize(self, width: int, height: int) -> None:
        old_scale = self.map.scale
        old_offset = self.map.offset
        self.map.rescale((width, height))

        for p in self.players:
            rel_x = (p.pos.x - old_offset[0]) / old_scale
            rel_y = (p.pos.y - old_offset[1]) / old_scale
            p.pos.x = rel_x * self.map.scale + self.map.offset[0]
            p.pos.y = rel_y * self.map.scale + self.map.offset[1]
            p.rect.x = int(p.pos.x)
            p.rect.y = int(p.pos.y)

        self._sync_player_scales()
        self.landing_frames = load_vfx_frames("assets/vfx/landing", scale=self.map.scale)
        self.vfx_list.clear()
        self.sign_manager = SignManager(self.map.sign_rects, self.sign_manager._texts)
        self.sign_dialogs = [SignDialog(), SignDialog()]
        self.pressure_plates = PressurePlateManager(self.map.pressure_rects, self.map.scale)
        self.breakables = BreakableManager(self.map.get_layer_tiles("BrakablePlatform"))

    def on_resize(self, width: int, height: int) -> None:
        self._base_resize(width, height)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from core.scenes.pause import Pause

            self.manager.push(Pause(self.manager))

    def _update_player(self, i: int, p: Player, dt: float) -> None:
        if self.portal and self.portal.should_hide_player(i):
            return
        if p.dead:
            p.update(dt, self.map.collision_rects, self.map.water_rects)
            return

        p.update(
            dt,
            self.map.collision_rects,
            self.map.water_rects,
            stairs_rects=self.map.stairs_rects,
            lava_rects=self.map.lava_rects,
            platform_rects=self.map.platform_rects,
            breakable_rects=self.breakables.active_rects(),
        )

        # Lava countdown
        if p.in_lava:
            self._lava_timers[i] += dt
            if int(self._lava_timers[i] / LAVA_JOLT_INTERVAL) != int(
                (self._lava_timers[i] - dt) / LAVA_JOLT_INTERVAL
            ):
                intensity = LAVA_JOLT_BASE_INTENSITY + self._lava_timers[i] * LAVA_JOLT_MULTIPLIER
                self.split_screen.shake_all(intensity, LAVA_JOLT_DURATION)
            if self._lava_timers[i] >= LAVA_DEATH_TIME:
                offset = -PLAYER_SPAWN_OFFSET if i == 0 else PLAYER_SPAWN_OFFSET
                p.respawn(self.spawn_x + offset, self.spawn_y)
                self._lava_timers[i] = 0.0
                self.split_screen.shake_all(LAVA_DEATH_SHAKE_INTENSITY, LAVA_DEATH_SHAKE_DURATION)
        else:
            self._lava_timers[i] = max(self._lava_timers[i] - dt * LAVA_DECAY_RATE, 0.0)

        # Fall death
        if p.dead and p._death_timer < dt * 2:
            self._death_flash[i] = DEATH_ANIM_DURATION
            self.split_screen.shake_all(10.0, 0.3)
        if p.death_complete:
            offset = -PLAYER_SPAWN_OFFSET if i == 0 else PLAYER_SPAWN_OFFSET
            p.respawn(self.spawn_x + offset, self.spawn_y)
            self._death_flash[i] = 0.0
        if self._death_flash[i] > 0:
            self._death_flash[i] = max(self._death_flash[i] - dt, 0.0)

        # Landing VFX
        if p.just_landed and self.landing_frames and not p.in_water:
            self.vfx_list.append(VFXAnimation(self.landing_frames, p.rect.centerx, p.rect.bottom))
            self.split_screen.shake_all(LANDING_SHAKE_INTENSITY, LANDING_SHAKE_DURATION)

    def _update_shared(self, dt: float) -> None:
        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

        self.breakables.update(dt, *(p.rect for p in self.players))
        self.pressure_plates.update(dt, *(p.rect for p in self.players))

        # Portal
        if self.portal:
            all_pressed = all(p.activated for p in self.pressure_plates.plates)
            if all_pressed and not self._portal_activated:
                self.portal.activate()
                self._portal_activated = True
            self.portal.update(dt, self.players[0].rect, self.players[1].rect)

            if self.portal.is_done:
                self._on_level_complete()
                return

        # Camera — collapse if a player entered portal
        if self.portal and (self.portal.p1_entered or self.portal.p2_entered):
            remaining = self.players[1] if self.portal.p1_entered else self.players[0]
            self.split_screen.update(dt, remaining.rect, remaining.rect)
        else:
            self.split_screen.update(dt, self.players[0].rect, self.players[1].rect)

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.update(dt)

        # Signs — per player
        for i, p in enumerate(self.players):
            text = self.sign_manager.get_active_text(p.rect)
            if text:
                self.sign_dialogs[i].show(text)
            else:
                self.sign_dialogs[i].hide()
            self.sign_dialogs[i].update(dt)

    def _on_level_complete(self) -> None:
        """Override in subclass for level transition behavior."""
        from core.scenes.main_menu import MainMenu

        self.manager.replace(MainMenu(self.manager))

    def _draw_world(
        self,
        surface: pygame.Surface,
        cam_offset: tuple[int, int],
        view_size: tuple[int, int],
    ) -> None:
        surface.fill(BG_COLOR)
        self.map.draw(surface, cam_offset)
        self.breakables.draw(surface, cam_offset)
        self.pressure_plates.draw(surface, cam_offset)
        if self.portal:
            self.portal.draw(surface, cam_offset)
        for i, p in enumerate(self.players):
            if self.portal and self.portal.should_hide_player(i):
                continue
            if not self._should_draw_player(i):
                continue
            p.draw(surface, cam_offset, show_nametag=self._show_nametag(i))
        for vfx in self.vfx_list:
            vfx.draw(surface, cam_offset)

    def _should_draw_player(self, index: int) -> bool:
        return True

    def _show_nametag(self, index: int) -> bool:
        return True

    def _draw_player_hud(
        self, surface: pygame.Surface, player_index: int, center: tuple[int, int]
    ) -> None:
        sw, sh = surface.get_size()
        cx, cy = center

        # Death flash
        flash = self._death_flash[player_index]
        if flash > 0.01:
            alpha = int(DEATH_FLASH_MAX_ALPHA * (flash / DEATH_ANIM_DURATION))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((*DEATH_FLASH_COLOR, alpha))
            surface.blit(overlay, (0, 0))

        # Lava vignette + countdown
        lava_t = self._lava_timers[player_index]
        if lava_t > 0.01:
            progress = min(lava_t / LAVA_DEATH_TIME, 1.0)
            alpha = int(LAVA_VIGNETTE_MAX_ALPHA * progress)
            vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
            vignette.fill((*LAVA_VIGNETTE_COLOR, alpha))
            surface.blit(vignette, (0, 0))

            from core.gui import Label

            remaining = max(0, LAVA_DEATH_TIME - lava_t)
            countdown = Label(
                f"{remaining:.1f}", size=LAVA_COUNTDOWN_SIZE, color=LAVA_COUNTDOWN_COLOR
            )
            countdown.draw(surface, cx, cy)

        # Sign popup
        self.sign_dialogs[player_index].draw_at(surface, cx, int(sh * SIGN_DIALOG_Y_RATIO))

    def _draw_shared_hud(self, surface: pygame.Surface) -> None:
        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.draw(surface)
        if self.portal:
            self.portal.draw_cutaway(surface)
            cam = self.split_screen.shared_cam.offset
            self.portal.draw_vignette(surface, cam)
