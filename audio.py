import os
import math
import wave
import struct

import pygame

import settings


def _synth_track(path, notes, note_duration, sample_rate=44100, volume=0.22, waveform="square"):
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        frames = bytearray()
        n_samples = int(sample_rate * note_duration)
        for freq in notes:
            for i in range(n_samples):
                t = i / sample_rate
                if waveform == "square":
                    val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
                else:
                    val = math.sin(2 * math.pi * freq * t)
                fade = min(1.0, i / 200, (n_samples - i) / 200)
                sample = int(val * volume * fade * 32767)
                frames += struct.pack('<h', sample)
        f.writeframes(bytes(frames))


def ensure_default_music():
    try:
        os.makedirs(settings.SOUND_ASSET_DIR, exist_ok=True)
        if not os.path.isfile(settings.MUSIC_MENU_PATH):
            menu_notes = [261, 294, 330, 349, 392, 349, 330, 294] * 3
            _synth_track(settings.MUSIC_MENU_PATH, menu_notes, note_duration=0.32, volume=0.16, waveform="sine")
        if not os.path.isfile(settings.MUSIC_ACTION_PATH):
            action_notes = [196, 196, 220, 196, 233, 220, 196, 174] * 4
            _synth_track(settings.MUSIC_ACTION_PATH, action_notes, note_duration=0.11, volume=0.22, waveform="square")
    except Exception as e:
        print(f"[audio] could not generate placeholder music: {e}")


class AudioManager:
    def __init__(self):
        self.available = True
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[audio] mixer init failed: {e}")
            self.available = False

        self.volume = settings.DEFAULT_MUSIC_VOLUME
        self.current_track = None

        if self.available:
            ensure_default_music()

    def _play(self, path):
        if not self.available or self.current_track == path:
            return
        if not os.path.isfile(path):
            print(f"[audio] Missing music file: {path}")
            pygame.mixer.music.stop()
            self.current_track = None
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(loops=-1)
            self.current_track = path
        except Exception as e:
            print(f"[audio] failed to play {path}: {e}")

    def play_menu_music(self):
        self._play(settings.MUSIC_MENU_PATH)

    def play_action_music(self):
        self._play(settings.MUSIC_ACTION_PATH)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.available:
            pygame.mixer.music.set_volume(self.volume)