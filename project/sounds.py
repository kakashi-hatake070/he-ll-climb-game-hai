"""Sound loading and playback wrapper with graceful fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pygame

from settings import SOUNDS_DIR


class SoundManager:
    """Handle sound effects and music, falling back silently if files are missing."""

    def __init__(self, save_data) -> None:
        self.save_data = save_data
        self.volume = float(save_data.get("sound_volume", 0.8))
        self.muted = bool(save_data.get("muted", False))
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.load_sounds()

    def load_sounds(self) -> None:
        """Load available sound effects from the assets folder."""

        names = {
            "coin": "coin.wav",
            "fuel": "fuel.wav",
            "crash": "crash.wav",
            "boost": "boost.wav",
            "click": "click.wav",
            "jump": "jump.wav",
            "engine": "engine.wav",
        }
        for key, file_name in names.items():
            path = SOUNDS_DIR / file_name
            self.sounds[key] = pygame.mixer.Sound(str(path)) if path.exists() else None
        music_path = SOUNDS_DIR / "music.ogg"
        if music_path.exists():
            try:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def set_volume(self, volume: float) -> None:
        """Adjust global sound volume."""

        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        for sound in self.sounds.values():
            if sound is not None:
                sound.set_volume(self.volume)

    def toggle_mute(self) -> None:
        """Mute or unmute audio."""

        self.muted = not self.muted
        volume = 0.0 if self.muted else self.volume
        pygame.mixer.music.set_volume(volume)
        for sound in self.sounds.values():
            if sound is not None:
                sound.set_volume(volume)

    def play_coin(self) -> None:
        self._play("coin")

    def play_fuel(self) -> None:
        self._play("fuel")

    def play_crash(self) -> None:
        self._play("crash")

    def play_boost(self) -> None:
        self._play("boost")

    def play_menu_click(self) -> None:
        self._play("click")

    def play_jump(self) -> None:
        self._play("jump")

    def _play(self, key: str) -> None:
        """Safely play a sound effect if it exists and audio is enabled."""

        if self.muted:
            return
        sound = self.sounds.get(key)
        if sound is not None:
            sound.set_volume(self.volume)
            sound.play()
