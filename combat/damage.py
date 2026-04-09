# [ID: DMG-001] damage.py — resolve hit events, apply damage + knockback
from utils.constants import HIT_STOP_FRAMES
from utils import logger  # Damage logging (always on per rules)
from engine import renderer


def resolve_hit(attacker, defender, attack) -> float:  # Apply hit to defender
    # [ID: DMG-002] Guard — never damage dead entities
    if defender.hp <= 0:
        return 0.0   # No damage dealt

    # [ID: DMG-002A] Parry System check
    if getattr(defender, "state", "") == "parry":
        p_frame = getattr(defender, "parry_frame", 0)
        p_cfg = getattr(defender, "parry_config", None)
        if p_cfg and p_frame >= p_cfg["startup"] and p_frame <= p_cfg["startup"] + p_cfg["active"]:
            # Successful Parry
            logger.log_damage(0, getattr(attacker, "name", "?"), getattr(defender, "name", "?") + " (PARRIED!)")
            
            # Hit stop to emphasize clash
            attacker.hit_stop_timer = 25
            defender.hit_stop_timer = 15
            
            # Visual feedback
            renderer.add_shake(15.0)
            renderer.spawn_hit_particles(defender.x + defender.width//2, defender.y + defender.height//2, (200, 255, 255))
            
            p_type = p_cfg["type"]
            if p_type == "poison":
                attacker.apply_status("poison", 180)
                attacker.apply_status("slow", 60)
            elif p_type == "perfect":
                # Instant recovery
                defender.state = "idle"
            elif p_type == "dodge":
                # Evasive roll behind attacker
                defender.x = attacker.x + (attacker.width + 20) if not attacker.facing_left else attacker.x - defender.width - 20
                defender.state = "idle"
            
            # Briefly stun attacker
            attacker.enter_hit_stun()
            attacker.hit_stun_timer = 20  # Override stun
            return 0.0

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
