# sound/instruments.py
# module for handling the generation of sounds/instruments.

###### IMPORT ######

import json
from pathlib import Path
import re

import numpy as np

###### CONSTANTS ######

GENERIC_TONE_MAP = {1.0: 1.0}

ACTIVE_PIANO_TONES_MAP = {
  "mode": "full",
  "ratio_to_amplitude": {
    "0.12517239739106154": 1.2871310710906982,
    "0.20142019165228545": 1.3530174493789673,
    "1.0": 7.166596412658691,
    "1.990756859872307": 5.453855514526367,
    "3.009048340815759": 1.706058144569397,
    "4.013037016637489": 1.4692285060882568,
    "5.027287138721416": 0.7135562300682068,
    "6.065744477032464": 0.22622086107730865,
    "7.137746838349019": 0.14152146875858307,
    "8.19152528791629": 0.2609124481678009,
    "9.28392726577476": 0.10105157643556595,
    "10.391111196913263": 0.0162956602871418
  },
  "root_frequency_hz": 524.8164672851562,
  "window_duration_s": 0.2,
  "window_start_s": 0.6
}

ACTIVE_BELLS_TONES_MAP = {
  "mode": "full",
  "ratio_to_amplitude": {
    "1.0": 73.73168182373047,
    "1.9907569730128027": 81.62438201904297,
    "2.9716145551536357": 64.74060821533203,
    "3.963113411775611": 42.132293701171875,
    "4.964745528128782": 91.01268005371094,
    "5.990284269632932": 24.234329223632812,
    "6.96125866826892": 32.08193588256836,
    "7.9889817490563": 9.296048164367676,
    "8.941732722032826": 21.840566635131836,
    "9.883601723884535": 5.68519401550293,
    "10.924681330402766": 14.564982414245605,
    "11.92520031098834": 77.2205810546875,
    "12.855406629392482": 4.740595817565918,
    "13.858173399379389": 5.825884819030762,
    "14.93916037148389": 1.8241504430770874,
    "15.904120802403988": 19.095888137817383,
    "16.931410215427633": 0.9660757184028625,
    "17.800815871964282": 1.7104504108428955,
    "19.923707853862517": 1.1313793659210205,
    "22.865138360224115": 1.0612810850143433,
    "30.11487823198177": 0.07450783252716064,
    "33.70632264564371": 0.7302631139755249
  },
  "root_frequency_hz": 221.2460174560547,
  "window_duration_s": 0.2,
  "window_start_s": 0.10000000000000003
}

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
    for ratio, amp in tonesMap["ratio_to_amplitude"].items():
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
    return AdditiveInstrument(t, freq, magnitude, ACTIVE_BELLS_TONES_MAP, decay=True, decay_power=0.7)

###### REGISTRY ######

INSTRUMENTS_BY_WAVE = {
    0: Square,
    1: Triangle,
    2: Sawtooth,
    3: Piano,
    4: Bells,
}

def get_instrument(waves: int):
    return INSTRUMENTS_BY_WAVE.get(waves, Sawtooth)