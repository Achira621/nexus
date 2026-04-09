# [ID: INP-001] input_handler.py - frame-perfect input poll with 5-input buffer
import pygame                         # Event and key state polling
from collections import deque         # Ring buffer for combo detection
from utils.constants import INPUT_BUFFER_SIZE  # Buffer size constant
from utils import logger              # Input debug logging


# [ID: INP-002] Frame input snapshot - passed to entities each frame
class InputState:
    __slots__ = (                     # Slot allocation for speed
        "move_left", "move_right", "jump", "crouch",
        "attack_light", "attack_heavy", "attack_special", "parry",
        "mouse_x", "mouse_y", "pause", "debug_toggle",
    )

    def __init__(self):               # Zero-initialise all fields
        self.move_left = False        # A / Left arrow held
        self.move_right = False       # D / Right arrow held
        self.jump = False             # W / Space - just-pressed this frame
        self.crouch = False           # S / Down arrow held
        self.attack_light = False     # LMB - just-pressed this frame
        self.attack_heavy = False     # RMB - just-pressed this frame
        self.attack_special = False   # W/Space + RMB - just-pressed this frame
        self.parry = False            # F or Numpad 0
        self.mouse_x = 0              # Mouse pixel X
        self.mouse_y = 0              # Mouse pixel Y
        self.pause = False            # Escape - just-pressed
        self.debug_toggle = False     # F3 - just-pressed


# [ID: INP-003] Ring buffer storing last N meaningful inputs for combo detection
input_buffer: deque = deque(maxlen=INPUT_BUFFER_SIZE)

# [ID: INP-004] Current and Previous frame key & mouse state
_current_keys  = None
_current_mouse = (False, False, False)
_prev_keys     = None
_prev_mouse    = (False, False, False)


def poll(player_id: int = 1) -> InputState:   # Read all devices → return clean InputState
    global _current_keys, _prev_keys, _prev_mouse, _current_mouse

    # [ID: INP-005] Snapshot devices ONCE per frame (first poll(1) call)
    if player_id == 1 or _current_keys is None:
        _current_keys = pygame.key.get_pressed()
        _current_mouse = pygame.mouse.get_pressed()
    
    keys   = _current_keys
    mb     = _current_mouse
    mpos   = pygame.mouse.get_pos()        # Always current

    # Bootstrap previous state on first frame
    if _prev_keys is None:
        _prev_keys = keys

    # [ID: INP-006] Just-pressed = current True AND previous False
    def just(cur: bool, prev: bool) -> bool:
        return cur and not prev            # Edge-triggered detection

    state = InputState()                   # Fresh snapshot

    if player_id == 1:
        # Player 1 uses WASD + Mouse + F
        state.move_left = bool(keys[pygame.K_a])
        state.move_right = bool(keys[pygame.K_d])
        state.crouch = bool(keys[pygame.K_s])
        state.mouse_x = mpos[0]
        state.mouse_y = mpos[1]

        is_w_held = bool(keys[pygame.K_w] or keys[pygame.K_SPACE])
        cur_jump = is_w_held
        prev_jump = bool(_prev_keys[pygame.K_w] or _prev_keys[pygame.K_SPACE])

        cur_light = bool(mb[0] or keys[pygame.K_q])
        prev_light = bool(_prev_mouse[0] or _prev_keys[pygame.K_q])
        cur_heavy = bool(mb[2] or keys[pygame.K_e])
        prev_heavy = bool(_prev_mouse[2] or _prev_keys[pygame.K_e])

        just_light = just(cur_light, prev_light)
        just_heavy = just(cur_heavy, prev_heavy)

        if is_w_held and just_heavy:
            state.attack_special = True
            state.attack_heavy = False
            state.jump = False
        else:
            state.attack_heavy = just_heavy
            state.jump = just(cur_jump, prev_jump)

        state.attack_light = just_light
        state.parry = just(bool(keys[pygame.K_f]), bool(_prev_keys[pygame.K_f]))

    else:
        # Player 2 uses Arrows + Numpad
        state.move_left = bool(keys[pygame.K_LEFT])
        state.move_right = bool(keys[pygame.K_RIGHT])
        state.crouch = bool(keys[pygame.K_DOWN])
        state.mouse_x = mpos[0]
        state.mouse_y = mpos[1]

        is_w_held = bool(keys[pygame.K_UP])
        cur_jump = is_w_held
        prev_jump = bool(_prev_keys[pygame.K_UP])

        cur_light = bool(keys[pygame.K_KP1])
        prev_light = bool(_prev_keys[pygame.K_KP1])
        cur_heavy = bool(keys[pygame.K_KP2])
        prev_heavy = bool(_prev_keys[pygame.K_KP2])

        just_light = just(cur_light, prev_light)
        just_heavy = just(cur_heavy, prev_heavy)

        if is_w_held and just_heavy:
            state.attack_special = True
            state.attack_heavy = False
            state.jump = False
        else:
            state.attack_heavy = just_heavy
            state.jump = just(cur_jump, prev_jump)

        state.attack_light = just_light
        state.parry = just(bool(keys[pygame.K_KP0]), bool(_prev_keys[pygame.K_KP0]))

    # [ID: INP-009] System keys - just-pressed (Only read by main loop, P1 is easiest)
    if player_id == 1:
        state.pause = just(bool(keys[pygame.K_ESCAPE]), bool(_prev_keys[pygame.K_ESCAPE]))
        state.debug_toggle = just(bool(keys[pygame.K_F3]), bool(_prev_keys[pygame.K_F3]))

    # [ID: INP-010] Buffer meaningful actions for combo system
    if state.attack_light or state.attack_heavy or state.attack_special or state.jump or state.parry:
        input_buffer.append(state)          # Push to ring buffer

    return state                           # Return clean snapshot


def cleanup_frame() -> None:
    # [ID: INP-011] Transition current state to previous for NEXT frame
    global _current_keys, _current_mouse, _prev_keys, _prev_mouse
    if _current_keys is not None:
        _prev_keys = _current_keys
        _prev_mouse = _current_mouse

    _current_keys = None
    _current_mouse = (False, False, False)
    _current_mouse_pos = (0, 0)
