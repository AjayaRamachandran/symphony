# sound/instruments.py
# module for handling the generation of sounds/instruments.

###### IMPORT ######

import json
from pathlib import Path
import re

import numpy as np

###### CONSTANTS ######

GENERIC_TONE_MAP = {1.0: 1.0}

GENERATED_PIANO_MAP_PATH = r"inner\\src\\sound\\maps\\piano_tones_map.json"
GENERATED_GUITAR_MAP_PATH = r"inner\\src\\sound\\maps\\guitar_tones_map.json"
GENERATED_MALE_VOICE_AAA_MAP_PATH = r"inner\\src\\sound\\maps\\male_voice_aaa_tones_map.json"
GENERATED_MALE_VOICE_OOO_MAP_PATH = r"inner\\src\\sound\\maps\\male_voice_ooo_tones_map.json"
GENERATED_MALE_VOICE_EEE_MAP_PATH = r"inner\\src\\sound\\maps\\male_voice_eee_tones_map.json"
GENERATED_MALE_VOICE_MMM_MAP_PATH = r"inner\\src\\sound\\maps\\male_voice_mmm_tones_map.json"
MALE_VOICE_AAA_MAPS_DIR = Path(r"inner\\src\\sound\\maps\\aaa")
MALE_VOICE_AAA_FILE_HZ_PATTERN = re.compile(r"_([0-9]+(?:\.[0-9]+)?)hz$", re.IGNORECASE)

GENERATED_BRASS_MAP_PATH = r"inner\\src\\sound\\maps\\brass_tones_map.json"

def _load_generated_tones_map(map_path: Path) -> dict[float, float]:
    try:
        with open(map_path, "r", encoding="utf-8") as generated_map_file:
            payload = json.load(generated_map_file)
    except Exception:
        return GENERIC_TONE_MAP

    ratio_to_amplitude = payload.get("ratio_to_amplitude")
    if not isinstance(ratio_to_amplitude, dict):
        return GENERIC_TONE_MAP

    loaded_map: dict[float, float] = {}
    for ratio_key, amp_val in ratio_to_amplitude.items():
        try:
            ratio = float(ratio_key)
            amp = float(amp_val)
        except (TypeError, ValueError):
            continue
        loaded_map[ratio] = amp

    return loaded_map if loaded_map else GENERIC_TONE_MAP


def _load_male_voice_aaa_lut_maps() -> list[tuple[float, dict[float, float]]]:
    lut_maps: list[tuple[float, dict[float, float]]] = []
    if not MALE_VOICE_AAA_MAPS_DIR.exists():
        return lut_maps

    for map_file in MALE_VOICE_AAA_MAPS_DIR.glob("*.json"):
        match = MALE_VOICE_AAA_FILE_HZ_PATTERN.search(map_file.stem)
        if match is None:
            continue
        try:
            root_hz = float(match.group(1))
        except ValueError:
            continue
        lut_maps.append((root_hz, _load_generated_tones_map(map_file)))

    lut_maps.sort(key=lambda item: item[0])
    return lut_maps


ACTIVE_PIANO_TONES_MAP = _load_generated_tones_map(GENERATED_PIANO_MAP_PATH)
ACTIVE_GUITAR_TONES_MAP = _load_generated_tones_map(GENERATED_GUITAR_MAP_PATH)
ACTIVE_MALE_VOICE_AAA_TONES_MAP = _load_generated_tones_map(GENERATED_MALE_VOICE_AAA_MAP_PATH)
ACTIVE_BRASS_TONES_MAP = _load_generated_tones_map(GENERATED_BRASS_MAP_PATH)

ACTIVE_MALE_VOICE_OOO_TONES_MAP = _load_generated_tones_map(GENERATED_MALE_VOICE_OOO_MAP_PATH)
ACTIVE_MALE_VOICE_EEE_TONES_MAP = _load_generated_tones_map(GENERATED_MALE_VOICE_EEE_MAP_PATH)
ACTIVE_MALE_VOICE_MMM_TONES_MAP = _load_generated_tones_map(GENERATED_MALE_VOICE_MMM_MAP_PATH)
ACTIVE_MALE_VOICE_AAA_LUT_MAPS = _load_male_voice_aaa_lut_maps()

PHASE_JITTER_STRENGTH = 1.0
GENERIC_DECAY_BASE = 4.0
GENERIC_DECAY_REF_FREQ = 440.0

###### METHODS / CLASSES ######

def Square(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return np.sign(np.sin(2 * np.pi * freq * t)) * magnitude


def Triangle(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t)) * magnitude


def Sawtooth(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return 2 * (t * freq - np.floor(0.5 + t * freq)) * magnitude


def _root_frequency_decay_envelope(t: np.ndarray, root_freq: float, decay: bool, decay_power: float = 1.0) -> float | np.ndarray:
    if not decay:
        return 1.0
    freq_scale = float(np.sqrt(max(float(root_freq), 1e-6) / GENERIC_DECAY_REF_FREQ))
    freq_scale = float(np.clip(freq_scale, 0.35, 2.0))
    decay_rate = GENERIC_DECAY_BASE * freq_scale
    return np.exp(-decay_rate * t * decay_power)

### ADDITIVE ENGINE ###

def AdditiveInstrument(
    t: np.ndarray,
    freq: float,
    magnitude: float,
    tonesMap: dict[float, float],
    decay: bool = True,
    decay_power: float = 0.7,
) -> np.ndarray:
    if t.size == 0:
        return np.zeros_like(t)

    wave = np.zeros_like(t, dtype=np.float64)
    for ratio, amp in tonesMap.items():
        partial_freq = float(freq) * float(ratio)
        if partial_freq <= 0:
            continue
        partial = float(amp) * np.sin(2 * np.pi * partial_freq * t)
        wave += partial

    wave *= _root_frequency_decay_envelope(t, freq, decay, decay_power)

    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak

    return np.clip(wave * magnitude, -1.0, 1.0)

### FFT INSTRUMENT ###

def ComplexInstrument(t: np.ndarray, freq: float, magnitude: float, tonesMap: dict[float, float], decay: bool = True) -> np.ndarray:
    overtone_items = sorted(tonesMap.items(), key=lambda item: item[0])
    if not overtone_items or t.size == 0:
        return np.zeros_like(t)

    if t.size > 1:
        dt = float(t[1] - t[0])
        sample_rate = int(round(1.0 / dt)) if dt > 0 else 44100
    else:
        sample_rate = 44100

    n_samples = int(t.size)
    nyquist = sample_rate / 2.0
    n_bins = (n_samples // 2) + 1
    spectrum = np.zeros(n_bins, dtype=np.complex128)

    total_amp = 0.0
    for ratio, amp in overtone_items:
        overtone_freq = freq * ratio
        if overtone_freq <= 0 or overtone_freq > nyquist:
            continue
        bin_idx = int(round((overtone_freq / sample_rate) * n_samples))
        if 0 <= bin_idx < n_bins:
            phase = float(np.random.uniform(-np.pi, np.pi))
            spectrum[bin_idx] += float(amp) * np.exp(1j * phase)
            total_amp += float(amp)

    wave = np.fft.irfft(spectrum, n=n_samples).astype(np.float64, copy=False)

    if total_amp > 0:
        wave /= total_amp
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak

    time_decay = _root_frequency_decay_envelope(t, freq, decay)

    result = wave * time_decay * magnitude * 3
    return np.clip(result, -1.0, 1.0)

### WRAPPERS ###

def Piano(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return AdditiveInstrument(t, freq - 1, magnitude, ACTIVE_PIANO_TONES_MAP, decay=True, decay_power=0.3)

def Bells(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return AdditiveInstrument(t, freq, magnitude, ACTIVE_GUITAR_TONES_MAP, decay=True, decay_power=0.7)

def MaleVoiceAah(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    if not ACTIVE_MALE_VOICE_AAA_LUT_MAPS:
        return AdditiveInstrument(t, freq, magnitude, ACTIVE_MALE_VOICE_AAA_TONES_MAP, decay=False)

    input_freq = float(freq)
    closest_hz, closest_map = min(
        ACTIVE_MALE_VOICE_AAA_LUT_MAPS, key=lambda item: abs(item[0] - input_freq)
    )
    if closest_hz <= 0:
        return AdditiveInstrument(t, freq, magnitude, ACTIVE_MALE_VOICE_AAA_TONES_MAP, decay=False)
    return AdditiveInstrument(t, freq, magnitude, closest_map, decay=False)

def MaleVoiceOoh(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return AdditiveInstrument(t, freq, magnitude, ACTIVE_MALE_VOICE_OOO_TONES_MAP, decay=False)

def MaleVoiceEee(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return AdditiveInstrument(t, freq, magnitude, ACTIVE_MALE_VOICE_EEE_TONES_MAP, decay=False)

def MaleVoiceMmm(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
    return AdditiveInstrument(t, freq, magnitude, ACTIVE_MALE_VOICE_MMM_TONES_MAP, decay=False)

# def Brass(t: np.ndarray, freq: float, magnitude: float) -> np.ndarray:
#     return AdditiveInstrument(t, freq, magnitude, ACTIVE_BRASS_TONES_MAP, decay=False)

###### REGISTRY ######

INSTRUMENTS_BY_WAVE = {
    0: Square,
    1: Triangle,
    2: Sawtooth,
    3: Piano,
    4: Bells,
    # 5: MaleVoiceAah,
    # 6: Brass,
    # 6: MaleVoiceOoh,
    # 7: MaleVoiceEee,
    # 8: MaleVoiceMmm,
}

def get_instrument(waves: int):
    return INSTRUMENTS_BY_WAVE.get(waves, Sawtooth)