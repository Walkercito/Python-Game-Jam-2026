LEVELS: dict[str, dict] = {
    "tutorial_001": {
        "map": "assets/tiled/tutorial_001.tmx",
        "zone_subtitle": "Zone One",
        "zone_title": "Tutorial Valley",
        "signs": {
            0: "Stand on both plates to open the portal!",
        },
        "npcs": {
            "Lizard": {0: "You sssshouldn't be here.. *sssh*"},
        },
        "next_level": "level_001",
        "zoom": None,
        "tutorial": [
            {"keys": ["A", "D"], "text": "Move", "action": "move"},
            {"keys": ["W"], "text": "Jump", "action": "jump"},
            {"keys": ["W", "W"], "text": "Double jump at the peak!", "action": "double_jump"},
            {"keys": ["S"], "text": "Fast fall", "action": "fast_fall"},
        ],
    },
    "level_001": {
        "map": "assets/tiled/level_001.tmx",
        "zone_subtitle": "Zone Two",
        "zone_title": "The Farlands",
        "signs": {
            0: "Careful with the lava!",
            1: "Climb the stairs together",
            2: "These platforms won't hold long...",
            3: "Stand on both plates!",
        },
        "npcs": {
            "People": {0: "I'm freezing up here! My friend left me..."},
            "Duck": {0: "Oh my *quack*! This is nice"},
        },
        "next_level": "level_002",
        "zoom": 5.0,
    },
    "level_002": {
        "map": "assets/tiled/level_002.tmx",
        "zone_subtitle": "Zone 3",
        "zone_title": "The Crucible",
        "signs": {
            0: "Some doors may require to stay still",
        },
        "npcs": {
            "People": {0: "My friend tried to reach that plate alone... *he didn't make it.*"},
            "Duck": {0: "Quack! Watch out for the platforms!"},
            "Lizard": {0: "*Ssss...* careful up here..."},
        },
        "next_level": None,
        "zoom": 5.0,
    },
}
