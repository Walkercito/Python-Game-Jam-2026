import pygame

from core.config.game_settings import settings
from core.gui import Button, Divider, Label, TextInput, Toggle
from core.network import (
    DEFAULT_PORT,
    GameClient,
    GameServer,
    NgrokTunnel,
    PartyBroadcaster,
    PartyFinder,
    generate_party_code,
)
from core.scene import Scene, SceneManager

BG_COLOR = (14, 7, 27)


class HostLobby(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        self.title = Label("Host Party", size=46)
        self.div_l = Divider(scale=0.9, style=3, fade=True)
        self.div_r = Divider(scale=0.9, style=3, fade=True)
        self.div_r.image = pygame.transform.flip(self.div_r.image, True, False)

        self.name_label = Label("Your Name", size=24)
        self.name_input = TextInput(width=320, height=54, placeholder="Enter name...", font_size=22)

        # Internet toggle
        self.internet_label = Label("Internet", size=20)
        self.internet_toggle = Toggle(width=70, height=36, active=False, style=6)
        self.internet_toggle.on_change = lambda _v: None  # just a flag

        self.code_label = Label("", size=48)
        self.code_hint = Label("", size=16, color=(160, 155, 140))
        self.internet_url_label = Label("", size=22, color=(120, 200, 120))
        self.status_label = Label("", size=22, color=(180, 175, 160))
        self.players_label = Label("", size=24)

        self.host_btn = Button(
            "Create Party", width=320, height=66, font_size=28, variant="primary"
        )
        self.host_btn.callback = self._on_host

        self.start_btn = Button("Start Game", width=320, height=66, font_size=28, variant="primary")
        self.start_btn.callback = self._on_start

        self.back_btn = Button("Back", width=240, height=58, font_size=24, variant="secondary")
        self.back_btn.callback = self._on_back

        self.server: GameServer | None = None
        self.client: GameClient | None = None
        self.broadcaster: PartyBroadcaster | None = None
        self.tunnel: NgrokTunnel | None = None
        self.party_code = ""
        self.hosting = False
        self.widgets: list = [
            self.name_input,
            self.internet_toggle,
            self.host_btn,
            self.back_btn,
        ]

        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.name_input.set_position(cx, cy - 60)
        self.internet_toggle.set_position(cx + 60, cy + 10)
        self.host_btn.set_position(cx, cy + 80)
        self.start_btn.set_position(cx, cy + 200)
        self.back_btn.set_position(cx, cy + 300)

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _on_host(self) -> None:
        name = self.name_input.text.strip() or "Host"
        self.party_code = generate_party_code()

        self.server = GameServer()
        self.server.start_background()

        self.broadcaster = PartyBroadcaster(self.party_code, DEFAULT_PORT, name)
        self.broadcaster.start()

        self.client = GameClient()
        self.client.join("127.0.0.1", DEFAULT_PORT, name)

        self.hosting = True
        display_code = f"{self.party_code[:3]}-{self.party_code[3:]}"
        self.code_label.set_text(display_code)
        self.code_hint.set_text("LAN party code")
        self.status_label.set_text("Waiting for player...")

        # Internet mode
        if self.internet_toggle.active:
            if NgrokTunnel.is_available():
                self.tunnel = NgrokTunnel()
                self.tunnel.start()
                self.internet_url_label.set_text("Starting tunnel...")
            else:
                self.internet_url_label.set_text("ngrok not installed")
                self.internet_url_label.color = (200, 80, 80)
                self.internet_url_label.set_text("ngrok not installed")

        self.copy_btn = Button("Copy Code", width=200, height=50, font_size=18, variant="secondary")
        self.copy_btn.callback = self._on_copy_code
        self.copy_url_btn = Button(
            "Copy URL", width=200, height=50, font_size=18, variant="secondary"
        )
        self.copy_url_btn.callback = self._on_copy_url
        self.copied_label = Label("", size=16, color=(120, 200, 120))
        self.widgets = [self.copy_btn, self.copy_url_btn, self.start_btn, self.back_btn]

    def _copy_to_clipboard(self, text: str) -> None:
        pygame.scrap.put_text(text)
        self.copied_label.set_text("Copied!")

    def _on_copy_code(self) -> None:
        self._copy_to_clipboard(self.party_code)

    def _on_copy_url(self) -> None:
        if self.tunnel and self.tunnel.public_url:
            self._copy_to_clipboard(self.tunnel.public_url)

    def _on_start(self) -> None:
        if self.client and self.client.has_remote_player:
            self.client.send({"action": "start_game"})

    def _on_back(self) -> None:
        if self.broadcaster:
            self.broadcaster.stop()
            self.broadcaster = None
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None
        if self.server:
            self.server.stop_sync()
            self.server = None
        self.client = None
        self.hosting = False
        self.manager.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        for w in self.widgets:
            w.handle_event(event)

    def update(self, dt: float) -> None:
        if self.client:
            self.client.pump()
            if self.client.game_started:
                if self.broadcaster:
                    self.broadcaster.stop()
                self._start_network_game()

        # Poll ngrok tunnel status
        if self.tunnel and not self.tunnel.ready and not self.tunnel.error:
            self.internet_url_label.set_text("Starting tunnel...")
        elif self.tunnel and self.tunnel.ready:
            self.internet_url_label.set_text(self.tunnel.public_url)
        elif self.tunnel and self.tunnel.error:
            self.internet_url_label.set_text(self.tunnel.error)

    def _start_network_game(self) -> None:
        from core.scenes.network_gameplay import NetworkGameplay

        self.manager.replace(NetworkGameplay(self.manager, self.client, self.server, is_host=True))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        sw, _sh = surface.get_size()
        cx = sw // 2
        cy = _sh // 2
        title_y = cy - 200

        title_gap = self.title.rect.width // 2 + 100
        self.div_l.draw(surface, cx - title_gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.div_r.draw(surface, cx + title_gap, title_y)

        if not self.hosting:
            self.name_label.draw(surface, cx, cy - 100)
            self.name_input.draw(surface)
            self.internet_label.draw(surface, cx - 30, cy + 10)
            self.internet_toggle.draw(surface)
            self.host_btn.draw(surface)
        else:
            # LAN code
            self.code_label.draw(surface, cx, cy - 90)
            self.code_hint.draw(surface, cx, cy - 55)
            self.copy_btn.set_position(cx - 110, cy - 20)
            self.copy_btn.draw(surface)

            # Internet URL (if tunnel active)
            if self.tunnel:
                self.internet_url_label.draw(surface, cx, cy + 30)
                if self.tunnel.ready:
                    self.copy_url_btn.set_position(cx + 110, cy - 20)
                    self.copy_url_btn.draw(surface)

            self.copied_label.draw(surface, cx, cy + 60)

            if self.client and self.client.lobby_players:
                names = [p["name"] for p in self.client.lobby_players]
                self.players_label.set_text(" & ".join(names))
                self.players_label.draw(surface, cx, cy + 100)

            if self.client and self.client.has_remote_player:
                self.status_label.set_text("Ready!")
                self.status_label.draw(surface, cx, cy + 130)
                self.start_btn.set_position(cx, cy + 200)
                self.start_btn.draw(surface)
            else:
                self.status_label.draw(surface, cx, cy + 130)

        self.back_btn.draw(surface)


class JoinLobby(Scene):
    def __init__(self, manager: SceneManager) -> None:
        super().__init__(manager)

        self.title = Label("Join Party", size=46)
        self.div_l = Divider(scale=0.9, style=3, fade=True)
        self.div_r = Divider(scale=0.9, style=3, fade=True)
        self.div_r.image = pygame.transform.flip(self.div_r.image, True, False)

        self.name_label = Label("Your Name", size=24)
        self.name_input = TextInput(width=320, height=54, placeholder="Enter name...", font_size=22)

        self.code_label = Label("Party Code or URL", size=24)
        self.code_input = TextInput(
            width=320, height=54, placeholder="ABC-123 or address", max_length=40, font_size=22
        )

        self.status_label = Label("", size=22, color=(180, 175, 160))
        self.players_label = Label("", size=24)

        self.join_btn = Button("Connect", width=320, height=66, font_size=28, variant="primary")
        self.join_btn.callback = self._on_find

        self.back_btn = Button("Back", width=240, height=58, font_size=24, variant="secondary")
        self.back_btn.callback = self._on_back

        self.client: GameClient | None = None
        self.finder: PartyFinder | None = None
        self.phase = "input"
        self.player_name = ""
        self.widgets: list = [self.name_input, self.code_input, self.join_btn, self.back_btn]

        self._layout(*settings.screen_size)

    def _layout(self, sw: int, sh: int) -> None:
        cx = sw // 2
        cy = sh // 2

        self.name_input.set_position(cx, cy - 80)
        self.code_input.set_position(cx, cy + 10)
        self.join_btn.set_position(cx, cy + 100)
        self.back_btn.set_position(cx, cy + 260)

    def on_resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    def _on_find(self) -> None:
        self.player_name = self.name_input.text.strip() or "Player"
        raw = self.code_input.text.strip()

        # Direct IP/URL connect (for internet play via ngrok or IP)
        if "." in raw:
            host = raw.split(":")[0]
            port = int(raw.split(":")[1]) if ":" in raw else DEFAULT_PORT
            self.client = GameClient()
            self.client.join(host, port, self.player_name)
            self.phase = "connected"
            self.status_label.set_text("Connecting...")
            self.widgets = [self.back_btn]
            return

        # LAN party code discovery
        code = raw.upper().replace("-", "")
        if len(code) != 6:
            self.status_label.set_text("Enter a 6-char code or address")
            return

        self.finder = PartyFinder()
        self.finder.find(code)
        self.phase = "searching"
        self.status_label.set_text("Searching on LAN...")
        self.widgets = [self.back_btn]

    def _on_back(self) -> None:
        if self.finder:
            self.finder.searching = False
        self.client = None
        self.manager.pop()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return
        for w in self.widgets:
            w.handle_event(event)

    def update(self, dt: float) -> None:
        if self.phase == "searching" and self.finder:
            if self.finder.found_host:
                self.client = GameClient()
                self.client.join(self.finder.found_host, self.finder.found_port, self.player_name)
                self.phase = "connected"
                self.status_label.set_text("Connecting...")
            elif self.finder.error:
                self.status_label.set_text(self.finder.error)
                self.phase = "input"
                self.widgets = [self.name_input, self.code_input, self.join_btn, self.back_btn]

        if self.client:
            self.client.pump()
            if self.client.server_full:
                self.status_label.set_text("Party is full!")
            elif self.client.was_connected and not self.client.connected:
                from core.scenes.disconnected import Disconnected

                self.manager.replace(Disconnected(self.manager, "Lost connection to host"))
                return
            elif self.client.connected:
                self.status_label.set_text("Waiting for host to start...")
            if self.client.game_started:
                self._start_network_game()

    def _start_network_game(self) -> None:
        from core.scenes.network_gameplay import NetworkGameplay

        self.manager.replace(NetworkGameplay(self.manager, self.client, server=None, is_host=False))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        sw, _sh = surface.get_size()
        cx = sw // 2
        cy = _sh // 2
        title_y = cy - 200

        title_gap = self.title.rect.width // 2 + 100
        self.div_l.draw(surface, cx - title_gap, title_y)
        self.title.draw(surface, cx, title_y)
        self.div_r.draw(surface, cx + title_gap, title_y)

        if self.phase == "input":
            self.name_label.draw(surface, cx, cy - 120)
            self.name_input.draw(surface)
            self.code_label.draw(surface, cx, cy - 30)
            self.code_input.draw(surface)
            self.join_btn.draw(surface)
        else:
            self.status_label.draw(surface, cx, cy - 20)
            if self.client and self.client.lobby_players:
                names = [p["name"] for p in self.client.lobby_players]
                self.players_label.set_text(" & ".join(names))
                self.players_label.draw(surface, cx, cy + 30)

        self.back_btn.draw(surface)
