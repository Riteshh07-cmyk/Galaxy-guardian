"""
audio.py
--------
Music + sound effects, all synthesized in code -- no audio asset files.

Music:
  - One menu track (calm).
  - Several "level" tracks that rotate as you climb levels, each a bit
    faster / brighter than the last, so the soundtrack visibly ramps up
    zone by zone instead of looping the exact same thing forever.
  - A separate, more intense boss track that kicks in the instant a boss
    fight starts and switches back the instant it ends.

Sound effects:
  - One distinct one-shot "laser" sound per weapon type (normal, double,
    triple, spread, rapid, plasma), built directly as short numpy wave
    arrays and handed to pygame as pygame.mixer.Sound objects -- nothing
    written to disk for these, they just live in memory for the run.
"""

import os
import math
import wave
import struct

import numpy as np
import pygame

import settings


SOUND_ASSET_DIR = getattr(settings, "SOUND_ASSET_DIR", "assets/sounds")
MUSIC_MENU_PATH = getattr(settings, "MUSIC_MENU_PATH", os.path.join(SOUND_ASSET_DIR, "music_menu.wav"))
DEFAULT_MUSIC_VOLUME = getattr(settings, "DEFAULT_MUSIC_VOLUME", 0.5)
DEFAULT_SFX_VOLUME = getattr(settings, "DEFAULT_SFX_VOLUME", 0.6)

SAMPLE_RATE = 44100

# --- Level music: (notes, note_duration, volume, waveform) ----------------
# Each entry is a little faster / brighter than the last, so the deeper
# you get, the more energetic the loop feels -- without needing a unique
# file per level (there could be dozens). Tracks just cycle through this
# list as the level climbs.
LEVEL_TRACK_DEFS = [
    ([196, 220, 247, 262, 294, 262, 247, 220] * 3, 0.30, 0.15, "sine"),
    ([220, 262, 294, 330, 349, 330, 294, 262] * 3, 0.24, 0.16, "square"),
    ([247, 294, 330, 370, 392, 370, 330, 294] * 3, 0.20, 0.17, "square"),
    ([262, 311, 349, 392, 440, 392, 349, 311] * 3, 0.16, 0.18, "square"),
]

BOSS_TRACK_NOTES = [174, 174, 196, 174, 207, 196, 174, 155,
                     174, 174, 220, 196, 233, 220, 196, 174] * 3
BOSS_TRACK_DURATION = 0.11
BOSS_TRACK_VOLUME = 0.22


def _level_track_path(index):
    return os.path.join(SOUND_ASSET_DIR, f"music_level_{index}.wav")


def _boss_track_path():
    return os.path.join(SOUND_ASSET_DIR, "music_boss.wav")


def _synth_track(path, notes, note_duration, sample_rate=SAMPLE_RATE, volume=0.22, waveform="square"):
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
    """Generates every placeholder music track that doesn't already exist
    on disk. Safe to call every launch -- skips anything already there."""
    try:
        os.makedirs(SOUND_ASSET_DIR, exist_ok=True)

        if not os.path.isfile(MUSIC_MENU_PATH):
            menu_notes = [261, 294, 330, 349, 392, 349, 330, 294] * 3
            _synth_track(MUSIC_MENU_PATH, menu_notes, note_duration=0.32, volume=0.16, waveform="sine")

        for i, (notes, note_duration, volume, waveform) in enumerate(LEVEL_TRACK_DEFS):
            path = _level_track_path(i)
            if not os.path.isfile(path):
                _synth_track(path, notes, note_duration=note_duration, volume=volume, waveform=waveform)

        boss_path = _boss_track_path()
        if not os.path.isfile(boss_path):
            _synth_track(boss_path, BOSS_TRACK_NOTES, note_duration=BOSS_TRACK_DURATION,
                         volume=BOSS_TRACK_VOLUME, waveform="square")
    except Exception as e:
        print(f"[audio] could not generate placeholder music: {e}")


# ---------------------------------------------------------------------------
# Weapon sound effects -- short, in-memory only (no files), each weapon
# gets its own little sonic identity so swapping weapons is audible even
# with your eyes on the action instead of the HUD badge.
# ---------------------------------------------------------------------------

def _tone_wave(freq, duration, sample_rate=SAMPLE_RATE, waveform="square", volume=0.25, pitch_bend=0.0):
    """Builds a mono float wave for one tone. pitch_bend is a fractional
    sweep applied linearly over the note's duration (e.g. -0.3 means the
    pitch glides down to 70% of freq by the end -- a classic laser 'pew'
    shape; positive values glide up instead, for a charge-up feel)."""
    n_samples = max(1, int(sample_rate * duration))
    t = np.linspace(0, duration, n_samples, endpoint=False)
    swept_freq = freq * (1.0 + pitch_bend * (t / duration))
    phase = 2 * np.pi * np.cumsum(swept_freq) / sample_rate

    if waveform == "square":
        wave_arr = np.sign(np.sin(phase))
    elif waveform == "saw":
        wave_arr = 2 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    else:  # sine
        wave_arr = np.sin(phase)

    fade_len = min(200, n_samples // 4) if n_samples > 8 else 0
    envelope = np.ones(n_samples)
    if fade_len > 0:
        envelope[:fade_len] = np.linspace(0.0, 1.0, fade_len)
        envelope[-fade_len:] = np.linspace(1.0, 0.0, fade_len)

    return wave_arr * envelope * volume


def _make_sound(freq, duration, **kwargs):
    samples = (_tone_wave(freq, duration, **kwargs) * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _make_multi_pulse_sound(freq, pulse_duration, count, gap, **kwargs):
    silence = np.zeros(int(SAMPLE_RATE * gap))
    parts = []
    for i in range(count):
        parts.append(_tone_wave(freq, pulse_duration, **kwargs))
        if i < count - 1:
            parts.append(silence)
    combined = np.concatenate(parts)
    samples = (combined * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _build_weapon_sfx():
    """Returns {weapon_name: pygame.mixer.Sound}. Each weapon's sound
    mirrors its personality: normal is a clean single zap, double/triple
    literally fire multiple quick pulses, spread is a slightly rougher
    sawtooth (wide, less precise), rapid is a tiny quiet blip (since it
    fires constantly and shouldn't wall-of-noise the mix), plasma is a
    low, slower, rising charge-thump."""
    return {
        "normal": _make_sound(880, 0.09, waveform="square", volume=0.22, pitch_bend=-0.3),
        "double": _make_multi_pulse_sound(760, 0.07, 2, 0.045, waveform="square", volume=0.20, pitch_bend=-0.25),
        "triple": _make_multi_pulse_sound(700, 0.055, 3, 0.04, waveform="square", volume=0.18, pitch_bend=-0.2),
        "spread": _make_sound(620, 0.11, waveform="saw", volume=0.18, pitch_bend=-0.15),
        "rapid": _make_sound(1200, 0.045, waveform="square", volume=0.14, pitch_bend=-0.4),
        "plasma": _make_sound(220, 0.22, waveform="sine", volume=0.28, pitch_bend=0.6),
    }


class AudioManager:
    def __init__(self):
        self.available = True
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
        except Exception as e:
            print(f"[audio] mixer init failed: {e}")
            self.available = False

        self.volume = DEFAULT_MUSIC_VOLUME
        self.sfx_volume = DEFAULT_SFX_VOLUME
        self.current_track = None

        self.level_music_paths = [_level_track_path(i) for i in range(len(LEVEL_TRACK_DEFS))]
        self.boss_music_path = _boss_track_path()

        self.weapon_sfx = {}

        if self.available:
            ensure_default_music()
            try:
                self.weapon_sfx = _build_weapon_sfx()
            except Exception as e:
                print(f"[audio] could not build weapon sfx: {e}")

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
        self._play(MUSIC_MENU_PATH)

    def play_level_music(self, level):
        """Rotates through LEVEL_TRACK_DEFS as the level climbs -- each
        track a bit faster/brighter than the last, cycling back to the
        start once you run past the end of the list."""
        if not self.level_music_paths:
            return
        index = (max(1, level) - 1) % len(self.level_music_paths)
        self._play(self.level_music_paths[index])

    def play_boss_music(self):
        self._play(self.boss_music_path)

    def play_action_music(self):
        """Kept for backward compatibility with older callers -- maps
        onto the first level track."""
        self.play_level_music(1)

    def play_weapon_sound(self, weapon_name):
        if not self.available:
            return
        sound = self.weapon_sfx.get(weapon_name)
        if sound is None:
            return
        try:
            sound.set_volume(self.sfx_volume)
            sound.play()
        except Exception as e:
            print(f"[audio] failed to play weapon sfx '{weapon_name}': {e}")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.available:
            pygame.mixer.music.set_volume(self.volume)

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))