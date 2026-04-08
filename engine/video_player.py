# [ID: VID-001] video_player.py — frame-by-frame MP4 → pygame.Surface decoder
# OpenCV is optional: if it's missing, skip the intro video instead of crashing.
try:
    import cv2  # type: ignore
except Exception:
    cv2 = None
import pygame      # Surface target
from utils import logger  # Debug output


class VideoPlayer:  # Decodes one MP4 file into pygame Surfaces on demand
    def __init__(self, path: str, screen_w: int, screen_h: int):
        # [ID: VID-002] Open video file and store display dimensions
        self._cap       = None                        # OpenCV capture handle
        self._screen_w  = screen_w                    # Target blit width
        self._screen_h  = screen_h                    # Target blit height
        self._done      = True                        # True if file failed to open (or disabled)
        self._fps       = 30.0                        # Source FPS (fallback)
        self._accum     = 0.0                         # Time accumulator (seconds)
        self._frame_dur = 1.0 / self._fps             # Seconds per source frame
        self._surface: "pygame.Surface | None" = None # Last decoded frame surface
        self._pending   = True                        # New frame needed this tick

        if cv2 is None:
            logger.log_asset("[VID] OpenCV (cv2) not available â€” skipping intro video")
            return

        self._cap  = cv2.VideoCapture(path)
        self._done = not self._cap.isOpened()
        if self._done:                                # Log failure cleanly
            logger.log_asset(f"[VID] WARN: could not open {path}")
            return

        self._fps       = self._cap.get(cv2.CAP_PROP_FPS) or 30.0  # Source FPS
        self._frame_dur = 1.0 / self._fps             # Seconds per source frame
        logger.log_asset(f"[VID] Opened {path} @ {self._fps:.1f} fps")
        self._advance()   # Pre-load first frame immediately

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def update(self, dt: float) -> "pygame.Surface | None":
        # [ID: VID-003] Advance time accumulator; decode new frame when due
        if self._done:
            return self._surface          # Return last frame after stream ends

        self._accum += dt                 # Accumulate real time
        while self._accum >= self._frame_dur:   # Consume whole-frame intervals
            self._accum -= self._frame_dur
            self._advance()               # Decode next frame from stream

        return self._surface              # Current decoded surface

    def is_done(self) -> bool:
        # [ID: VID-004] True once all frames have been decoded
        return self._done

    def release(self) -> None:
        # [ID: VID-005] Release OpenCV capture handle — call when done
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _advance(self) -> None:
        # [ID: VID-006] Read next frame from OpenCV, convert to pygame Surface
        if cv2 is None or self._cap is None:
            self._done = True
            return

        ret, frame_bgr = self._cap.read()        # Returns (bool, ndarray BGR)
        if not ret:                              # End of stream
            self._done = True
            self._cap.release()
            return

        # Resize to screen dimensions in one step (avoids extra blit overhead)
        frame_bgr = cv2.resize(frame_bgr, (self._screen_w, self._screen_h))

        # OpenCV delivers BGR; pygame wants RGB — flip channels
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # [ID: VID-007] Convert numpy ndarray → pygame Surface
        # frame_rgb shape: (H, W, 3) — pygame.surfarray expects (W, H, 3)
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        self._surface = surf              # Store for callers
