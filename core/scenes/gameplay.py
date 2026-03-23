from core.config.constants import (
    P1_KEYS,
    P1_OUTLINE_LOCAL,
    P2_KEYS,
    P2_OUTLINE_LOCAL,
    PLAYER_SPAWN_OFFSET,
)
from core.player import Player
from core.scene import SceneManager
from core.scenes.base_gameplay import BaseGameplay


class Gameplay(BaseGameplay):
    def __init__(
        self,
        manager: SceneManager,
        level_id: str = "tutorial_001",
        p1_name: str = "Green",
        p2_name: str = "Orange",
    ) -> None:
        super().__init__(manager, level_id)
        self._p1_name = p1_name
        self._p2_name = p2_name

        self.player1 = Player(
            self.spawn_x - PLAYER_SPAWN_OFFSET,
            self.spawn_y,
            keys=P1_KEYS,
            outline_color=P1_OUTLINE_LOCAL,
            character="green",
            name=p1_name,
        )
        self.player2 = Player(
            self.spawn_x + PLAYER_SPAWN_OFFSET,
            self.spawn_y,
            keys=P2_KEYS,
            outline_color=P2_OUTLINE_LOCAL,
            character="orange",
            name=p2_name,
        )
        self.players = [self.player1, self.player2]
        self._sync_player_scales()

    def _on_level_complete(self) -> None:
        if self.next_level:
            self.manager.replace(
                Gameplay(self.manager, self.next_level, self._p1_name, self._p2_name)
            )
        else:
            from core.scenes.main_menu import MainMenu

            self.manager.replace(MainMenu(self.manager))

    def update(self, dt: float) -> None:
        for i, p in enumerate(self.players):
            self._update_player(i, p, dt)
        self._update_shared(dt)

    def draw(self, surface) -> None:
        self.split_screen.render(
            surface,
            self._draw_world,
            self.player1.rect,
            self.player2.rect,
            hud_fn=self._draw_player_hud,
        )
        self._draw_shared_hud(surface)
