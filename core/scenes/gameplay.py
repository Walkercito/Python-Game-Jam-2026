import pygame

from core.camera import SplitScreen
from core.config.constants import P1_KEYS, P2_KEYS, PLAYER_SCALE
from core.hud import ZoneAnnouncement
from core.map_loader import TMXMap
from core.player import Player
from core.scene import Scene, SceneManager
from core.vfx import VFXAnimation, load_vfx_frames

BASE_MAP_SCALE = 4.0


class Gameplay(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)
        self.map = TMXMap("assets/tiled/tutorial_001.tmx")

        spawn_x = self.map.offset[0] + self.map.scaled_size[0] // 2
        spawn_y = self.map.offset[1] + self.map.scaled_size[1] // 2

        self.player1 = Player(spawn_x - 40, spawn_y, keys=P1_KEYS, outline_color=(255, 80, 80), character="green")
        self.player2 = Player(spawn_x + 40, spawn_y, keys=P2_KEYS, outline_color=(80, 130, 255), character="orange")
        self.players = [self.player1, self.player2]

        self._sync_player_scales()
        self.landing_frames = load_vfx_frames("assets/vfx/landing", scale=self.map.scale)
        self.vfx_list: list[VFXAnimation] = []
        self.split_screen = SplitScreen()
        self.zone_announcement = ZoneAnnouncement("Zone One", "Tutorial Valley")

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

    def update(self, dt: float) -> None:
        for p in self.players:
            p.update(dt, self.map.collision_rects, self.map.water_rects)

            if p.just_landed and self.landing_frames and not p.in_water:
                self.vfx_list.append(
                    VFXAnimation(
                        self.landing_frames,
                        p.rect.centerx,
                        p.rect.bottom,
                    )
                )
                self.split_screen.shake_all(4.0, 0.12)

        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

        self.split_screen.update(dt, self.player1.rect, self.player2.rect)

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.update(dt)

    def _draw_world(
        self,
        surface: pygame.Surface,
        cam_offset: tuple[int, int],
        view_size: tuple[int, int],
    ) -> None:
        surface.fill((14, 7, 27))
        self.map.draw(surface, cam_offset)
        for p in self.players:
            p.draw(surface, cam_offset)
        for vfx in self.vfx_list:
            vfx.draw(surface, cam_offset)

    def draw(self, surface: pygame.Surface) -> None:
        self.split_screen.render(
            surface, self._draw_world, self.player1.rect, self.player2.rect
        )
        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.draw(surface)
