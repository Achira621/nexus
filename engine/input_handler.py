# [ID: INP-001] input_handler.py — frame-perfect input poll with 5-input buffer
import pygame                         # Event and key state polling
from collections import deque         # Ring buffer for combo detection
from utils.constants import INPUT_BUFFER_SIZE  # Buffer size constant
from utils import logger              # Input debug logging


# [ID: INP-002] Frame input snapshot — passed to entities each frame
class InputState:
    __slots__ = (                     # Slot allocation for speed
        "move_left", "move_right", "jump", "crouch",
        "attack_light", "attack_heavy", "attack_special",
        "mouse_x", "mouse_y", "pause", "debug_toggle",
    )

    def __init__(self):               # Zero-initialise all fields
        self.move_left    = False     # A / Left arrow held
        self.move_right   = False     # D / Right arrow held
        self.jump         = False     # W / Space — just-pressed this frame
        self.crouch       = False     # S / Down arrow held
        self.attack_light = False     # LMB — just-pressed this frame
        self.attack_heavy = False     # RMB — just-pressed this frame
        self.attack_special = False   # W/Space + RMB — just-pressed this frame
        self.mouse_x      = 0         # Mouse pixel X
        self.mouse_y      = 0         # Mouse pixel Y
        self.pause        = False     # Escape — just-pressed
        self.debug_toggle = False     # F3 — just-pressed


# [ID: INP-003] Ring buffer storing last N meaningful inputs for combo detection
input_buffer: deque = deque(maxlen=INPUT_BUFFER_SIZE)

# [ID: INP-004] Previous-frame key & mouse state for just-pressed detection
_prev_keys  = None
_prev_mouse = (False, False, False)


def poll() -> InputState:   # Read all devices → return clean InputState
    global _prev_keys, _prev_mouse

    keys   = pygame.key.get_pressed()      # Snapshot entire keyboard
    mb     = pygame.mouse.get_pressed()    # (LMB, MMB, RMB) booleans
    mpos   = pygame.mouse.get_pos()        # (x, y) pixel position

    # [ID: INP-005] Bootstrap previous state on first frame
    if _prev_keys is None:
        _prev_keys = keys

    # [ID: INP-006] Just-pressed = current True AND previous False
    def just(cur: bool, prev: bool) -> bool:
        return cur and not prev            # Edge-triggered detection

    state = InputState()                   # Fresh snapshot

    state.move_left    = bool(keys[pygame.K_a] or keys[pygame.K_LEFT])
    state.move_right   = bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
    state.crouch       = bool(keys[pygame.K_s] or keys[pygame.K_DOWN])
    state.mouse_x      = mpos[0]
    state.mouse_y      = mpos[1]

    # [ID: INP-007] Jump — just-pressed (W or Space)
    is_w_held = bool(keys[pygame.K_w] or keys[pygame.K_SPACE])
    cur_jump  = is_w_held
    prev_jump = bool(_prev_keys[pygame.K_w] or _prev_keys[pygame.K_SPACE])
    
    # [ID: INP-008] Attack inputs — just-pressed
    cur_light = bool(mb[0])
    prev_light = bool(_prev_mouse[0])
    cur_heavy = bool(mb[2])
    prev_heavy = bool(_prev_mouse[2])
    
    just_light = just(cur_light, prev_light)
    just_heavy = just(cur_heavy, prev_heavy)
    
    # Special: Right click while W is held. Prevent Heavy if Special triggered.
    if is_w_held and just_heavy:
        state.attack_special = True
        state.attack_heavy = False
        state.jump = False       # Swallow the jump if they are just doing a special
    else:
        state.attack_heavy = just_heavy
        state.jump = just(cur_jump, prev_jump)
        
    state.attack_light = just_light

    # [ID: INP-009] System keys — just-pressed
    state.pause        = just(bool(keys[pygame.K_ESCAPE]), bool(_prev_keys[pygame.K_ESCAPE]))
    state.debug_toggle = just(bool(keys[pygame.K_F3]),     bool(_prev_keys[pygame.K_F3]))

    # [ID: INP-010] Buffer meaningful actions for combo system
    if state.attack_light or state.attack_heavy or state.attack_special or state.jump:
        input_buffer.append(state)          # Push to ring buffer
        logger.log_input(
            f"light={state.attack_light} heavy={state.attack_heavy} "
            f"special={state.attack_special} jump={state.jump}"
        )

    _prev_keys  = keys    # Store for next frame
    _prev_mouse = mb      # Store for next frame
    return state          # Return clean snapshot
