# [ID: HIT-001] hitbox.py — Hurtbox (receives damage) and Hitbox (deals damage)
import pygame  # For Rect intersection tests


class Hurtbox:  # Damageable area — always active while entity is alive
    def __init__(self, x: float, y: float, w: float, h: float, duration: int = 1):
        # [ID: HIT-002] Initialize geometry from entity position
        self.x = x   # World left edge
        self.y = y   # World top edge
        self.w = w   # Width  (px)
        self.h = h   # Height (px)

    def get_rect(self) -> pygame.Rect:    # Convert to pygame Rect
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    def sync(self, entity) -> None:       # Track entity position every frame
        # [ID: HIT-003] Slight inset so hurtbox is tighter than sprite
        self.x = entity.x + entity.width  * 0.05   # 5% inset left
        self.y = entity.y + entity.height * 0.08   # 8% inset top
        self.w = entity.width  * 0.90               # 90% of width
        self.h = entity.height * 0.88               # 88% of height


class Hitbox:   # Damaging area — only active during attack active frames
    def __init__(self, x: float, y: float, w: float, h: float, duration: int = 1):
        # [ID: HIT-004] Geometry of the damaging region
        self.x = x      # World left edge
        self.y = y      # World top edge
        self.w = w      # Width  (px)
        self.h = h      # Height (px)
        self.duration = duration  # Frames this hitbox should remain valid
        self.active = True  # Live flag

    def get_rect(self) -> pygame.Rect:    # Convert to pygame Rect
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    @classmethod
    def from_attack(cls, entity, attack) -> "Hitbox":  # Build from entity + attack
        # [ID: HIT-005] Position hitbox in front of the attacking entity
        forward_offset = attack.hitbox_forward_offset or entity.width * 0.08
        hw = attack.hitbox_width or attack.hitbox_range
        if entity.facing_left:                         # Faces left
            hx = entity.x - hw - forward_offset        # Extends left of body
        else:                                          # Faces right
            hx = entity.x + entity.width + forward_offset  # Extends right of body
        hy = entity.y + entity.height * attack.hitbox_y_factor
        hh = entity.height * attack.hitbox_height_factor
        return cls(hx, hy, hw, hh, attack.active)      # Construct and return


def check_hit(hitbox: "Hitbox | None", hurtbox: Hurtbox) -> bool:  # Rect test
    # [ID: HIT-006] Pure rect intersection — no pixel collision per rules
    if hitbox is None or not hitbox.active:   # Must be live
        return False
    return hitbox.get_rect().colliderect(hurtbox.get_rect())  # Pygame test
