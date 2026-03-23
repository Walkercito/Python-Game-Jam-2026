import pygame

from core.camera import SplitScreen
from core.config.constants import (
    DEATH_ANIM_DURATION,
    LAVA_DEATH_TIME,
    P1_KEYS,
    P2_KEYS,
    PLAYER_SCALE,
)
from core.config.levels import LEVELS
from core.hud import ZoneAnnouncement
from core.interactable import BreakableManager, PressurePlateManager, SignDialog, SignManager
from core.map_loader import TMXMap
from core.player import Player
from core.portal import Portal
from core.scene import Scene, SceneManager
from core.vfx import VFXAnimation, load_vfx_frames

BASE_MAP_SCALE = 4.0


class Gameplay(Scene):
    def __init__(
        self,
        manager: SceneManager,
        level_id: str = "tutorial_001",
        p1_name: str = "Green",
        p2_name: str = "Orange",
    ) -> None:
        super().__init__(manager)
        self.level_id = level_id
        self._p1_name = p1_name
        self._p2_name = p2_name
        level = LEVELS[level_id]

        self.map = TMXMap(level["map"], zoom=level.get("zoom"))

        self.spawn_x = self.map.offset[0] + self.map.scaled_size[0] // 2
        self.spawn_y = self.map.offset[1] + self.map.scaled_size[1] // 2
        spawn_x = self.spawn_x
        spawn_y = self.spawn_y

        self.player1 = Player(
            spawn_x - 40,
            spawn_y,
            keys=P1_KEYS,
            outline_color=(255, 80, 80),
            character="green",
            name=p1_name,
        )
        self.player2 = Player(
            spawn_x + 40,
            spawn_y,
            keys=P2_KEYS,
            outline_color=(80, 130, 255),
            character="orange",
            name=p2_name,
        )
        self.players = [self.player1, self.player2]

        self._sync_player_scales()
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
        self._death_flash = [0.0, 0.0]  # red flash timer per player

    def _sync_player_scales(self) -> None:
        new_scale = PLAYER_SCALE * (self.map.scale / BASE_MAP_SCALE)
        for p in self.players:
            if abs(new_scale - p.current_scale) > 0.01:
                p.rescale(new_scale)

    def on_resize(self, width: int, height: int) -> None:
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

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from core.scenes.pause import Pause

            self.manager.push(Pause(self.manager))

    def update(self, dt: float) -> None:
        self.breakables.update(dt, self.player1.rect, self.player2.rect)

        for i, p in enumerate(self.players):
            if self.portal and self.portal.should_hide_player(i):
                continue
            p.update(
                dt,
                self.map.collision_rects,
                self.map.water_rects,
                stairs_rects=self.map.stairs_rects,
                lava_rects=self.map.lava_rects,
                platform_rects=self.map.platform_rects,
                breakable_rects=self.breakables.active_rects(),
            )

            # Lava — 2s countdown with hurt jolt
            if p.in_lava:
                self._lava_timers[i] += dt
                # Minecraft-style: quick directional jolt every 0.3s
                if int(self._lava_timers[i] / 0.3) != int((self._lava_timers[i] - dt) / 0.3):
                    self.split_screen.shake_all(3.0 + self._lava_timers[i] * 2, 0.08)
                if self._lava_timers[i] >= LAVA_DEATH_TIME:
                    p.pos.x = self.spawn_x + (-40 if i == 0 else 40)
                    p.pos.y = self.spawn_y
                    p.rect.x = int(p.pos.x)
                    p.rect.y = int(p.pos.y)
                    p.velocity.x = 0
                    p.velocity.y = 0
                    self._lava_timers[i] = 0.0
                    self.split_screen.shake_all(8.0, 0.3)
            else:
                self._lava_timers[i] = max(self._lava_timers[i] - dt * 2, 0.0)

            # Fall death — trigger red flash and shake on impact
            if p.dead and p._death_timer < dt * 2:  # just died this frame
                self._death_flash[i] = DEATH_ANIM_DURATION
                self.split_screen.shake_all(10.0, 0.3)

            # Respawn after death animation
            if p.death_complete:
                spawn_offset = -40 if i == 0 else 40
                p.respawn(self.spawn_x + spawn_offset, self.spawn_y)
                self._death_flash[i] = 0.0

            # Decay death flash
            if self._death_flash[i] > 0:
                self._death_flash[i] = max(self._death_flash[i] - dt, 0.0)

            if p.just_landed and self.landing_frames and not p.in_water:
                self.vfx_list.append(
                    VFXAnimation(self.landing_frames, p.rect.centerx, p.rect.bottom)
                )
                self.split_screen.shake_all(4.0, 0.12)

        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

        # If a player entered the portal, collapse to single camera on the remaining one
        if self.portal and (self.portal.p1_entered or self.portal.p2_entered):
            remaining = self.player2 if self.portal.p1_entered else self.player1
            self.split_screen.update(dt, remaining.rect, remaining.rect)
        else:
            self.split_screen.update(dt, self.player1.rect, self.player2.rect)

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.update(dt)

        # Pressure plates
        self.pressure_plates.update(dt, self.player1.rect, self.player2.rect)

        # Portal activation
        if self.portal:
            all_pressed = all(p.activated for p in self.pressure_plates.plates)
            if all_pressed and not self._portal_activated:
                self.portal.activate()
                self._portal_activated = True

            self.portal.update(dt, self.player1.rect, self.player2.rect)

            if self.portal.is_done:
                if self.next_level:
                    self.manager.replace(
                        Gameplay(self.manager, self.next_level, self._p1_name, self._p2_name)
                    )
                else:
                    from core.scenes.main_menu import MainMenu

                    self.manager.replace(MainMenu(self.manager))
                return

        # Signs — per player
        for i, p in enumerate(self.players):
            text = self.sign_manager.get_active_text(p.rect)
            if text:
                self.sign_dialogs[i].show(text)
            else:
                self.sign_dialogs[i].hide()
            self.sign_dialogs[i].update(dt)

    def _draw_world(
        self,
        surface: pygame.Surface,
        cam_offset: tuple[int, int],
        view_size: tuple[int, int],
    ) -> None:
        surface.fill((14, 7, 27))
        self.map.draw(surface, cam_offset)
        self.breakables.draw(surface, cam_offset)
        self.pressure_plates.draw(surface, cam_offset)
        if self.portal:
            self.portal.draw(surface, cam_offset)
        for i, p in enumerate(self.players):
            if self.portal and self.portal.should_hide_player(i):
                continue
            p.draw(surface, cam_offset, show_nametag=True)
        for vfx in self.vfx_list:
            vfx.draw(surface, cam_offset)

    def _draw_player_hud(
        self, surface: pygame.Surface, player_index: int, center: tuple[int, int]
    ) -> None:
        sw, sh = surface.get_size()
        cx, cy = center

        # Fall death red flash
        flash = self._death_flash[player_index]
        if flash > 0.01:
            alpha = int(180 * (flash / DEATH_ANIM_DURATION))
            red_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            red_overlay.fill((200, 20, 20, alpha))
            surface.blit(red_overlay, (0, 0))

        # Lava red vignette + countdown
        lava_t = self._lava_timers[player_index]
        if lava_t > 0.01:
            progress = min(lava_t / LAVA_DEATH_TIME, 1.0)
            alpha = int(140 * progress)
            vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
            vignette.fill((180, 30, 20, alpha))
            surface.blit(vignette, (0, 0))

            from core.gui import Label

            remaining = max(0, LAVA_DEATH_TIME - lava_t)
            countdown = Label(f"{remaining:.1f}", size=48, color=(255, 60, 40))
            countdown.draw(surface, cx, cy)

        # Sign popup (per-player, positioned at half center)
        self.sign_dialogs[player_index].draw_at(surface, cx, int(sh * 0.78))

    def draw(self, surface: pygame.Surface) -> None:
        self.split_screen.render(
            surface,
            self._draw_world,
            self.player1.rect,
            self.player2.rect,
            hud_fn=self._draw_player_hud,
        )
        # Shared HUD — on top of everything
        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.draw(surface)
        if self.portal:
            self.portal.draw_cutaway(surface)
            cam = self.split_screen.shared_cam.offset
            self.portal.draw_vignette(surface, cam)
