# [ID: REN-001] renderer.py — ALL draw calls in one place, zero game logic
import pygame                # Surface, draw, font
import math                  # sin() for pulsing effects
import random                # Particle spread
from utils.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y,
    COLOR_BG_TOP, COLOR_BG_BOTTOM, COLOR_GROUND_TOP, COLOR_GROUND_LINE,
    COLOR_PLAYER, COLOR_ENEMY,
    COLOR_HP_PLAYER, COLOR_HP_ENEMY, COLOR_HP_BG, COLOR_HP_BORDER,
    COLOR_HIT_FLASH, COLOR_UI_TEXT, COLOR_WIN_GOLD,
    COLOR_SPARK_A, COLOR_SPARK_B, COLOR_SPARK_C,
    COLOR_HITBOX_DBG, COLOR_HURTBOX_DBG,
    HUD_HP_BAR_WIDTH, HUD_HP_BAR_HEIGHT, HUD_HP_BAR_Y, HUD_HP_PADDING,
    HUD_ICON_SIZE, HUD_SEGMENT_COUNT, MAX_PARTICLES, DEBUG_MODE,
    ICON_DIR,
)
from utils import asset_loader   # Cached icon loading
import os                        # Path construction
import engine.vfx as vfx

# [ID: REN-002] Module-level state — pre-created surfaces and particle list
_bg_surf: "pygame.Surface | None"   = None   # Pre-rendered gradient background
_arena_bg: "pygame.Surface | None"  = None   # Arena background image (PNG)
_font_big:   "pygame.font.Font | None" = None  # Large HUD font
_font_med:   "pygame.font.Font | None" = None  # Medium HUD font
_font_small: "pygame.font.Font | None" = None  # Small debug font
_frame_counter: int = 0  # Global frame count for animations

_shake_intensity: float = 0.0
_shake_timer: int = 0
_ghost_hp_player: float = 0.0
_ghost_hp_enemy: float = 0.0
_damage_texts: list = []

# [ID: REN-003] Icon filenames from binding_icons mapped to game UI roles
_ICON_HP_BAR    = "ghost_100_target_0010.png"  # Circular target — HP indicator
_ICON_ATTACK_L  = "ghost_010_wpn_0070.png"     # Knife — light attack
_ICON_ATTACK_H  = "ghost_010_wpn_0110.png"     # Heavy weapon
_ICON_ENERGY    = "ghost_020_ammo_0050.png"    # Energy orb


def init(screen: pygame.Surface, bg_path: "str | None" = None) -> None:
    # [ID: REN-004] Call once after pygame.init(); optionally load arena bg image
    global _bg_surf, _arena_bg, _font_big, _font_med, _font_small

    # Pre-render gradient background (used as fallback)
    _bg_surf = _build_gradient(SCREEN_WIDTH, SCREEN_HEIGHT,
                               COLOR_BG_TOP, COLOR_BG_BOTTOM)

    # [ID: REN-004A] Load arena background image if path provided
    if bg_path and os.path.exists(bg_path):
        try:
            raw      = pygame.image.load(bg_path).convert()
            _arena_bg = pygame.transform.smoothscale(raw, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception as exc:
            _arena_bg = None    # Non-fatal — falls back to gradient
            import sys; print(f"[REN] bg load failed: {exc}", file=sys.stderr)
    else:
        _arena_bg = None   # No image path given — use gradient

    # [ID: REN-005] Load system fonts (fallback to pygame default if unavailable)
    try:
        _font_big   = pygame.font.SysFont("segoeui", 48, bold=True)
        _font_med   = pygame.font.SysFont("segoeui", 28)
        _font_small = pygame.font.SysFont("consolas", 16)
    except Exception:
        _font_big   = pygame.font.Font(None, 52)   # Pygame built-in fallback
        _font_med   = pygame.font.Font(None, 32)
        _font_small = pygame.font.Font(None, 20)


def draw(screen: pygame.Surface, player, enemy,
         dt: float, debug: bool = False) -> None:  # Master draw call
    global _frame_counter, _shake_intensity, _shake_timer
    _frame_counter += 1   # Advance global frame for pulse effects

    dx, dy = 0, 0
    if _shake_timer > 0:
        _shake_timer -= 1
        dx = int((random.random() - 0.5) * _shake_intensity)
        dy = int((random.random() - 0.5) * _shake_intensity)
        _shake_intensity *= 0.9

    world_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # [ID: REN-006] Strict draw order: BG → arena → entities → HUD → particles
    _draw_background(world_surf)
    _draw_arena(world_surf)
    vfx.draw_bg_auras(world_surf, [player, enemy], _frame_counter)
    
    _draw_entity(world_surf, enemy,  COLOR_ENEMY,  flip=True)   # Enemy faces left
    _draw_entity(world_surf, player, COLOR_PLAYER, flip=False)  # Player faces right

    # [ID: REN-007] Draw hitbox/hurtbox overlays only in debug mode
    if debug or DEBUG_MODE:
        _draw_debug(world_surf, player)
        _draw_debug(world_surf, enemy)

    vfx.draw_fg_effects(world_surf)     # Moduler VFX Foreground
    _draw_damage_texts(world_surf)

    # Blit world with shake offset
    screen.fill((0, 0, 0))
    screen.blit(world_surf, (dx, dy))

    _draw_hud(screen, player, enemy)  # HUD last — always on top


def spawn_hit_particles(x: float, y: float, color: tuple = (255, 200, 50)) -> None:   # Called on successful hit
    # Delegate to procedural VFX system
    vfx.spawn_impact(x, y, color)

def add_shake(intensity: float) -> None:
    global _shake_intensity, _shake_timer
    _shake_intensity = intensity
    _shake_timer = 15

def spawn_damage_number(x: float, y: float, damage: int) -> None:
    _damage_texts.append({
        "x": x, "y": y, "vy": -2.0 - random.random()*1.5,
        "vx": (random.random() - 0.5) * 2.0,
        "life": 40, "max_life": 40, "damage": damage
    })


# ------------------------------------------------------------------ #
#  Private draw helpers — rendering only, no state changes           #
# ------------------------------------------------------------------ #

def _build_gradient(w: int, h: int, top: tuple, bot: tuple) -> pygame.Surface:
    # [ID: REN-009] Build a vertical gradient surface pixel by pixel
    surf = pygame.Surface((w, h))
    for y in range(h):
        t   = y / h   # Normalised 0..1
        r   = int(top[0] + (bot[0] - top[0]) * t)
        g   = int(top[1] + (bot[1] - top[1]) * t)
        b   = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))   # Horizontal line
    return surf


def _draw_background(screen: pygame.Surface) -> None:
    # [ID: REN-006A] Prefer arena background image over procedural gradient
    if _arena_bg:
        screen.blit(_arena_bg, (0, 0))  # Blit full-size arena photo
    elif _bg_surf:
        screen.blit(_bg_surf, (0, 0))   # Blit pre-rendered gradient
    else:
        screen.fill(COLOR_BG_TOP)       # Fallback solid fill

    # Lift the scene slightly instead of adding per-sprite spotlight effects.
    haze = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    haze.fill((235, 225, 210, 20))
    screen.blit(haze, (0, 0))


def _draw_arena(screen: pygame.Surface) -> None:
    # [ID: REN-010] Draw stylised ground platform
    ground_rect = pygame.Rect(0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y)
    pygame.draw.rect(screen, COLOR_GROUND_TOP, ground_rect)   # Ground fill
    pygame.draw.line(screen, COLOR_GROUND_LINE,               # Highlight line
                     (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)

    # [ID: REN-011] Energy rune decorations — pulsing circles on ground
    pulse = int(abs(math.sin(_frame_counter * 0.04)) * 30)    # Pulse amplitude
    rune_color = (40 + pulse, 30 + pulse, 90 + pulse)         # Dynamic colour
    for rx in [SCREEN_WIDTH // 4, SCREEN_WIDTH // 2, 3 * SCREEN_WIDTH // 4]:
        pygame.draw.circle(screen, rune_color, (rx, GROUND_Y), 18, 2)  # Rune ring
        pygame.draw.circle(screen, rune_color, (rx, GROUND_Y),  6, 0)  # Rune dot


def _draw_entity(screen: pygame.Surface, entity,
                 base_color: tuple, flip: bool) -> None:
    # [ID: REN-012] Draw entity — use Animator frame if available, else shape
    frame = entity.animator.get_frame()   # Get current animation Surface or None

    # [ID: REN-013] Apply hit flash or status effect colours
    color = base_color
    if entity.hit_flash > 0:
        if entity.hit_flash % 2 == 0:
            color = COLOR_HIT_FLASH
        else:
            color = (255, 90, 90)
    elif getattr(entity, "state", "") == "hit_stun":
        color = (220, 70, 70)
    elif getattr(entity, "status_effects", None):
        if "burn" in entity.status_effects:
            color = (255, 100, 0)    # Orange for burn
        elif "poison" in entity.status_effects:
            color = (100, 255, 0)    # Green for poison
        elif "slow" in entity.status_effects:
            color = (100, 100, 255)  # Blue for slow
        elif "immobilize" in entity.status_effects:
            color = (150, 150, 150)  # Grey for immobilize

    if frame is not None:   # Sprite sheet frame available
        sprite = pygame.transform.flip(frame, entity.facing_left, False)  # Mirror
        if entity.hit_flash > 0:   # Apply flash overlay
            flash_surf = sprite.copy()
            flash_color = COLOR_HIT_FLASH if entity.hit_flash % 2 == 0 else (255, 70, 70)
            flash_surf.fill((*flash_color, 220), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = flash_surf
        screen.blit(sprite, (int(entity.x), int(entity.y)))   # Draw sprite

    else:   # No sprite — draw procedural energy shape
        _draw_procedural_entity(screen, entity, color)

    # [ID: REN-014] Draw energy glow ring below entity feet
    foot_x = int(entity.x + entity.width  // 2)   # Centre of feet
    foot_y = int(entity.y + entity.height)         # Bottom of entity
    glow_r = entity.width // 2                     # Shadow radius
    shadow_surf = pygame.Surface((glow_r * 2 + 4, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (*color, 60),  # Semi-transparent ellipse
                        shadow_surf.get_rect())
    screen.blit(shadow_surf, (foot_x - glow_r - 2, foot_y - 4))


def _draw_procedural_entity(screen: pygame.Surface,
                             entity, color: tuple) -> None:
    # [ID: REN-015] Procedural stand-in: stylised energy rectangle with details
    r  = pygame.Rect(int(entity.x), int(entity.y), entity.width, entity.height)
    dim_color = tuple(max(0, c - 60) for c in color)   # Darker body fill

    # Body — dark fill with coloured border
    pygame.draw.rect(screen, dim_color, r, border_radius=8)   # Body fill
    pygame.draw.rect(screen, color,     r, 3, border_radius=8)  # Glow border

    # Head circle
    head_r = entity.width // 4                          # Head radius
    head_x = int(entity.x + entity.width  // 2)        # Centred horizontally
    head_y = int(entity.y + head_r + 4)                 # Near top of body
    pygame.draw.circle(screen, dim_color, (head_x, head_y), head_r)   # Head fill
    pygame.draw.circle(screen, color,     (head_x, head_y), head_r, 2)  # Head glow

    # Eye — direction indicator
    eye_offset = 6 if not entity.facing_left else -6    # Side based on facing
    pygame.draw.circle(screen, color,
                       (head_x + eye_offset, head_y - 2), 4)   # Eye dot

    # Attack state — draw a weapon arm extended
    if entity.state == "attacking" and entity.hitbox is not None:
        arm_x = int(entity.hitbox.x + entity.hitbox.w // 2)   # Mid of hitbox
        arm_y = int(entity.y + entity.height // 2)             # Mid of body
        body_cx = int(entity.x + entity.width // 2)            # Body centre
        pygame.draw.line(screen, color, (body_cx, arm_y),
                         (arm_x, arm_y), 4)                    # Extended arm line
        pygame.draw.circle(screen, color, (arm_x, arm_y), 7)   # Fist dot


def _draw_debug(screen: pygame.Surface, entity) -> None:
    # [ID: REN-016] Debug overlays — hurtbox (green) and hitbox (red)
    dbg_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    hr = entity.hurtbox.get_rect()   # Hurtbox rect
    pygame.draw.rect(dbg_surf, (*COLOR_HURTBOX_DBG, 60), hr)   # Fill
    pygame.draw.rect(dbg_surf, (*COLOR_HURTBOX_DBG, 180), hr, 1)  # Border

    if entity.hitbox and entity.hitbox.active:   # Only if hitbox is live
        hb = entity.hitbox.get_rect()
        pygame.draw.rect(dbg_surf, (*COLOR_HITBOX_DBG, 60),  hb)
        pygame.draw.rect(dbg_surf, (*COLOR_HITBOX_DBG, 200), hb, 1)

    screen.blit(dbg_surf, (0, 0))   # Overlay transparent debug surface

    # Velocity vector
    if _font_small:
        txt = _font_small.render(
            f"vx:{entity.vx:.1f} vy:{entity.vy:.1f} {entity.state}",
            True, COLOR_UI_TEXT)
        screen.blit(txt, (int(entity.x), int(entity.y) - 18))   # Above entity


# Deprecated internal particle drawer - moved to vfx.py

def _draw_damage_texts(screen: pygame.Surface) -> None:
    alive = []
    for dt in _damage_texts:
        dt["x"] += dt["vx"]
        dt["y"] += dt["vy"]
        dt["vy"] += 0.1
        dt["life"] -= 1
        if dt["life"] > 0 and _font_med:
            alpha = int(255 * (dt["life"] / dt["max_life"]))
            txt_surf = _font_med.render(str(int(dt["damage"])), True, (255, 60, 60))
            txt_surf.set_alpha(alpha)
            screen.blit(txt_surf, (int(dt["x"]) - txt_surf.get_width()//2, int(dt["y"]) - txt_surf.get_height()//2))
            alive.append(dt)
    _damage_texts.clear()
    _damage_texts.extend(alive)


def _draw_hud(screen: pygame.Surface, player, enemy) -> None:
    global _ghost_hp_player, _ghost_hp_enemy
    if _ghost_hp_player == 0.0: _ghost_hp_player = player.hp
    if _ghost_hp_enemy == 0.0: _ghost_hp_enemy = enemy.hp
    
    _ghost_hp_player = _ghost_hp_player + (player.hp - _ghost_hp_player) * 0.05
    _ghost_hp_enemy = _ghost_hp_enemy + (enemy.hp - _ghost_hp_enemy) * 0.05

    # [ID: REN-018] HUD: health bars, names, AI debug state
    _draw_hp_bar(screen, player.hp, _ghost_hp_player, player.max_hp,
                 HUD_HP_PADDING, HUD_HP_BAR_Y,
                 COLOR_HP_PLAYER, player.name.upper(), left=True, is_flashing=(player.hit_flash > 0))
    _draw_hp_bar(screen, enemy.hp, _ghost_hp_enemy, enemy.max_hp,
                 SCREEN_WIDTH - HUD_HP_PADDING - HUD_HP_BAR_WIDTH, HUD_HP_BAR_Y,
                 COLOR_HP_ENEMY, enemy.name.upper(), left=False, is_flashing=(enemy.hit_flash > 0))

    # [ID: REN-019] Try to draw icon HP indicators from binding_icons
    _draw_icon_safe(screen, _ICON_HP_BAR, COLOR_HP_PLAYER,
                    HUD_HP_PADDING - 4, HUD_HP_BAR_Y - 8, HUD_ICON_SIZE + 12)
    _draw_icon_safe(screen, _ICON_HP_BAR, COLOR_HP_ENEMY,
                    SCREEN_WIDTH - HUD_HP_PADDING - HUD_ICON_SIZE - 8,
                    HUD_HP_BAR_Y - 8, HUD_ICON_SIZE + 12)

    # [ID: REN-020] VS label centred at top
    if _font_med:
        vs = _font_med.render("VS", True, COLOR_UI_TEXT)
        screen.blit(vs, (SCREEN_WIDTH // 2 - vs.get_width() // 2, HUD_HP_BAR_Y + 2))

    # [ID: REN-021] Controls hint at bottom
    if _font_small:
        hint = _font_small.render(
            "WASD: Move  |  LMB: Light Attack  |  RMB: Heavy Attack  |  F3: Debug",
            True, (100, 100, 150))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           SCREEN_HEIGHT - 22))


def _draw_hp_bar(screen: pygame.Surface, hp: float, ghost_hp: float, max_hp: float,
                 bx: int, by: int, color: tuple, label: str,
                 left: bool, is_flashing: bool = False) -> None:
    # [ID: REN-022] Segmented health bar with ghost bar
    ratio = max(0.0, hp / max_hp)
    ghost_ratio = max(0.0, ghost_hp / max_hp)

    # Bar track background
    bg = pygame.Rect(bx, by, HUD_HP_BAR_WIDTH, HUD_HP_BAR_HEIGHT)
    pygame.draw.rect(screen, COLOR_HP_BG,     bg, border_radius=4)
    pygame.draw.rect(screen, COLOR_HP_BORDER, bg, 2, border_radius=4)

    # Ghost HP fill (red/orange)
    ghost_w = int(HUD_HP_BAR_WIDTH * ghost_ratio)
    if ghost_w > 2:
        ghost_fill = pygame.Rect(bx + 1, by + 1, ghost_w - 2, HUD_HP_BAR_HEIGHT - 2)
        if not left: ghost_fill.x = bx + HUD_HP_BAR_WIDTH - ghost_w + 1
        pygame.draw.rect(screen, (255, 60, 60), ghost_fill, border_radius=3)

    # Actual HP fill
    fill_w = int(HUD_HP_BAR_WIDTH * ratio)
    if fill_w > 2:
        fill = pygame.Rect(bx + 1, by + 1, fill_w - 2, HUD_HP_BAR_HEIGHT - 2)
        if not left: fill.x = bx + HUD_HP_BAR_WIDTH - fill_w + 1
        fill_color = COLOR_HIT_FLASH if is_flashing else color
        pygame.draw.rect(screen, fill_color, fill, border_radius=3)

    # Segment dividers
    seg_w = HUD_HP_BAR_WIDTH // HUD_SEGMENT_COUNT
    for i in range(1, HUD_SEGMENT_COUNT):
        sx = bx + i * seg_w         # X of divider line
        pygame.draw.line(screen, COLOR_HP_BG, (sx, by + 1),
                         (sx, by + HUD_HP_BAR_HEIGHT - 2), 1)

    # Label text
    if _font_small:
        hp_text = _font_small.render(f"{label}  {int(hp)}/{int(max_hp)}",
                                      True, COLOR_UI_TEXT)
        tx = bx if left else bx + HUD_HP_BAR_WIDTH - hp_text.get_width()
        screen.blit(hp_text, (tx, by + HUD_HP_BAR_HEIGHT + 4))


def _draw_icon_safe(screen: pygame.Surface, icon_name: str, tint: tuple,
                    x: int, y: int, size: int) -> None:
    # [ID: REN-023] Load and draw icon — silently skip if file missing
    path = os.path.join(ICON_DIR, icon_name)
    if not os.path.exists(path):
        return   # Icon file not present yet — skip gracefully
    try:
        icon = asset_loader.load_tinted(path, tint, size)
        screen.blit(icon, (x, y))   # Blit tinted icon
    except Exception:
        pass     # Any load/blit error is non-fatal in renderer


def draw_round_intro(screen: pygame.Surface, timer: float) -> None:
    # timer goes from 0 to 2.5
    global _font_big
    if not _font_big: return
    
    # "ROUND 1" / "FIGHT!" animation
    # Fade in -> scale -> disappear
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    
    scale = 1.0
    alpha = 255
    txt = ""
    col = (255, 255, 255)

    if timer < 1.5:
        # Round 1
        scale = max(1.0, 3.0 - (timer / 0.5) * 2.0) if timer < 0.5 else 1.0
        alpha = min(255, int((timer / 0.2) * 255)) if timer < 0.2 else 255
        if timer > 1.2:
            alpha = max(0, int(((1.5 - timer) / 0.3) * 255))
        
        txt = "ROUND 1"
        col = (255, 200, 50)
    elif timer < 2.5:
        # Fight
        t2 = timer - 1.5
        scale = max(1.0, 2.0 - (t2 / 0.2)) if t2 < 0.2 else 1.0 + (t2 * 0.5)
        alpha = min(255, int((t2 / 0.1) * 255)) if t2 < 0.1 else 255
        if t2 > 0.8:
            alpha = max(0, int(((1.0 - t2) / 0.2) * 255))
            
        txt = "FIGHT!"
        col = (255, 50, 50)
    else:
        return
        
    base_surf = _font_big.render(txt, True, col)
    base_surf.set_alpha(alpha)
    w = int(base_surf.get_width() * scale)
    h = int(base_surf.get_height() * scale)
    scaled = pygame.transform.smoothscale(base_surf, (max(1, w), max(1, h)))
    screen.blit(scaled, (cx - w//2, cy - h//2 - 50))

def draw_result(screen: pygame.Surface, winner: str) -> None:
    # [ID: REN-024] Full-screen win/loss overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))     # Semi-transparent black
    screen.blit(overlay, (0, 0))

    if _font_big and _font_med:
        pulse = abs(math.sin(_frame_counter * 0.08))   # Pulsing brightness
        alpha = int(180 + 75 * pulse)
        col   = (*COLOR_WIN_GOLD, alpha) if winner != "DRAW" else (*COLOR_UI_TEXT, alpha)

        title = _font_big.render(f"{winner} WINS!", True, COLOR_WIN_GOLD)
        sub   = _font_med.render("Press R to restart  |  ESC to quit", True, COLOR_UI_TEXT)

        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                             SCREEN_HEIGHT // 2 - 50))
        screen.blit(sub,   (SCREEN_WIDTH // 2 - sub.get_width()   // 2,
                             SCREEN_HEIGHT // 2 + 20))


def draw_pause_menu(screen: pygame.Surface) -> None:
    # Overlay for pause state with controls
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))     # Dark translucent overlay
    screen.blit(overlay, (0, 0))

    if _font_big and _font_med and _font_small:
        title = _font_big.render("PAUSED", True, COLOR_UI_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        # P1 Controls
        p1_title = _font_med.render("PLAYER 1 CONTROLS", True, COLOR_PLAYER)
        screen.blit(p1_title, (SCREEN_WIDTH // 4 - p1_title.get_width() // 2, 200))
        
        p1_lines = [
            "Movement: W, A, S, D",
            "Jump: W / Space",
            "Light Attack: LMB / Q",
            "Heavy Attack: RMB / E",
            "Parry: F",
            "Special: W + RMB"
        ]
        
        for i, line in enumerate(p1_lines):
            txt = _font_small.render(line, True, COLOR_UI_TEXT)
            screen.blit(txt, (SCREEN_WIDTH // 4 - 80, 250 + i * 30))

        # P2 Controls
        p2_title = _font_med.render("PLAYER 2 CONTROLS", True, COLOR_ENEMY)
        screen.blit(p2_title, (3 * SCREEN_WIDTH // 4 - p2_title.get_width() // 2, 200))
        
        p2_lines = [
            "Movement: Arrow Keys",
            "Jump: Up Arrow",
            "Light Attack: Numpad 1",
            "Heavy Attack: Numpad 2",
            "Parry: Numpad 0",
            "Special: Up + Numpad 2"
        ]
        
        for i, line in enumerate(p2_lines):
            txt = _font_small.render(line, True, COLOR_UI_TEXT)
            screen.blit(txt, (3 * SCREEN_WIDTH // 4 - 80, 250 + i * 30))

        sub = _font_med.render("Press ESC to resume  |  Press R to return to lobby", True, (150, 150, 150))
        screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT - 100))

