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
from core.doors import CoopDoorManager, DoorManager
from core.hud import ZoneAnnouncement
from core.interactable import BreakableManager, PressurePlateManager, SignDialog, SignManager
from core.map_loader import TMXMap
from core.moving_platform import MovingPlatformManager
from core.player import Player
from core.portal import Portal
from core.resource import resource_path
from core.scene import Scene, SceneManager
from core.tutorial import TutorialManager
from core.vfx import VFXAnimation, load_vfx_frames


class BaseGameplay(Scene):
    def __init__(self, manager: SceneManager, level_id: str = "tutorial_001") -> None:
        super().__init__(manager)
        self.level_id = level_id
        level = LEVELS[level_id]

        self.map = TMXMap(str(resource_path(level["map"])), zoom=level.get("zoom"))

        from core.audio import play_music

        play_music(level_id)

        spawn_a = self.map.get_spawn("A")
        spawn_b = self.map.get_spawn("B")
        self.spawn_x = spawn_a[0] if spawn_a else self.map.offset[0] + self.map.scaled_size[0] // 2
        self.spawn_y = spawn_a[1] if spawn_a else self.map.offset[1] + self.map.scaled_size[1] // 2
        self.spawn_b_x = spawn_b[0] if spawn_b else self.spawn_x
        self.spawn_b_y = spawn_b[1] if spawn_b else self.spawn_y

        self.players: list[Player] = []  # subclass fills this

        self.landing_frames = load_vfx_frames(
            str(resource_path("assets/vfx/landing")), scale=self.map.scale
        )
        self.vfx_list: list[VFXAnimation] = []
        self.split_screen = SplitScreen()
        self.zone_announcement = ZoneAnnouncement(level["zone_subtitle"], level["zone_title"])

        all_rects = list(self.map.sign_rects)
        all_texts = dict(level.get("signs", {}))

        npc_config = level.get("npcs", {})
        for layer_name, rect in self.map.npc_rects:
            npc_texts = npc_config.get(layer_name, {})
            # Count how many of this NPC type we've seen
            count = sum(1 for n, _ in self.map.npc_rects if n == layer_name)
            idx_in_layer = sum(1 for r in all_rects if r == rect) if count > 1 else 0
            text = npc_texts.get(idx_in_layer, "...")
            all_texts[len(all_rects)] = text
            all_rects.append(rect)

        self.sign_manager = SignManager(all_rects, all_texts)
        self.sign_dialogs = [SignDialog(), SignDialog()]

        self.pressure_plates = PressurePlateManager(self.map.pressure_rects, self.map.scale)
        self.breakables = BreakableManager(self.map.get_layer_tiles("BrakablePlatform"))

        self.door_manager = DoorManager(
            self.map.get_layer_tiles("Door"),
            self.map.door_pressure_rects,
            self.map.scale,
        )

        self.coop_doors = CoopDoorManager(
            self.map.get_layer_tiles("SecondDoor"),
            self.map.second_door_pressure_rects,
            self.map.scale,
        )

        self.moving_platforms = MovingPlatformManager(
            self.map.get_layer_tiles("MovingPlatforms"),
            self.map.moving_platform_points,
        )

        portal_rects = self.map.portal_rects
        self.portal: Portal | None = None
        if portal_rects:
            self.portal = Portal(portal_rects[0], self.map.scale)
        self.next_level = level.get("next_level")
        self._portal_activated = False
        self._lava_timers = [0.0, 0.0]
        self._death_flash = [0.0, 0.0]
        self._on_platform_timer = 0.0  # hysteresis for platform music
        self._idle_timer = 0.0
        self._idle_stage = 0  # 0=waiting, 1=still played, 2=still_2 played
        self._players_moved = False
        self._voice_channel: pygame.mixer.Channel | None = None

        self.tutorial: TutorialManager | None = None
        if level.get("tutorial"):
            self.tutorial = TutorialManager(level.get("tutorial"))

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
        self.landing_frames = load_vfx_frames(
            str(resource_path("assets/vfx/landing")), scale=self.map.scale
        )
        self.vfx_list.clear()

        all_rects = list(self.map.sign_rects)
        for _layer_name, rect in self.map.npc_rects:
            all_rects.append(rect)
        self.sign_manager = SignManager(all_rects, self.sign_manager._texts)
        self.sign_dialogs = [SignDialog(), SignDialog()]
        self.pressure_plates = PressurePlateManager(self.map.pressure_rects, self.map.scale)
        self.breakables = BreakableManager(self.map.get_layer_tiles("BrakablePlatform"))
        self.door_manager = DoorManager(
            self.map.get_layer_tiles("Door"),
            self.map.door_pressure_rects,
            self.map.scale,
        )
        coop_was_opened = self.coop_doors._opened
        self.coop_doors = CoopDoorManager(
            self.map.get_layer_tiles("SecondDoor"),
            self.map.second_door_pressure_rects,
            self.map.scale,
        )
        self.coop_doors._opened = coop_was_opened
        self.moving_platforms = MovingPlatformManager(
            self.map.get_layer_tiles("MovingPlatforms"),
            self.map.moving_platform_points,
        )

        spawn_a = self.map.get_spawn("A")
        spawn_b = self.map.get_spawn("B")
        self.spawn_x = spawn_a[0] if spawn_a else self.map.offset[0] + self.map.scaled_size[0] // 2
        self.spawn_y = spawn_a[1] if spawn_a else self.map.offset[1] + self.map.scaled_size[1] // 2
        self.spawn_b_x = spawn_b[0] if spawn_b else self.spawn_x
        self.spawn_b_y = spawn_b[1] if spawn_b else self.spawn_y

        portal_was_active = self.portal.is_active if self.portal else False
        portal_rects = self.map.portal_rects
        if portal_rects:
            new_portal = Portal(portal_rects[0], self.map.scale)
            if portal_was_active:
                new_portal.state = self.portal.state
                new_portal.frame_index = self.portal.frame_index
                new_portal.p1_entered = self.portal.p1_entered
                new_portal.p2_entered = self.portal.p2_entered
            self.portal = new_portal

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

        collision = (
            self.map.collision_rects
            + self.door_manager.collision_rects()
            + self.coop_doors.collision_rects()
        )
        platforms = self.map.platform_rects + self.moving_platforms.rects()
        p.update(
            dt,
            collision,
            self.map.water_rects,
            stairs_rects=self.map.stairs_rects,
            lava_rects=self.map.lava_rects,
            platform_rects=platforms,
            breakable_rects=self.breakables.active_rects(),
        )

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
                if self._should_play_sfx(i):
                    from core.audio import play_sfx

                    play_sfx("error")
        else:
            self._lava_timers[i] = max(self._lava_timers[i] - dt * LAVA_DECAY_RATE, 0.0)

        map_bottom = self.map.offset[1] + self.map.scaled_size[1] + 200
        if p.pos.y > map_bottom and not p.dead:
            offset = -PLAYER_SPAWN_OFFSET if i == 0 else PLAYER_SPAWN_OFFSET
            p.respawn(self.spawn_x + offset, self.spawn_y)
            self.split_screen.shake_all(6.0, 0.2)

        if p.dead and p._death_timer < dt * 2:
            self._death_flash[i] = DEATH_ANIM_DURATION
            self.split_screen.shake_all(10.0, 0.3)
            if self._should_play_sfx(i):
                from core.audio import play_sfx

                play_sfx("impact")
        if p.death_complete:
            offset = -PLAYER_SPAWN_OFFSET if i == 0 else PLAYER_SPAWN_OFFSET
            p.respawn(self.spawn_x + offset, self.spawn_y)
            self._death_flash[i] = 0.0
        if self._death_flash[i] > 0:
            self._death_flash[i] = max(self._death_flash[i] - dt, 0.0)

        if p.just_landed and self.landing_frames and not p.in_water:
            self.vfx_list.append(VFXAnimation(self.landing_frames, p.rect.centerx, p.rect.bottom))
            self.split_screen.shake_all(LANDING_SHAKE_INTENSITY, LANDING_SHAKE_DURATION)

    def _update_world(self, dt: float) -> None:
        """Update world systems BEFORE player physics so positions are current."""
        self.moving_platforms.update(dt)
        self.door_manager.update(dt, *(p.rect for p in self.players))
        self.coop_doors.update(dt, [p.rect for p in self.players])

        from core.audio import play_music

        on_platform = False
        for p in self.players:
            probe = pygame.Rect(p.rect.x, p.rect.y, p.rect.width, p.rect.height + 6)
            if any(probe.colliderect(mr) for mr in self.moving_platforms.rects()):
                on_platform = True
                break

        if on_platform:
            self._on_platform_timer = 0.5
        elif self._on_platform_timer > 0:
            self._on_platform_timer -= dt

        if self._on_platform_timer > 0 and self.moving_platforms.platforms:
            play_music("moving_platform", fade_ms=800)
        else:
            play_music(self.level_id, fade_ms=800)

    def _update_shared(self, dt: float) -> None:
        for vfx in self.vfx_list:
            vfx.update(dt)
        self.vfx_list = [v for v in self.vfx_list if not v.finished]

        self.breakables.update(dt, *(p.rect for p in self.players))
        self.pressure_plates.update(dt, *(p.rect for p in self.players))

        if self.portal:
            all_pressed = all(p.activated for p in self.pressure_plates.plates)
            if all_pressed and not self._portal_activated:
                self.portal.activate()
                self._portal_activated = True
            self.portal.update(dt, self.players[0].rect, self.players[1].rect)

            if self.portal.is_done:
                self._on_level_complete()
                return

        if self.portal and (self.portal.p1_entered or self.portal.p2_entered):
            remaining = self.players[1] if self.portal.p1_entered else self.players[0]
            self.split_screen.update(dt, remaining.rect, remaining.rect)
        else:
            self.split_screen.update(dt, self.players[0].rect, self.players[1].rect)

        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.update(dt)

        for i, p in enumerate(self.players):
            text = self.sign_manager.get_active_text(p.rect)
            if text:
                self.sign_dialogs[i].show(text)
            else:
                self.sign_dialogs[i].hide()
            self.sign_dialogs[i].update(dt)

        if self.tutorial and len(self.players) >= 2:
            self.tutorial.update(dt, self.players[0], self.players[1])

        if not self._players_moved:
            anyone_moving = any(abs(p.velocity.x) > 10 for p in self.players)
            if anyone_moving:
                self._players_moved = True
            else:
                self._idle_timer += dt
                if self._idle_stage == 0 and self._idle_timer >= 30.0:
                    self._idle_stage = 1
                    self._play_voice("assets/audio/voice/still.mp3")
                elif self._idle_stage == 1 and self._idle_timer >= 120.0:
                    self._idle_stage = 2
                    self._play_voice("assets/audio/voice/still_2.mp3")

        if self._voice_channel and not self._voice_channel.get_busy():
            self._voice_channel = None
            from core.config.game_settings import settings as gs

            pygame.mixer.music.set_volume(gs.music_volume)

    def _play_voice(self, relative_path: str) -> None:
        from core.config.game_settings import settings
        from core.resource import resource_path

        path = resource_path(relative_path)
        if not path.exists():
            return

        pygame.mixer.music.set_volume(settings.music_volume * 0.15)

        sound = pygame.mixer.Sound(path)
        sound.set_volume(settings.sfx_volume)
        self._voice_channel = sound.play()

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
        self.moving_platforms.draw(surface, cam_offset)
        self.door_manager.draw(surface, cam_offset)
        self.coop_doors.draw(surface, cam_offset)
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
        if self.tutorial:
            for i, p in enumerate(self.players):
                if self.portal and self.portal.should_hide_player(i):
                    continue
                self.tutorial.draw_for_player(surface, i, p.rect, cam_offset)

    def _should_draw_player(self, index: int) -> bool:
        return True

    def _show_nametag(self, index: int) -> bool:
        return True

    def _should_play_sfx(self, player_index: int) -> bool:
        """Override in network gameplay to only play SFX for local player."""
        return True

    def _draw_player_hud(
        self, surface: pygame.Surface, player_index: int, center: tuple[int, int]
    ) -> None:
        sw, sh = surface.get_size()
        cx, cy = center

        flash = self._death_flash[player_index]
        if flash > 0.01:
            alpha = int(DEATH_FLASH_MAX_ALPHA * (flash / DEATH_ANIM_DURATION))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((*DEATH_FLASH_COLOR, alpha))
            surface.blit(overlay, (0, 0))

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

        self.sign_dialogs[player_index].draw_at(surface, cx, int(sh * SIGN_DIALOG_Y_RATIO))

    def _draw_shared_hud(self, surface: pygame.Surface) -> None:
        if self.zone_announcement and not self.zone_announcement.finished:
            self.zone_announcement.draw(surface)
        if self.portal:
            self.portal.draw_cutaway(surface)
            cam = self.split_screen.shared_cam.offset
            self.portal.draw_vignette(surface, cam)
