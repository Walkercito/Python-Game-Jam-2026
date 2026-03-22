from core.engine import Engine


def main():
    game = Engine()
    game.load_map("assets/tiled/tutorial_001.tmx")
    game.run()


if __name__ == "__main__":
    main()
