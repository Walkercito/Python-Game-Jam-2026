from pathlib import Path

import pygame
import pytmx
from pytmx.util_pygame import load_pygame

from core.config.constants import LAYER_PROPERTIES
from core.config.game_settings import settings


class MapLayer:
    def __init__(
        self, layer: pytmx.TiledTileLayer, tile_size: tuple[int, int], properties: dict
    ) -> None:
        self.name = layer.name
        self.tile_size = tile_size
        self.properties = {**properties, **layer.properties}
        self.rects: list[pygame.Rect] = []
        self._build_rects(layer)

    @property
    def has_collision(self) -> bool:
        return self.properties.get("collision", False)

    @property
    def is_water(self) -> bool:
        return self.properties.get("water", False)

    @property
    def speed_modifier(self) -> float:
        return self.properties.get("speed_modifier", 1.0)

    def _build_rects(self, layer: pytmx.TiledTileLayer) -> None:
        tw, th = self.tile_size
        for x, y, gid in layer:
            if gid:
                self.rects.append(pygame.Rect(x * tw, y * th, tw, th))


class TMXMap:
    def __init__(
        self,
        filepath: str | Path,
        target_size: tuple[int, int] | None = None,
    ) -> None:
        self.tmx_data = load_pygame(str(filepath))
        self.tile_size = (self.tmx_data.tilewidth, self.tmx_data.tileheight)
        self.pixel_size = (
            self.tmx_data.width * self.tile_size[0],
            self.tmx_data.height * self.tile_size[1],
        )

        self.layers: dict[str, MapLayer] = {}
        self._parse_layers()
        self._surface = self._pre_render()

        self.scale = 1.0
        self.scaled_size = self.pixel_size
        self.offset = (0, 0)
        self._scaled_surface = self._surface
        self.rescale(target_size or settings.screen_size)

    def _parse_layers(self) -> None:
        for layer in self.tmx_data.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            properties = LAYER_PROPERTIES.get(layer.name, {})
            self.layers[layer.name] = MapLayer(layer, self.tile_size, properties)

    def _pre_render(self) -> pygame.Surface:
        surface = pygame.Surface(self.pixel_size, pygame.SRCALPHA)
        for layer in self.tmx_data.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, image in layer.tiles():
                surface.blit(image, (x * self.tile_size[0], y * self.tile_size[1]))
        return surface

    def rescale(self, target_size: tuple[int, int]) -> None:
        self.scale = min(
            target_size[0] / self.pixel_size[0],
            target_size[1] / self.pixel_size[1],
        )
        self.scaled_size = (
            int(self.pixel_size[0] * self.scale),
            int(self.pixel_size[1] * self.scale),
        )
        self.offset = (
            (target_size[0] - self.scaled_size[0]) // 2,
            (target_size[1] - self.scaled_size[1]) // 2,
        )
        self._scaled_surface = pygame.transform.scale(self._surface, self.scaled_size)

    def _scale_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            int(rect.x * self.scale) + self.offset[0],
            int(rect.y * self.scale) + self.offset[1],
            int(rect.width * self.scale),
            int(rect.height * self.scale),
        )

    @property
    def collision_rects(self) -> list[pygame.Rect]:
        rects: list[pygame.Rect] = []
        for layer in self.layers.values():
            if layer.has_collision:
                rects.extend(self._scale_rect(r) for r in layer.rects)
        return rects

    @property
    def water_rects(self) -> list[pygame.Rect]:
        rects: list[pygame.Rect] = []
        for layer in self.layers.values():
            if layer.is_water:
                rects.extend(self._scale_rect(r) for r in layer.rects)
        return rects

    def get_layer(self, name: str) -> MapLayer | None:
        return self.layers.get(name)

    def get_properties_at(self, x: int, y: int) -> dict:
        native_x = int((x - self.offset[0]) / self.scale)
        native_y = int((y - self.offset[1]) / self.scale)
        point = pygame.Rect(native_x, native_y, 1, 1)
        result: dict = {}
        for layer in self.layers.values():
            if not layer.properties:
                continue
            for rect in layer.rects:
                if rect.colliderect(point):
                    result.update(layer.properties)
                    break
        return result

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        x = self.offset[0] - camera_offset[0]
        y = self.offset[1] - camera_offset[1]
        surface.blit(self._scaled_surface, (x, y))
