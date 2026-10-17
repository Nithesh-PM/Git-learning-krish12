import math
import random
import sys
from pathlib import Path

import pygame


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60
HUD_HEIGHT = 68
WORLD_RECT = pygame.Rect(0, HUD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT)
PLAYER_SPEED = 225
PLAYER_RADIUS = 17
PISTOL_MAGAZINE = 12
PLAYER_MAX_HEALTH = 100

COLOURS = {
    "background": (19, 25, 29),
    "road": (29, 34, 37),
    "road_line": (72, 72, 59),
    "sidewalk": (50, 55, 54),
    "building": (38, 44, 44),
    "building_edge": (72, 77, 71),
    "player": (81, 170, 198),
    "zombie": (111, 148, 89),
    "runner": (174, 139, 79),
    "brute": (143, 85, 83),
    "bullet": (255, 220, 132),
    "accent": (218, 78, 67),
    "text": (232, 233, 220),
    "muted": (161, 170, 165),
}


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    colour: tuple[int, int, int],
    position: tuple[int, int],
    *,
    center: bool = False,
) -> pygame.Rect:
    image = font.render(text, True, colour)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(image, rect)
    return rect


def circle_hits_obstacle(
    position: pygame.Vector2, radius: int, obstacle: pygame.Rect
) -> bool:
    closest_x = max(obstacle.left, min(position.x, obstacle.right))
    closest_y = max(obstacle.top, min(position.y, obstacle.bottom))
    dx = position.x - closest_x
    dy = position.y - closest_y
    return dx * dx + dy * dy < radius * radius


def move_circle(
    position: pygame.Vector2,
    velocity: pygame.Vector2,
    radius: int,
    delta_time: float,
    obstacles: list[pygame.Rect],
) -> pygame.Vector2:
    result = position.copy()
    result.x += velocity.x * delta_time
    result.x = max(radius, min(SCREEN_WIDTH - radius, result.x))
    if any(circle_hits_obstacle(result, radius, obstacle) for obstacle in obstacles):
        result.x = position.x

    result.y += velocity.y * delta_time
    result.y = max(HUD_HEIGHT + radius, min(SCREEN_HEIGHT - radius, result.y))
    if any(circle_hits_obstacle(result, radius, obstacle) for obstacle in obstacles):
        result.y = position.y
    return result


class Obstacle:
    def __init__(self, rect: pygame.Rect, kind: str) -> None:
        self.rect = rect
        self.kind = kind

    def draw(self, surface: pygame.Surface) -> None:
        if self.kind == "car":
            pygame.draw.rect(surface, (50, 61, 63), self.rect, border_radius=8)
            inner = self.rect.inflate(-16, -15)
            pygame.draw.rect(surface, (31, 43, 47), inner, border_radius=5)
            pygame.draw.rect(surface, (108, 115, 106), self.rect, 2, border_radius=8)
            for x in (self.rect.left + 5, self.rect.right - 9):
                pygame.draw.rect(
                    surface, (17, 20, 21), (x, self.rect.top + 8, 5, 13)
                )
                pygame.draw.rect(
                    surface, (17, 20, 21), (x, self.rect.bottom - 21, 5, 13)
                )
        elif self.kind == "barricade":
            pygame.draw.rect(surface, (94, 72, 53), self.rect, border_radius=3)
            stripe_y = self.rect.centery
            pygame.draw.line(
                surface,
                (198, 135, 57),
                (self.rect.left + 3, stripe_y - 4),
                (self.rect.right - 3, stripe_y - 4),
                5,
            )
            pygame.draw.line(
                surface,
                (198, 135, 57),
                (self.rect.left + 3, stripe_y + 5),
                (self.rect.right - 3, stripe_y + 5),
                4,
            )
        else:
            pygame.draw.rect(surface, (72, 76, 69), self.rect, border_radius=2)
            pygame.draw.rect(
                surface, (103, 105, 91), self.rect, 2, border_radius=2
            )
            pygame.draw.line(
                surface,
                (52, 57, 52),
                self.rect.topleft,
                self.rect.bottomright,
                3,
            )


class Particle:
    def __init__(
        self,
        position: pygame.Vector2,
        colour: tuple[int, int, int],
        *,
        count: int = 6,
        speed: float = 95,
        lifetime: float = 0.32,
    ) -> None:
        self.pieces: list[
            tuple[pygame.Vector2, pygame.Vector2, int]
        ] = []
        for _ in range(count):
            velocity = pygame.Vector2()
            velocity.from_polar(
                (random.uniform(speed * 0.35, speed), random.uniform(0, math.tau))
            )
            self.pieces.append((position.copy(), velocity, random.randint(2, 4)))
        self.colour = colour
        self.lifetime = lifetime
        self.age = 0.0
        self.max_lifetime = lifetime

    def update(self, delta_time: float) -> None:
        self.age += delta_time
        drag = max(0, 1 - 4 * delta_time)
        for position, velocity, _ in self.pieces:
            position += velocity * delta_time
            velocity *= drag

    def draw(self, surface: pygame.Surface) -> None:
        remaining = max(0.0, 1 - self.age / self.max_lifetime)
        for position, _, base_radius in self.pieces:
            radius = max(1, round(base_radius * remaining))
            pygame.draw.circle(
                surface,
                self.colour,
                (round(position.x), round(position.y)),
                radius,
            )

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime


class Bullet:
    SPEED = 720
    RANGE = 780
    DAMAGE = 34

    def __init__(self, position: pygame.Vector2, direction: pygame.Vector2) -> None:
        self.position = position.copy()
        self.previous_position = position.copy()
        self.velocity = direction * self.SPEED
        self.travelled = 0.0
        self.alive = True

    def update(self, delta_time: float, obstacles: list[pygame.Rect]) -> None:
        self.previous_position = self.position.copy()
        step = self.velocity * delta_time
        self.position += step
        self.travelled += step.length()
        start = (round(self.previous_position.x), round(self.previous_position.y))
        end = (round(self.position.x), round(self.position.y))
        if (
            self.travelled >= self.RANGE
            or not WORLD_RECT.collidepoint(self.position.x, self.position.y)
            or any(obstacle.clipline(start, end) for obstacle in obstacles)
        ):
            self.alive = False

    def hits_circle(self, center: pygame.Vector2, radius: int) -> bool:
        segment = self.position - self.previous_position
        length_squared = segment.length_squared()
        if length_squared == 0:
            closest = self.position
        else:
            projection = (center - self.previous_position).dot(segment) / length_squared
            closest = self.previous_position + segment * max(0.0, min(1.0, projection))
        return (center - closest).length_squared() <= radius * radius

    def draw(self, surface: pygame.Surface) -> None:
        tail = self.position - self.velocity.normalize() * 10
        pygame.draw.line(
            surface,
            (187, 127, 67),
            (round(tail.x), round(tail.y)),
            (round(self.position.x), round(self.position.y)),
            2,
        )
        pygame.draw.circle(
            surface,
            COLOURS["bullet"],
            (round(self.position.x), round(self.position.y)),
            3,
        )


class Player:
    def __init__(self) -> None:
        self.position = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.62)
        self.health = PLAYER_MAX_HEALTH
        self.magazine = PISTOL_MAGAZINE
        self.reserve_ammo = 72
        self.reload_time = 0.0
        self.damage_flash = 0.0
        self.shot_cooldown = 0.0
        self.radius = PLAYER_RADIUS

    def update(self, delta_time: float, keys, obstacles: list[pygame.Rect]) -> None:
        movement = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if movement.length_squared() > 0:
            movement = movement.normalize() * PLAYER_SPEED
        self.position = move_circle(
            self.position, movement, self.radius, delta_time, obstacles
        )
        self.shot_cooldown = max(0.0, self.shot_cooldown - delta_time)
        self.damage_flash = max(0.0, self.damage_flash - delta_time)
        was_reloading = self.reload_time > 0
        self.reload_time = max(0.0, self.reload_time - delta_time)
        if was_reloading and self.reload_time == 0:
            self.finish_reload()
        if self.reload_time == 0 and self.magazine == 0 and self.reserve_ammo > 0:
            self.reload()

    def reload(self) -> None:
        if self.reload_time > 0 or self.magazine >= PISTOL_MAGAZINE:
            return
        if self.reserve_ammo <= 0:
            return
        self.reload_time = 1.05

    def finish_reload(self) -> None:
        needed = PISTOL_MAGAZINE - self.magazine
        loaded = min(needed, self.reserve_ammo)
        self.magazine += loaded
        self.reserve_ammo -= loaded
        self.reload_time = 0

    def shoot(
        self, target: tuple[int, int], sound: pygame.mixer.Sound | None
    ) -> Bullet | None:
        if self.shot_cooldown > 0 or self.reload_time > 0 or self.magazine <= 0:
            return None
        aim = pygame.Vector2(target) - self.position
        if aim.length_squared() == 0:
            return None
        direction = aim.normalize()
        self.magazine -= 1
        self.shot_cooldown = 0.23
        if sound is not None:
            sound.play()
        muzzle = self.position + direction * (self.radius + 7)
        return Bullet(muzzle, direction)

    def take_damage(self, amount: int) -> None:
        self.health = max(0, self.health - amount)
        self.damage_flash = 0.2

    def draw(self, surface: pygame.Surface, target: tuple[int, int]) -> None:
        aim = pygame.Vector2(target) - self.position
        if aim.length_squared() == 0:
            aim = pygame.Vector2(1, 0)
        direction = aim.normalize()
        gun_start = self.position + direction * 9
        gun_end = self.position + direction * 30
        pygame.draw.line(surface, (38, 43, 42), gun_start, gun_end, 7)
        pygame.draw.line(surface, (137, 143, 129), gun_start, gun_end, 3)
        body_colour = (255, 164, 123) if self.damage_flash > 0 else COLOURS["player"]
        center = (round(self.position.x), round(self.position.y))
        pygame.draw.circle(surface, (14, 18, 19), center, self.radius + 3)
        pygame.draw.circle(surface, body_colour, center, self.radius)
        pygame.draw.circle(surface, (197, 210, 195), center, 5)
        pygame.draw.circle(
            surface,
            (25, 31, 32),
            (round(self.position.x + direction.x * 7), round(self.position.y + direction.y * 7)),
            2,
        )


class Zombie:
    TYPES = {
        "walker": {"speed": 66, "health": 55, "radius": 16, "damage": 9, "colour": COLOURS["zombie"], "points": 10},
        "runner": {"speed": 112, "health": 34, "radius": 13, "damage": 7, "colour": COLOURS["runner"], "points": 15},
        "brute": {"speed": 43, "health": 112, "radius": 21, "damage": 18, "colour": COLOURS["brute"], "points": 25},
    }

    def __init__(self, kind: str, position: pygame.Vector2, elapsed: float) -> None:
        stats = self.TYPES[kind]
        self.kind = kind
        self.position = position
        self.speed = stats["speed"] * (1 + min(elapsed / 360, 0.2))
        self.health = stats["health"]
        self.max_health = stats["health"]
        self.radius = stats["radius"]
        self.damage = stats["damage"]
        self.colour = stats["colour"]
        self.points = stats["points"]
        self.attack_cooldown = random.uniform(0.1, 0.7)
        self.hit_flash = 0.0
        self.walk_phase = random.random() * math.tau

    def update(
        self,
        delta_time: float,
        player: Player,
        obstacles: list[pygame.Rect],
    ) -> int:
        self.walk_phase += delta_time * 7
        self.hit_flash = max(0.0, self.hit_flash - delta_time)
        self.attack_cooldown = max(0.0, self.attack_cooldown - delta_time)
        offset = player.position - self.position
        distance = offset.length()
        if distance <= self.radius + player.radius + 3:
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 0.9
                return self.damage
            return 0
        if distance > 0:
            direction = offset / distance
            velocity = direction * self.speed
            self.position = move_circle(
                self.position, velocity, self.radius, delta_time, obstacles
            )
        return 0

    def hit(self, damage: int) -> bool:
        self.health -= damage
        self.hit_flash = 0.1
        return self.health <= 0

    def draw(self, surface: pygame.Surface) -> None:
        x, y = round(self.position.x), round(self.position.y)
        wobble = round(math.sin(self.walk_phase) * 2)
        colour = (205, 202, 174) if self.hit_flash > 0 else self.colour
        pygame.draw.ellipse(
            surface,
            (18, 22, 20),
            (x - self.radius, y + self.radius - 3, self.radius * 2, 8),
        )
        pygame.draw.circle(surface, colour, (x, y + wobble), self.radius)
        pygame.draw.circle(
            surface,
            (51, 62, 47),
            (x + self.radius // 3, y - 3 + wobble),
            max(3, self.radius // 5),
        )
        pygame.draw.circle(
            surface,
            (230, 202, 142),
            (x + self.radius // 3, y - 3 + wobble),
            2,
        )
        if self.health < self.max_health:
            bar = pygame.Rect(x - self.radius, y - self.radius - 8, self.radius * 2, 4)
            pygame.draw.rect(surface, (44, 26, 24), bar)
            bar.width = round(bar.width * max(0, self.health) / self.max_health)
            pygame.draw.rect(surface, (192, 69, 61), bar)


class AmmoPickup:
    def __init__(self, position: pygame.Vector2) -> None:
        self.position = position
        self.amount = random.choice((18, 24, 30))
        self.lifetime = 24.0
        self.phase = random.random() * math.tau

    def update(self, delta_time: float) -> None:
        self.lifetime -= delta_time
        self.phase += delta_time * 3

    def draw(self, surface: pygame.Surface) -> None:
        x, y = round(self.position.x), round(self.position.y + math.sin(self.phase) * 3)
        rect = pygame.Rect(x - 10, y - 8, 20, 16)
        pygame.draw.rect(surface, (18, 24, 21), rect.inflate(4, 4), border_radius=3)
        pygame.draw.rect(surface, (111, 145, 88), rect, border_radius=3)
        pygame.draw.rect(surface, (194, 211, 151), rect, 2, border_radius=3)
        pygame.draw.line(surface, (36, 49, 35), (x - 5, y), (x + 5, y), 3)
        pygame.draw.line(surface, (36, 49, 35), (x, y - 5), (x, y + 5), 3)


class City:
    def __init__(self) -> None:
        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill(COLOURS["background"])
        pygame.draw.rect(
            self.background, COLOURS["road"], (0, 110, SCREEN_WIDTH, 196)
        )
        pygame.draw.rect(
            self.background, COLOURS["road"], (325, HUD_HEIGHT, 180, SCREEN_HEIGHT - HUD_HEIGHT)
        )
        pygame.draw.rect(
            self.background,
            COLOURS["sidewalk"],
            (0, 96, SCREEN_WIDTH, 14),
        )
        pygame.draw.rect(
            self.background,
            COLOURS["sidewalk"],
            (0, 306, SCREEN_WIDTH, 12),
        )
        pygame.draw.rect(
            self.background,
            COLOURS["sidewalk"],
            (311, HUD_HEIGHT, 14, SCREEN_HEIGHT - HUD_HEIGHT),
        )
        pygame.draw.rect(
            self.background,
            COLOURS["sidewalk"],
            (505, HUD_HEIGHT, 13, SCREEN_HEIGHT - HUD_HEIGHT),
        )
        for x in range(16, SCREEN_WIDTH, 64):
            pygame.draw.line(
                self.background, (35, 40, 39), (x, 113), (x + 16, 113), 2
            )
            pygame.draw.line(
                self.background, (35, 40, 39), (x, 303), (x + 16, 303), 2
            )
        for y in range(HUD_HEIGHT + 8, SCREEN_HEIGHT, 60):
            pygame.draw.line(
                self.background, (35, 40, 39), (328, y), (328, y + 20), 2
            )
            pygame.draw.line(
                self.background, (35, 40, 39), (502, y), (502, y + 20), 2
            )
        for _ in range(70):
            x = random.randrange(SCREEN_WIDTH)
            y = random.randrange(HUD_HEIGHT, SCREEN_HEIGHT)
            if not (95 <= y <= 319 or 310 <= x <= 518):
                pygame.draw.circle(
                    self.background,
                    random.choice(((29, 36, 35), (34, 39, 37), (27, 33, 33))),
                    (x, y),
                    random.choice((1, 2, 3)),
                )
        self.obstacles = [
            Obstacle(pygame.Rect(70, 156, 102, 50), "car"),
            Obstacle(pygame.Rect(736, 239, 122, 54), "car"),
            Obstacle(pygame.Rect(370, 378, 92, 30), "barricade"),
            Obstacle(pygame.Rect(611, 435, 70, 58), "wall"),
            Obstacle(pygame.Rect(790, 489, 90, 25), "barricade"),
            Obstacle(pygame.Rect(174, 445, 84, 44), "car"),
            Obstacle(pygame.Rect(652, 121, 40, 46), "wall"),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        for obstacle in self.obstacles:
            obstacle.draw(surface)

    @property
    def collision_rects(self) -> list[pygame.Rect]:
        return [obstacle.rect for obstacle in self.obstacles]

    def random_open_position(self, radius: int = 20) -> pygame.Vector2:
        for _ in range(100):
            position = pygame.Vector2(
                random.randint(radius + 8, SCREEN_WIDTH - radius - 8),
                random.randint(HUD_HEIGHT + radius + 8, SCREEN_HEIGHT - radius - 8),
            )
            if not any(
                circle_hits_obstacle(position, radius + 4, rect)
                for rect in self.collision_rects
            ):
                return position
        return pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.7)

    def edge_position(self, radius: int = 20) -> pygame.Vector2:
        edge = random.randrange(4)
        if edge == 0:
            return pygame.Vector2(random.randint(0, SCREEN_WIDTH), HUD_HEIGHT + radius)
        if edge == 1:
            return pygame.Vector2(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT - radius)
        if edge == 2:
            return pygame.Vector2(radius, random.randint(HUD_HEIGHT, SCREEN_HEIGHT))
        return pygame.Vector2(SCREEN_WIDTH - radius, random.randint(HUD_HEIGHT, SCREEN_HEIGHT))


class Game:
    MENU = "menu"
    INSTRUCTIONS = "instructions"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zombie Hunter - Last Light")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 30)
        self.font_large = pygame.font.Font(None, 64)
        self.font_title = pygame.font.Font(None, 82)
        self.state = self.MENU
        self.city = City()
        self.player = Player()
        self.zombies: list[Zombie] = []
        self.bullets: list[Bullet] = []
        self.pickups: list[AmmoPickup] = []
        self.particles: list[Particle] = []
        self.score = 0
        self.elapsed = 0.0
        self.spawn_timer = 0.0
        self.pickup_timer = 8.0
        self.kills = 0
        self.fire_held = False
        self.sound_effects = self.load_optional_sounds()
        self.buttons: dict[str, pygame.Rect] = {}

    @staticmethod
    def load_optional_sounds() -> dict[str, pygame.mixer.Sound]:
        sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
        except pygame.error as error:
            print(f"Optional audio is unavailable: {error}", file=sys.stderr)
            return sounds

        sounds_dir = Path(__file__).resolve().parent / "assets" / "sounds"
        for key, filename in (
            ("shoot", "shoot.wav"),
            ("hit", "hit.wav"),
            ("pickup", "pickup.wav"),
        ):
            path = sounds_dir / filename
            if path.is_file():
                try:
                    sounds[key] = pygame.mixer.Sound(str(path))
                except pygame.error as error:
                    print(f"Could not load optional sound {path.name}: {error}", file=sys.stderr)
        return sounds

    def reset(self) -> None:
        self.city = City()
        self.player = Player()
        self.zombies.clear()
        self.bullets.clear()
        self.pickups.clear()
        self.particles.clear()
        self.score = 0
        self.elapsed = 0.0
        self.spawn_timer = 1.2
        self.pickup_timer = 7.0
        self.kills = 0
        self.fire_held = False

    def run(self) -> None:
        running = True
        while running:
            delta_time = min(self.clock.tick(FPS) / 1000, 0.05)
            running = self.handle_events()
            if self.state == self.PLAYING:
                self.update(delta_time)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == self.PLAYING:
                    self.fire_held = True
                elif self.state in (self.MENU, self.INSTRUCTIONS, self.GAME_OVER):
                    if not self.handle_menu_click(event.pos):
                        return False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.fire_held = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.INSTRUCTIONS or self.state == self.PAUSED:
                        self.state = self.MENU
                    elif self.state == self.PLAYING:
                        self.state = self.PAUSED
                        self.fire_held = False
                    elif self.state in (self.GAME_OVER, self.MENU):
                        return False
                elif self.state == self.MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game()
                    elif event.key == pygame.K_i:
                        self.state = self.INSTRUCTIONS
                elif self.state == self.INSTRUCTIONS and event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.start_game()
                elif self.state == self.PAUSED and event.key in (
                    pygame.K_p,
                    pygame.K_RETURN,
                ):
                    self.state = self.PLAYING
                elif self.state == self.PLAYING and event.key == pygame.K_r:
                    self.player.reload()
                elif self.state == self.GAME_OVER and event.key in (
                    pygame.K_RETURN,
                    pygame.K_r,
                ):
                    self.start_game()
        return True

    def handle_menu_click(self, position: tuple[int, int]) -> bool:
        for name, rect in self.buttons.items():
            if rect.collidepoint(position):
                if name == "start" or name == "restart":
                    self.start_game()
                elif name == "instructions":
                    self.state = self.INSTRUCTIONS
                elif name == "back":
                    self.state = self.MENU
                elif name == "quit":
                    return False
        return True

    def start_game(self) -> None:
        self.reset()
        self.state = self.PLAYING

    def update(self, delta_time: float) -> None:
        self.elapsed += delta_time
        self.player.update(delta_time, pygame.key.get_pressed(), self.city.collision_rects)

        if self.fire_held or pygame.mouse.get_pressed()[0]:
            bullet = self.player.shoot(pygame.mouse.get_pos(), self.sound_effects.get("shoot"))
            if bullet is not None:
                self.bullets.append(bullet)
                self.particles.append(
                    Particle(bullet.position, (251, 189, 92), count=3, speed=45, lifetime=0.12)
                )

        interval = max(0.38, 1.8 - self.elapsed / 95)
        self.spawn_timer -= delta_time
        if self.spawn_timer <= 0:
            self.spawn_zombie()
            self.spawn_timer = interval * random.uniform(0.7, 1.25)

        for zombie in self.zombies:
            damage = zombie.update(delta_time, self.player, self.city.collision_rects)
            if damage:
                self.player.take_damage(damage)
                self.play_sound("hit")
                self.particles.append(
                    Particle(self.player.position, (211, 69, 61), count=7)
                )

        for bullet in self.bullets:
            bullet.update(delta_time, self.city.collision_rects)
            if not bullet.alive:
                continue
            for zombie in self.zombies:
                if bullet.hits_circle(zombie.position, zombie.radius + 4):
                    bullet.alive = False
                    defeated = zombie.hit(Bullet.DAMAGE)
                    self.particles.append(
                        Particle(bullet.position, (157, 189, 116), count=4)
                    )
                    if defeated:
                        self.score += zombie.points
                        self.kills += 1
                        self.zombies.remove(zombie)
                        self.particles.append(
                            Particle(
                                zombie.position,
                                (118, 151, 88),
                                count=13,
                                speed=120,
                                lifetime=0.55,
                            )
                        )
                        self.maybe_drop_ammo(zombie.position)
                    break

        self.bullets = [bullet for bullet in self.bullets if bullet.alive]
        self.pickup_timer -= delta_time
        if self.pickup_timer <= 0 and len(self.pickups) < 2:
            position = self.city.random_open_position()
            if (position - self.player.position).length() > 100:
                self.pickups.append(AmmoPickup(position))
            self.pickup_timer = random.uniform(15, 22)
        for pickup in self.pickups:
            pickup.update(delta_time)
            if (pickup.position - self.player.position).length() < self.player.radius + 16:
                self.player.reserve_ammo = min(180, self.player.reserve_ammo + pickup.amount)
                self.pickups.remove(pickup)
                self.score += 2
                self.play_sound("pickup")
                self.particles.append(
                    Particle(pickup.position, (183, 215, 133), count=9)
                )
        self.pickups = [pickup for pickup in self.pickups if pickup.lifetime > 0]
        for particle in self.particles:
            particle.update(delta_time)
        self.particles = [particle for particle in self.particles if particle.alive]

        if self.player.health <= 0:
            self.state = self.GAME_OVER
            self.fire_held = False

    def spawn_zombie(self) -> None:
        roll = random.random()
        if self.elapsed < 25 or roll < max(0.32, 0.66 - self.elapsed / 500):
            kind = "walker"
        elif roll < 0.82:
            kind = "runner"
        else:
            kind = "brute"
        self.zombies.append(
            Zombie(kind, self.city.edge_position(Zombie.TYPES[kind]["radius"]), self.elapsed)
        )

    def maybe_drop_ammo(self, position: pygame.Vector2) -> None:
        if self.kills % 5 == 0 and len(self.pickups) < 3:
            self.pickups.append(AmmoPickup(position.copy()))

    def play_sound(self, key: str) -> None:
        sound = self.sound_effects.get(key)
        if sound is not None:
            sound.play()

    def draw(self) -> None:
        self.screen.fill(COLOURS["background"])
        if self.state in (self.PLAYING, self.PAUSED, self.GAME_OVER):
            self.draw_world()
            self.draw_hud()
            if self.state == self.PAUSED:
                self.draw_overlay("PAUSED", "Press P or Enter to continue")
            elif self.state == self.GAME_OVER:
                self.draw_overlay("YOU WERE OVERRUN", "Press Enter or R to try again")
        elif self.state == self.INSTRUCTIONS:
            self.draw_instructions()
        else:
            self.draw_menu()

    def draw_world(self) -> None:
        self.city.draw(self.screen)
        for pickup in self.pickups:
            pickup.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)
        for zombie in self.zombies:
            zombie.draw(self.screen)
        self.player.draw(self.screen, pygame.mouse.get_pos())
        for particle in self.particles:
            particle.draw(self.screen)

    def draw_hud(self) -> None:
        pygame.draw.rect(self.screen, (15, 19, 21), (0, 0, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.screen, (76, 81, 75), (0, HUD_HEIGHT - 1), (SCREEN_WIDTH, HUD_HEIGHT - 1), 2)
        draw_text(self.screen, self.font_small, "HEALTH", COLOURS["muted"], (18, 10))
        health_rect = pygame.Rect(18, 34, 188, 16)
        pygame.draw.rect(self.screen, (52, 39, 38), health_rect, border_radius=4)
        health_fill = health_rect.copy()
        health_fill.width = round(health_rect.width * self.player.health / PLAYER_MAX_HEALTH)
        if health_fill.width:
            health_colour = (90, 177, 106) if self.player.health > 35 else (218, 90, 72)
            pygame.draw.rect(self.screen, health_colour, health_fill, border_radius=4)
        draw_text(
            self.screen,
            self.font_small,
            f"{self.player.health:03d}%",
            COLOURS["text"],
            (214, 31),
        )
        draw_text(self.screen, self.font_small, "PISTOL", COLOURS["muted"], (300, 10))
        ammo_colour = COLOURS["accent"] if self.player.magazine == 0 else COLOURS["text"]
        ammo_label = f"{self.player.magazine:02d} / {self.player.reserve_ammo:03d}"
        if self.player.reload_time > 0:
            ammo_label = "RELOADING..."
        draw_text(self.screen, self.font, ammo_label, ammo_colour, (300, 31))
        draw_text(self.screen, self.font_small, "SCORE", COLOURS["muted"], (510, 10))
        draw_text(self.screen, self.font, f"{self.score:06d}", COLOURS["text"], (510, 31))
        draw_text(self.screen, self.font_small, "SURVIVED", COLOURS["muted"], (672, 10))
        minutes, seconds = divmod(int(self.elapsed), 60)
        draw_text(self.screen, self.font, f"{minutes:02d}:{seconds:02d}", COLOURS["text"], (672, 31))
        draw_text(
            self.screen,
            self.font_small,
            f"THREATS: {len(self.zombies)}",
            (197, 126, 104),
            (823, 30),
        )
        if self.player.magazine == 0 and self.player.reserve_ammo == 0:
            draw_text(
                self.screen,
                self.font_small,
                "FIND AMMO",
                (245, 180, 93),
                (390, 48),
            )

    def draw_menu(self) -> None:
        self.draw_title_backdrop()
        draw_text(
            self.screen, self.font_title, "ZOMBIE", COLOURS["text"], (SCREEN_WIDTH // 2, 170), center=True
        )
        draw_text(
            self.screen,
            self.font_title,
            "HUNTER",
            COLOURS["accent"],
            (SCREEN_WIDTH // 2, 236),
            center=True,
        )
        draw_text(
            self.screen,
            self.font,
            "LAST LIGHT  |  SURVIVE THE OUTBREAK",
            COLOURS["muted"],
            (SCREEN_WIDTH // 2, 289),
            center=True,
        )
        self.buttons = {}
        self.draw_button("start", "START GAME", (SCREEN_WIDTH // 2, 374), width=245)
        self.draw_button("instructions", "INSTRUCTIONS", (SCREEN_WIDTH // 2, 434), width=245)
        self.draw_button("quit", "QUIT", (SCREEN_WIDTH // 2, 494), width=245)
        draw_text(
            self.screen,
            self.font_small,
            "WASD / ARROWS MOVE     MOUSE AIM     LEFT CLICK FIRE",
            COLOURS["muted"],
            (SCREEN_WIDTH // 2, 578),
            center=True,
        )

    def draw_instructions(self) -> None:
        self.draw_title_backdrop()
        draw_text(
            self.screen,
            self.font_large,
            "FIELD MANUAL",
            COLOURS["text"],
            (SCREEN_WIDTH // 2, 110),
            center=True,
        )
        instructions = [
            ("MOVE", "WASD or arrow keys. Use the open streets to outmaneuver the dead."),
            ("AIM & FIRE", "Point with your mouse. Hold the left button to fire the pistol."),
            ("RELOAD", "Press R to reload. Reloading starts automatically when the clip is empty."),
            ("SURVIVE", "Zombies grow faster and arrive more often. Avoid their attacks."),
            ("AMMO", "Walk over green supply cases or defeat five zombies to find ammo."),
            ("PAUSE", "Press Escape to pause. Press P or Enter to continue."),
        ]
        y = 196
        for heading, body in instructions:
            draw_text(self.screen, self.font, heading, (218, 155, 100), (168, y))
            draw_text(self.screen, self.font_small, body, COLOURS["text"], (168, y + 30))
            y += 61
        self.buttons = {}
        self.draw_button("back", "BACK", (SCREEN_WIDTH // 2, 590), width=180)

    def draw_title_backdrop(self) -> None:
        self.screen.fill((19, 25, 29))
        pygame.draw.rect(self.screen, (27, 33, 35), (0, 360, SCREEN_WIDTH, 180))
        pygame.draw.rect(self.screen, (48, 52, 49), (0, 536, SCREEN_WIDTH, 104))
        pygame.draw.line(self.screen, (86, 75, 60), (0, 536), (SCREEN_WIDTH, 536), 3)
        for x, width, height in ((45, 140, 244), (222, 120, 302), (620, 143, 265), (797, 130, 328)):
            building = pygame.Rect(x, 536 - height, width, height)
            pygame.draw.rect(self.screen, (31, 39, 40), building)
            pygame.draw.rect(self.screen, (62, 68, 63), building, 2)
            for wx in range(building.left + 16, building.right - 10, 30):
                for wy in range(building.top + 24, building.bottom - 14, 42):
                    pygame.draw.rect(self.screen, (78, 76, 61), (wx, wy, 8, 13))
        for x in range(30, SCREEN_WIDTH, 85):
            pygame.draw.line(self.screen, (48, 54, 51), (x, 544), (x + 9, 640), 2)

    def draw_button(
        self, name: str, label: str, center: tuple[int, int], *, width: int = 220
    ) -> None:
        rect = pygame.Rect(0, 0, width, 44)
        rect.center = center
        self.buttons[name] = rect
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = (91, 54, 48) if hovered else (35, 43, 43)
        border = (218, 110, 81) if hovered else (91, 98, 87)
        pygame.draw.rect(self.screen, fill, rect, border_radius=5)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=5)
        draw_text(self.screen, self.font, label, COLOURS["text"], rect.center, center=True)

    def draw_overlay(self, title: str, subtitle: str) -> None:
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 9, 11, 190))
        self.screen.blit(shade, (0, 0))
        draw_text(
            self.screen,
            self.font_large,
            title,
            COLOURS["accent"] if title.startswith("YOU") else COLOURS["text"],
            (SCREEN_WIDTH // 2, 264),
            center=True,
        )
        if title.startswith("YOU"):
            draw_text(
                self.screen,
                self.font,
                f"FINAL SCORE  {max(0, self.score):06d}",
                COLOURS["text"],
                (SCREEN_WIDTH // 2, 320),
                center=True,
            )
        draw_text(
            self.screen,
            self.font,
            subtitle,
            COLOURS["muted"],
            (SCREEN_WIDTH // 2, 369),
            center=True,
        )


def main() -> None:
    game = Game()
    try:
        game.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
