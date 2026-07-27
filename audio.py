import os
import math
import wave
import struct

import numpy as np
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


# ---------------------------------------------------------------------------
# Sound effects -- synthesized in memory with numpy (no asset files needed,
# same philosophy as the placeholder music above). Each is built once at
# startup and cached, then played via pygame.mixer.Sound.play() which uses
# its own channels, independent of the looping background music.
# ---------------------------------------------------------------------------

_SAMPLE_RATE = 44100


def _envelope(n_samples, attack=0.05, decay_power=1.6):
    """Quick attack, smooth power-curve decay -- works for almost any
    short percussive SFX (shots, hits, blips, chimes)."""
    t = np.linspace(0, 1, n_samples, endpoint=False)
    attack_samples = max(1, int(n_samples * attack))
    env = np.ones(n_samples)
    env[:attack_samples] = np.linspace(0, 1, attack_samples)
    decay = (1 - t) ** decay_power
    return np.minimum(env, 1.0) * decay


def _tone_sound(freq_start, freq_end, duration, volume=0.35, waveform="square", decay_power=1.6):
    n = int(_SAMPLE_RATE * duration)
    if n <= 0:
        n = 1
    t = np.linspace(0, duration, n, endpoint=False)
    freq = np.linspace(freq_start, freq_end, n)
    phase = np.cumsum(2 * np.pi * freq / _SAMPLE_RATE)
    if waveform == "square":
        wave_arr = np.sign(np.sin(phase))
    elif waveform == "triangle":
        wave_arr = 2 * np.abs(2 * (phase / (2 * np.pi) - np.floor(phase / (2 * np.pi) + 0.5))) - 1
    else:  # sine
        wave_arr = np.sin(phase)
    env = _envelope(n, decay_power=decay_power)
    samples = (wave_arr * env * volume * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _noise_burst_sound(duration, volume=0.35, decay_power=2.2, low_pass=0.0):
    n = int(_SAMPLE_RATE * duration)
    if n <= 0:
        n = 1
    noise = np.random.uniform(-1, 1, n)
    if low_pass > 0:
        # Cheap one-pole low-pass filter to make noise feel like a boom
        # instead of harsh static.
        alpha = low_pass
        filtered = np.empty_like(noise)
        prev = 0.0
        for i in range(n):
            prev = prev + alpha * (noise[i] - prev)
            filtered[i] = prev
        noise = filtered
    env = _envelope(n, attack=0.01, decay_power=decay_power)
    samples = (noise * env * volume * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _chime_sound(freqs, note_duration=0.09, volume=0.3):
    """A short sequence of clean sine notes -- used for pleasant feedback
    (coin pickup, victory) rather than combat sounds."""
    n_per_note = int(_SAMPLE_RATE * note_duration)
    chunks = []
    for freq in freqs:
        t = np.linspace(0, note_duration, n_per_note, endpoint=False)
        wave_arr = np.sin(2 * np.pi * freq * t)
        env = _envelope(n_per_note, attack=0.02, decay_power=1.2)
        chunks.append(wave_arr * env)
    samples = (np.concatenate(chunks) * volume * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _build_sfx_library():
    """Builds every sound effect once. Returns a dict; on any failure
    (e.g. mixer not available) returns an empty dict so callers can fail
    silently, same philosophy as the rest of audio.py."""
    return {
        "shoot_light": _tone_sound(880, 520, 0.07, volume=0.22, waveform="square", decay_power=2.0),
        "shoot_heavy": _tone_sound(420, 180, 0.11, volume=0.28, waveform="square", decay_power=1.8),
        "explosion": _noise_burst_sound(0.32, volume=0.35, decay_power=2.0, low_pass=0.35),
        "explosion_big": _noise_burst_sound(0.55, volume=0.42, decay_power=1.6, low_pass=0.22),
        "player_hit": _tone_sound(220, 80, 0.18, volume=0.32, waveform="triangle", decay_power=1.4),
        "shield_block": _tone_sound(700, 900, 0.12, volume=0.24, waveform="triangle", decay_power=1.8),
        "shield_activate": _tone_sound(300, 700, 0.16, volume=0.22, waveform="sine", decay_power=1.3),
        "boost_engage": _noise_burst_sound(0.22, volume=0.16, decay_power=1.2, low_pass=0.5),
        "coin": _chime_sound([880, 1320], note_duration=0.06, volume=0.28),
        "boss_phase": _tone_sound(180, 90, 0.4, volume=0.3, waveform="square", decay_power=1.1),
        "boss_victory": _chime_sound([523, 659, 784, 1046], note_duration=0.1, volume=0.3),
        "powerup_select": _chime_sound([659, 880, 1046], note_duration=0.08, volume=0.3),
        "ui_click": _tone_sound(500, 700, 0.05, volume=0.18, waveform="square", decay_power=2.5),
    }


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
        self.sfx = {}

        if self.available:
            ensure_default_music()
            try:
                self.sfx = _build_sfx_library()
            except Exception as e:
                print(f"[audio] could not synthesize sound effects: {e}")
                self.sfx = {}

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

    def play_sfx(self, name):
        """Plays a synthesized one-shot sound effect by name. Fails
        silently if audio isn't available or the name is unknown --
        gameplay should never break because of a missing sound."""
        if not self.available:
            return
        sound = self.sfx.get(name)
        if sound is None:
            return
        try:
            sound.set_volume(self.volume)
            sound.play()
        except Exception as e:
            print(f"[audio] failed to play sfx '{name}': {e}")