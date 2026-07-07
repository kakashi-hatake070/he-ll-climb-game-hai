"""Application entry point for Hill Climb Clone."""

from __future__ import annotations

import pygame

from game import Game
from settings import HEIGHT, FPS, WIDTH, WINDOW_TITLE


def main() -> None:
    """Create the game and run the main loop."""

    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    try:
        pygame.mixer.init()
    except pygame.error:
        pass
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Game(screen)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        running = game.handle_events()
        game.update(dt)
        game.render()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
