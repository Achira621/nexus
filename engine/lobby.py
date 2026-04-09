# [ID: LBY-001] lobby.py — 3-Panel Cinematic Character Select
import sys
import pygame
import math
import os
import re

from combat.roster import (
    get_vajra_kali, get_takshaka, get_rudra_shiva, get_vajra_garuda
)
from utils.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    SPRITE_DIR, BG_DIR,
    COLOR_PLAYER, COLOR_ENEMY, FPS
)
from utils import asset_loader

# ------------------------------------------------------------------ #
#  Roster definition
# ------------------------------------------------------------------ #
ROSTER = [
    {
        "name":    "Vajra-Kali",
        "factory": get_vajra_kali,
        "color":   (255, 80, 30),
        "role":    "Aggressive",
        "desc":    "The Crimson Tempest. Closes gaps quickly and exploits fiery bursts.",
        "skills":  ["Agni Strike (Burn)", "Vidyut Lash (Combo)"]
    },
    {
        "name":    "Takshaka",
        "factory": get_takshaka,
        "color":   (0, 210, 130),
        "role":    "Control",
        "desc":    "The Venom Architect. Locks down enemies with heavy zoning tactics.",
        "skills":  ["Coil Guard (Root)", "Serpent Dominion (Slow)"]
    },
    {
        "name":    "Shinobi",
        "factory": get_rudra_shiva,
        "color":   (130, 80, 255),
        "role":    "Balanced",
        "desc":    "The Ascendant. Deals devastating, slow sweeping celestial attacks.",
        "skills":  ["Trishul Cleave", "Tandava Focus"]
    },
    {
        "name":    "Samurai",
        "factory": get_vajra_garuda,
        "color":   (255, 200, 50),
        "role":    "Mobility",
        "desc":    "The Sky Warden. Unmatched verticality and air-to-ground dominance.",
        "skills":  ["Wing Gust", "Talon Strike"]
    },
]

# States
LOBBY_STATE_P1 = 0
LOBBY_STATE_P2 = 1
LOBBY_STATE_VS = 2

# Visual Bounds
GRID_X = 80
GRID_Y = 180
CELL_W = 120
CELL_H = 120
CELL_PAD = 20

def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())

def load_preview_anim(sprite_id: str) -> list:
    # Build large animated sprite for the center lobby
    folder = os.path.join(SPRITE_DIR, sprite_id)
    sheet_path = asset_loader.find_sheet(folder)
    frames = []
    
    if sprite_id == "vajra_kali":
        idle_path = os.path.join(folder, "Vajra kali-idle.png")
        if os.path.exists(idle_path):
            raw_frames = asset_loader.load_spritesheet_grid(idle_path, 5, 5)
            frames = raw_frames[:15]
    elif sprite_id == "takshaka":
        if sheet_path:
             frames = asset_loader.load_spritesheet_grid(sheet_path, 6, 4)[:6]
    elif sprite_id in ("rudra_shiva", "vajra_garuda"):
        idle_path = os.path.join(folder, "Idle.png")
        if os.path.exists(idle_path):
            frames = asset_loader.load_spritesheet_grid(idle_path, 6, 1)
    else:
        if sheet_path:
            # Most default character idle loops are first 6 frames
            raw_frames = asset_loader.load_spritesheet_grid(sheet_path, 6, 4)
            if not raw_frames:
                 raw_frames = asset_loader.load_spritesheet_grid(sheet_path, 6, 6)
            if raw_frames:
                 frames = raw_frames[:6]
                 
    w, h = 420, 500  # Massive lobby scaling
    scaled = []
    for f in frames:
        alpha_rect = f.get_bounding_rect()
        if alpha_rect.width > 0 and alpha_rect.height > 0:
            trimmed = pygame.Surface(alpha_rect.size, pygame.SRCALPHA)
            trimmed.blit(f, (0, 0), alpha_rect)
            scaled.append(pygame.transform.smoothscale(trimmed, (w, h)))
            
    # Absolute fallback (draw colored box) if it fails
    if not scaled:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (150, 150, 150, 120), surf.get_rect(), border_radius=20)
        scaled.append(surf)
        
    return scaled


def _get_grid_rect(index: int) -> pygame.Rect:
    col = index % 2
    row = index // 2
    px = GRID_X + col * (CELL_W + CELL_PAD)
    py = GRID_Y + row * (CELL_H + CELL_PAD)
    return pygame.Rect(px, py, CELL_W, CELL_H)


def run(screen: pygame.Surface, clock: pygame.time.Clock) -> tuple:
    pygame.event.clear()

    try:
        font_main  = pygame.font.SysFont("segoeui", 54, bold=True)
        font_sub   = pygame.font.SysFont("segoeui", 32, bold=True)
        font_desc  = pygame.font.SysFont("segoeui", 20)
        font_btn   = pygame.font.SysFont("segoeui", 28, bold=True)
    except Exception:
        font_main  = pygame.font.Font(None, 64)
        font_sub   = pygame.font.Font(None, 40)
        font_desc  = pygame.font.Font(None, 24)
        font_btn   = pygame.font.Font(None, 32)
        
    # Load background
    bg_path = os.path.join(BG_DIR, "arenabackground.png")
    bg_surf = None
    if os.path.exists(bg_path):
        try:
            raw = pygame.image.load(bg_path).convert()
            bg_surf = pygame.transform.smoothscale(raw, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except: pass

    # Pre-cache animations for everyone to keep hovering swift
    previews = {}
    icons = {}
    for entry in ROSTER:
        sid = entry["factory"](1).get("sprite_id", entry["name"])
        anims = load_preview_anim(sid)
        previews[entry["name"]] = anims
        # Scale down the first frame for the icon grid
        if anims:
            icons[entry["name"]] = pygame.transform.smoothscale(anims[0], (int(CELL_W*0.9), int(CELL_H*0.9)))
            
    # State tracking
    state = LOBBY_STATE_P1
    p1_idx = 0
    p2_idx = 1
    
    hover_idx = 0
    active_idx = 0
    
    frame = 0
    vs_timer = 0.0
    game_mode = "PvE"

    # Layout vars
    btn_rect = pygame.Rect(SCREEN_WIDTH - 250, SCREEN_HEIGHT - 120, 200, 60)

    while True:
        dt = clock.tick(FPS) / 1000.0
        frame += 1
        
        m_x, m_y = pygame.mouse.get_pos()
        m_clicked = False
        
        # Determine tracking index
        active_idx = p1_idx if state == LOBBY_STATE_P1 else p2_idx

        # Check Mouse Hovers over Grid
        for i in range(len(ROSTER)):
            r = _get_grid_rect(i)
            if r.collidepoint(m_x, m_y):
                hover_idx = i

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    m_clicked = True
                    # Click on grid locks character
                    for i in range(len(ROSTER)):
                        r = _get_grid_rect(i)
                        if r.collidepoint(m_x, m_y):
                            if state == LOBBY_STATE_P1:
                                p1_idx = i
                            elif state == LOBBY_STATE_P2:
                                p2_idx = i

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_a, pygame.K_LEFT):
                    active_idx = max(0, active_idx - 1)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    active_idx = min(len(ROSTER)-1, active_idx + 1)
                elif event.key in (pygame.K_w, pygame.K_UP):
                    active_idx = max(0, active_idx - 2)
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    active_idx = min(len(ROSTER)-1, active_idx + 2)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Keyboard shortcut for ready
                    if state == LOBBY_STATE_P1:
                        state = LOBBY_STATE_P2
                        hover_idx = p2_idx
                    elif state == LOBBY_STATE_P2:
                        state = LOBBY_STATE_VS
                        
                elif event.key in (pygame.K_m,):
                    if state == LOBBY_STATE_P1:
                        game_mode = "PvP" if game_mode == "PvE" else "PvE"

                if state == LOBBY_STATE_P1: p1_idx = active_idx
                if state == LOBBY_STATE_P2: p2_idx = active_idx
                hover_idx = active_idx

        # Ready Button check
        btn_hover = btn_rect.collidepoint(m_x, m_y)
        if m_clicked and btn_hover:
            if state == LOBBY_STATE_P1:
                state = LOBBY_STATE_P2
                hover_idx = p2_idx
            elif state == LOBBY_STATE_P2:
                state = LOBBY_STATE_VS

        if state == LOBBY_STATE_VS:
            vs_timer += dt
            if vs_timer > 3.0: 
                break

        _draw(screen, state, frame, bg_surf, hover_idx, p1_idx, p2_idx, btn_rect, btn_hover, previews, icons, font_main, font_sub, font_desc, font_btn, vs_timer, game_mode)
        pygame.display.flip()

    p_config = ROSTER[p1_idx]["factory"](1)
    e_config = ROSTER[p2_idx]["factory"](-1)
    return p_config, e_config, game_mode


def _draw(screen, state, frame, bg_surf, hover_idx, p1_idx, p2_idx, btn_rect, btn_hover, previews, icons, font_main, font_sub, font_desc, font_btn, vs_timer, game_mode):
    # ──── BACKGROUND ────
    if bg_surf:
        screen.blit(bg_surf, (0, 0))
    else:
        screen.fill((10, 14, 28))
    
    # Overlay dark tint for contrast
    dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 10, 180))
    screen.blit(dim, (0, 0))
    
    pulse = abs(math.sin(frame * 0.05))

    if state == LOBBY_STATE_VS:
        _draw_vs_screen(screen, p1_idx, p2_idx, vs_timer, font_main, font_sub)
        return

    # ──── TITLE HEADER ────
    title_text = "SELECT PLAYER 1" if state == LOBBY_STATE_P1 else "SELECT PLAYER 2 (OPPONENT)"
    title_col = COLOR_PLAYER if state == LOBBY_STATE_P1 else COLOR_ENEMY
    t_surf = font_main.render(title_text, True, title_col)
    screen.blit(t_surf, (80, 50))
    
    if state == LOBBY_STATE_P1:
        mode_surf = font_sub.render(f"Mode: {game_mode} (Press 'M' to toggle)", True, (200, 200, 200))
        screen.blit(mode_surf, (80, 110))
    
    # Selection locked checks
    current_pick = p1_idx if state == LOBBY_STATE_P1 else p2_idx
    entry = ROSTER[hover_idx]

    # ──── LEFT: GRID ────
    for i, char in enumerate(ROSTER):
        r = _get_grid_rect(i)
        is_hover = (i == hover_idx)
        is_selected = (i == current_pick)
        
        # Background box
        box_alpha = 150 if is_hover else 80
        box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(box, (30, 35, 60, box_alpha), box.get_rect(), border_radius=12)
        
        # Border
        b_col = (200, 200, 220) if is_hover else (80, 80, 100)
        if is_selected:
            b_col = title_col
        pygame.draw.rect(box, b_col, box.get_rect(), 3 + (2 if is_selected else 0), border_radius=12)
        screen.blit(box, r)
        
        # Draw Icon
        icon = icons.get(char["name"])
        if icon:
            # Add breathing scale on hover
            if is_hover:
                scale_icn = pygame.transform.smoothscale(icon, (int(r.w*1.05), int(r.h*1.05)))
                screen.blit(scale_icn, (r.centerx - scale_icn.get_width()//2, r.centery - scale_icn.get_height()//2))
            else:
                screen.blit(icon, (r.centerx - icon.get_width()//2, r.centery - icon.get_height()//2))
                
        # Badge locks
        if i == p1_idx and state == LOBBY_STATE_P2:
            badge = font_desc.render("P1", True, (255, 255, 255))
            pygame.draw.rect(screen, COLOR_PLAYER, (r.x-10, r.y-10, 36, 26), border_radius=6)
            screen.blit(badge, (r.x - 4, r.y - 8))


    # ──── CENTER: LIVING PREVIEW ────
    anim_list = previews.get(entry["name"])
    if anim_list:
        # Loop animation at 10FPS (frame // 6)
        anim_idx = (frame // 6) % len(anim_list)
        sprite = anim_list[anim_idx]
        
        # Breathing float
        float_y = math.sin(frame * 0.04) * 8
        cx = SCREEN_WIDTH // 2 - sprite.get_width() // 2
        cy = SCREEN_HEIGHT // 2 - sprite.get_height() // 2 + float_y + 40
        
        # Back glow
        glow_rad = int(250 + pulse * 20)
        glow_surf = pygame.Surface((glow_rad*2, glow_rad*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*entry["color"], 25), (glow_rad, glow_rad), glow_rad)
        screen.blit(glow_surf, (cx + sprite.get_width()//2 - glow_rad, cy + sprite.get_height()//2 - glow_rad))
        
        screen.blit(sprite, (cx, cy))


    # ──── RIGHT: INFO PANEL ────
    info_x = SCREEN_WIDTH - 400
    info_y = 180
    
    # Big Name
    in_name = font_main.render(entry["name"].upper(), True, (255, 255, 255))
    screen.blit(in_name, (info_x, info_y))
    
    # Role Badge
    role_bg = pygame.Surface((150, 30), pygame.SRCALPHA)
    pygame.draw.rect(role_bg, (*entry["color"], 180), role_bg.get_rect(), border_radius=15)
    screen.blit(role_bg, (info_x, info_y + 70))
    role_text = font_desc.render(entry["role"], True, (255, 255, 255))
    screen.blit(role_text, (info_x + 75 - role_text.get_width()//2, info_y + 73))
    
    # Desc
    wrapped = entry["desc"].split(". ")
    for iy, line in enumerate(wrapped):
        d_surf = font_desc.render(line + ".", True, (180, 190, 210))
        screen.blit(d_surf, (info_x, info_y + 130 + (iy * 30)))
        
    # Skills
    screen.blit(font_desc.render("Abilities:", True, (200, 200, 200)), (info_x, info_y + 220))
    for sy, skill in enumerate(entry["skills"]):
        pygame.draw.circle(screen, entry["color"], (info_x + 10, info_y + 262 + (sy * 30)), 4)
        sk_surf = font_desc.render(skill, True, (255, 255, 255))
        screen.blit(sk_surf, (info_x + 25, info_y + 250 + (sy * 30)))


    # ──── READY BUTTON ────
    fill_col = (*title_col, 255) if not btn_hover else (255, 255, 255)
    pygame.draw.rect(screen, fill_col, btn_rect, border_radius=8)
    
    btn_text = font_btn.render("LOCK IN" if state == LOBBY_STATE_P1 else "READY", True, (10, 10, 20))
    screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width()//2, btn_rect.centery - btn_text.get_height()//2))



def _draw_vs_screen(screen, p1_idx, p2_idx, vs_timer, font_main, font_sub):
    p1 = ROSTER[p1_idx]
    p2 = ROSTER[p2_idx]
    
    # Splitting screen colors
    pygame.draw.rect(screen, (*p1["color"], 60), (0, 0, SCREEN_WIDTH//2, SCREEN_HEIGHT))
    pygame.draw.rect(screen, (*p2["color"], 60), (SCREEN_WIDTH//2, 0, SCREEN_WIDTH//2, SCREEN_HEIGHT))
    
    # Names sliding in
    slide = min(1.0, vs_timer / 0.6)
    ease = 1.0 - (1.0 - slide)**3
    
    # P1 Name
    n1 = font_main.render(p1["name"].upper(), True, p1["color"])
    x1 = -400 + (SCREEN_WIDTH//4 * ease)
    screen.blit(n1, (x1, SCREEN_HEIGHT//2 - 40))
    
    # P2 Name
    n2 = font_main.render(p2["name"].upper(), True, p2["color"])
    x2 = SCREEN_WIDTH + 400 - (SCREEN_WIDTH//4 * ease) - n2.get_width()
    screen.blit(n2, (x2, SCREEN_HEIGHT//2 - 40))
    
    # VS text pops in
    if vs_timer > 0.6:
        vs_t = font_main.render("VS", True, (250, 40, 40))
        cx, cy = SCREEN_WIDTH//2 - vs_t.get_width()//2, SCREEN_HEIGHT//2 - 40
        
        # Scaling pop
        scale = max(1.0, 3.0 - (vs_timer - 0.6) * 10)
        scaled_vs = pygame.transform.smoothscale(vs_t, (int(vs_t.get_width()*scale), int(vs_t.get_height()*scale)))
        screen.blit(scaled_vs, (cx - (scaled_vs.get_width() - vs_t.get_width())//2, cy - (scaled_vs.get_height() - vs_t.get_height())//2))

    # Fade out
    if vs_timer > 2.2:
        fade = min(1.0, (vs_timer - 2.2) / 0.8)
        fs = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fs.set_alpha(int(255 * fade))
        fs.fill((0,0,0))
        screen.blit(fs, (0,0))
