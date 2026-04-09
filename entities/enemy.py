# [ID: ENE-001] enemy.py — AI-controlled fighter entity
import pygame
from engine.physics   import step as physics_step
from engine.animator  import Animator
from combat.hitbox    import Hurtbox, Hitbox
from combat.attack    import make_light, make_heavy
from utils.constants  import (
    ENEMY_HP, ENEMY_SPEED,
    ENEMY_START_X, ENEMY_START_Y, ENEMY_WIDTH, ENEMY_HEIGHT,
    HIT_STUN_FRAMES,
)
from utils import logger


S_IDLE     = "idle"
S_MOVE     = "move"
S_JUMPING  = "jumping"
S_ATTACK   = "attack"
S_RECOVERY = "recovery"
S_HIT      = "hit"
S_DEAD     = "dead"
S_PARRY    = "parry"


class Enemy:   # AI-driven fighter — AI writes vx and calls begin_attack()
    def __init__(self, frame_map: dict, config: dict = None):
        # [ID: ENE-003] World position and physics
        self.x          = float(ENEMY_START_X)
        self.y          = float(ENEMY_START_Y)
        self.vx         = 0.0
        self.vy         = 0.0
        self.width      = ENEMY_WIDTH
        self.height     = ENEMY_HEIGHT
        self.on_ground  = False
        self.facing_left = True    # Enemy starts facing left (toward player)
        self.name       = config["name"] if config else "Enemy"

        # [ID: ENE-004] Health and combat state
        hp_val = config["hp"] if config else float(ENEMY_HP)
        self.hp             = hp_val
        self.max_hp         = hp_val
        self.energy         = 0.0
        self.max_energy     = 100.0
        self.speed_mult     = config["speed_mult"] if config else 1.0
        self.moveset        = config["attacks"] if config else None
        self.parry_config   = config.get("parry", None)
        
        self.state          = S_IDLE
        self.current_attack = None
        self.attack_frame   = 0
        self.parry_frame    = 0
        self.has_hit        = False
        self.hit_stun_timer = 0
        self.hit_stop_timer = 0
        self.hit_flash      = 0
        
        # [ID: ENE-004B] Status effects
        self.status_effects = {}

        # [ID: ENE-005] AI state (set and read by enemy_ai module)
        self.ai_state = "idle"   # Exposed for debug overlay

        # [ID: ENE-006] Animation and collision
        self.animator = Animator(frame_map, self.name)
        self.hurtbox  = Hurtbox(self.x, self.y, self.width, self.height)
        self.hitbox: "Hitbox | None" = None

    # ------------------------------------------------------------------ #
    #  Public update — called after AI has set vx / triggered attacks    #
    # ------------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        # [ID: ENE-007] Dead — only animate
        if self.state == S_DEAD:
            self.animator.set_state("dead")
            self.animator.update(dt)
            return

        if self.hit_stop_timer > 0:
            return

        self._tick_timers()
        self._process_status_effects()

        if self.state in (S_MOVE, S_JUMPING, S_ATTACK):
            self.energy = min(self.max_energy, self.energy + 0.15)

        if self.state == S_HIT:
            self._update_stun()
        elif self.state == S_PARRY:
            self._update_parry()
        elif self.state in (S_ATTACK, S_RECOVERY):
            self._update_attack()
        elif self.status_effects.get("immobilize", 0) > 0:
            self.vx *= 0.5               # Cannot move if immobilized
            self.state = S_IDLE if self.on_ground else S_JUMPING
        else:
            if not self.on_ground:
                self.state = S_JUMPING
            elif self.vx != 0.0:
                self.state = S_MOVE
            else:
                self.state = S_IDLE

        physics_step(self)
        self.hurtbox.sync(self)
        self.animator.update(dt)
        self._sync_anim()
        self._check_death()

    # ------------------------------------------------------------------ #
    #  AI command interface (called by enemy_ai.py)                      #
    # ------------------------------------------------------------------ #
    def move_toward(self, target_x: float) -> None:   # AI movement command
        # [ID: ENE-008] Approach target horizontally
        if self.status_effects.get("immobilize", 0) > 0:
            return
            
        base_speed = ENEMY_SPEED * self.speed_mult
        if self.status_effects.get("slow", 0) > 0:
            base_speed *= 0.5
            
        if target_x < self.x:
            self.vx          = -base_speed
            self.facing_left = True
        else:
            self.vx          = base_speed
            self.facing_left = False

    def stop_moving(self) -> None:   # AI halt command
        self.vx    = 0.0             # Zero velocity

    def begin_attack(self, attack_type: str = "light") -> None:  # AI attack trigger
        # [ID: ENE-009] Guard — cannot attack while busy
        if self.state in (S_ATTACK, S_RECOVERY, S_HIT, S_DEAD):
            return
        direction = -1 if self.facing_left else 1
        
        if self.moveset and attack_type in self.moveset:
            atk = self.moveset[attack_type]
            atk.direction = direction
            self.current_attack = atk
        else:
            if attack_type == "heavy":
                self.current_attack = make_heavy(direction)
            else:
                self.current_attack = make_light(direction)
                
        self.state          = S_ATTACK
        self.attack_frame   = 0
        self.has_hit        = False
        self.hitbox         = None
        attack_key = f"attack_{self.current_attack.attack_type}"
        if attack_key in self.animator.frame_map:
            self.animator.set_state(attack_key)
        elif "attack_heavy" in self.animator.frame_map:
            self.animator.set_state("attack_heavy")
        else:
            self.animator.set_state("attack_light")
        self.animator.lock()

    def begin_parry(self) -> None:
        if self.on_ground and self.parry_config:
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

    # ------------------------------------------------------------------ #
    #  Attack frame logic                                                 #
    # ------------------------------------------------------------------ #
    def _update_attack(self) -> None:
        if self.current_attack is None:
            self.state = S_IDLE
            self.animator.unlock()
            return
        atk = self.current_attack
        self.attack_frame += 1   # Advance frame counter

        if self.attack_frame <= atk.startup:
            self.hitbox  = None
            self.vx     *= 0.5
            if getattr(atk, "movement_override", 0) != 0:
                self.vx = atk.movement_override * atk.direction

        elif self.attack_frame <= atk.startup + atk.active:  # Active
            # [ID: ENE-011] Live hitbox during active frames
            self.hitbox = Hitbox.from_attack(self, atk)
            if getattr(atk, "movement_override", 0) != 0:
                self.vx = atk.movement_override * atk.direction
        else:                                              # Recovery
            self.state  = S_RECOVERY
            self.hitbox = None
            self.vx    *= 0.3

        if self.attack_frame >= atk.total_frames:          # Attack done
            self.state          = S_IDLE
            self.current_attack = None
            self.hitbox         = None
            self.animator.unlock()

    # ------------------------------------------------------------------ #
    #  Parry frame logic                                                  #
    # ------------------------------------------------------------------ #
    def _update_parry(self) -> None:
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
        self.vx *= 0.75                 # Friction during stun
        if self.hit_stun_timer <= 0:
            # [ID: ENE-012] Stun expired — back to idle
            self.state  = S_IDLE if self.on_ground else S_JUMPING
            self.vx     = 0.0

    def enter_hit_stun(self) -> None:   # Called by damage.resolve_hit()
        if self.state == S_DEAD:
            return
        # [ID: ENE-013] Interrupt any action with stun
        self.state          = S_HIT
        self.hit_stun_timer = HIT_STUN_FRAMES
        self.hit_flash      = 10
        self.current_attack = None
        self.hitbox         = None
        self.animator.unlock()

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #
    def apply_status(self, effect: str, duration: int) -> None:
        if effect:
            self.status_effects[effect] = max(self.status_effects.get(effect, 0), duration)
            self.hit_flash = 5

    def _process_status_effects(self) -> None:
        for eff, duration in list(self.status_effects.items()):
            if duration > 0:
                self.status_effects[eff] -= 1
                if eff == "burn":
                    self.hp = max(0, self.hp - 0.05)
                elif eff == "poison":
                    self.hp = max(0, self.hp - 0.08)
            else:
                del self.status_effects[eff]
                
    def _tick_timers(self) -> None:
        if self.hit_stun_timer > 0:
            self.hit_stun_timer -= 1   # Decrement stun countdown
        if self.hit_flash > 0:
            self.hit_flash -= 1        # Decrement flash countdown

    def _sync_anim(self) -> None:   # Map state → animator key
        # [ID: ENE-014] Translate game state to animation state string
        if self.state in (S_ATTACK, S_RECOVERY) and self.current_attack:
            atype = self.current_attack.attack_type        # e.g. "light", "heavy"
            key   = f"attack_{atype}"                      # Build state key
            if key in self.animator.frame_map:             # Exact match
                self.animator.set_state(key)
            elif "attack_heavy" in self.animator.frame_map:  # Fallback to heavy
                self.animator.set_state("attack_heavy")
            else:                                          # Last resort — light
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
            self.animator.set_state("walk")
        elif self.state == S_MOVE:
            self.animator.set_state("walk")
        else:
            self.animator.set_state("idle")

    def _check_death(self) -> None:
        if self.hp <= 0 and self.state != S_DEAD:
            # [ID: ENE-015] Enter dead state
            self.state  = S_DEAD
            self.vx     = 0.0
            self.hitbox = None
            self.animator.unlock()

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def is_dead(self) -> bool:
        return self.state == S_DEAD
