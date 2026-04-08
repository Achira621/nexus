# [ID: DMG-001] damage.py — resolve hit events, apply damage + knockback
from utils.constants import HIT_STOP_FRAMES
from utils import logger  # Damage logging (always on per rules)
from engine import renderer


def resolve_hit(attacker, defender, attack) -> float:  # Apply hit to defender
    # [ID: DMG-002] Guard — never damage dead entities
    if defender.hp <= 0:
        return 0.0   # No damage dealt

    # [ID: DMG-003] Deterministic damage — no RNG, skill-based per design rules
    dmg = float(attack.damage)   # Exact value from attack definition

    # [ID: DMG-004] Apply damage and clamp HP to zero minimum
    defender.hp = max(0.0, defender.hp - dmg)   # Subtract then clamp

    # [ID: DMG-005] Determine knockback direction (always away from attacker)
    kx, ky = attack.knockback                    # Base knockback vector
    if attacker.x < defender.x:                 # Attacker is to the left
        kx_dir = abs(kx)                        # Push defender rightward
    else:                                        # Attacker is to the right
        kx_dir = -abs(kx)                       # Push defender leftward

    # [ID: DMG-006] Apply velocity impulse directly to defender's physics state
    defender.vx += kx_dir                       # Horizontal impulse
    defender.vy += ky                           # Vertical impulse (negative = up)

    # Apply status effect if the attack has one
    if hasattr(attack, "status_effect") and attack.status_effect:
        defender.apply_status(attack.status_effect, attack.status_duration)

    # [ID: DMG-007] Put defender into hit stun and trigger flash effect
    defender.enter_hit_stun()                   # State machine transition
    attacker.hit_stop_timer = max(getattr(attacker, "hit_stop_timer", 0), HIT_STOP_FRAMES)
    defender.hit_stop_timer = max(getattr(defender, "hit_stop_timer", 0), HIT_STOP_FRAMES)

    # [ID: DMG-008] Trigger visual feedback
    if dmg > 15:
        renderer.add_shake(12.0)
    else:
        renderer.add_shake(5.0)
    renderer.spawn_damage_number(defender.x + defender.width//2, defender.y + 40, int(dmg))

    # [ID: DBG-001] Always log damage per debugging rules
    logger.log_damage(dmg, getattr(attacker, "name", "?"),
                      getattr(defender, "name", "?"))
    return dmg   # Return damage applied (used by renderer for effects)
