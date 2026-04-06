"""
Motor Noise Model — generates human-like drag parameters for programmatic actions.

When an AI agent executes a move_card action, the Motor dimension needs realistic
mouse drag parameters (time, distance, accuracy) rather than perfect pixel-precise
movements. This model uses Fitts' Law with stochastic noise to simulate human
motor control at configurable skill levels.

The generated parameters are injected into MotorCard.MergeMotorCard() on the Unity side.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class DragParams:
    """Parameters simulating a human mouse drag."""
    time_spanned: float       # Duration in seconds
    distance_drop: float      # Squared distance cursor traveled
    distance_to_slot: float   # Squared distance from drop point to slot center
    half_distance: float      # Squared distance to halfway anchor
    min_distance_slots: list  # Squared min distances to all 5 slots during drag

    def to_dict(self) -> dict:
        return {
            "motor_time": self.time_spanned,
            "motor_distance": self.distance_drop,
            "motor_dist_to_slot": self.distance_to_slot,
            "motor_half_distance": self.half_distance,
            "motor_min_distances": self.min_distance_slots,
        }


class MotorNoiseModel:
    """Generates human-like motor noise parameters for programmatic actions.

    Args:
        skill_level: 0.0 = very clumsy, 1.0 = expert human. Never robot-perfect.
        rng_seed: Optional seed for reproducibility.
    """

    def __init__(self, skill_level: float = 0.5, rng_seed: int = None):
        self.skill = np.clip(skill_level, 0.0, 1.0)
        self.rng = np.random.default_rng(rng_seed)

    def generate_drag_params(
        self,
        source_pos: tuple,
        target_pos: tuple,
        all_slot_positions: dict = None,
    ) -> DragParams:
        """Generate noisy drag parameters for a card move.

        Args:
            source_pos: (x, y) world position of source slot
            target_pos: (x, y) world position of target slot
            all_slot_positions: dict of slot_name -> (x, y) for all slots

        Returns:
            DragParams with realistic noise applied.
        """
        src = np.array(source_pos, dtype=np.float64)
        tgt = np.array(target_pos, dtype=np.float64)
        true_distance = np.linalg.norm(tgt - src)

        # --- Movement time (Fitts' Law + noise) ---
        # Base time decreases with skill: expert ~0.3s, novice ~1.5s
        base_time = 0.3 + (1 - self.skill) * 1.2
        # Log-normal noise: higher variance for lower skill
        time_noise = self.rng.lognormal(0, 0.3 * (1 - self.skill))
        drag_time = np.clip(base_time * time_noise, 0.15, 3.0)

        # --- Path inefficiency (extra distance from non-straight path) ---
        # Expert: nearly straight (1.05x). Novice: meandering (up to 2x)
        path_inefficiency = 1.0 + self.rng.exponential(0.15 * (1 - self.skill))
        drag_distance_sq = (true_distance * path_inefficiency) ** 2

        # --- Drop accuracy (distance from slot center at drop) ---
        # Rayleigh distribution: sigma decreases with skill
        accuracy_sigma = max(0.05, 0.5 * (1 - self.skill))
        drop_offset = self.rng.rayleigh(accuracy_sigma)
        drop_offset_sq = drop_offset ** 2

        # --- Halfway accuracy (for "speed accuracy halfway" mode) ---
        halfway_sigma = accuracy_sigma * 1.5
        halfway_offset = self.rng.rayleigh(halfway_sigma)
        halfway_offset_sq = halfway_offset ** 2

        # --- Visit-all-slots distances ---
        min_distances_sq = []
        if all_slot_positions:
            for i in range(1, 6):
                slot_key = str(i)
                if slot_key in all_slot_positions:
                    slot_pos = np.array(all_slot_positions[slot_key])
                    # Simulate cursor passing near each slot during drag
                    # Better skill = closer passes
                    visit_sigma = max(0.1, 0.8 * (1 - self.skill))
                    visit_noise = self.rng.rayleigh(visit_sigma)
                    min_distances_sq.append(visit_noise ** 2)
                else:
                    min_distances_sq.append(1.0)
        else:
            # Default: moderate distances
            for _ in range(5):
                visit_noise = self.rng.rayleigh(0.5)
                min_distances_sq.append(visit_noise ** 2)

        return DragParams(
            time_spanned=drag_time,
            distance_drop=drag_distance_sq,
            distance_to_slot=drop_offset_sq,
            half_distance=halfway_offset_sq,
            min_distance_slots=min_distances_sq,
        )
