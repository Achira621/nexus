# [ID: RST-001] roster.py — Defines specific characters and their lore abilities
from combat.attack import Attack
from utils.constants import (
    LIGHT_DAMAGE, HEAVY_DAMAGE, DIRECTIONAL_DAMAGE,
    LIGHT_STARTUP, LIGHT_ACTIVE, LIGHT_RECOVERY,
    HEAVY_STARTUP, HEAVY_ACTIVE, HEAVY_RECOVERY,
    DIRECTIONAL_STARTUP, DIRECTIONAL_ACTIVE, DIRECTIONAL_RECOVERY,
    LIGHT_KNOCKBACK, HEAVY_KNOCKBACK, DIRECTIONAL_KNOCKBACK,
    LIGHT_RANGE, HEAVY_RANGE, DIRECTIONAL_RANGE,
    PLAYER_HP
)

# [ID: RST-002] Vajra-Kali — The Crimson Tempest (Aggressive, Fire)
def get_vajra_kali(direction: int = 1) -> dict:
    return {
        "name": "Vajra-Kali",
        "sprite_id": "vajra_kali",
        "hp": float(PLAYER_HP),
        "speed_mult": 1.1,      # Slightly faster
        "attacks": {
            "light": Attack(    # Agni Strike: Fast flame attack with burn
                damage=LIGHT_DAMAGE, startup=LIGHT_STARTUP - 1, active=LIGHT_ACTIVE,
                recovery=LIGHT_RECOVERY, knockback=LIGHT_KNOCKBACK, direction=direction,
                attack_type="light", hitbox_range=LIGHT_RANGE,
                status_effect="burn", status_duration=90
            ),
            "heavy": Attack(    # Prithvi Slam: Ground smash with heavy knockback
                damage=HEAVY_DAMAGE + 5, startup=HEAVY_STARTUP + 2, active=HEAVY_ACTIVE,
                recovery=HEAVY_RECOVERY + 2, knockback=(12.0, -6.0), direction=direction,
                attack_type="heavy", hitbox_range=HEAVY_RANGE + 10
            ),
            "directional": Attack( # Vidyut Lash: Rapid combo extender, moves forward
                damage=DIRECTIONAL_DAMAGE, startup=DIRECTIONAL_STARTUP - 2, active=DIRECTIONAL_ACTIVE,
                recovery=DIRECTIONAL_RECOVERY, knockback=DIRECTIONAL_KNOCKBACK, direction=direction,
                attack_type="directional", hitbox_range=DIRECTIONAL_RANGE, movement_override=6.0
            ),
            "special": Attack(  # Brahmastra Surge: High damage multi-element finisher
                damage=30.0, startup=15, active=10, recovery=25,
                knockback=(15.0, -8.0), direction=direction,
                attack_type="special", hitbox_range=160.0
            )
        }
    }

# [ID: RST-003] Takshaka — The Venom Architect (Control, Poison)
def get_takshaka(direction: int = 1) -> dict:
    return {
        "name": "Takshaka",
        "sprite_id": "takshaka",
        "hp": float(PLAYER_HP),
        "speed_mult": 0.9,      # Slightly slower, calculated
        "attacks": {
            "light": Attack(    # Dark Strike: Basic poke
                damage=LIGHT_DAMAGE - 2, startup=LIGHT_STARTUP, active=LIGHT_ACTIVE,
                recovery=LIGHT_RECOVERY, knockback=LIGHT_KNOCKBACK, direction=direction,
                attack_type="light", hitbox_range=LIGHT_RANGE
            ),
            "heavy": Attack(    # Coil Guard: Control tool, immobilizes briefly
                damage=5.0, startup=HEAVY_STARTUP - 2, active=HEAVY_ACTIVE,
                recovery=HEAVY_RECOVERY, knockback=(2.0, 0.0), direction=direction,
                attack_type="heavy", hitbox_range=HEAVY_RANGE,
                status_effect="immobilize", status_duration=45
            ),
            "directional": Attack( # Venom Strike: Poison damage over time
                damage=DIRECTIONAL_DAMAGE - 4, startup=DIRECTIONAL_STARTUP, active=DIRECTIONAL_ACTIVE + 2,
                recovery=DIRECTIONAL_RECOVERY, knockback=DIRECTIONAL_KNOCKBACK, direction=direction,
                attack_type="directional", hitbox_range=DIRECTIONAL_RANGE + 20,
                status_effect="poison", status_duration=180
            ),
            "special": Attack(  # Serpent Dominion: Slows enemy significantly
                damage=15.0, startup=12, active=8, recovery=20,
                knockback=(8.0, -4.0), direction=direction,
                attack_type="special", hitbox_range=140.0,
                status_effect="slow", status_duration=120
            )
        }
    }

# [ID: RST-004] Rudra-Shiva — The Ascendant (Balanced, High Damage)
def get_rudra_shiva(direction: int = 1) -> dict:
    return {
        "name": "Rudra-Shiva",
        "sprite_id": "rudra_shiva",
        "hp": float(PLAYER_HP) + 15,
        "speed_mult": 1.0,      # Balanced speeed
        "attacks": {
            "light": Attack(    # Trishul Poke
                damage=LIGHT_DAMAGE, startup=LIGHT_STARTUP, active=LIGHT_ACTIVE,
                recovery=LIGHT_RECOVERY, knockback=LIGHT_KNOCKBACK, direction=direction,
                attack_type="light", hitbox_range=LIGHT_RANGE + 10
            ),
            "heavy": Attack(    # Tandava Smash
                damage=HEAVY_DAMAGE + 2, startup=HEAVY_STARTUP, active=HEAVY_ACTIVE,
                recovery=HEAVY_RECOVERY, knockback=HEAVY_KNOCKBACK, direction=direction,
                attack_type="heavy", hitbox_range=HEAVY_RANGE + 15
            ),
            "directional": Attack( # Third Eye Burst
                damage=DIRECTIONAL_DAMAGE + 2, startup=DIRECTIONAL_STARTUP, active=DIRECTIONAL_ACTIVE,
                recovery=DIRECTIONAL_RECOVERY, knockback=DIRECTIONAL_KNOCKBACK, direction=direction,
                attack_type="directional", hitbox_range=DIRECTIONAL_RANGE, movement_override=4.0
            ),
            "special": Attack(  # Mahadeva Wrath
                damage=28.0, startup=14, active=10, recovery=20,
                knockback=(14.0, -7.0), direction=direction,
                attack_type="special", hitbox_range=150.0
            )
        }
    }

# [ID: RST-005] Vajra-Garuda — The Sky Warden (High Mobility, Air)
def get_vajra_garuda(direction: int = 1) -> dict:
    return {
        "name": "Vajra-Garuda",
        "sprite_id": "vajra_garuda",
        "hp": float(PLAYER_HP) - 10,
        "speed_mult": 1.3,      # Very fast
        "attacks": {
            "light": Attack(    # Talon Slash
                damage=LIGHT_DAMAGE - 1, startup=LIGHT_STARTUP - 1, active=LIGHT_ACTIVE,
                recovery=LIGHT_RECOVERY - 2, knockback=LIGHT_KNOCKBACK, direction=direction,
                attack_type="light", hitbox_range=LIGHT_RANGE - 10,
                status_effect="burn", status_duration=30
            ),
            "heavy": Attack(    # Aerial Dive
                damage=HEAVY_DAMAGE - 2, startup=HEAVY_STARTUP - 1, active=HEAVY_ACTIVE,
                recovery=HEAVY_RECOVERY - 2, knockback=(10.0, -8.0), direction=direction,
                attack_type="heavy", hitbox_range=HEAVY_RANGE
            ),
            "directional": Attack( # Gale Dash (long movement override)
                damage=DIRECTIONAL_DAMAGE, startup=DIRECTIONAL_STARTUP - 1, active=DIRECTIONAL_ACTIVE,
                recovery=DIRECTIONAL_RECOVERY, knockback=DIRECTIONAL_KNOCKBACK, direction=direction,
                attack_type="directional", hitbox_range=DIRECTIONAL_RANGE + 20, movement_override=9.0
            ),
            "special": Attack(  # Divine Wind
                damage=20.0, startup=10, active=8, recovery=15,
                knockback=(18.0, -4.0), direction=direction,
                attack_type="special", hitbox_range=160.0
            )
        }
    }
