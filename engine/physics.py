# [ID: PHY-001] physics.py — gravity, movement integration, collision resolution
from utils.constants import (   # All values from constants
    GRAVITY, GROUND_Y, WALL_LEFT, WALL_RIGHT,
)
from utils import logger        # Collision debug logging


def apply_gravity(entity) -> None:   # Accumulate downward velocity
    if not entity.on_ground:         # Skip if standing on ground
        # [ID: PHY-002] Gravity adds to vertical velocity each frame
        entity.vy += GRAVITY         # Positive vy = moving down


def integrate(entity) -> None:       # Move entity by its velocity
    # [ID: PHY-003] Euler integration: new_pos = old_pos + velocity
    entity.x += entity.vx           # Horizontal displacement
    entity.y += entity.vy           # Vertical displacement


def resolve_ground(entity) -> None:  # Prevent entity from sinking into floor
    ground_top = GROUND_Y - entity.height   # Y where entity feet = ground
    if entity.y >= ground_top:             # Entity has reached or passed ground
        # [ID: PHY-004] Snap to ground and kill vertical velocity
        entity.y        = float(ground_top)
        entity.vy       = 0.0
        entity.on_ground = True
    else:
        entity.on_ground = False           # Still airborne


def clamp_walls(entity) -> None:  # Keep entity inside arena bounds
    # [ID: PHY-005] Horizontal boundary enforcement
    lo = float(WALL_LEFT)                  # Left arena edge
    hi = float(WALL_RIGHT - entity.width)  # Right edge (entity right = wall)
    if entity.x < lo:
        entity.x  = lo                    # Clamp left
        entity.vx = 0.0                   # Kill horizontal velocity on wall
        logger.log_collision("Wall clamp: LEFT")
    elif entity.x > hi:
        entity.x  = hi                    # Clamp right
        entity.vx = 0.0
        logger.log_collision("Wall clamp: RIGHT")


def step(entity) -> None:  # Full physics tick — call once per entity per frame
    # [ID: PHY-006] Correct physics order: gravity → integrate → ground → walls
    apply_gravity(entity)    # 1. Gravity accumulates velocity
    integrate(entity)        # 2. Velocity moves entity
    resolve_ground(entity)   # 3. Ground stops entity
    clamp_walls(entity)      # 4. Walls stop entity
