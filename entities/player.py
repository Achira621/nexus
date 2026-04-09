# [ID: PLR-001] player.py — Player entity: state machine, input dispatch, animations
import pygame                           # Rect type
from engine.physics   import step as physics_step   # Physics tick
from engine.animator  import Animator               # Animation controller
from combat.hitbox    import Hurtbox, Hitbox        # Collision geometry
from combat.attack    import make_light, make_heavy, make_directional  # Factories
from utils.constants  import (
    PLAYER_HP, PLAYER_SPEED, PLAYER_JUMP_FORCE,
    PLAYER_START_X, PLAYER_START_Y, PLAYER_WIDTH, PLAYER_HEIGHT,
    HIT_STUN_FRAMES,
)
from utils import logger   # Debug logging


# [ID: PLR-002] State machine constants
S_IDLE      = "idle"
S_MOVE      = "move"
S_JUMPING   = "jumping"
S_ATTACK    = "attack"
S_RECOVERY  = "recovery"
S_HIT       = "hit"
S_DEAD      = "dead"
S_PARRY     = "parry"


class Player:   # Human-controlled fighter entity
    def __init__(self, frame_map: dict, config: dict = None):   # config from roster.py
        # [ID: PLR-003] World position and physics state
        self.x          = float(PLAYER_START_X)
        self.y          = float(PLAYER_START_Y)
        self.vx         = 0.0
        self.vy         = 0.0
        self.width      = PLAYER_WIDTH
        self.height     = PLAYER_HEIGHT
        self.on_ground  = False
        self.facing_left = False   # Player starts facing right (toward enemy)
        self.name       = config["name"] if config else "Player"

        # [ID: PLR-004] Health and combat state
        hp_val = config["hp"] if config else float(PLAYER_HP)
        self.hp             = hp_val
        self.max_hp         = hp_val
        self.energy         = 0.0
        self.max_energy     = 100.0
        self.speed_mult     = config["speed_mult"] if config else 1.0
        self.moveset        = config["attacks"] if config else None
        self.parry_config   = config.get("parry", None)
        
        self.state          = S_IDLE
        self.current_attack = None    # Active Attack object or None
        self.parry_frame    = 0       # Frame counter within current parry
        self.attack_frame   = 0       # Frame counter within current attack
        self.has_hit        = False   # Prevents multi-hit per swing
        self.hit_stun_timer = 0       # Frames remaining in stun
        self.hit_stop_timer = 0       # Brief freeze on confirmed hit
        self.hit_flash      = 0       # Frames of white flash after hit
        
        # [ID: PLR-004B] Status effects tracker mapping name to frames remaining
        self.status_effects = {}

        # [ID: PLR-005] Animation and collision
        self.animator = Animator(frame_map, self.name)
        self.hurtbox  = Hurtbox(self.x, self.y, self.width, self.height)
        self.hitbox: "Hitbox | None" = None   # Only live during active frames

    # ------------------------------------------------------------------ #
    #  Public update — called once per frame before renderer              #
    # ------------------------------------------------------------------ #
    def update(self, inp, dt: float) -> None:   # inp = InputState
        # [ID: PLR-006] Dead entities — only animate, no control
        if self.state == S_DEAD:
            self.animator.set_state("dead")
            self.animator.update(dt)
            return

        if self.hit_stop_timer > 0:
            return

        self._tick_timers()              # Decrement hit flash + stun timers
        self._process_status_effects()   # Process DoT and modifiers

        if self.state in (S_MOVE, S_JUMPING, S_ATTACK):
            self.energy = min(self.max_energy, self.energy + 0.15)

        if self.state == S_HIT:    # Control locked during stun
            self._update_stun()
        elif self.state == S_PARRY: # Parrying logic
            self._update_parry(inp)
        elif self.state in (S_ATTACK, S_RECOVERY): # Mid-attack — advance frame counter
            self._update_attack(inp)
        elif self.status_effects.get("immobilize", 0) > 0:
            self.vx *= 0.5               # Cannot move if immobilized
            self.state = S_IDLE if self.on_ground else S_JUMPING
        else:                           # Normal control
            self._handle_movement(inp)
            self._handle_parry_input(inp)
            if self.state != S_PARRY:
                self._handle_attack_input(inp)

        physics_step(self)              # Gravity, integrate, ground, walls
        self.hurtbox.sync(self)         # Keep hurtbox glued to body
        self.animator.update(dt)        # Advance animation frame
        self._sync_anim()               # Map game state → animator state
        self._check_death()             # HP zero → dead state

    # ------------------------------------------------------------------ #
    #  Movement                                                           #
    # ------------------------------------------------------------------ #
    def _handle_movement(self, inp) -> None:
        # [ID: PLR-007] Translate WASD → velocity and direction
        base_speed = PLAYER_SPEED * self.speed_mult
        if self.status_effects.get("slow", 0) > 0:
            base_speed *= 0.5   # 50% slow down
            
        if inp.move_left:
            self.vx          = -base_speed
            self.facing_left = True
        elif inp.move_right:
            self.vx          = base_speed
            self.facing_left = False
        else:
            self.vx    = 0.0

        if inp.jump and self.on_ground:   # Jump only when grounded
            # [ID: PLR-008] Apply jump impulse
            self.vy         = PLAYER_JUMP_FORCE
            self.on_ground  = False
            logger.log_input(f"{self.name} jump")

        # Safely assign state without overriding air logic
        if not self.on_ground:
            self.state = S_JUMPING
        elif self.vx != 0.0:
            self.state = S_MOVE
        else:
            self.state = S_IDLE

    # ------------------------------------------------------------------ #
    #  Attack input                                                       #
    # ------------------------------------------------------------------ #
    def _handle_attack_input(self, inp) -> None:
        # [ID: PLR-009] Check inputs for attacks
        direction  = -1 if self.facing_left else 1
        is_moving  = inp.move_left or inp.move_right

        attack_type = None
        if inp.attack_special:
            attack_type = "special"
        elif inp.attack_heavy:
            attack_type = "heavy"
        elif inp.attack_light:
            attack_type = "directional" if is_moving else "light"
            
        if attack_type:
            if self.moveset and attack_type in self.moveset:
                atk = self.moveset[attack_type]
                atk.direction = direction    # Update facing on use
                self._begin_attack(atk)
            else:
                # Fallback to generic attacks if no moveset
                if attack_type == "directional":
                    self._begin_attack(make_directional(direction))
                elif attack_type == "heavy":
                    self._begin_attack(make_heavy(direction))
                elif attack_type == "light":
                    self._begin_attack(make_light(direction))

    def _handle_parry_input(self, inp) -> None:
        if inp.parry and self.on_ground and self.parry_config:
            self.state = S_PARRY
            self.parry_frame = 0
            self.hitbox = None
            if "shield" in self.animator.frame_map:
                self.animator.set_state("shield")
            elif "guard" in self.animator.frame_map:
                self.animator.set_state("guard")
            else:
                self.animator.set_state("hit")
            self.animator.lock()
            self.vx *= 0.2
            logger.log_input(f"{self.name} parry started ({self.parry_config['type']})")

    def _begin_attack(self, attack) -> None:   # Transition into attacking state
        # [ID: PLR-010] Initialise attack sequence
        self.state          = S_ATTACK
        self.current_attack = attack
        self.attack_frame   = 0
        self.has_hit        = False
        self.hitbox         = None
        attack_key = f"attack_{attack.attack_type}"
        if attack_key in self.animator.frame_map:
            self.animator.set_state(attack_key)
        elif "attack_heavy" in self.animator.frame_map:
            self.animator.set_state("attack_heavy")
        else:
            self.animator.set_state("attack_light")
        self.animator.lock()
        logger.log_input(f"Attack started: {attack.attack_type}")

    # ------------------------------------------------------------------ #
    #  Attack frame logic                                                 #
    # ------------------------------------------------------------------ #
    def _update_attack(self, inp) -> None:
        if self.current_attack is None:   # Sanity guard
            self.state = S_IDLE
            self.animator.unlock()
            return

        atk = self.current_attack
        self.attack_frame += 1            # Advance one frame

        if self.attack_frame <= atk.startup:               # Startup phase
            # [ID: PLR-011] No hitbox yet; slow drift allowed
            self.hitbox  = None
            self.animator.unlock()
            self.vx     *= 0.5
            if getattr(atk, "movement_override", 0) != 0:
                self.vx = atk.movement_override * atk.direction

        elif self.attack_frame <= atk.startup + atk.active:  # Active phase
            # [ID: PLR-012] Hitbox is live — damage resolution handled in main
            self.hitbox = Hitbox.from_attack(self, atk)
            if getattr(atk, "movement_override", 0) != 0:
                self.vx = atk.movement_override * atk.direction

        else:                                              # Recovery phase
            # [ID: PLR-013] Hitbox gone; sluggish recovery movement
            self.state   = S_RECOVERY
            self.hitbox  = None
            self.vx     *= 0.3

        if self.attack_frame >= atk.total_frames:          # Attack complete
            # [ID: PLR-014] Return to idle, clear state
            self.state          = S_IDLE
            self.current_attack = None
            self.hitbox         = None
            self.animator.unlock()

    # ------------------------------------------------------------------ #
    #  Parry frame logic                                                  #
    # ------------------------------------------------------------------ #
    def _update_parry(self, inp) -> None:
        if not self.parry_config:
            self.state = S_IDLE
            self.animator.unlock()
            return
            
        self.parry_frame += 1
        cfg = self.parry_config
        total_frames = cfg['startup'] + cfg['active'] + cfg['recovery']
        
        self.vx *= 0.8
        
        if self.parry_frame >= total_frames:
            self.state = S_IDLE
            self.animator.unlock()

    # ------------------------------------------------------------------ #
    #  Hit stun                                                           #
    # ------------------------------------------------------------------ #
    def _update_stun(self) -> None:
        # [ID: PLR-015] Friction during hit stun
        self.vx *= 0.75
        if self.hit_stun_timer <= 0:    # Stun expired
            self.state  = S_IDLE if self.on_ground else S_JUMPING
            self.vx     = 0.0

    def enter_hit_stun(self) -> None:   # Called by damage.resolve_hit()
        if self.state == S_DEAD:
            return
        # [ID: PLR-016] Interrupt any action with stun
        self.state          = S_HIT
        self.hit_stun_timer = HIT_STUN_FRAMES
        self.hit_flash      = 10
        self.current_attack = None
        self.hitbox         = None
        self.animator.unlock()

    # ------------------------------------------------------------------ #
    #  Status Effects & Helpers                                          #
    # ------------------------------------------------------------------ #
    def apply_status(self, effect: str, duration: int) -> None:
        if effect:
            # Overwrite length if re-applied
            self.status_effects[effect] = max(self.status_effects.get(effect, 0), duration)
            self.hit_flash = 5 # Small flash on apply

    def _process_status_effects(self) -> None:
        for eff, duration in list(self.status_effects.items()):
            if duration > 0:
                self.status_effects[eff] -= 1
                
                # Apply tick effects
                if eff == "burn":
                    self.hp = max(0, self.hp - 0.05)   # Fast, lower damage
                elif eff == "poison":
                    self.hp = max(0, self.hp - 0.08)   # Slower, higher damage
            else:
                del self.status_effects[eff]   # Remove expired effects

    def _tick_timers(self) -> None:   # Decrement frame-based timers
        if self.hit_stun_timer > 0:
            self.hit_stun_timer -= 1   # Count down stun timer
        if self.hit_flash > 0:
            self.hit_flash -= 1        # Count down flash timer

    def _sync_anim(self) -> None:     # Map game state to animator state string
        # [ID: PLR-017] Translate state enum to animation key
        if self.state in (S_ATTACK, S_RECOVERY) and self.current_attack:
            atype = self.current_attack.attack_type
            key   = f"attack_{atype}"
            if key in self.animator.frame_map:
                self.animator.set_state(key)
            elif "attack_heavy" in self.animator.frame_map:
                self.animator.set_state("attack_heavy")
            else:
                self.animator.set_state("attack_light")
        elif self.state == S_PARRY:
            if "shield" in self.animator.frame_map:
                self.animator.set_state("shield")
            elif "guard" in self.animator.frame_map:
                self.animator.set_state("guard")
            else:
                self.animator.set_state("hit")
        elif self.state == S_HIT:
            self.animator.set_state("hit")
        elif self.state == S_DEAD:
            self.animator.set_state("dead")
        elif self.state == S_JUMPING:
            self.animator.set_state("walk")    # Reuse walk frames for air
        elif self.state == S_MOVE:
            # [ID: PLR-017A] Use 'run' anim if Shift held and run frames exist
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LSHIFT] and "run" in self.animator.frame_map:
                self.animator.set_state("run")
            else:
                self.animator.set_state("walk")
        else:
            self.animator.set_state("idle")

    def _check_death(self) -> None:   # HP zero → dead state
        if self.hp <= 0 and self.state != S_DEAD:
            # [ID: PLR-018] Enter dead — freeze entity
            self.state   = S_DEAD
            self.vx      = 0.0
            self.hitbox  = None

    def get_rect(self) -> pygame.Rect:   # Sprite bounding rect for renderer
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def is_dead(self) -> bool:   # Public death check for game loop
        return self.state == S_DEAD
