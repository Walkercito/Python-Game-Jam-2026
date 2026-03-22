import pygame

from core.config.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE
from core.map_loader import TMXMap
from core.player import Player
from core.vfx import VFXAnimation, load_vfx_frames


class Engine:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.map: TMXMap | None = None
        self.player: Player | None = None
        self.vfx_list: list[VFXAnimation] = []
        self.landing_frames: list[pygame.Surface] = []

    def load_map(self, filepath: str) -> None:
        self.map = TMXMap(filepath)
        spawn_x = self.map.offset[0] + self.map.scaled_size[0] // 2
        spawn_y = self.map.offset[1] + self.map.scaled_size[1] // 2
        self.player = Player(spawn_x, spawn_y)
        self.landing_frames = load_vfx_frames("assets/vfx/landing", scale=self.map.scale)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self) -> None:
        dt = self.clock.get_time() / 1000.0
        if self.player and self.map:
            self.player.update(dt, self.map.collision_rects, self.map.water_rects)

            if self.player.just_landed and self.landing_frames and not self.player.in_water:
                self.vfx_list.append(
                    VFXAnimation(
                        self.landing_frames,
                        self.player.rect.centerx,
                        self.player.rect.bottom,
                    )
                )

        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

    def draw(self) -> None:
        self.screen.fill("black")
        if self.map:
            self.map.draw(self.screen)
        if self.player:
            self.player.draw(self.screen)
        for vfx in self.vfx_list:
            vfx.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
