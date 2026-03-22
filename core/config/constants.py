SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Python Game Jam 2026"

# Map
LAYER_PROPERTIES: dict[str, dict] = {
    "Floor": {"collision": True},
    "Water": {"water": True, "speed_modifier": 0.4, "gravity_modifier": 0.3, "jump_modifier": 0.6},
}

# Player physics
PLAYER_SCALE = 6.0
PLAYER_ACCELERATION = 1600.0
PLAYER_FRICTION = 8.0
PLAYER_MAX_SPEED = 500.0
PLAYER_GRAVITY = 1400.0
PLAYER_JUMP_FORCE = -620.0
PLAYER_FAST_FALL = 600.0
PLAYER_ANIMATION_SPEED = 0.12
