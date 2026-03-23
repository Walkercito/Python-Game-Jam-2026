import pygame

from core.camera import SplitScreen
from core.config.constants import LAVA_DEATH_TIME, P1_KEYS, PLAYER_SCALE
from core.config.levels import LEVELS
from core.hud import ZoneAnnouncement
from core.interactable import BreakableManager, PressurePlateManager, SignDialog, SignManager
from core.map_loader import TMXMap
from core.network import GameClient, GameServer
from core.player import Player
from core.portal import Portal
from core.scene import Scene, SceneManager
from core.vfx import VFXAnimation, load_vfx_frames

BASE_MAP_SCALE = 4.0


class NetworkGameplay(Scene):
    def __init__(
        self,
        manager: SceneManager,
        client: GameClient,
        server: GameServer | None,
        is_host: bool,
        level_id: str = "tutorial_001",
    ) -> None:
        super().__init__(manager)
        self.client = client
        self.server = server
        self.is_host = is_host

        level = LEVELS[level_id]
        self.map = TMXMap(level["map"], zoom=level.get("zoom"))
        self.spawn_x = self.map.offset[0] + self.map.scaled_size[0] // 2
        self.spawn_y = self.map.offset[1] + self.map.scaled_size[1] // 2

        local_char = "green" if self.client.my_slot == 0 else "orange"
        remote_char = "orange" if self.client.my_slot == 0 else "green"

        # Find remote player name from lobby
        remote_name = "Player"
        for p in self.client.lobby_players:
            if p["slot"] != self.client.my_slot:
                remote_name = p["name"]

        self.local_player = Player(
            self.spawn_x,
            self.spawn_y,
            keys=P1_KEYS,
            outline_color=(255, 255, 255),
            character=local_char,
            name=self.client.my_name,
        )
        self.remote_player = Player(
            self.spawn_x,
            self.spawn_y,
            keys=P1_KEYS,
            outline_color=(80, 130, 255),
            character=remote_char,
            name=remote_name,
        )
        self.players = [self.local_player, self.remote_player]

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

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from core.scenes.pause import Pause

            self.manager.push(Pause(self.manager))

    def _send_local_state(self) -> None:
        self.client.send_state(
            {
                "x": self.local_player.pos.x,
                "y": self.local_player.pos.y,
                "vx": self.local_player.velocity.x,
                "vy": self.local_player.velocity.y,
                "state": self.local_player.state,
                "facing": self.local_player.facing_right,
                "on_ground": self.local_player.on_ground,
            }
        )

    def _apply_remote_state(self) -> None:
        rs = self.client.remote_state
        if not rs:
            return
        self.remote_player.pos.x = rs.get("x", self.remote_player.pos.x)
        self.remote_player.pos.y = rs.get("y", self.remote_player.pos.y)
        self.remote_player.velocity.x = rs.get("vx", 0)
        self.remote_player.velocity.y = rs.get("vy", 0)
        self.remote_player.rect.x = int(self.remote_player.pos.x)
        self.remote_player.rect.y = int(self.remote_player.pos.y)
        self.remote_player.facing_right = rs.get("facing", True)
        self.remote_player.on_ground = rs.get("on_ground", False)
        self.remote_player.state = rs.get("state", "idle")

    def update(self, dt: float) -> None:
        self.client.pump()

        if self.client.was_connected and not self.client.connected:
            from core.scenes.disconnected import Disconnected

            self.manager.replace(Disconnected(self.manager, "Connection to host lost"))
            return

        self.breakables.update(dt, self.local_player.rect, self.remote_player.rect)

        # Local player
        self.local_player.update(
            dt,
            self.map.collision_rects,
            self.map.water_rects,
            stairs_rects=self.map.stairs_rects,
            lava_rects=self.map.lava_rects,
            platform_rects=self.map.platform_rects,
            breakable_rects=self.breakables.active_rects(),
        )

        # Lava for local player
        if self.local_player.in_lava:
            self._lava_timers[0] += dt
            if int(self._lava_timers[0] / 0.3) != int((self._lava_timers[0] - dt) / 0.3):
                self.split_screen.shake_all(3.0 + self._lava_timers[0] * 2, 0.08)
            if self._lava_timers[0] >= LAVA_DEATH_TIME:
                self.local_player.pos.x = self.spawn_x
                self.local_player.pos.y = self.spawn_y
                self.local_player.rect.x = int(self.local_player.pos.x)
                self.local_player.rect.y = int(self.local_player.pos.y)
                self.local_player.velocity.x = 0
                self.local_player.velocity.y = 0
                self._lava_timers[0] = 0.0
                self.split_screen.shake_all(8.0, 0.3)
        else:
            self._lava_timers[0] = max(self._lava_timers[0] - dt * 2, 0.0)

        # Remote player
        if self.client.has_remote_player:
            self._apply_remote_state()
            self.remote_player._animate(dt)

        self._send_local_state()

        # Landing VFX
        if self.local_player.just_landed and self.landing_frames and not self.local_player.in_water:
            self.vfx_list.append(
                VFXAnimation(
                    self.landing_frames,
                    self.local_player.rect.centerx,
                    self.local_player.rect.bottom,
                )
            )

        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

        # Pressure plates
        self.pressure_plates.update(dt, self.local_player.rect, self.remote_player.rect)

        # Portal
        if self.portal:
            all_pressed = all(p.activated for p in self.pressure_plates.plates)
            if all_pressed and not self._portal_activated:
                self.portal.activate()
                self._portal_activated = True
            self.portal.update(dt, self.local_player.rect, self.remote_player.rect)
            if self.portal.is_done:
                from core.scenes.main_menu import MainMenu

                self.manager.replace(MainMenu(self.manager))
                return

        # Split screen
        if self.client.has_remote_player:
            if self.portal and (self.portal.p1_entered or self.portal.p2_entered):
                remaining = self.remote_player if self.portal.p1_entered else self.local_player
                self.split_screen.update(dt, remaining.rect, remaining.rect)
            else:
                self.split_screen.update(dt, self.local_player.rect, self.remote_player.rect)

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.update(dt)

        # Signs
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
            if i == 1 and not self.client.has_remote_player:
                continue
            p.draw(surface, cam_offset, show_nametag=(i == 1))
        for vfx in self.vfx_list:
            vfx.draw(surface, cam_offset)

    def _draw_player_hud(
        self, surface: pygame.Surface, player_index: int, center: tuple[int, int]
    ) -> None:
        sw, sh = surface.get_size()
        cx, cy = center

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

        self.sign_dialogs[player_index].draw_at(surface, cx, int(sh * 0.78))

    def draw(self, surface: pygame.Surface) -> None:
        if self.client.has_remote_player:
            self.split_screen.render(
                surface,
                self._draw_world,
                self.local_player.rect,
                self.remote_player.rect,
                hud_fn=self._draw_player_hud,
            )
        else:
            sw, sh = surface.get_size()
            self.split_screen.shared_cam.follow_rect(self.local_player.rect, sw, sh)
            self.split_screen.shared_cam.update(1 / 60)
            self._draw_world(surface, self.split_screen.shared_cam.offset, (sw, sh))
            self._draw_player_hud(surface, 0, (sw // 2, sh // 2))

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.draw(surface)
        if self.portal:
            self.portal.draw_cutaway(surface)
            cam = self.split_screen.shared_cam.offset
            self.portal.draw_vignette(surface, cam)
