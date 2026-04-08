# [ID: AI-001] enemy_ai.py — deterministic state-machine AI, no randomness
from utils.constants import (   # All thresholds from constants
    AI_ATTACK_RANGE, AI_APPROACH_DISTANCE,
    AI_DEFEND_DURATION, AI_IDLE_DURATION,
)
from entities.enemy import S_ATTACK, S_RECOVERY, S_HIT
from utils import logger        # AI state transition logging


# [ID: AI-002] AI states per combat design rules
STATE_IDLE     = "idle"
STATE_APPROACH = "approach"
STATE_ATTACK   = "attack"
STATE_DEFEND   = "defend"

# [ID: AI-003] Module-level state — one AI instance
_state       = STATE_IDLE   # Current AI state
_timer       = 0            # Frames in current state


def update(enemy, player, dt: float) -> None:   # Called every frame by main loop
    global _state, _timer

    # [ID: AI-004] Stop AI when either character is dead
    if enemy.is_dead() or player.is_dead():
        enemy.stop_moving()    # Freeze enemy
        return

    _timer += 1                            # Increment state timer
    enemy.ai_state = _state               # Expose for debug overlay

    distance = abs(enemy.x - player.x)   # 1D horizontal distance to player

    # [ID: AI-005] Route to correct handler based on current state
    if _state == STATE_IDLE:
        _handle_idle(enemy, player, distance)
    elif _state == STATE_APPROACH:
        _handle_approach(enemy, player, distance)
    elif _state == STATE_ATTACK:
        _handle_attack(enemy, player, distance)
    elif _state == STATE_DEFEND:
        _handle_defend(enemy, player, distance)


def _transition(new_state: str) -> None:   # Change state and reset timer
    global _state, _timer
    # [ID: AI-006] Log every state transition for debug tracing
    logger.log_ai(new_state, f"from {_state} after {_timer} frames")
    _state = new_state    # Switch state
    _timer = 0            # Reset timer for new state


def _handle_idle(enemy, player, distance: float) -> None:
    enemy.stop_moving()                  # Stand still while idle
    if _timer >= AI_IDLE_DURATION:       # Idle period expired
        if distance <= AI_APPROACH_DISTANCE:
            # [ID: AI-007] Player is close enough — start approaching
            _transition(STATE_APPROACH)
        # else stay idle another cycle — prevents infinite approach on far player


def _handle_approach(enemy, player, distance: float) -> None:
    if distance <= AI_ATTACK_RANGE:      # Close enough to strike
        # [ID: AI-008] Enter attack state when in range
        _transition(STATE_ATTACK)
    else:
        enemy.move_toward(player.x)      # Close the gap


def _handle_attack(enemy, player, distance: float) -> None:
    enemy.stop_moving()                  # Stand still during attack decision
    if enemy.state not in (S_ATTACK, S_RECOVERY, S_HIT):   # Not already busy
        # [ID: AI-009] Choose attack deterministically based on range and health
        if distance > AI_ATTACK_RANGE * 0.8:
            enemy.begin_attack("directional")  # Long range poke (Venom Strike)
        elif enemy.hp < enemy.max_hp * 0.5 and distance <= AI_ATTACK_RANGE * 0.6:
            enemy.begin_attack("special")      # Desperation move (Serpent Dominion)
        elif distance <= AI_ATTACK_RANGE * 0.4:
            enemy.begin_attack("heavy")        # Point blank (Coil Guard)
        else:
            enemy.begin_attack("light")        # Normal range (Dark Strike)
        _transition(STATE_DEFEND)        # After initiating, move to defend


def _handle_defend(enemy, player, distance: float) -> None:
    enemy.stop_moving()                  # Hold position during recovery window
    if _timer >= AI_DEFEND_DURATION:     # Recovery window expired
        if distance <= AI_ATTACK_RANGE:
            # [ID: AI-010] Still in range — attack again immediately
            _transition(STATE_ATTACK)
        else:
            # [ID: AI-011] Player backed off — re-approach
            _transition(STATE_APPROACH)


def reset() -> None:   # Reset AI for new round or game restart
    global _state, _timer
    # [ID: AI-012] Full state reset
    _state = STATE_IDLE    # Return to initial state
    _timer = 0             # Reset frame counter
