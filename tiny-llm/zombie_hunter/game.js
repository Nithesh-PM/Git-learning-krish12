"use strict";

(() => {
  const WIDTH = 960;
  const HEIGHT = 640;
  const HUD_HEIGHT = 68;
  const PLAYER_RADIUS = 17;
  const PLAYER_SPEED = 225;
  const MAGAZINE_SIZE = 12;
  const MAX_HEALTH = 100;
  const TAU = Math.PI * 2;
  const canvas = document.querySelector("#game");
  const ctx = canvas.getContext("2d");

  const colours = {
    background: "#13191d",
    road: "#1d2225",
    player: "#51aac6",
    zombie: "#6f9459",
    runner: "#ae8b4f",
    brute: "#8f5553",
    bullet: "#ffdc84",
    accent: "#da4e43",
    text: "#e8e9dc",
    muted: "#a1aaa5",
  };

  const obstacleSpecs = [
    [70, 156, 102, 50, "car"],
    [736, 239, 122, 54, "car"],
    [370, 378, 92, 30, "barricade"],
    [611, 435, 70, 58, "wall"],
    [790, 489, 90, 25, "barricade"],
    [174, 445, 84, 44, "car"],
    [652, 121, 40, 46, "wall"],
  ];
  const zombieTypes = {
    walker: { speed: 66, health: 55, radius: 16, damage: 9, colour: colours.zombie, points: 10 },
    runner: { speed: 112, health: 34, radius: 13, damage: 7, colour: colours.runner, points: 15 },
    brute: { speed: 43, health: 112, radius: 21, damage: 18, colour: colours.brute, points: 25 },
  };

  const state = {
    screen: "menu",
    keys: new Set(),
    mouse: { x: WIDTH / 2, y: HEIGHT / 2, down: false },
    player: null,
    zombies: [],
    bullets: [],
    pickups: [],
    particles: [],
    obstacles: [],
    buttons: [],
    score: 0,
    kills: 0,
    elapsed: 0,
    spawnTimer: 0,
    pickupTimer: 7,
    lastTime: 0,
    flash: 0,
    message: "",
    messageTime: 0,
  };

  function makeCity() {
    state.obstacles = obstacleSpecs.map(([x, y, w, h, kind]) => ({ x, y, w, h, kind }));
  }

  function circleHitsRect(x, y, radius, rect) {
    const closestX = Math.max(rect.x, Math.min(x, rect.x + rect.w));
    const closestY = Math.max(rect.y, Math.min(y, rect.y + rect.h));
    const dx = x - closestX;
    const dy = y - closestY;
    return dx * dx + dy * dy < radius * radius;
  }

  function isOpen(x, y, radius) {
    return !state.obstacles.some((rect) => circleHitsRect(x, y, radius + 4, rect));
  }

  function openPosition(radius = 20) {
    for (let attempt = 0; attempt < 100; attempt += 1) {
      const x = radius + 8 + Math.random() * (WIDTH - 2 * radius - 16);
      const y = HUD_HEIGHT + radius + 8 + Math.random() * (HEIGHT - HUD_HEIGHT - 2 * radius - 16);
      if (isOpen(x, y, radius)) return { x, y };
    }
    return { x: WIDTH / 2, y: HEIGHT * 0.7 };
  }

  function moveEntity(entity, dx, dy) {
    let x = Math.max(entity.radius, Math.min(WIDTH - entity.radius, entity.x + dx));
    x = Math.max(entity.radius, Math.min(WIDTH - entity.radius, x));
    if (state.obstacles.some((rect) => circleHitsRect(x, entity.y, entity.radius, rect))) {
      x = entity.x;
    }

    let y = Math.max(HUD_HEIGHT + entity.radius, Math.min(HEIGHT - entity.radius, entity.y + dy));
    if (state.obstacles.some((rect) => circleHitsRect(x, y, entity.radius, rect))) {
      y = entity.y;
    }
    entity.x = x;
    entity.y = y;
  }

  function addParticles(x, y, colour, count = 6, speed = 95, lifetime = 0.32) {
    for (let index = 0; index < count; index += 1) {
      const angle = Math.random() * TAU;
      const magnitude = speed * (0.35 + Math.random() * 0.65);
      state.particles.push({
        x,
        y,
        vx: Math.cos(angle) * magnitude,
        vy: Math.sin(angle) * magnitude,
        radius: 2 + Math.random() * 2,
        colour,
        age: 0,
        lifetime,
      });
    }
  }

  function resetGame() {
    makeCity();
    state.player = {
      x: WIDTH / 2,
      y: HEIGHT * 0.62,
      radius: PLAYER_RADIUS,
      health: MAX_HEALTH,
      magazine: MAGAZINE_SIZE,
      reserve: 72,
      reload: 0,
      cooldown: 0,
      hurt: 0,
    };
    state.zombies = [];
    state.bullets = [];
    state.pickups = [];
    state.particles = [];
    state.score = 0;
    state.kills = 0;
    state.elapsed = 0;
    state.spawnTimer = 1.2;
    state.pickupTimer = 7;
    state.flash = 0;
    state.message = "";
    state.messageTime = 0;
    state.mouse.down = false;
  }

  function startGame() {
    resetGame();
    state.screen = "playing";
    canvas.focus();
  }

  function formatTime(seconds) {
    const whole = Math.floor(seconds);
    return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
  }

  function drawText(text, x, y, options = {}) {
    const { size = 20, colour = colours.text, align = "left", font = "Inter, Segoe UI, sans-serif", weight = 500 } = options;
    ctx.fillStyle = colour;
    ctx.font = `${weight} ${size}px ${font}`;
    ctx.textAlign = align;
    ctx.textBaseline = "middle";
    ctx.fillText(text, x, y);
  }

  function drawCity() {
    ctx.fillStyle = colours.background;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.fillStyle = "#1d2225";
    ctx.fillRect(0, 110, WIDTH, 196);
    ctx.fillRect(325, HUD_HEIGHT, 180, HEIGHT - HUD_HEIGHT);
    ctx.fillStyle = "#323736";
    ctx.fillRect(0, 96, WIDTH, 14);
    ctx.fillRect(0, 306, WIDTH, 12);
    ctx.fillRect(311, HUD_HEIGHT, 14, HEIGHT - HUD_HEIGHT);
    ctx.fillRect(505, HUD_HEIGHT, 13, HEIGHT - HUD_HEIGHT);

    ctx.strokeStyle = "#232827";
    ctx.lineWidth = 2;
    for (let x = 16; x < WIDTH; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 113);
      ctx.lineTo(x + 16, 113);
      ctx.moveTo(x, 303);
      ctx.lineTo(x + 16, 303);
      ctx.stroke();
    }
    for (let y = HUD_HEIGHT + 8; y < HEIGHT; y += 60) {
      ctx.beginPath();
      ctx.moveTo(328, y);
      ctx.lineTo(328, y + 20);
      ctx.moveTo(502, y);
      ctx.lineTo(502, y + 20);
      ctx.stroke();
    }
    for (let index = 0; index < 70; index += 1) {
      const x = (index * 137.5) % WIDTH;
      const y = HUD_HEIGHT + (index * 83.3) % (HEIGHT - HUD_HEIGHT);
      if ((y < 96 || y > 318) && (x < 311 || x > 518)) {
        ctx.fillStyle = ["#1d2423", "#222725", "#1b2121"][index % 3];
        ctx.beginPath();
        ctx.arc(x, y, index % 7 === 0 ? 2.5 : 1.5, 0, TAU);
        ctx.fill();
      }
    }
  }

  function drawObstacle(rect) {
    if (rect.kind === "car") {
      roundedRect(rect.x, rect.y, rect.w, rect.h, 8, "#323d3f", "#6c736a");
      roundedRect(rect.x + 8, rect.y + 7, rect.w - 16, rect.h - 15, 5, "#1f2b2f");
      ctx.fillStyle = "#111415";
      ctx.fillRect(rect.x + 5, rect.y + 8, 5, 13);
      ctx.fillRect(rect.x + 5, rect.y + rect.h - 21, 5, 13);
      ctx.fillRect(rect.x + rect.w - 10, rect.y + 8, 5, 13);
      ctx.fillRect(rect.x + rect.w - 10, rect.y + rect.h - 21, 5, 13);
    } else if (rect.kind === "barricade") {
      roundedRect(rect.x, rect.y, rect.w, rect.h, 3, "#5e4835");
      ctx.strokeStyle = "#c68739";
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(rect.x + 4, rect.y + rect.h / 2 - 4);
      ctx.lineTo(rect.x + rect.w - 4, rect.y + rect.h / 2 - 4);
      ctx.moveTo(rect.x + 4, rect.y + rect.h / 2 + 5);
      ctx.lineTo(rect.x + rect.w - 4, rect.y + rect.h / 2 + 5);
      ctx.stroke();
    } else {
      roundedRect(rect.x, rect.y, rect.w, rect.h, 2, "#484c45", "#67695b");
      ctx.strokeStyle = "#343934";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(rect.x, rect.y);
      ctx.lineTo(rect.x + rect.w, rect.y + rect.h);
      ctx.stroke();
    }
  }

  function roundedRect(x, y, width, height, radius, fill, stroke = null) {
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, radius);
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  function drawPlayer() {
    const player = state.player;
    const angle = Math.atan2(state.mouse.y - player.y, state.mouse.x - player.x);
    const muzzleX = player.x + Math.cos(angle) * 30;
    const muzzleY = player.y + Math.sin(angle) * 30;
    ctx.strokeStyle = "#262b2a";
    ctx.lineWidth = 7;
    ctx.beginPath();
    ctx.moveTo(player.x + Math.cos(angle) * 9, player.y + Math.sin(angle) * 9);
    ctx.lineTo(muzzleX, muzzleY);
    ctx.stroke();
    ctx.strokeStyle = "#898f81";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(player.x + Math.cos(angle) * 9, player.y + Math.sin(angle) * 9);
    ctx.lineTo(muzzleX, muzzleY);
    ctx.stroke();

    ctx.fillStyle = "#0e1213";
    ctx.beginPath();
    ctx.arc(player.x, player.y, player.radius + 3, 0, TAU);
    ctx.fill();
    ctx.fillStyle = player.hurt > 0 ? "#ffa47b" : colours.player;
    ctx.beginPath();
    ctx.arc(player.x, player.y, player.radius, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#c5d2c3";
    ctx.beginPath();
    ctx.arc(player.x, player.y, 5, 0, TAU);
    ctx.fill();
  }

  function drawZombie(zombie) {
    const wobble = Math.sin(zombie.phase) * 2;
    ctx.fillStyle = "#121614";
    ctx.beginPath();
    ctx.ellipse(zombie.x, zombie.y + zombie.radius, zombie.radius, 4, 0, 0, TAU);
    ctx.fill();
    ctx.fillStyle = zombie.hit > 0 ? "#cdcaad" : zombie.colour;
    ctx.beginPath();
    ctx.arc(zombie.x, zombie.y + wobble, zombie.radius, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#333e2f";
    ctx.beginPath();
    ctx.arc(zombie.x + zombie.radius / 3, zombie.y - 3 + wobble, Math.max(3, zombie.radius / 5), 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#e6ca8e";
    ctx.beginPath();
    ctx.arc(zombie.x + zombie.radius / 3, zombie.y - 3 + wobble, 2, 0, TAU);
    ctx.fill();
    if (zombie.health < zombie.maxHealth) {
      ctx.fillStyle = "#2c1a18";
      ctx.fillRect(zombie.x - zombie.radius, zombie.y - zombie.radius - 8, zombie.radius * 2, 4);
      ctx.fillStyle = "#c0453d";
      ctx.fillRect(zombie.x - zombie.radius, zombie.y - zombie.radius - 8, zombie.radius * 2 * Math.max(0, zombie.health) / zombie.maxHealth, 4);
    }
  }

  function drawPickup(pickup) {
    const y = pickup.y + Math.sin(pickup.phase) * 3;
    roundedRect(pickup.x - 10, y - 8, 20, 16, 3, "#6f9158", "#c2d397");
    ctx.strokeStyle = "#243123";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(pickup.x - 5, y);
    ctx.lineTo(pickup.x + 5, y);
    ctx.moveTo(pickup.x, y - 5);
    ctx.lineTo(pickup.x, y + 5);
    ctx.stroke();
  }

  function drawBullet(bullet) {
    const angle = Math.atan2(bullet.vy, bullet.vx);
    ctx.strokeStyle = "#bb7f43";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(bullet.x - Math.cos(angle) * 10, bullet.y - Math.sin(angle) * 10);
    ctx.lineTo(bullet.x, bullet.y);
    ctx.stroke();
    ctx.fillStyle = colours.bullet;
    ctx.beginPath();
    ctx.arc(bullet.x, bullet.y, 3, 0, TAU);
    ctx.fill();
  }

  function drawParticles() {
    for (const particle of state.particles) {
      const remaining = Math.max(0, 1 - particle.age / particle.lifetime);
      ctx.globalAlpha = remaining;
      ctx.fillStyle = particle.colour;
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, Math.max(1, particle.radius * remaining), 0, TAU);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function drawHud() {
    ctx.fillStyle = "#0f1315";
    ctx.fillRect(0, 0, WIDTH, HUD_HEIGHT);
    ctx.strokeStyle = "#4c514b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, HUD_HEIGHT - 1);
    ctx.lineTo(WIDTH, HUD_HEIGHT - 1);
    ctx.stroke();

    drawText("HEALTH", 18, 19, { size: 12, colour: colours.muted, weight: 600 });
    roundedRect(18, 34, 188, 16, 4, "#342726");
    const healthWidth = 188 * state.player.health / MAX_HEALTH;
    if (healthWidth > 0) roundedRect(18, 34, healthWidth, 16, 4, state.player.health > 35 ? "#5ab16a" : "#da5a48");
    drawText(`${String(state.player.health).padStart(3, "0")}%`, 214, 42, { size: 13 });

    drawText("PISTOL", 300, 19, { size: 12, colour: colours.muted, weight: 600 });
    drawText(state.player.reload > 0 ? "RELOADING..." : `${String(state.player.magazine).padStart(2, "0")} / ${String(state.player.reserve).padStart(3, "0")}`, 300, 43, {
      size: 20,
      colour: state.player.magazine === 0 ? colours.accent : colours.text,
    });
    drawText("SCORE", 510, 19, { size: 12, colour: colours.muted, weight: 600 });
    drawText(String(state.score).padStart(6, "0"), 510, 43, { size: 20 });
    drawText("SURVIVED", 672, 19, { size: 12, colour: colours.muted, weight: 600 });
    drawText(formatTime(state.elapsed), 672, 43, { size: 20 });
    drawText(`THREATS: ${state.zombies.length}`, 823, 42, { size: 13, colour: "#c57e68" });
    if (state.player.magazine === 0 && state.player.reserve === 0) {
      drawText("FIND AMMO", 390, 59, { size: 12, colour: "#f5b45d" });
    }
  }

  function drawWorld() {
    drawCity();
    for (const obstacle of state.obstacles) drawObstacle(obstacle);
    for (const pickup of state.pickups) drawPickup(pickup);
    for (const bullet of state.bullets) drawBullet(bullet);
    for (const zombie of state.zombies) drawZombie(zombie);
    drawPlayer();
    drawParticles();
    const vignette = ctx.createRadialGradient(WIDTH / 2, HEIGHT / 2, 120, WIDTH / 2, HEIGHT / 2, 650);
    vignette.addColorStop(0, "rgb(0 0 0 / 0%)");
    vignette.addColorStop(1, "rgb(0 0 0 / 31%)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    drawHud();
  }

  function drawButton(label, name, x, y, width = 245) {
    const rect = { x: x - width / 2, y: y - 22, w: width, h: 44, name };
    state.buttons.push(rect);
    const hover = pointInRect(state.mouse.x, state.mouse.y, rect);
    roundedRect(rect.x, rect.y, rect.w, rect.h, 5, hover ? "#5b3630" : "#232b2b", hover ? "#da6e51" : "#5b6257");
    drawText(label, x, y, { size: 17, align: "center", weight: 600 });
  }

  function pointInRect(x, y, rect) {
    return x >= rect.x && x <= rect.x + rect.w && y >= rect.y && y <= rect.y + rect.h;
  }

  function drawBackdrop() {
    ctx.fillStyle = "#13191d";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.fillStyle = "#1b2123";
    ctx.fillRect(0, 360, WIDTH, 180);
    ctx.fillStyle = "#303431";
    ctx.fillRect(0, 536, WIDTH, 104);
    ctx.strokeStyle = "#564b3c";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, 536);
    ctx.lineTo(WIDTH, 536);
    ctx.stroke();
    const buildings = [[45, 140, 244], [222, 120, 302], [620, 143, 265], [797, 130, 328]];
    for (const [x, width, height] of buildings) {
      const top = 536 - height;
      ctx.fillStyle = "#1f2728";
      ctx.fillRect(x, top, width, height);
      ctx.strokeStyle = "#3e443f";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, top, width, height);
      ctx.fillStyle = "#4e4c3d";
      for (let wx = x + 16; wx < x + width - 10; wx += 30) {
        for (let wy = top + 24; wy < 522; wy += 42) ctx.fillRect(wx, wy, 8, 13);
      }
    }
  }

  function drawMenu() {
    drawBackdrop();
    drawText("ZOMBIE", WIDTH / 2, 160, { size: 74, colour: colours.text, align: "center", font: "Barlow Condensed, Impact, sans-serif", weight: 800 });
    drawText("HUNTER", WIDTH / 2, 224, { size: 74, colour: colours.accent, align: "center", font: "Barlow Condensed, Impact, sans-serif", weight: 800 });
    drawText("LAST LIGHT  |  SURVIVE THE OUTBREAK", WIDTH / 2, 277, { size: 15, colour: colours.muted, align: "center", font: "DM Mono, monospace" });
    state.buttons = [];
    drawButton("START GAME", "start", WIDTH / 2, 354);
    drawButton("INSTRUCTIONS", "instructions", WIDTH / 2, 410);
    drawButton("QUIT", "quit", WIDTH / 2, 466);
    drawText("WASD / ARROWS MOVE     MOUSE AIM     LEFT CLICK FIRE", WIDTH / 2, 574, { size: 12, colour: colours.muted, align: "center", font: "DM Mono, monospace" });
  }

  function drawInstructions() {
    drawBackdrop();
    drawText("FIELD MANUAL", WIDTH / 2, 105, { size: 48, align: "center", font: "Barlow Condensed, Impact, sans-serif", weight: 700 });
    const entries = [
      ["MOVE", "WASD or arrow keys. Use open streets to outmaneuver the dead."],
      ["AIM & FIRE", "Point with your mouse. Hold left-click to fire your pistol."],
      ["RELOAD", "Press R to reload. An empty clip reloads automatically."],
      ["SURVIVE", "Zombies get faster and arrive more often. Avoid their attacks."],
      ["AMMO", "Walk over green supply cases or defeat five zombies to find ammo."],
      ["PAUSE", "Press Escape to pause. Press P or Enter to continue."],
    ];
    state.buttons = [];
    entries.forEach(([heading, body], index) => {
      const y = 180 + index * 56;
      drawText(heading, 168, y, { size: 16, colour: "#da9b64", weight: 700 });
      drawText(body, 168, y + 25, { size: 14, colour: colours.text });
    });
    drawButton("BACK", "back", WIDTH / 2, 578, 180);
  }

  function drawOverlay(title, subtitle, gameOver = false) {
    ctx.fillStyle = "rgb(6 9 11 / 78%)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    drawText(title, WIDTH / 2, 260, { size: 48, colour: gameOver ? colours.accent : colours.text, align: "center", font: "Barlow Condensed, Impact, sans-serif", weight: 700 });
    if (gameOver) drawText(`FINAL SCORE  ${String(state.score).padStart(6, "0")}`, WIDTH / 2, 314, { size: 20, align: "center", font: "DM Mono, monospace" });
    drawText(subtitle, WIDTH / 2, gameOver ? 362 : 328, { size: 17, colour: colours.muted, align: "center" });
    if (gameOver) {
      state.buttons = [];
      drawButton("PLAY AGAIN", "restart", WIDTH / 2, 425, 220);
      drawButton("MAIN MENU", "menu", WIDTH / 2, 480, 220);
    }
  }

  function draw() {
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    if (state.screen === "menu") drawMenu();
    else if (state.screen === "instructions") drawInstructions();
    else if (state.screen === "playing") {
      drawWorld();
      state.buttons = [];
      if (state.messageTime > 0) drawText(state.message, WIDTH / 2, 90, { size: 16, colour: "#f5b45d", align: "center" });
    } else if (state.screen === "paused") {
      drawWorld();
      state.buttons = [];
      drawOverlay("PAUSED", "Press P or Enter to continue");
    } else if (state.screen === "gameover") {
      drawWorld();
      drawOverlay("YOU WERE OVERRUN", "Press Enter or R to try again", true);
    } else if (state.screen === "quit") {
      drawBackdrop();
      state.buttons = [];
      drawText("THANKS FOR PLAYING", WIDTH / 2, 250, { size: 48, align: "center", font: "Barlow Condensed, Impact, sans-serif", weight: 700 });
      drawText("You can close this browser tab.", WIDTH / 2, 310, { size: 18, colour: colours.muted, align: "center" });
      drawButton("MAIN MENU", "menu", WIDTH / 2, 385);
    }
  }

  function createZombie() {
    const roll = Math.random();
    const kind = state.elapsed < 25 || roll < Math.max(0.32, 0.66 - state.elapsed / 500)
      ? "walker"
      : roll < 0.82 ? "runner" : "brute";
    const stats = zombieTypes[kind];
    const edge = Math.floor(Math.random() * 4);
    let x;
    let y;
    if (edge === 0) {
      x = Math.random() * WIDTH;
      y = HUD_HEIGHT + stats.radius;
    } else if (edge === 1) {
      x = Math.random() * WIDTH;
      y = HEIGHT - stats.radius;
    } else if (edge === 2) {
      x = stats.radius;
      y = HUD_HEIGHT + Math.random() * (HEIGHT - HUD_HEIGHT);
    } else {
      x = WIDTH - stats.radius;
      y = HUD_HEIGHT + Math.random() * (HEIGHT - HUD_HEIGHT);
    }
    state.zombies.push({
      kind,
      ...stats,
      x,
      y,
      health: stats.health,
      maxHealth: stats.health,
      speed: stats.speed * (1 + Math.min(state.elapsed / 360, 0.2)),
      attackCooldown: 0.1 + Math.random() * 0.6,
      phase: Math.random() * TAU,
      hit: 0,
    });
  }

  function spawnPickup(x = null, y = null) {
    const position = x === null ? openPosition() : { x, y };
    state.pickups.push({
      x: position.x,
      y: position.y,
      amount: [18, 24, 30][Math.floor(Math.random() * 3)],
      lifetime: 24,
      phase: Math.random() * TAU,
    });
  }

  function shoot() {
    const player = state.player;
    if (player.cooldown > 0 || player.reload > 0 || player.magazine <= 0) return;
    const dx = state.mouse.x - player.x;
    const dy = state.mouse.y - player.y;
    const length = Math.hypot(dx, dy);
    if (length === 0) return;
    const vx = dx / length * 720;
    const vy = dy / length * 720;
    player.magazine -= 1;
    player.cooldown = 0.23;
    state.bullets.push({
      x: player.x + dx / length * (player.radius + 7),
      y: player.y + dy / length * (player.radius + 7),
      previousX: player.x + dx / length * (player.radius + 7),
      previousY: player.y + dy / length * (player.radius + 7),
      vx,
      vy,
      travelled: 0,
      alive: true,
    });
    state.flash = 0.08;
    addParticles(player.x + dx / length * (player.radius + 9), player.y + dy / length * (player.radius + 9), "#f5bd5c", 3, 45, 0.12);
  }

  function reload() {
    const player = state.player;
    if (player.reload > 0 || player.magazine >= MAGAZINE_SIZE || player.reserve <= 0) return;
    player.reload = 1.05;
  }

  function segmentHitsCircle(x1, y1, x2, y2, cx, cy, radius) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthSquared = dx * dx + dy * dy;
    if (lengthSquared === 0) return (cx - x1) ** 2 + (cy - y1) ** 2 <= radius ** 2;
    const t = Math.max(0, Math.min(1, ((cx - x1) * dx + (cy - y1) * dy) / lengthSquared));
    const closestX = x1 + t * dx;
    const closestY = y1 + t * dy;
    return (cx - closestX) ** 2 + (cy - closestY) ** 2 <= radius ** 2;
  }

  function segmentHitsRect(x1, y1, x2, y2, rect) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    let low = 0;
    let high = 1;
    for (const [p, q] of [
      [-dx, x1 - rect.x],
      [dx, rect.x + rect.w - x1],
      [-dy, y1 - rect.y],
      [dy, rect.y + rect.h - y1],
    ]) {
      if (p === 0) {
        if (q < 0) return false;
      } else {
        const t = q / p;
        if (p < 0) low = Math.max(low, t);
        else high = Math.min(high, t);
        if (low > high) return false;
      }
    }
    return true;
  }

  function update(dt) {
    state.elapsed += dt;
    state.flash = Math.max(0, state.flash - dt);
    state.messageTime = Math.max(0, state.messageTime - dt);
    const player = state.player;
    player.cooldown = Math.max(0, player.cooldown - dt);
    player.hurt = Math.max(0, player.hurt - dt);

    if (player.reload > 0) {
      player.reload = Math.max(0, player.reload - dt);
      if (player.reload === 0) {
        const loaded = Math.min(MAGAZINE_SIZE - player.magazine, player.reserve);
        player.magazine += loaded;
        player.reserve -= loaded;
      }
    }
    if (player.magazine === 0 && player.reserve > 0 && player.reload === 0) reload();

    let moveX = Number(state.keys.has("d") || state.keys.has("arrowright")) - Number(state.keys.has("a") || state.keys.has("arrowleft"));
    let moveY = Number(state.keys.has("s") || state.keys.has("arrowdown")) - Number(state.keys.has("w") || state.keys.has("arrowup"));
    const moveLength = Math.hypot(moveX, moveY);
    if (moveLength > 0) {
      moveX = moveX / moveLength * PLAYER_SPEED * dt;
      moveY = moveY / moveLength * PLAYER_SPEED * dt;
      moveEntity(player, moveX, moveY);
    }
    if (state.mouse.down) shoot();

    state.spawnTimer -= dt;
    if (state.spawnTimer <= 0) {
      createZombie();
      state.spawnTimer = Math.max(0.38, 1.8 - state.elapsed / 95) * (0.7 + Math.random() * 0.55);
    }

    for (const zombie of state.zombies) {
      zombie.phase += dt * 7;
      zombie.hit = Math.max(0, zombie.hit - dt);
      zombie.attackCooldown = Math.max(0, zombie.attackCooldown - dt);
      const dx = player.x - zombie.x;
      const dy = player.y - zombie.y;
      const distance = Math.hypot(dx, dy);
      if (distance <= zombie.radius + player.radius + 3) {
        if (zombie.attackCooldown <= 0) {
          zombie.attackCooldown = 0.9;
          player.health = Math.max(0, player.health - zombie.damage);
          player.hurt = 0.2;
          addParticles(player.x, player.y, "#d3453d", 7);
        }
      } else if (distance > 0) {
        moveEntity(zombie, dx / distance * zombie.speed * dt, dy / distance * zombie.speed * dt);
      }
    }

    for (const bullet of state.bullets) {
      if (!bullet.alive) continue;
      bullet.previousX = bullet.x;
      bullet.previousY = bullet.y;
      bullet.x += bullet.vx * dt;
      bullet.y += bullet.vy * dt;
      bullet.travelled += Math.hypot(bullet.vx * dt, bullet.vy * dt);
      if (bullet.travelled >= 780 || bullet.y < HUD_HEIGHT || bullet.y > HEIGHT || bullet.x < 0 || bullet.x > WIDTH ||
          state.obstacles.some((rect) => segmentHitsRect(bullet.previousX, bullet.previousY, bullet.x, bullet.y, rect))) {
        bullet.alive = false;
        continue;
      }
      for (const zombie of state.zombies) {
        if (!segmentHitsCircle(bullet.previousX, bullet.previousY, bullet.x, bullet.y, zombie.x, zombie.y, zombie.radius + 4)) continue;
        bullet.alive = false;
        zombie.health -= 34;
        zombie.hit = 0.1;
        addParticles(bullet.x, bullet.y, "#9dbd74", 4);
        if (zombie.health <= 0) {
          state.score += zombie.points;
          state.kills += 1;
          state.zombies.splice(state.zombies.indexOf(zombie), 1);
          addParticles(zombie.x, zombie.y, "#769758", 13, 120, 0.55);
          if (state.kills % 5 === 0 && state.pickups.length < 3) spawnPickup(zombie.x, zombie.y);
        }
        break;
      }
    }
    state.bullets = state.bullets.filter((bullet) => bullet.alive);

    state.pickupTimer -= dt;
    if (state.pickupTimer <= 0 && state.pickups.length < 2) {
      const position = openPosition();
      if (Math.hypot(position.x - player.x, position.y - player.y) > 100) spawnPickup(position.x, position.y);
      state.pickupTimer = 15 + Math.random() * 7;
    }
    for (const pickup of state.pickups) {
      pickup.lifetime -= dt;
      pickup.phase += dt * 3;
      if (Math.hypot(pickup.x - player.x, pickup.y - player.y) < player.radius + 16) {
        player.reserve = Math.min(180, player.reserve + pickup.amount);
        state.score += 2;
        pickup.lifetime = 0;
        state.message = `+${pickup.amount} AMMO`;
        state.messageTime = 1.1;
        addParticles(pickup.x, pickup.y, "#b7d785", 9);
      }
    }
    state.pickups = state.pickups.filter((pickup) => pickup.lifetime > 0);

    for (const particle of state.particles) {
      particle.age += dt;
      particle.x += particle.vx * dt;
      particle.y += particle.vy * dt;
      const drag = Math.max(0, 1 - 4 * dt);
      particle.vx *= drag;
      particle.vy *= drag;
    }
    state.particles = state.particles.filter((particle) => particle.age < particle.lifetime);

    if (player.health <= 0) {
      state.screen = "gameover";
      state.mouse.down = false;
    }
  }

  function updatePointer(event) {
    const rect = canvas.getBoundingClientRect();
    state.mouse.x = (event.clientX - rect.left) * WIDTH / rect.width;
    state.mouse.y = (event.clientY - rect.top) * HEIGHT / rect.height;
  }

  function clickButton(name) {
    if (name === "start" || name === "restart") startGame();
    else if (name === "instructions") state.screen = "instructions";
    else if (name === "back" || name === "menu") state.screen = "menu";
    else if (name === "quit") state.screen = "quit";
  }

  canvas.addEventListener("pointermove", updatePointer);
  canvas.addEventListener("pointerdown", (event) => {
    updatePointer(event);
    if (event.button !== 0) return;
    event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    if (state.screen === "playing") {
      state.mouse.down = true;
    } else {
      const button = state.buttons.find((item) => pointInRect(state.mouse.x, state.mouse.y, item));
      if (button) clickButton(button.name);
    }
  });
  canvas.addEventListener("pointerup", (event) => {
    updatePointer(event);
    if (event.button === 0) state.mouse.down = false;
  });
  canvas.addEventListener("pointercancel", () => { state.mouse.down = false; });
  window.addEventListener("blur", () => {
    state.keys.clear();
    state.mouse.down = false;
    if (state.screen === "playing") state.screen = "paused";
  });

  window.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(key)) event.preventDefault();
    state.keys.add(key);
    if (key === "escape") {
      if (state.screen === "playing") {
        state.screen = "paused";
        state.mouse.down = false;
      } else if (state.screen === "paused" || state.screen === "instructions") {
        state.screen = "menu";
      } else if (state.screen === "gameover") {
        state.screen = "menu";
      }
    } else if (state.screen === "menu") {
      if (key === "enter" || key === " ") startGame();
      if (key === "i") state.screen = "instructions";
    } else if (state.screen === "instructions" && (key === "enter" || key === " ")) {
      startGame();
    } else if (state.screen === "playing" && key === "r") {
      reload();
    } else if (state.screen === "paused" && (key === "p" || key === "enter")) {
      state.screen = "playing";
    } else if (state.screen === "gameover" && (key === "enter" || key === "r")) {
      startGame();
    } else if (state.screen === "quit" && key === "enter") {
      state.screen = "menu";
    }
  });
  window.addEventListener("keyup", (event) => state.keys.delete(event.key.toLowerCase()));

  function frame(timestamp) {
    const dt = state.lastTime === 0 ? 0 : Math.min((timestamp - state.lastTime) / 1000, 0.05);
    state.lastTime = timestamp;
    if (state.screen === "playing") update(dt);
    draw();
    window.requestAnimationFrame(frame);
  }

  makeCity();
  window.requestAnimationFrame(frame);
})();
