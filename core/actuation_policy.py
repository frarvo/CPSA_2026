# actuation_policy.py
# Defines which actuators to activate based on the events.
#
# Author: Francesco Urru
# Repository: https://github.com/frarvo/STOPme
# License: MIT


from typing import List, Dict, Optional
import random
import time

from utils.audio_paths import AudioLibrary
from utils.config import get_policy_attempts

TAG_NO_CLASS = 0
TAG_NON_DANGEROUS = 1
TAG_DANGEROUS = 2
TAG_NON_STEREOTIPY = 3


class StereotipyActivationPolicy:
    """
    Event-driven loop:
      - For tag 1,2: emit one actuation per event.
      - If the next event is still 1 or 2, retry on the SAME actuator (variation).
      - After N attempts on that actuator, switch actuator (random different if possible).
      - If the tag changes to 0 or 3 after an actuation, set the CURRENT actuator as
        "successful". Next time the same event tag appears, choose this actuator.
    """

    def __init__(self, actuator_ids: List[str]):
        self.actuator_ids = list(actuator_ids or [])
        self.retries_per_actuator = max(1, int(get_policy_attempts()))
        self.rng = random.Random()

        # State across events
        self._current_tag: Optional[int] = None
        self._current_actuator: Optional[str] = None
        self._attempts_on_current: int = 0
        self._variation_idx: int = 0
        self._variation_idx_per_actuator: Dict[str, int] = {}


        # Variations
        self._led_variants_mild = [
            {"color": (255, 255, 255, 0), "intensity": 50, "speed": 100},
            {"color": (180, 220, 255, 0), "intensity": 60, "speed": 100},
            {"color": (200, 255, 200, 0), "intensity": 70, "speed": 100},
        ]
        self._led_variants_strong = [
            {"color": (255,   0,   0, 0), "intensity": 100, "speed": 100},
            {"color": (255, 128,   0, 0), "intensity": 100, "speed": 100},
            {"color": (255,   0, 255, 0), "intensity": 100, "speed": 100},
        ]
        self._meta_variants_mild = [
            {"duty": 40, "duration": 700},
            {"duty": 55, "duration": 800},
            {"duty": 70, "duration": 900},
        ]
        self._meta_variants_strong = [
            {"duty": 100, "duration": 900},
            {"duty": 100, "duration": 1100},
            {"duty": 100, "duration": 1300},
        ]
        self._spk_variants_mild = [
            {"file": getattr(AudioLibrary, "CUSTOM_MILD_1", getattr(AudioLibrary, "MISSING_FILE", ""))},
            {"file": getattr(AudioLibrary, "CUSTOM_MILD_2", getattr(AudioLibrary, "MISSING_FILE", ""))},
            {"file": getattr(AudioLibrary, "CUSTOM_MILD_3", getattr(AudioLibrary, "MISSING_FILE", ""))},
        ]
        self._spk_variants_strong = [
            {"file": getattr(AudioLibrary, "CUSTOM_STRONG_1", getattr(AudioLibrary, "MISSING_FILE", ""))},
            {"file": getattr(AudioLibrary, "CUSTOM_STRONG_2", getattr(AudioLibrary, "MISSING_FILE", ""))},
            {"file": getattr(AudioLibrary, "CUSTOM_STRONG_3", getattr(AudioLibrary, "MISSING_FILE", ""))},
        ]
        self._spk_cooldown_sec = 5
        self._spk_last_fire_time: Dict[str, float] = {}

    def handle(self, event: dict) -> Optional[Dict]:
        if not self.actuator_ids:
            return None

        tag = self._parse_tag(event.get("stereotipy_tag"))
        now = time.monotonic()

        # Back to non-stereotypy: reset.
        off_action = None
        if tag in (TAG_NO_CLASS, TAG_NON_STEREOTIPY) or tag is None:
            if self._current_tag in (TAG_NON_DANGEROUS, TAG_DANGEROUS) and self._current_actuator:
                if self._current_actuator.startswith("led_"):
                    off_action = {"actuator_id": self._current_actuator, "params": {"color": (0, 0, 0, 0), "intensity": 0, "speed": 100}}
            self._reset_state()
            return off_action

        # First positive event (or severity changed): choose actuator
        if self._current_tag != tag or self._current_actuator is None:
            self._current_tag = tag
            self._attempts_on_current = 0
            #self._variation_idx = 0

        # If we reached the attempt limit on this actuator, switch now
        if self._attempts_on_current >= self.retries_per_actuator:
            self._current_actuator = self._pick_random(exclude=self._current_actuator)
            self._attempts_on_current = 0
            #self._variation_idx = 0

        if self._current_actuator and self._current_actuator.startswith("speaker"):
            last = self._spk_last_fire_time.get(self._current_actuator, 0.0)
            if now - last < self._spk_cooldown_sec:
                return None

        # Build actuation
        mild = (tag == TAG_NON_DANGEROUS)
        var_idx = self._get_variation_idx(self._current_actuator)
        result = self._params_for(self._current_actuator, mild=mild, variation_index=var_idx, now=now)
        if not result:
            # Fallback: pick another actuator immediately
            self._current_actuator = self._pick_random(exclude=self._current_actuator)
            self._attempts_on_current = 0
            #self._variation_idx = 0
            var_idx = self._get_variation_idx(self._current_actuator)
            result = self._params_for(self._current_actuator, mild=mild, variation_index=var_idx, now=now)
            if not result:
                return None

        # Record fire time and attempt only if actual actuation was produced
        self._spk_last_fire_time[self._current_actuator] = now
        self._attempts_on_current += 1
        #self._variation_idx += 1
        self._bump_variation_idx(self._current_actuator)
        return result

    # ----- helpers -----
    def _parse_tag(self, raw) -> Optional[int]:
        try:
            return int(raw)
        except Exception:
            return None

    def _pick_random(self, exclude: Optional[str]) -> Optional[str]:
        candidates = self.actuator_ids
        if exclude and len(candidates) > 1:
            candidates = [a for a in candidates if a != exclude]
        return self.rng.choice(candidates) if candidates else None

    def _params_for(self, actuator_id: Optional[str], *, mild: bool, variation_index: int, now: float) -> Optional[Dict]:
        if not actuator_id:
            return None

        if actuator_id.startswith("led_"):
            variants = self._led_variants_mild if mild else self._led_variants_strong
            params = variants[variation_index % len(variants)]

        elif actuator_id.startswith("speaker_"):
            variants = self._spk_variants_mild if mild else self._spk_variants_strong

            try:
                params = variants[variation_index % len(variants)]
            except (KeyError, IndexError):
                params = {"file": getattr(AudioLibrary, "MISSING_FILE", "")}

        elif actuator_id.startswith("meta_"):
            variants = self._meta_variants_mild if mild else self._meta_variants_strong
            params = variants[variation_index % len(variants)]

        else:
            return None

        return {"actuator_id": actuator_id, "params": params}

    def _reset_state(self):
        self._current_tag = None
        self._current_actuator = None
        self._attempts_on_current = 0
        self._variation_idx = 0

    def _get_variation_idx(self, actuator_id: Optional[str]) -> int:
        if not actuator_id:
            return 0
        return self._variation_idx_per_actuator.get(actuator_id, 0)

    def _bump_variation_idx(self, actuator_id: Optional[str]):
        if not actuator_id:
            return
        self._variation_idx_per_actuator[actuator_id] = self._get_variation_idx(actuator_id) + 1