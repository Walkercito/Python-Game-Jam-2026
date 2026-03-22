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
PLAYER_ACCELERATION = 2200.0
PLAYER_FRICTION = 10.0
PLAYER_MAX_SPEED = 600.0
PLAYER_GRAVITY = 1800.0
PLAYER_JUMP_FORCE = -720.0
PLAYER_FAST_FALL = 900.0
PLAYER_ANIMATION_SPEED = 0.1

# Squash & stretch
SQUASH_FACTOR = 0.65
STRETCH_FACTOR = 1.3
SQUASH_DURATION = 0.1
STRETCH_DURATION = 0.12

# Input bindings
P1_KEYS = {"left": "a", "right": "d", "jump": "w", "down": "s"}
P2_KEYS = {"left": "[1]", "right": "[3]", "jump": "[5]", "down": "[2]"}

# Split screen
SPLIT_THRESHOLD = 350.0
SPLIT_MERGE_THRESHOLD = 300.0
