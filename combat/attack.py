# [ID: COM-001] attack.py — Attack data class with full frame-timing model
from dataclasses import dataclass   # Clean data container
from utils.constants import (       # All values from constants, no hardcoding
    LIGHT_DAMAGE, LIGHT_STARTUP, LIGHT_ACTIVE, LIGHT_RECOVERY,
    LIGHT_KNOCKBACK, LIGHT_RANGE,
    HEAVY_DAMAGE, HEAVY_STARTUP, HEAVY_ACTIVE, HEAVY_RECOVERY,
    HEAVY_KNOCKBACK, HEAVY_RANGE,
    DIRECTIONAL_DAMAGE, DIRECTIONAL_STARTUP, DIRECTIONAL_ACTIVE,
    DIRECTIONAL_RECOVERY, DIRECTIONAL_KNOCKBACK, DIRECTIONAL_RANGE,
)


@dataclass
class Attack:  # Every attack move — defines all timing and damage properties
    # [ID: COM-002] Required attributes per combat design rules
    damage:       float   # Hit points removed on successful hit
    startup:      int     # Frames before hitbox activates
    active:       int     # Frames during which hitbox is live
    recovery:     int     # Frames of cooldown after active ends
    knockback:    tuple   # (kx, ky) push impulse vector
    direction:    int     # +1 = right, -1 = left (assigned at runtime)
    attack_type:  str     # "light" | "heavy" | "directional" | "special"
    hitbox_range: float   # How far the hitbox extends (px)
    hitbox_width: float = 0.0  # Optional explicit hitbox width
    hitbox_height_factor: float = 0.65  # Portion of body height covered
    hitbox_y_factor: float = 0.15  # Vertical placement relative to body
    hitbox_forward_offset: float = 0.0  # Forward offset from body edge
    status_effect: str = None  # e.g., "burn", "poison", "slow", "immobilize"
    status_duration: int = 0   # Duration in frames
    movement_override: float = 0.0  # Optional forced vx (e.g. for dash)

    @property
    def total_frames(self) -> int:   # Total attack duration in frames
        return self.startup + self.active + self.recovery  # Sum three phases


# [ID: COM-003] Factory — light attack (fast, low damage)
def make_light(direction: int = 1) -> Attack:
    return Attack(
        damage=LIGHT_DAMAGE, startup=LIGHT_STARTUP,
        active=LIGHT_ACTIVE, recovery=LIGHT_RECOVERY,
        knockback=LIGHT_KNOCKBACK, direction=direction,
        attack_type="light", hitbox_range=LIGHT_RANGE,
    )


# [ID: COM-004] Factory — heavy attack (slow, high damage)
def make_heavy(direction: int = 1) -> Attack:
    return Attack(
        damage=HEAVY_DAMAGE, startup=HEAVY_STARTUP,
        active=HEAVY_ACTIVE, recovery=HEAVY_RECOVERY,
        knockback=HEAVY_KNOCKBACK, direction=direction,
        attack_type="heavy", hitbox_range=HEAVY_RANGE,
    )


# [ID: COM-005] Factory — directional attack (movement + input combo)
def make_directional(direction: int = 1) -> Attack:
    return Attack(
        damage=DIRECTIONAL_DAMAGE, startup=DIRECTIONAL_STARTUP,
        active=DIRECTIONAL_ACTIVE, recovery=DIRECTIONAL_RECOVERY,
        knockback=DIRECTIONAL_KNOCKBACK, direction=direction,
        attack_type="directional", hitbox_range=DIRECTIONAL_RANGE,
    )
