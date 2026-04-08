import pygame
import math
import random
from utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT

_fg_effects = []
_trails = {}

def update(dt: float):
    # Active Effects (Sparks / Bursts)
    alive_fg = []
    for ef in _fg_effects:
        ef['life'] -= dt
        if ef['life'] > 0:
            if ef['type'] == 'spark':
                ef['x'] += ef['vx'] * dt * 60
                ef['y'] += ef['vy'] * dt * 60
                ef['vy'] += 0.25 * dt * 60  # Gravity
            elif ef['type'] == 'burst':
                ef['radius'] += 400 * dt
            alive_fg.append(ef)
    _fg_effects.clear()
    _fg_effects.extend(alive_fg)
    
    # Trails fade
    for eid, data in _trails.items():
        keep = []
        for p in data['points']:
            p['life'] -= dt
            if p['life'] > 0:
                keep.append(p)
        data['points'] = keep

def spawn_impact(x: float, y: float, color: tuple):
    # Expanding ring
    _fg_effects.append({
        'type': 'burst',
        'x': x, 'y': y,
        'radius': 10,
        'color': color,
        'life': 0.2, 'max_life': 0.2
    })
    _fg_effects.append({
        'type': 'burst',
        'x': x, 'y': y,
        'radius': 5,
        'color': (255, 255, 255),
        'life': 0.15, 'max_life': 0.15
    })
    # Sparks trajectory
    for _ in range(12):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(8, 16)
        _fg_effects.append({
            'type': 'spark',
            'x': x, 'y': y,
            'vx': math.cos(angle)*speed,
            'vy': math.sin(angle)*speed,
            'color': random.choice([color, (255, 255, 255), (255, 210, 100)]),
            'life': random.uniform(0.15, 0.35),
            'max_life': 0.35
        })

def add_trail_point(entity, x: float, y: float, color: tuple):
    eid = id(entity)
    if eid not in _trails:
        _trails[eid] = {'points': [], 'color': color}
    # Don't add if very close to previous
    pts = _trails[eid]['points']
    if pts:
        last = pts[-1]
        dist = math.hypot(last['x']-x, last['y']-y)
        if dist < 5: return
        
    pts.append({'x': x, 'y': y, 'life': 0.15, 'max_life': 0.15})
    if len(pts) > 10:
        pts.pop(0)

def draw_bg_auras(screen: pygame.Surface, entities: list, frame_counter: int):
    # Ambient mist / float particles
    pulse = abs(math.sin(frame_counter * 0.05))
    
    for entity in entities:
        # Determine aura color. Default to their thematic tint
        # Rudra-Shiva is purple, Vajra is red/orange, Takshaka is green
        aura_col = (100, 100, 100)
        h_name = getattr(entity, 'name', '').lower()
        if 'kali' in h_name: aura_col = (255, 50, 0)
        elif 'taksh' in h_name: aura_col = (0, 200, 80)
        elif 'rudra' in h_name: aura_col = (120, 60, 255)
        elif 'garud' in h_name: aura_col = (255, 200, 0)
        else: aura_col = (100, 100, 100)
        
        cx = int(entity.x + entity.width/2)
        cy = int(entity.y + entity.height/2)
        
        # Draw soft glow
        rad = int(entity.width * 0.8 + 20 * pulse)
        glow = pygame.Surface((rad*2, rad*2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*aura_col, 20), (rad, rad), rad)
        pygame.draw.circle(glow, (*aura_col, 35), (rad, rad), int(rad*0.6))
        screen.blit(glow, (cx - rad, cy - rad + 20))
        
def draw_fg_effects(screen: pygame.Surface):
    # Trails
    for eid, data in _trails.items():
        pts = data['points']
        if len(pts) < 2: continue
        
        c = data['color']
        # Build polygon for thick trail
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i+1]
            
            life_ratio = p1['life'] / p1['max_life']
            alpha = int(255 * life_ratio)
            thickness = int(25 * life_ratio)
            
            if thickness < 1: continue
            
            dx = p2['x'] - p1['x']
            dy = p2['y'] - p1['y']
            length = math.hypot(dx, dy)
            if length == 0: continue
            
            nx, ny = -dy/length, dx/length  # Normal
            
            poly = [
                (p1['x'] + nx*thickness, p1['y'] + ny*thickness),
                (p1['x'] - nx*thickness, p1['y'] - ny*thickness),
                (p2['x'] - nx*(thickness*0.6), p2['y'] - ny*(thickness*0.6)),
                (p2['x'] + nx*(thickness*0.6), p2['y'] + ny*(thickness*0.6))
            ]
            
            surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (*c, alpha), poly)
            screen.blit(surf, (0,0))
            
    # Impacts & Sparks
    for ef in _fg_effects:
        life_ratio = ef['life'] / ef['max_life']
        alpha = int(255 * life_ratio)
        
        if ef['type'] == 'burst':
            rad = int(ef['radius'])
            if rad > 0:
                b_surf = pygame.Surface((rad*2, rad*2), pygame.SRCALPHA)
                width = int(8 * life_ratio) + 2
                pygame.draw.circle(b_surf, (*ef['color'], alpha), (rad, rad), rad, width)
                screen.blit(b_surf, (int(ef['x']) - rad, int(ef['y']) - rad))
                
        elif ef['type'] == 'spark':
            sz = 6
            ps = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            
            # Stretch based on velocity
            length = math.hypot(ef['vx'], ef['vy'])
            if length > 0.1:
                end_x = sz + (ef['vx'] / length) * (length * 0.8)
                end_y = sz + (ef['vy'] / length) * (length * 0.8)
                pygame.draw.line(ps, (*ef['color'], alpha), (sz, sz), (end_x, end_y), int(3 * life_ratio)+1)
                pygame.draw.circle(ps, (255,255,255, alpha), (sz, sz), int(2*life_ratio)+1)
            else:
                pygame.draw.circle(ps, (*ef['color'], alpha), (sz, sz), int(3*life_ratio)+1)
                
            screen.blit(ps, (int(ef['x']) - sz, int(ef['y']) - sz))
