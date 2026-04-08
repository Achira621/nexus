# [ID: ANM-001] animator.py — state-driven, frame-based animation controller
import pygame              # Surface type reference
from utils.constants import ANIM_FPS_IDLE, ANIM_FPS_WALK, ANIM_FPS_RUN, ANIM_FPS_ATTACK, ANIM_FPS_HIT
from utils import logger   # Animation debug logging


# [ID: ANM-002] Per-state animation metadata: playback speed and loop flag
ANIM_META: dict = {
    "idle":           {"fps": ANIM_FPS_IDLE,   "loop": True},
    "walk":           {"fps": ANIM_FPS_WALK,   "loop": True},
    "run":            {"fps": ANIM_FPS_RUN,    "loop": True},   # [ID: ANM-008] Sprint animation
    "attack_light":   {"fps": ANIM_FPS_ATTACK, "loop": False},
    "attack_heavy":   {"fps": ANIM_FPS_ATTACK, "loop": False},
    "attack_directional": {"fps": ANIM_FPS_ATTACK, "loop": False},
    "attack_special":     {"fps": ANIM_FPS_ATTACK, "loop": False},   # [ID: ANM-007] Special move
    "hit":            {"fps": ANIM_FPS_HIT,    "loop": False},
    "dead":           {"fps": 8,               "loop": False},
}


class Animator:   # Per-entity animation controller
    def __init__(self, frame_map: dict, name: str = ""):
        # [ID: ANM-003] Store frame sequences and initialise idle state
        self.frame_map     = frame_map       # { state: [Surface, ...] }
        self.name          = name            # Entity name for debug logs
        self.state         = "idle"          # Current animation state
        self._elapsed      = 0.0             # Seconds elapsed in this state
        self._frame_dur    = 1.0 / ANIM_FPS_IDLE  # Seconds per frame
        self._loop         = True            # Does current state loop?
        self.done          = False           # True when one-shot finishes
        self._locked       = False           # Prevents mid-attack interruptions

    def set_state(self, new_state: str) -> None:   # Switch animation state
        if new_state == self.state:                # Already in this state
            return                                 # No restart needed
        if self._locked:                           # One-shot animation has priority
            return
        if new_state not in self.frame_map:        # Frames not loaded
            return                                 # Silently ignore

        # [ID: ANM-004] Reset counters when entering new state
        self.state      = new_state
        self._elapsed   = 0.0
        self.done       = False
        meta = ANIM_META.get(new_state, {"fps": 8, "loop": True})
        self._frame_dur = 1.0 / meta["fps"]       # New frame duration
        self._loop      = meta["loop"]             # Loop flag for new state
        logger.log_anim(self.name, new_state)      # Debug log transition

    def lock(self) -> None:
        self._locked = True

    def unlock(self) -> None:
        self._locked = False

    def update(self, dt: float) -> None:   # Advance animation by dt seconds
        frames = self.frame_map.get(self.state, [])  # Current frame list
        if not frames:                               # Nothing to animate
            return
        total = len(frames)                          # Frame count
        # [ID: ANM-005] Accumulate time and decide current frame index
        self._elapsed += dt
        max_time = total * self._frame_dur           # Duration of full cycle
        if self._loop:                               # Looping state (idle/walk)
            if self._elapsed >= max_time:
                self._elapsed %= max_time            # Wrap around
        else:                                        # One-shot state (attack/hit)
            if self._elapsed >= max_time:
                self._elapsed = max_time - 0.001     # Hold last frame
                self.done = True                     # Signal completion

    def get_frame(self) -> "pygame.Surface | None":  # Surface to blit this frame
        frames = self.frame_map.get(self.state, [])  # Current list
        if not frames:                               # No frames available
            fallback = self.frame_map.get("idle", [])
            if not fallback:
                # [ID: ANM-009] Universal fallback across any loaded list to avoid disappearances
                for val in self.frame_map.values():
                    if val:
                        frames = val
                        break
            else:
                frames = fallback
                
        if not frames:
            # Utter failure fallback — pink box
            fallback_surf = pygame.Surface((80, 80))
            fallback_surf.fill((255, 0, 255))
            return fallback_surf

        total = len(frames)
        # [ID: ANM-006] Derive integer index from elapsed time
        idx = int(self._elapsed / self._frame_dur)   # Frame index
        idx = max(0, min(idx, total - 1))            # Clamp to valid range
        return frames[idx]                           # Return Surface

    def is_done(self) -> bool:   # Check if one-shot animation completed
        return self.done         # Read done flag
