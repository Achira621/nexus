# [ID: LOG-001] logger.py — categorised debug output
import datetime  # Used for timestamps in log messages

# [ID: LOG-002] Per-category enable flags (toggle independently)
LOG_INPUT     = False   # Keyboard / mouse events
LOG_COLLISION = False   # Hitbox intersection events
LOG_DAMAGE    = True    # Damage dealt (always on per rules)
LOG_AI        = False   # AI state transitions
LOG_ANIM      = False   # Animation state changes
LOG_ASSET     = False   # Asset loading events


def _log(category: str, message: str) -> None:  # Internal base logger
    # [ID: LOG-003] Format: [HH:MM:SS.mmm][CATEGORY] message
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Timestamp string
    print(f"[{ts}][{category}] {message}")  # Output to stdout


def log_input(message: str) -> None:  # Log input events
    if LOG_INPUT:  # Guard behind flag
        _log("INP", message)  # Forward to base logger


def log_collision(message: str) -> None:  # Log collision events
    if LOG_COLLISION:  # Guard behind flag
        _log("COL", message)  # Forward to base logger


def log_damage(damage: float, attacker: str, defender: str) -> None:  # Log damage
    # [ID: DBG-001] Always print damage — required by debugging rules
    print(f"[DAMAGE] {attacker} attacked {defender} for {damage}")  # Direct print
    if LOG_DAMAGE:  # Also structured log
        _log("DMG", f"{attacker} -> {defender}: {damage:.1f} hp")  # Formatted log


def log_ai(new_state: str, reason: str = "") -> None:  # Log AI state change
    if LOG_AI:  # Guard behind flag
        _log("AI ", f"-> {new_state}  ({reason})")  # Show transition


def log_anim(entity: str, state: str) -> None:  # Log animation state change
    if LOG_ANIM:  # Guard behind flag
        _log("ANM", f"{entity}: -> {state}")  # Entity and new animation


def log_asset(path: str) -> None:  # Log asset load event
    if LOG_ASSET:  # Guard behind flag
        _log("AST", f"Loaded: {path}")  # Show loaded path
