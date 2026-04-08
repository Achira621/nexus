# [ID: MAIN-001] main.py — game loop entry; orchestrates all systems
import sys                          # sys.exit for clean shutdown
import pygame                       # Core game library
import os                           # Path operations
import math                         # Fade calculations
import json                         # Bounding-box sprite metadata

# --- Engine imports ---
from engine import input_handler    # Frame-perfect input polling
from engine import renderer         # All draw calls
from engine.lobby import run as run_lobby          # Character select screen
from engine.video_player import VideoPlayer        # MP4 arena intro
import engine.vfx as vfx                           # Transient effects

# --- Combat ---
from combat.hitbox import check_hit   # Hit detection utility
from combat import damage             # Damage + knockback resolution

# --- Entities ---
from entities.player import Player    # Human-controlled fighter
from entities.enemy  import Enemy     # AI-controlled fighter

# --- AI ---
from ai import enemy_ai               # Deterministic state-machine AI

# --- Utilities ---
from utils.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, DEBUG_MODE,
    BG_DIR, SPRITE_DIR,
    PLAYER_WIDTH, PLAYER_HEIGHT, ENEMY_WIDTH, ENEMY_HEIGHT,
    COLOR_PLAYER, COLOR_ENEMY,
)
from utils import logger              # Debug output
from utils import asset_loader        # Cached image loader


# ------------------------------------------------------------------ #
#  Game state constants                                               #
# ------------------------------------------------------------------ #

# [ID: MAIN-GS] Four top-level game states
GS_LOBBY   = "lobby"     # Character select
GS_LOADING = "loading"   # Arena intro MP4 + fade
GS_FIGHT   = "fight"     # Battle loop
GS_RESULT  = "result"    # Win/loss screen


# ------------------------------------------------------------------ #
#  Sprite loading helpers                                             #
# ------------------------------------------------------------------ #

def _build_placeholder_frames(color: tuple, w: int, h: int,
                               states: list, count: int) -> dict:
    # [ID: MAIN-002] Build procedural coloured-rect animation frames
    frame_map = {}
    for state in states:
        frames = []
        for i in range(count):
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            shade = max(0, min(255, int(color[0]) + i * 8))
            body  = (shade, color[1], color[2], 200)
            pygame.draw.rect(surf, body, (0, 0, w, h), border_radius=8)
            pygame.draw.rect(surf, (*color, 255), (0, 0, w, h), 2, border_radius=8)
            frames.append(surf)
        frame_map[state] = frames
    return frame_map


def _remove_edge_background(frame: pygame.Surface, tolerance: int = 18) -> pygame.Surface:
    # [ID: MAIN-BGK] Remove dark sheet background only when it is connected to edges.
    width, height = frame.get_size()
    if width == 0 or height == 0:
        return frame

    corner = frame.get_at((0, 0))
    if corner[3] < 250 or (corner[0] + corner[1] + corner[2]) > 50:
        return frame

    working = frame.copy()
    rgb = pygame.surfarray.pixels3d(working)
    alpha = pygame.surfarray.pixels_alpha(working)
    visited = set()
    stack = []

    def _matches_bg(px: int, py: int) -> bool:
        return (
            abs(int(rgb[px, py, 0]) - int(corner[0])) <= tolerance and
            abs(int(rgb[px, py, 1]) - int(corner[1])) <= tolerance and
            abs(int(rgb[px, py, 2]) - int(corner[2])) <= tolerance
        )

    for px in range(width):
        stack.append((px, 0))
        stack.append((px, height - 1))
    for py in range(height):
        stack.append((0, py))
        stack.append((width - 1, py))

    while stack:
        px, py = stack.pop()
        if (px, py) in visited:
            continue
        visited.add((px, py))
        if not (0 <= px < width and 0 <= py < height):
            continue
        if alpha[px, py] == 0 or not _matches_bg(px, py):
            continue

        alpha[px, py] = 0
        stack.append((px - 1, py))
        stack.append((px + 1, py))
        stack.append((px, py - 1))
        stack.append((px, py + 1))

    del rgb, alpha
    return working


def _scale_frame(frame: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    # [ID: MAIN-SCL] Trim transparent padding so sprites look grounded after scaling.
    try:
        working = _remove_edge_background(frame)
    except Exception:
        working = frame

    alpha_rect = working.get_bounding_rect()
    if alpha_rect.width > 0 and alpha_rect.height > 0:
        trimmed = pygame.Surface(alpha_rect.size, pygame.SRCALPHA)
        trimmed.blit(working, (0, 0), alpha_rect)
    else:
        trimmed = working
    return pygame.transform.smoothscale(trimmed, (target_w, target_h))


def _load_strip(path: str, target_w: int, target_h: int) -> list:
    # [ID: MAIN-STR] Load a single-row horizontal sprite strip.
    # Frame width = image height (square frames); cols = img_w // img_h
    if not os.path.exists(path):
        return []
    try:
        raw = pygame.image.load(path).convert_alpha()
        img_w, img_h = raw.get_size()
        if img_h == 0:
            return []
        cols   = max(1, img_w // img_h)     # Square frames assumption
        f_w    = img_w // cols              # Frame width (px)
        frames = []
        for i in range(cols):
            rect  = pygame.Rect(i * f_w, 0, f_w, img_h)
            frame = pygame.Surface((f_w, img_h), pygame.SRCALPHA)
            frame.blit(raw, (0, 0), rect)
            frames.append(_scale_frame(frame, target_w, target_h))
        logger.log_asset(f"[STRIP] {os.path.basename(path)} → {len(frames)} frames")
        return frames
    except Exception as exc:
        logger.log_asset(f"[STRIP] WARN: {path} failed — {exc}")
        return []


def _load_grid_sheet(path: str, columns: int, rows: int,
                     target_w: int, target_h: int) -> list:
    # [ID: MAIN-STRG] Load a regular grid spritesheet into a flat frame list.
    if not os.path.exists(path):
        return []
    try:
        frames = asset_loader.load_spritesheet_grid(path, columns, rows)
        scaled = [_scale_frame(frame, target_w, target_h) for frame in frames]
        logger.log_asset(
            f"[GRID] {os.path.basename(path)} â†’ {len(scaled)} frames ({columns}x{rows})"
        )
        return scaled
    except Exception as exc:
        logger.log_asset(f"[GRID] WARN: {path} failed â€” {exc}")
        return []


def _load_box_sheet(path: str, boxes_path: str,
                    target_w: int, target_h: int) -> list:
    # [ID: MAIN-BOX] Load exact animation frames from exported bounding boxes.
    if not os.path.exists(path) or not os.path.exists(boxes_path):
        return []
    try:
        raw = pygame.image.load(path).convert_alpha()
        with open(boxes_path, "r", encoding="utf-8") as handle:
            boxes = json.load(handle)

        frames = []
        for box in boxes:
            rect = pygame.Rect(
                int(box["x"]),
                int(box["y"]),
                int(box["width"]),
                int(box["height"]),
            )
            frame = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame.blit(raw, (0, 0), rect)
            frames.append(_scale_frame(frame, target_w, target_h))

        logger.log_asset(f"[BOX] {os.path.basename(path)} â†’ {len(frames)} frames")
        return frames
    except Exception as exc:
        logger.log_asset(f"[BOX] WARN: {path} failed â€” {exc}")
        return []


def _take_frames(frames: list, count: int) -> list:
    # [ID: MAIN-TAKE] Keep only the leading frames needed for a state.
    return frames[:max(0, min(count, len(frames)))]


def _fill_missing_states(frame_map: dict, states: list) -> dict:
    # [ID: MAIN-FILL] Reuse nearby animations before falling back to placeholders.
    fallback_order = {
        "idle": [
            "walk", "run", "attack_light", "attack_heavy",
            "attack_directional", "attack_special", "hit", "dead",
        ],
        "walk": [
            "run", "idle", "attack_directional", "attack_light",
            "attack_heavy", "attack_special", "hit", "dead",
        ],
        "run": [
            "walk", "idle", "attack_directional", "attack_light",
            "attack_heavy", "attack_special", "hit", "dead",
        ],
        "attack_light": [
            "attack_heavy", "attack_directional", "attack_special",
            "walk", "idle", "hit", "dead",
        ],
        "attack_heavy": [
            "attack_light", "attack_directional", "attack_special",
            "walk", "idle", "hit", "dead",
        ],
        "attack_directional": [
            "attack_light", "attack_heavy", "attack_special",
            "walk", "idle", "hit", "dead",
        ],
        "attack_special": [
            "attack_heavy", "attack_directional", "attack_light",
            "walk", "idle", "hit", "dead",
        ],
        "hit": [
            "attack_heavy", "attack_light", "attack_directional",
            "attack_special", "idle", "walk", "dead",
        ],
        "dead": [
            "hit", "idle", "walk", "attack_heavy",
            "attack_light", "attack_directional", "attack_special",
        ],
    }

    for state in states:
        if state in frame_map and frame_map[state]:
            continue
        for candidate in fallback_order.get(state, []):
            if candidate in frame_map and frame_map[candidate]:
                frame_map[state] = frame_map[candidate]
                break
    return frame_map


# [ID: MAIN-003A] Per-character grid descriptor
SHEET_CONFIGS: dict = {
    "vajra_kali": {
        "cols": 6, "rows": 6,
        "map": {
            "idle":               (0, 0, 6),
            "walk":               (1, 0, 6),
            "attack_light":       (2, 0, 6),
            "attack_heavy":       (3, 0, 6),
            "hit":                (4, 0, 3),
            "dead":               (4, 3, 3),
            "attack_directional": (5, 0, 6),
            "attack_special":     (5, 0, 6),
        },
    },
    "takshaka": {
        "cols": 6, "rows": 4,
        "map": {
            "idle":               (0, 0, 6),
            "walk":               (1, 0, 6),
            "attack_light":       (2, 0, 6),
            "attack_heavy":       (3, 0, 6),
            "attack_directional": (3, 0, 6),
            "attack_special":     (3, 0, 6),
            "hit":                (2, 4, 2),
            "dead":               (3, 4, 2),
        },
    },
    "rudra_shiva": {
        "cols": 6, "rows": 4,
        "map": {
            "idle":               (0, 0, 6),
            "walk":               (1, 0, 6),
            "attack_light":       (1, 0, 6),
            "attack_directional": (2, 0, 6),
            "attack_heavy":       (2, 0, 6),
            "attack_special":     (2, 0, 6),
            "hit":                (3, 0, 3),
            "dead":               (3, 3, 3),
        },
    },
    "vajra_garuda": {
        "cols": 6, "rows": 4,
        "map": {
            "idle":               (0, 0, 6),
            "walk":               (1, 0, 6),
            "attack_light":       (2, 0, 6),
            "attack_directional": (2, 0, 6),
            "attack_heavy":       (3, 0, 6),
            "attack_special":     (3, 0, 6),
            "hit":                (3, 4, 1),
            "dead":               (3, 5, 1),
        },
    },
    "narakalok": {
        "cols": 5, "rows": 5,
        "map": {
            "idle":               (0, 0, 5),
            "walk":               (1, 0, 5),
            "attack_light":       (2, 0, 5),
            "attack_directional": (2, 0, 5),
            "attack_heavy":       (3, 0, 5),
            "attack_special":     (3, 0, 5),
            "hit":                (4, 0, 2),
            "dead":               (4, 3, 2),
        },
    },
}


def _slice_frames(all_frames: list, cols: int,
                  row: int, start_col: int, count: int) -> list:
    # [ID: MAIN-003B] Extract `count` frames from a flat grid list
    base = row * cols + start_col
    end  = min(base + count, len(all_frames))
    return all_frames[base:end]


def _try_load_sprites(folder: str, states: list, w: int, h: int,
                      fallback_color: tuple, sprite_id: str) -> dict:
    # [ID: MAIN-004] Load sheet → slice into named animation states
    frame_map  = {}
    cfg        = SHEET_CONFIGS.get(sprite_id)
    sheet_path = asset_loader.find_sheet(folder)

    if sheet_path and cfg:
        cols      = cfg["cols"]
        rows      = cfg["rows"]
        anim_map  = cfg["map"]
        all_frames = asset_loader.load_spritesheet_grid(sheet_path, cols, rows)
        scaled     = [_scale_frame(frame, w, h) for frame in all_frames]
        for state, (row, sc, fc) in anim_map.items():
            sliced = _slice_frames(scaled, cols, row, sc, fc)
            if sliced:
                frame_map[state] = sliced
                logger.log_asset(f"  {sprite_id}.{state} → {len(sliced)} frames")

    elif sheet_path:
        logger.log_asset(f"[WARN] No SHEET_CONFIG for {sprite_id}, using generic 6×6")
        all_frames = asset_loader.load_spritesheet_grid(sheet_path, 6, 6)
        scaled     = [_scale_frame(frame, w, h) for frame in all_frames]
        frame_map["idle"]               = scaled[0:6]
        frame_map["walk"]               = scaled[6:12]
        frame_map["attack_light"]       = scaled[12:18]
        frame_map["attack_heavy"]       = scaled[18:24]
        frame_map["hit"]                = scaled[24:27]
        frame_map["dead"]               = scaled[27:30]
        frame_map["attack_directional"] = frame_map["attack_heavy"]
        frame_map["attack_special"]     = frame_map["attack_heavy"]
    else:
        logger.log_asset(f"[WARN] No sheet found in {folder}, trying sequences")
        for state in states:
            seq = asset_loader.load_sequence(folder, state, list(range(8)))
            if seq:
                frame_map[state] = [_scale_frame(frame, w, h) for frame in seq]

    # [ID: MAIN-004D] Vajra-Kali dedicated walk & run sheets override main sheet
    if sprite_id == "vajra_kali":
        idle_path = os.path.join(folder, "Vajra kali-idle.png")
        atk_path  = os.path.join(folder, "Vajra kali-attack.png")
        walk_path = os.path.join(folder, "Vajra Kali-walk.png")
        run_path  = os.path.join(folder, "Vajra Kali-run.png")

        idle_frames = _load_grid_sheet(idle_path, 5, 5, w, h)
        atk_frames  = _load_grid_sheet(atk_path,  5, 5, w, h)
        walk_frames = _load_grid_sheet(walk_path, 5, 5, w, h)
        run_frames  = _load_grid_sheet(run_path,  5, 5, w, h)

        if idle_frames:
            frame_map["idle"] = _take_frames(idle_frames, 15)
            logger.log_asset(f"  vajra_kali.idle â†’ {len(idle_frames)} frames [GRID]")

        if atk_frames:
            attack_seq = _take_frames(atk_frames, 20)
            frame_map["attack_light"] = attack_seq
            frame_map["attack_heavy"] = attack_seq
            frame_map["attack_directional"] = attack_seq
            frame_map["attack_special"] = attack_seq
            logger.log_asset(f"  vajra_kali.attack â†’ {len(atk_frames)} frames [GRID]")

        if walk_frames:
            frame_map["walk"] = walk_frames   # Override sheet walk with dedicated sheet
            logger.log_asset(f"  vajra_kali.walk → {len(walk_frames)} frames [STRIP]")
        if run_frames:
            frame_map["run"] = run_frames     # New run state from dedicated sheet
            logger.log_asset(f"  vajra_kali.run  → {len(run_frames)} frames [STRIP]")

    if sprite_id == "takshaka":
        box_sheet = os.path.join(
            folder, "combined_sprite_0e66fb99-8e31-4885-8035-465907dd83b9.png"
        )
        box_json = os.path.join(folder, "Shoryuken_bounding_boxes.json")
        attack_frames = _load_box_sheet(box_sheet, box_json, w, h)
        if attack_frames:
            attack_seq = _take_frames(attack_frames, 25)
            frame_map["attack_light"] = attack_seq
            frame_map["attack_heavy"] = attack_seq
            frame_map["attack_directional"] = attack_seq
            frame_map["attack_special"] = attack_seq
            logger.log_asset(f"  takshaka.attack → {len(attack_seq)} frames [BOX]")

    return frame_map


def _load_assets(p_config: dict, e_config: dict):
    # [ID: MAIN-003] Load/build all animation frame maps for both fighters
    states = ["idle", "walk", "run", "attack_light", "attack_heavy",
              "attack_directional", "attack_special", "hit", "dead"]

    p_folder = os.path.join(SPRITE_DIR, p_config.get("sprite_id", "player"))
    e_folder = os.path.join(SPRITE_DIR, e_config.get("sprite_id", "enemy"))

    p_frames = _try_load_sprites(p_folder, states,
                                 PLAYER_WIDTH, PLAYER_HEIGHT, COLOR_PLAYER,
                                 p_config.get("sprite_id", ""))
    e_frames = _try_load_sprites(e_folder, states,
                                 ENEMY_WIDTH, ENEMY_HEIGHT, COLOR_ENEMY,
                                 e_config.get("sprite_id", ""))

    p_frames = _fill_missing_states(p_frames, states)
    e_frames = _fill_missing_states(e_frames, states)

    # [ID: MAIN-005] Merge with placeholders for any missing states
    p_placeholder = _build_placeholder_frames(COLOR_PLAYER,
                        PLAYER_WIDTH, PLAYER_HEIGHT, states, 4)
    e_placeholder = _build_placeholder_frames(COLOR_ENEMY,
                        ENEMY_WIDTH, ENEMY_HEIGHT, states, 4)

    for s in states:
        if s not in p_frames:
            p_frames[s] = p_placeholder[s]
        if s not in e_frames:
            e_frames[s] = e_placeholder[s]

    return p_frames, e_frames


# ------------------------------------------------------------------ #
#  Combat resolution — called every frame                            #
# ------------------------------------------------------------------ #

def _resolve_combat(player: Player, enemy: Enemy) -> None:
    # [ID: MAIN-006] Check if player's hitbox hits enemy's hurtbox
    if not player.has_hit and player.hitbox is not None:
        if check_hit(player.hitbox, enemy.hurtbox):
            dmg = damage.resolve_hit(player, enemy, player.current_attack)
            if dmg > 0:
                player.has_hit = True
                hit_x = float(player.hitbox.x + player.hitbox.w * 0.5)
                hit_y = float(player.hitbox.y + player.hitbox.h * 0.5)
                renderer.spawn_hit_particles(hit_x, hit_y)

    # [ID: MAIN-008] Check if enemy's hitbox hits player's hurtbox
    if not enemy.has_hit and enemy.hitbox is not None:
        if check_hit(enemy.hitbox, player.hurtbox):
            dmg = damage.resolve_hit(enemy, player, enemy.current_attack)
            if dmg > 0:
                enemy.has_hit = True
                hit_x = float(enemy.hitbox.x + enemy.hitbox.w * 0.5)
                hit_y = float(enemy.hitbox.y + enemy.hitbox.h * 0.5)
                renderer.spawn_hit_particles(hit_x, hit_y)


# ------------------------------------------------------------------ #
#  Loading screen (MP4 + fade transition)                            #
# ------------------------------------------------------------------ #

_FADE_DURATION = 0.6    # Seconds of black-fade before fight begins


def _draw_loading_fallback(screen: pygame.Surface, elapsed: float) -> None:
    # [ID: MAIN-LOAD-FALLBACK] Draw a simple animated loading screen when MP4 playback is unavailable.
    screen.fill((5, 8, 20))

    pulse = 0.5 + 0.5 * math.sin(elapsed * 4.0)
    title_font = pygame.font.SysFont("segoeui", 54, bold=True)
    hint_font = pygame.font.SysFont("segoeui", 24, bold=True)
    title_col = (
        int(180 + 60 * pulse),
        int(120 + 80 * pulse),
        40,
    )

    title = title_font.render("LOADING BATTLE", True, title_col)
    hint = hint_font.render("Preparing arena...", True, (210, 215, 235))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 210))
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 285))

    bar_w = 420
    bar_h = 18
    bar_x = SCREEN_WIDTH // 2 - bar_w // 2
    bar_y = 355
    pygame.draw.rect(screen, (25, 35, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=10)
    fill_ratio = min(1.0, elapsed / 1.8)
    pygame.draw.rect(
        screen,
        (255, 140, 50),
        (bar_x, bar_y, int(bar_w * fill_ratio), bar_h),
        border_radius=10,
    )
    pygame.draw.rect(screen, (240, 220, 160), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)


def _run_loading(screen: pygame.Surface, clock: pygame.time.Clock) -> None:
    # [ID: MAIN-LOAD] Play arena intro video then fade to black
    video_path = os.path.join(BG_DIR, "lodinganimation.mp4")
    player_v   = VideoPlayer(video_path, SCREEN_WIDTH, SCREEN_HEIGHT)

    if player_v.is_done():
        fallback_elapsed = 0.0
        fallback_duration = 1.8
        while fallback_elapsed < fallback_duration:
            dt = clock.tick(FPS) / 1000.0
            fallback_elapsed += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                        fallback_elapsed = fallback_duration

            _draw_loading_fallback(screen, fallback_elapsed)
            pygame.display.flip()

        player_v.release()
        return

    # Phase 1: play video until it finishes
    while not player_v.is_done():
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            # [ID: MAIN-LOAD-SKIP] SPACE / ENTER skips the video
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                 pygame.K_ESCAPE):
                    player_v._done = True   # Force-exit video loop

        frame_surf = player_v.update(dt)
        if frame_surf:
            screen.blit(frame_surf, (0, 0))
        else:
            screen.fill((0, 0, 0))   # Black gap between frames
        pygame.display.flip()

    player_v.release()

    # Phase 2: fade to black before fight starts
    fade_elapsed = 0.0
    while fade_elapsed < _FADE_DURATION:
        dt = clock.tick(FPS) / 1000.0
        fade_elapsed += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        ratio = min(1.0, fade_elapsed / _FADE_DURATION)
        alpha = int(255 * ratio)             # 0 → 255 (transparent → black)

        # Keep last video frame on screen, overlay growing black
        fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade_surf.set_alpha(alpha)
        fade_surf.fill((0, 0, 0))
        screen.blit(fade_surf, (0, 0))
        pygame.display.flip()


# ------------------------------------------------------------------ #
#  Main entry point                                                   #
# ------------------------------------------------------------------ #

def main() -> None:
    # [ID: MAIN-009] Initialise pygame and create window
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    # [ID: MAIN-010] Renderer init — pass arena background image
    arena_bg_path = os.path.join(BG_DIR, "arenabackground.png")
    renderer.init(screen, bg_path=arena_bg_path)

    # [ID: MAIN-012] Game state tracking
    game_state = GS_LOBBY    # Start at character select
    debug_mode = DEBUG_MODE
    game_over  = False
    winner     = ""
    player: "Player | None" = None
    enemy:  "Enemy  | None" = None
    round_timer = 0.0

    # ---------------------------------------------------------------- #
    #  Top-level game state machine                                     #
    # ---------------------------------------------------------------- #
    while True:

        # ============================================================ #
        #  LOBBY — character select                                     #
        # ============================================================ #
        if game_state == GS_LOBBY:
            # [ID: MAIN-LOBBY] Blocking call — returns when player confirms
            p_config, e_config = run_lobby(screen, clock)
            game_state = GS_LOADING   # Move to loading animation

        # ============================================================ #
        #  LOADING — play MP4 intro then fade in                       #
        # ============================================================ #
        elif game_state == GS_LOADING:
            # [ID: MAIN-LOADING] Load assets BEFORE showing the video
            # (avoids stutter mid-playback)
            asset_loader.clear()     # Reset cache for fresh round
            p_frames, e_frames = _load_assets(p_config, e_config)
            player = Player(p_frames, p_config)
            enemy  = Enemy(e_frames, e_config)
            enemy_ai.reset()
            game_over  = False
            winner     = ""

            # Play the video intro
            _run_loading(screen, clock)

            # Fade-in from black into the fight
            fade_in_elapsed = 0.0
            fade_in_dur     = 0.5
            while fade_in_elapsed < fade_in_dur:
                dt = clock.tick(FPS) / 1000.0
                fade_in_elapsed += dt
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                renderer.draw(screen, player, enemy, dt, debug_mode)
                ratio = 1.0 - min(1.0, fade_in_elapsed / fade_in_dur)
                fade_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                fade_s.set_alpha(int(255 * ratio))
                fade_s.fill((0, 0, 0))
                screen.blit(fade_s, (0, 0))
                pygame.display.flip()

            game_state = GS_FIGHT   # Hand off to fight loop

        # ============================================================ #
        #  FIGHT — main battle loop                                    #
        # ============================================================ #
        elif game_state == GS_FIGHT:
            raw_dt = clock.tick(FPS)
            dt     = min(raw_dt / 1000.0, 0.05)
            round_timer += dt
            vfx.update(dt)

            # ── Events ──
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            inp = input_handler.poll()

            if inp.debug_toggle:
                debug_mode = not debug_mode
                logger.log_input(f"Debug mode: {debug_mode}")

            # ── Win condition check ──
            if game_over:
                if inp.pause:
                    pygame.quit(); sys.exit()
                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    # [ID: MAIN-016] R → back to lobby for fresh round
                    game_state = GS_LOBBY
                renderer.draw(screen, player, enemy, dt, debug_mode)
                renderer.draw_result(screen, winner)
                pygame.display.flip()
                continue

            # ── AI ──
            if player.hit_stop_timer > 0 or enemy.hit_stop_timer > 0:
                player.hit_stop_timer = max(0, player.hit_stop_timer - 1)
                enemy.hit_stop_timer = max(0, enemy.hit_stop_timer - 1)
                renderer.draw(screen, player, enemy, dt, debug_mode)
                if round_timer < 3.0:
                    renderer.draw_round_intro(screen, round_timer)
                pygame.display.flip()
                continue

            enemy_ai.update(enemy, player, dt)

            # ── Entity updates ──
            player.update(inp, dt)
            enemy.update(dt)

            # ── VFX Trails ──
            if player.state == "attack" and player.hitbox and getattr(player.hitbox, 'active', True):
                vfx.add_trail_point(player, float(player.hitbox.x + player.hitbox.w/2), float(player.hitbox.y + player.hitbox.h/2), COLOR_PLAYER)
            if enemy.state == "attack" and enemy.hitbox and getattr(enemy.hitbox, 'active', True):
                vfx.add_trail_point(enemy, float(enemy.hitbox.x + enemy.hitbox.w/2), float(enemy.hitbox.y + enemy.hitbox.h/2), COLOR_ENEMY)

            # ── Combat ──
            _resolve_combat(player, enemy)

            # ── Win condition evaluation ──
            if player.is_dead() or enemy.is_dead():
                game_over = True
                game_state = GS_RESULT
                if player.is_dead() and enemy.is_dead():
                    winner = "DRAW"
                elif player.is_dead():
                    winner = "ENEMY"
                else:
                    winner = "PLAYER"

            # ── Render ──
            renderer.draw(screen, player, enemy, dt, debug_mode)
            if round_timer < 3.0:
                renderer.draw_round_intro(screen, round_timer)
            pygame.display.flip()

        # ============================================================ #
        #  RESULT — win/loss overlay                                   #
        # ============================================================ #
        elif game_state == GS_RESULT:
            raw_dt = clock.tick(FPS)
            dt     = min(raw_dt / 1000.0, 0.05)
            vfx.update(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            inp = input_handler.poll()
            if inp.pause:
                pygame.quit(); sys.exit()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                # [ID: MAIN-RESULT-R] Return to lobby
                game_state = GS_LOBBY

            renderer.draw(screen, player, enemy, dt, debug_mode)
            renderer.draw_result(screen, winner)
            pygame.display.flip()


# [ID: MAIN-022] Standard Python entry-point guard
if __name__ == "__main__":
    main()   # Launch the game
