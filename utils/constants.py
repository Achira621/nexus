# [ID: CON-001] constants.py — all global values, no hardcoding elsewhere
import os  # Used for path construction

# [ID: CON-002] Display settings
SCREEN_WIDTH  = 1280   # Horizontal resolution
SCREEN_HEIGHT = 720    # Vertical resolution
FPS           = 60     # Target frames per second
TITLE         = "Kalpavyuha: Nexus"  # Window title

# [ID: CON-003] Physics constants
GRAVITY       = 0.8    # Downward acceleration per frame (pixels/frame²)
GROUND_Y      = 560    # Y coordinate of ground surface
WALL_LEFT     = 40     # Left arena boundary (pixels)
WALL_RIGHT    = 1240   # Right arena boundary (pixels)

# [ID: CON-004] Player stats
PLAYER_HP         = 100    # Starting health points
PLAYER_SPEED      = 5.0    # Horizontal movement speed (pixels/frame)
PLAYER_JUMP_FORCE = -17.0  # Upward impulse on jump (negative = up)
PLAYER_START_X    = 220    # Spawn X position
PLAYER_START_Y    = 360    # Spawn Y position
PLAYER_WIDTH      = 140    # Collision/sprite width  (px)
PLAYER_HEIGHT     = 200    # Collision/sprite height (px)

# [ID: CON-005] Enemy stats
ENEMY_HP         = 100     # Starting health points
ENEMY_SPEED      = 3.5     # Horizontal movement speed (pixels/frame)
ENEMY_JUMP_FORCE = -15.0   # Upward impulse on jump
ENEMY_START_X    = 980     # Spawn X position
ENEMY_START_Y    = 360     # Spawn Y position
ENEMY_WIDTH      = 140     # Collision/sprite width  (px)
ENEMY_HEIGHT     = 200     # Collision/sprite height (px)

# [ID: CON-006] Light attack frame data
LIGHT_DAMAGE    = 8               # Damage dealt on hit
LIGHT_STARTUP   = 12              # Frames before hitbox activates
LIGHT_ACTIVE    = 4               # Frames hitbox is live
LIGHT_RECOVERY  = 16              # Cooldown frames after active ends
LIGHT_KNOCKBACK = (7.0, -2.5)     # (horizontal, vertical) impulse
LIGHT_RANGE     = 70              # Hitbox horizontal reach (px)

# [ID: CON-007] Heavy attack frame data
HEAVY_DAMAGE    = 20
HEAVY_STARTUP   = 22
HEAVY_ACTIVE    = 6
HEAVY_RECOVERY  = 26
HEAVY_KNOCKBACK = (15.0, -8.0)
HEAVY_RANGE     = 100

# [ID: CON-008] Directional attack frame data
DIRECTIONAL_DAMAGE    = 12
DIRECTIONAL_STARTUP   = 14
DIRECTIONAL_ACTIVE    = 5
DIRECTIONAL_RECOVERY  = 18
DIRECTIONAL_KNOCKBACK = (8.0, -3.0)
DIRECTIONAL_RANGE     = 85

# [ID: CON-009] Hit stun duration
HIT_STUN_FRAMES = 35   # Frames of stun on hit receiver
HIT_STOP_FRAMES = 12    # Brief freeze for both fighters on confirmed hit

# [ID: CON-010] AI behaviour thresholds
AI_ATTACK_RANGE      = 130   # Distance (px) to trigger attack
AI_APPROACH_DISTANCE = 700   # Distance (px) to start approaching
AI_DEFEND_DURATION   = 30    # Frames AI holds defend after attacking
AI_IDLE_DURATION     = 25    # Frames AI idles before engaging

# [ID: CON-011] Input buffer
INPUT_BUFFER_SIZE = 5   # Number of inputs kept in ring buffer

# [ID: CON-012] Animation playback speeds (frames per second)
ANIM_FPS_IDLE   = 8
ANIM_FPS_WALK   = 12
ANIM_FPS_RUN    = 14    # Dedicated run sheet (faster than walk)
ANIM_FPS_ATTACK = 12
ANIM_FPS_HIT    = 12

# [ID: CON-013] Kalpavyuha energy colour palette (R, G, B)
COLOR_BG_TOP      = (8,   8,  20)   # Deep space gradient top
COLOR_BG_BOTTOM   = (18, 12,  45)   # Dark purple gradient bottom
COLOR_GROUND_TOP  = (35, 28,  70)   # Ground surface top edge
COLOR_GROUND_LINE = (80, 60, 160)   # Ground highlight line
COLOR_PLAYER      = (0,  200, 255)  # Cyan — player tint
COLOR_ENEMY       = (255, 80,  30)  # Orange-red — enemy tint
COLOR_HP_PLAYER   = (0,  230, 255)  # Player HP bar fill
COLOR_HP_ENEMY    = (255, 70,  20)  # Enemy HP bar fill
COLOR_HP_BG       = (25,  20,  50)  # HP bar background track
COLOR_HP_BORDER   = (60,  50, 100)  # HP bar border
COLOR_HIT_FLASH   = (255, 255, 210) # White flash on hit
COLOR_UI_TEXT     = (220, 220, 255) # HUD label text
COLOR_SPARK_A     = (255, 255, 150) # Particle bright centre
COLOR_SPARK_B     = (255, 180,  50) # Particle mid ring
COLOR_SPARK_C     = (180,  80,  20) # Particle outer dim
COLOR_HITBOX_DBG  = (255,  50,  50) # Debug hitbox overlay
COLOR_HURTBOX_DBG = (50,  255,  50) # Debug hurtbox overlay
COLOR_WIN_GOLD    = (255, 215,   0) # Win screen text

# [ID: CON-014] HUD layout
HUD_HP_BAR_WIDTH  = 420   # Width of each health bar (px)
HUD_HP_BAR_HEIGHT = 22    # Height of health bar (px)
HUD_HP_BAR_Y      = 28    # Y position of health bars from top
HUD_HP_PADDING    = 28    # Padding from screen edge
HUD_ICON_SIZE     = 36    # Size of UI icons (px)
HUD_SEGMENT_COUNT = 10    # Number of HP bar segments

# [ID: CON-015] Particle system limits
MAX_PARTICLES = 80   # Hard cap on simultaneous particles

# [ID: CON-016] Debug toggle (F3 key)
DEBUG_MODE = False   # Enables hitbox/hurtbox overlays

# [ID: CON-017] Asset directory paths (relative to this file's parent)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
ASSET_DIR  = os.path.join(_ROOT, "assets")            # assets/
ICON_DIR   = os.path.join(ASSET_DIR, "icons")         # assets/icons/
SPRITE_DIR = os.path.join(ASSET_DIR, "sprites")       # assets/sprites/
BG_DIR     = os.path.join(ASSET_DIR, "backgrounds")   # assets/backgrounds/
EFFECT_DIR = os.path.join(ASSET_DIR, "effects")       # assets/effects/
