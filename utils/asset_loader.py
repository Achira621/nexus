# [ID: AST-001] asset_loader.py — singleton cache, prevents duplicate loads
import os          # File path operations
import pygame      # Surface loading and scaling
from utils import logger  # Debug asset loading


# [ID: AST-002] Global surface cache — key: (path, w, h, tint) → Surface
_cache: dict = {}


def load(path: str) -> pygame.Surface:  # Load surface once, return cached copy
    if path not in _cache:              # Only load if not in cache
        _cache[path] = pygame.image.load(path).convert_alpha()  # RGBA load
        logger.log_asset(path)          # Debug log the load event
    return _cache[path]                 # Return cached surface


def load_scaled(path: str, w: int, h: int) -> pygame.Surface:  # Load and scale
    key = (path, w, h, None)           # Unique cache key with dimensions
    if key not in _cache:              # Check cache before work
        raw = load(path)               # Load raw (also cached)
        _cache[key] = pygame.transform.smoothscale(raw, (w, h))  # Scale it
    return _cache[key]                 # Return cached scaled surface


def load_tinted(path: str, tint: tuple, size: int = 36) -> pygame.Surface:
    # [ID: AST-003] Load icon, scale, and apply colour tint via multiply blend
    key = (path, size, size, tint)     # Unique key includes tint colour
    if key not in _cache:              # Check cache
        raw = load_scaled(path, size, size)   # Load scaled base
        tinted = raw.copy()                   # Copy — don't mutate cached base
        overlay = pygame.Surface(raw.get_size(), pygame.SRCALPHA)  # Tint layer
        overlay.fill((*tint, 255))            # Fill with full-opacity tint colour
        tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)  # Multiply
        _cache[key] = tinted                  # Store result
    return _cache[key]                        # Return tinted surface


def load_sequence(folder: str, prefix: str, indices: list) -> list:
    # [ID: AST-004] Load a numbered frame sequence from a folder
    frames = []                               # Accumulate loaded frames
    for idx in indices:                       # Iterate over requested indices
        fname  = f"{prefix}_{idx:04d}.png"   # Zero-padded filename
        fpath  = os.path.join(folder, fname) # Full path
        if os.path.exists(fpath):            # Only load files that exist
            frames.append(load(fpath))       # Add to sequence
    return frames                            # Return list of Surfaces


def load_spritesheet_grid(path: str, columns: int, rows: int,
                         auto_colorkey: bool = True) -> list:
    # [ID: AST-005] Chop a single image sheet into a 1D list of (rows*cols) frames
    frames = []                                # Accumulate sliced frames
    if not os.path.exists(path):               # Bail if file missing
        return frames

    cache_key = (path, "spritesheet", columns, rows)
    if cache_key not in _cache:
        # [ID: AST-005A] Load JPG via convert() then punch colorkey from corner pixel
        is_jpg = path.lower().endswith((".jpg", ".jpeg"))
        if is_jpg:
            surf = pygame.image.load(path).convert()   # No alpha channel in JPG
            if auto_colorkey:
                corner = surf.get_at((0, 0))           # Sample top-left background
                surf.set_colorkey(corner, pygame.RLEACCEL)   # Transparent that colour
        else:
            surf = pygame.image.load(path).convert_alpha()  # PNG keeps alpha
            if auto_colorkey:
                corner = surf.get_at((0, 0))
                if corner[3] < 10:                     # Already transparent — leave
                    pass
                else:
                    surf.set_colorkey(corner)          # Solid colour bg → transparent
        _cache[cache_key] = surf
        logger.log_asset(path)                         # Debug log the load event

    sheet   = _cache[cache_key]                        # Cached surface
    sht_w, sht_h = sheet.get_size()                   # Full sheet dimensions
    frm_w   = sht_w // columns                        # Width of one cell
    frm_h   = sht_h // rows                           # Height of one cell

    for row in range(rows):                            # Walk rows top to bottom
        for col in range(columns):                     # Walk cols left to right
            rect  = pygame.Rect(col * frm_w, row * frm_h, frm_w, frm_h)   # Cell rect
            frame = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()  # RGBA dst
            frame.blit(sheet, (0, 0), rect)            # Blit cell into frame surface
            frames.append(frame)                       # Append to 1D list

    return frames                                      # Return all (rows*cols) frames


def find_sheet(folder: str) -> "str | None":
    # [ID: AST-005B] Return path to sheet.jpg or sheet.png inside folder, or None
    for ext in (".jpg", ".jpeg", ".png"):              # Prefer JPG (uploaded format)
        p = os.path.join(folder, "sheet" + ext)        # Canonical name
        if os.path.exists(p):
            return p
    return None                                        # No sheet found
    

    return result


def load_auto_slice(path: str) -> list:
    # [ID: AST-007] Dynamically extract frames from a transparent 1D strip
    # Uses mask connectivity to find bounding boxes of discrete characters
    if not os.path.exists(path):
        return []

    sheet = load(path)
    mask = pygame.mask.from_surface(sheet)
    
    # Get all bounding rects of connected non-transparent components
    rects = mask.get_bounding_rects()
    if not rects:
        return []

    # Filter out tiny specks of noise (less than 8x8 pixels)
    rects = [r for r in rects if r.width > 8 and r.height > 8]
    
    # For a 1D strip, we group rects that are vertically overlapping or horizontally close
    # This ensures a character holding a separate weapon is treated as one frame
    if not rects:
        return []
    
    rects.sort(key=lambda r: r.x)
    
    merged = []
    if rects:
        curr = rects[0]
        for i in range(1, len(rects)):
            nxt = rects[i]
            # If the next rect is very close or overlaps in X, merge them
            # We assume frames are separated by at least 20-30 pixels
            gap = nxt.x - (curr.x + curr.width)
            if gap < 25: # Merge threshold
                curr = curr.union(nxt)
            else:
                merged.append(curr)
                curr = nxt
        merged.append(curr)

    frames = []
    for r in merged:
        # Create a surface for the sprite and blit it
        frame = pygame.Surface(r.size, pygame.SRCALPHA).convert_alpha()
        frame.blit(sheet, (0, 0), r)
        frames.append(frame)
        
    return frames


def clear() -> None:  # Clear entire cache (e.g. on scene reload)
    _cache.clear()    # Empty dictionary
