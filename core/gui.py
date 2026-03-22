from pathlib import Path

import pygame

GUI_DIR = Path("assets/gui/kenney_fantasy-ui-borders/PNG/Double")
FONT_PATH = Path("assets/font/BoldPixels.ttf")
SLICE_MARGIN = 32


class NineSlice:
    def __init__(self, image: pygame.Surface, margin: int = SLICE_MARGIN) -> None:
        self.margin = margin
        w, h = image.get_size()
        m = margin

        self.corners = {
            "tl": image.subsurface(0, 0, m, m),
            "tr": image.subsurface(w - m, 0, m, m),
            "bl": image.subsurface(0, h - m, m, m),
            "br": image.subsurface(w - m, h - m, m, m),
        }
        self.edges = {
            "t": image.subsurface(m, 0, w - 2 * m, m),
            "b": image.subsurface(m, h - m, w - 2 * m, m),
            "l": image.subsurface(0, m, m, h - 2 * m),
            "r": image.subsurface(w - m, m, m, h - 2 * m),
        }
        self.center = image.subsurface(m, m, w - 2 * m, h - 2 * m)

    def render(self, width: int, height: int) -> pygame.Surface:
        m = min(self.margin, width // 3, height // 3)
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        tl = pygame.transform.scale(self.corners["tl"], (m, m))
        tr = pygame.transform.scale(self.corners["tr"], (m, m))
        bl = pygame.transform.scale(self.corners["bl"], (m, m))
        br = pygame.transform.scale(self.corners["br"], (m, m))

        surface.blit(tl, (0, 0))
        surface.blit(tr, (width - m, 0))
        surface.blit(bl, (0, height - m))
        surface.blit(br, (width - m, height - m))

        surface.blit(pygame.transform.scale(self.edges["t"], (width - 2 * m, m)), (m, 0))
        surface.blit(pygame.transform.scale(self.edges["b"], (width - 2 * m, m)), (m, height - m))
        surface.blit(pygame.transform.scale(self.edges["l"], (m, height - 2 * m)), (0, m))
        surface.blit(pygame.transform.scale(self.edges["r"], (m, height - 2 * m)), (width - m, m))

        surface.blit(pygame.transform.scale(self.center, (width - 2 * m, height - 2 * m)), (m, m))

        return surface


class Panel:
    def __init__(
        self,
        width: int,
        height: int,
        style: int = 6,
        transparent: bool = False,
        fill_color: tuple[int, int, int] = (40, 45, 55),
        border_color: tuple[int, int, int] = (180, 185, 195),
    ) -> None:
        if transparent:
            fill_path = GUI_DIR / "Transparent center" / f"panel-transparent-center-{style:03d}.png"
            border_path = (
                GUI_DIR / "Transparent border" / f"panel-transparent-border-{style:03d}.png"
            )
        else:
            fill_path = GUI_DIR / "Panel" / f"panel-{style:03d}.png"
            border_path = GUI_DIR / "Border" / f"panel-border-{style:03d}.png"

        fill_img = pygame.image.load(fill_path).convert_alpha()
        border_img = pygame.image.load(border_path).convert_alpha()

        fill_slice = NineSlice(fill_img)
        border_slice = NineSlice(border_img)

        fill_surface = fill_slice.render(width, height)
        fill_surface.fill((*fill_color, 255), special_flags=pygame.BLEND_RGBA_MULT)

        border_surface = border_slice.render(width, height)
        border_surface.fill((*border_color, 255), special_flags=pygame.BLEND_RGBA_MULT)

        self.image = fill_surface
        self.image.blit(border_surface, (0, 0))

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        surface.blit(self.image, (x, y))


class Label:
    def __init__(
        self,
        text: str,
        size: int = 24,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        self.font = pygame.font.Font(FONT_PATH, size)
        self.color = color
        self.set_text(text)

    def set_text(self, text: str) -> None:
        self.text = text
        self.image = self.font.render(text, True, self.color)
        self.rect = self.image.get_rect()

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        self.rect.center = (x, y)
        surface.blit(self.image, self.rect)


class Divider:
    def __init__(
        self,
        scale: float = 1.0,
        style: int = 2,
        fade: bool = False,
        color: tuple[int, int, int] = (180, 185, 195),
    ) -> None:
        folder = "Divider Fade" if fade else "Divider"
        prefix = "divider-fade" if fade else "divider"
        img = pygame.image.load(GUI_DIR / folder / f"{prefix}-{style:03d}.png").convert_alpha()
        w, h = img.get_size()
        self.image = pygame.transform.scale(img, (int(w * scale), int(h * scale)))
        self.image.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        rect = self.image.get_rect(center=(x, y))
        surface.blit(self.image, rect)


BUTTON_STYLES = {
    "primary": {
        "fill": (35, 38, 48),
        "border": (180, 185, 195),
        "hover_fill": (220, 225, 235),
        "hover_border": (255, 255, 255),
        "hover_text": (30, 30, 40),
    },
    "secondary": {
        "fill": (30, 33, 42),
        "border": (120, 125, 135),
        "hover_fill": (50, 55, 68),
        "hover_border": (180, 185, 195),
    },
    "danger": {
        "fill": (30, 33, 42),
        "border": (120, 125, 135),
        "hover_fill": (55, 60, 75),
        "hover_border": (220, 225, 235),
    },
}


class Button:
    def __init__(
        self,
        text: str,
        width: int = 260,
        height: int = 60,
        style: int = 6,
        hover_style: int = 1,
        font_size: int = 20,
        variant: str = "secondary",
    ) -> None:
        colors = BUTTON_STYLES[variant]
        self.normal = Panel(
            width,
            height,
            style,
            fill_color=colors["fill"],
            border_color=colors["border"],
        )
        self.hovered_panel = Panel(
            width,
            height,
            hover_style,
            fill_color=colors["hover_fill"],
            border_color=colors["hover_border"],
        )
        self.label = Label(text, font_size)
        self.hover_label = Label(text, font_size, color=colors.get("hover_text", (255, 255, 255)))
        self.rect = pygame.Rect(0, 0, width, height)
        self.hovered = False
        self.callback: callable = lambda: None

    def set_position(self, x: int, y: int) -> None:
        self.rect.center = (x, y)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()

    def draw(self, surface: pygame.Surface) -> None:
        panel = self.hovered_panel if self.hovered else self.normal
        label = self.hover_label if self.hovered else self.label
        panel.draw(surface, self.rect.x, self.rect.y)
        label.draw(surface, self.rect.centerx, self.rect.centery)


class Slider:
    def __init__(
        self,
        width: int = 300,
        height: int = 40,
        value: float = 0.5,
        style: int = 6,
    ) -> None:
        self.panel = Panel(width, height, style, transparent=True)
        self.rect = pygame.Rect(0, 0, width, height)
        self.value = value
        self.dragging = False
        self.on_change: callable = lambda v: None
        self.value_label = Label(f"{int(value * 100)}%", size=14)

    def set_position(self, x: int, y: int) -> None:
        self.rect.center = (x, y)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])

    def _update_value(self, mouse_x: int) -> None:
        margin = 12
        inner_x = self.rect.x + margin
        inner_w = self.rect.width - 2 * margin
        self.value = max(0.0, min(1.0, (mouse_x - inner_x) / inner_w))
        self.value_label.set_text(f"{int(self.value * 100)}%")
        self.on_change(self.value)

    def draw(self, surface: pygame.Surface) -> None:
        self.panel.draw(surface, self.rect.x, self.rect.y)

        margin = 12
        inner_x = self.rect.x + margin
        inner_w = self.rect.width - 2 * margin
        fill_w = int(inner_w * self.value)
        fill_rect = pygame.Rect(inner_x, self.rect.centery - 4, fill_w, 8)
        pygame.draw.rect(surface, (180, 180, 200), fill_rect, border_radius=3)

        knob_x = inner_x + fill_w
        pygame.draw.circle(surface, (255, 255, 255), (knob_x, self.rect.centery), 8)

        self.value_label.draw(surface, self.rect.right + 30, self.rect.centery)


class Toggle:
    def __init__(
        self,
        width: int = 80,
        height: int = 40,
        active: bool = False,
        style: int = 6,
    ) -> None:
        self.panel = Panel(width, height, style, transparent=True)
        self.rect = pygame.Rect(0, 0, width, height)
        self.active = active
        self.on_change: callable = lambda v: None

    def set_position(self, x: int, y: int) -> None:
        self.rect.center = (x, y)

    def handle_event(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.active = not self.active
            self.on_change(self.active)

    def draw(self, surface: pygame.Surface) -> None:
        self.panel.draw(surface, self.rect.x, self.rect.y)

        margin = 8
        knob_w = (self.rect.width - margin * 3) // 2
        knob_h = self.rect.height - margin * 2
        if self.active:
            knob_x = self.rect.x + self.rect.width - margin - knob_w
            color = (120, 200, 120)
        else:
            knob_x = self.rect.x + margin
            color = (100, 100, 100)

        knob_rect = pygame.Rect(knob_x, self.rect.y + margin, knob_w, knob_h)
        pygame.draw.rect(surface, color, knob_rect, border_radius=4)
