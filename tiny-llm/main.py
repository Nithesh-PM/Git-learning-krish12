import random
import sys

import pygame


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SIZE = 40
PLAYER_SPEED = 300
COIN_SIZE = 20


def random_coin_position() -> tuple[int, int]:
    return (
        random.randint(0, SCREEN_WIDTH - COIN_SIZE),
        random.randint(0, SCREEN_HEIGHT - COIN_SIZE),
    )


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Coin Collector")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    player = pygame.Rect(
        (SCREEN_WIDTH - PLAYER_SIZE) // 2,
        (SCREEN_HEIGHT - PLAYER_SIZE) // 2,
        PLAYER_SIZE,
        PLAYER_SIZE,
    )
    coin = pygame.Rect(*random_coin_position(), COIN_SIZE, COIN_SIZE)
    score = 0
    running = True

    while running:
        delta_time = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            running = False

        horizontal = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        vertical = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(
            keys[pygame.K_UP] or keys[pygame.K_w]
        )
        player.x += round(horizontal * PLAYER_SPEED * delta_time)
        player.y += round(vertical * PLAYER_SPEED * delta_time)
        player.clamp_ip(screen.get_rect())

        if player.colliderect(coin):
            score += 1
            coin.update(*random_coin_position(), COIN_SIZE, COIN_SIZE)

        screen.fill((25, 30, 45))
        pygame.draw.rect(screen, (80, 170, 255), player, border_radius=6)
        pygame.draw.ellipse(screen, (255, 205, 65), coin)
        score_text = font.render(f"Score: {score}", True, (245, 245, 245))
        screen.blit(score_text, (16, 16))
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
