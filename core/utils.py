from pathlib import Path

import pygame


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(t, 1.0))


def load_spritesheet(
    filepath: Path,
    frame_size: tuple[int, int],
    frame_count: int,
    scale: float = 1.0,
) -> list[pygame.Surface]:
    sheet = pygame.image.load(filepath).convert_alpha()
    frames: list[pygame.Surface] = []
    w, h = frame_size
    scaled = (int(w * scale), int(h * scale))
    for i in range(frame_count):
        frame = sheet.subsurface(pygame.Rect(i * w, 0, w, h))
        frames.append(pygame.transform.scale(frame, scaled))
    return frames
