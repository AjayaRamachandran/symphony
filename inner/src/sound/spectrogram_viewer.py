"""Generate and view a log-frequency spectrogram in pygame."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np
import pygame

try:
    from scipy.io import wavfile
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "scipy is required for reading audio. Install with: pip install scipy"
    ) from exc


MIN_FREQ_HZ = 20.0
MAX_FREQ_HZ = 22050.0
ANALYSIS_MAX_FREQ_HZ = 44100.0

# Set this to your input audio file path (.wav, .mp3, etc.).
#AUDIO_FILE_PATH = Path(r"inner\\src\\sound\\c6-piano-note.mp3")
mode = "full"
filename = "brass"

AUDIO_FILE_PATH = Path(f"inner\\src\\sound\\sources\\{filename}.mp3")
NFFT = 4096
HOP = 1024
LOG_BINS = 512
HIGH_FREQ_VISUAL_BOOST = 1.0


def output_tones_map_path(base_filename: str, root_frequency_hz: float, capture_mode: str) -> Path:
    root_freq_text = f"{root_frequency_hz:.2f}hz"
    return Path(f"inner\\src\\sound\\maps\\{base_filename}_tones_map.json")
    # return Path(f"inner\\src\\sound\\maps\\aaa\\{base_filename}_{capture_mode}_tones_map_{root_freq_text}.json")


def load_audio_mono(audio_path: Path) -> tuple[int, np.ndarray]:
    suffix = audio_path.suffix.lower()

    if suffix == ".wav":
        sample_rate, samples = wavfile.read(str(audio_path))
    else:
        # Fallback loader for compressed formats like MP3.
        try:
            librosa = importlib.import_module("librosa")
        except ImportError as exc:
            raise ImportError(
                "MP3/non-WAV input requires librosa. Install with: pip install librosa"
            ) from exc

        samples, sample_rate = librosa.load(str(audio_path), sr=None, mono=True)

    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    samples = samples.astype(np.float32)
    peak = np.max(np.abs(samples))
    if peak > 0:
        samples /= peak

    return sample_rate, samples


def compute_spectral_frames(
    samples: np.ndarray,
    sample_rate: int,
    nfft: int = 4096,
    hop: int = 1024,
    log_bins: int = 512,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(samples) < nfft:
        samples = np.pad(samples, (0, nfft - len(samples)))

    n_frames = 1 + (len(samples) - nfft) // hop
    if n_frames <= 0:
        n_frames = 1

    window = np.hanning(nfft).astype(np.float32)
    freqs_linear = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    max_analysis_hz = min(float(sample_rate) / 2.0, ANALYSIS_MAX_FREQ_HZ)
    valid = (freqs_linear >= MIN_FREQ_HZ) & (freqs_linear <= max_analysis_hz)
    freqs_band = freqs_linear[valid]

    if freqs_band.size < 2:
        raise ValueError(
            f"Input sample rate ({sample_rate} Hz) is too low for {MIN_FREQ_HZ}-{MAX_FREQ_HZ} Hz analysis."
        )

    spec_linear = np.empty((freqs_band.size, n_frames), dtype=np.float32)
    frame_times = np.empty(n_frames, dtype=np.float32)

    for idx in range(n_frames):
        start = idx * hop
        frame = samples[start : start + nfft]
        if len(frame) < nfft:
            frame = np.pad(frame, (0, nfft - len(frame)))
        fft_mag = np.abs(np.fft.rfft(frame * window))
        spec_linear[:, idx] = fft_mag[valid]
        frame_times[idx] = (start + (nfft / 2.0)) / sample_rate

    freqs_log = np.geomspace(MIN_FREQ_HZ, max_analysis_hz, num=log_bins).astype(np.float32)
    spec_log = np.empty((log_bins, n_frames), dtype=np.float32)
    for idx in range(n_frames):
        spec_log[:, idx] = np.interp(freqs_log, freqs_band, spec_linear[:, idx])

    return freqs_log, spec_log.astype(np.float32), frame_times


def average_spectrum_in_window(
    spec_log: np.ndarray,
    frame_times: np.ndarray,
    window_start_s: float,
    window_duration_s: float,
) -> np.ndarray:
    window_end_s = window_start_s + window_duration_s
    in_window = (frame_times >= window_start_s) & (frame_times <= window_end_s)

    if np.any(in_window):
        return np.mean(spec_log[:, in_window], axis=1).astype(np.float32)

    nearest_idx = int(np.argmin(np.abs(frame_times - window_start_s)))
    return spec_log[:, nearest_idx].astype(np.float32)


def normalize_amplitudes(values: np.ndarray) -> np.ndarray:
    vmax = float(np.max(values))
    if vmax <= 0:
        return np.zeros_like(values, dtype=np.float32)
    return (values / vmax).astype(np.float32)


def freq_to_x(freq_hz: float, left: int, width: int, min_freq_hz: float, max_freq_hz: float) -> int:
    log_min = np.log10(min_freq_hz)
    log_max = np.log10(max_freq_hz)
    ratio = (np.log10(freq_hz) - log_min) / (log_max - log_min)
    return int(left + width * ratio)


def x_to_freq(x: int, left: int, width: int, min_freq_hz: float, max_freq_hz: float) -> float:
    frac = np.clip((x - left) / max(width, 1), 0.0, 1.0)
    return float(min_freq_hz * ((max_freq_hz / min_freq_hz) ** frac))


def amp_to_y(amplitude: float, top: int, height: int) -> int:
    amp = float(np.clip(amplitude, 0.0, 1.0))
    return int(top + (1.0 - amp) * height)


def apply_visual_height_boost(
    amplitude: float,
    freq_hz: float,
    min_freq_hz: float,
    max_freq_hz: float,
    max_extra_scale: float,
) -> float:
    """Boost high-frequency amplitudes for drawing only."""
    if max_extra_scale <= 0.0 or max_freq_hz <= min_freq_hz:
        return float(np.clip(amplitude, 0.0, 1.0))

    log_min = np.log10(min_freq_hz)
    log_max = np.log10(max_freq_hz)
    freq_log = np.log10(np.clip(freq_hz, min_freq_hz, max_freq_hz))
    freq_ratio = float(np.clip((freq_log - log_min) / (log_max - log_min), 0.0, 1.0))
    visual_scale = 1.0 + (max_extra_scale * freq_ratio)
    return float(np.clip(amplitude * visual_scale, 0.0, 1.0))


def draw_view(
    screen: pygame.Surface,
    frequencies: np.ndarray,
    average_amplitude_norm: np.ndarray,
    hover_text: str,
    hover_freq: float | None,
    view_min_freq: float,
    view_max_freq: float,
) -> pygame.Rect:
    screen_w, screen_h = screen.get_size()
    bg_color = (18, 18, 20)
    axis_color = (230, 230, 230)
    text_color = (240, 240, 240)

    margin_left = 88
    margin_right = 32
    margin_top = 56
    margin_bottom = 72

    plot_rect = pygame.Rect(
        margin_left,
        margin_top,
        screen_w - margin_left - margin_right,
        screen_h - margin_top - margin_bottom,
    )

    screen.fill(bg_color)
    pygame.draw.rect(screen, axis_color, plot_rect, width=1)

    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 15)

    title_text = font.render(
        "Average Spectrum (100-5000 Hz, log frequency) - Hover for values",
        True,
        text_color,
    )
    screen.blit(title_text, (margin_left, 14))

    hover_surface = font.render(hover_text, True, (255, 220, 120))
    screen.blit(hover_surface, (margin_left, 34))

    x_tick_values = np.geomspace(view_min_freq, view_max_freq, num=6)
    for freq in x_tick_values:
        x = freq_to_x(float(freq), plot_rect.left, plot_rect.width, view_min_freq, view_max_freq)
        pygame.draw.line(
            screen, axis_color, (x, plot_rect.bottom), (x, plot_rect.bottom + 6), width=1
        )
        label = small_font.render(f"{int(round(float(freq)))}", True, text_color)
        screen.blit(label, (x - label.get_width() // 2, plot_rect.bottom + 10))

    y_tick_values = [0.0, 0.25, 0.5, 0.75, 1.0]
    for amp in y_tick_values:
        y = amp_to_y(amp, plot_rect.top, plot_rect.height)
        pygame.draw.line(
            screen, axis_color, (plot_rect.left - 6, y), (plot_rect.left, y), width=1
        )
        label = small_font.render(f"{amp:.2f}", True, text_color)
        screen.blit(label, (plot_rect.left - label.get_width() - 10, y - label.get_height() // 2))

    # Draw spectrum polyline.
    points: list[tuple[int, int]] = []
    mask = (frequencies >= view_min_freq) & (frequencies <= view_max_freq)
    visible_freqs = frequencies[mask]
    visible_amps_norm = average_amplitude_norm[mask]

    for freq, amp in zip(visible_freqs, visible_amps_norm):
        x = freq_to_x(
            float(freq),
            plot_rect.left,
            plot_rect.width,
            view_min_freq,
            view_max_freq,
        )
        amp_visual = apply_visual_height_boost(
            amplitude=float(amp),
            freq_hz=float(freq),
            min_freq_hz=view_min_freq,
            max_freq_hz=view_max_freq,
            max_extra_scale=HIGH_FREQ_VISUAL_BOOST,
        )
        y = amp_to_y(amp_visual, plot_rect.top, plot_rect.height)
        points.append((x, y))
    if len(points) > 1:
        pygame.draw.lines(screen, (255, 120, 60), False, points, width=2)

    if hover_freq is not None:
        hx = freq_to_x(hover_freq, plot_rect.left, plot_rect.width, view_min_freq, view_max_freq)
        pygame.draw.line(
            screen, (100, 200, 255), (hx, plot_rect.top), (hx, plot_rect.bottom), width=1
        )

    x_label = font.render("Frequency (Hz, log scale)", True, text_color)
    screen.blit(
        x_label,
        (plot_rect.centerx - x_label.get_width() // 2, screen_h - margin_bottom + 36),
    )

    y_label = font.render("Relative Amplitude", True, text_color)
    y_label_rot = pygame.transform.rotate(y_label, 90)
    screen.blit(y_label_rot, (12, plot_rect.centery - y_label_rot.get_height() // 2))

    amp_label = small_font.render("Line = Average amplitude over duration", True, text_color)
    screen.blit(amp_label, (screen_w - amp_label.get_width() - 12, 10))

    return plot_rect


def run_viewer(
    frequencies: np.ndarray,
    spec_log: np.ndarray,
    frame_times: np.ndarray,
    sample_duration_s: float,
) -> None:
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((1200, 700))
    pygame.display.set_caption("Spectrogram Viewer")

    window_duration_s = 0.2
    window_step_s = 0.1
    max_window_start = max(0.0, sample_duration_s - window_duration_s)
    window_start_s = 0.0
    average_amplitude_raw = average_spectrum_in_window(
        spec_log, frame_times, window_start_s, window_duration_s
    )
    average_amplitude_norm = normalize_amplitudes(average_amplitude_raw)
    hover_text = (
        "Move mouse over graph. Left/Right arrows shift analysis window by 0.1s."
    )
    hover_freq = None
    mode = "full"
    root_freq = None
    full_ratio_to_amp: dict[float, float] = {}
    manual_ratio_to_amp: dict[float, float] = {}
    initial_max_freq = min(MAX_FREQ_HZ, float(np.max(frequencies)))
    view_min_freq = MIN_FREQ_HZ
    view_max_freq = initial_max_freq
    plot_rect = draw_view(
        screen,
        frequencies,
        average_amplitude_norm,
        hover_text,
        hover_freq,
        view_min_freq,
        view_max_freq,
    )
    pygame.display.flip()

    clock = pygame.time.Clock()
    running = True

    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                mode = "manual" if mode == "full" else "full"
                root_freq = None
                full_ratio_to_amp.clear()
                manual_ratio_to_amp.clear()
                hover_text = (
                    f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                    f"mode={mode.upper()} | capture reset"
                )
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                root_freq = None
                full_ratio_to_amp.clear()
                manual_ratio_to_amp.clear()
                hover_text = (
                    f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                    "capture reset | click to select root"
                )
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if root_freq is None:
                    hover_text = (
                        f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                        "select root first, then press Enter to save"
                    )
                else:
                    if mode == "full":
                        ratio_to_amp = dict(sorted(full_ratio_to_amp.items()))
                    else:
                        ratio_to_amp = dict(sorted(manual_ratio_to_amp.items()))

                    output_payload = {
                        "mode": mode,
                        "root_frequency_hz": root_freq,
                        "window_start_s": float(window_start_s),
                        "window_duration_s": float(window_duration_s),
                        "ratio_to_amplitude": ratio_to_amp,
                    }
                    output_tones_file = output_tones_map_path(filename, root_freq, mode)
                    output_tones_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_tones_file, "w", encoding="utf-8") as output_file:
                        json.dump(output_payload, output_file, indent=2, sort_keys=True)

                    print("\n# Tones map saved")
                    print(f"mode = {mode}")
                    print(f"root_frequency_hz = {root_freq}")
                    print("# Copyable hashmap: key=(freq/rootfreq), value=amplitude")
                    print(ratio_to_amp)
                    print(f"# Saved tones map to file: {output_tones_file}")

                    hover_text = (
                        f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                        f"mode={mode.upper()} | saved {len(ratio_to_amp)} frequencies"
                    )
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                if event.key == pygame.K_LEFT:
                    window_start_s = max(0.0, window_start_s - window_step_s)
                else:
                    window_start_s = min(max_window_start, window_start_s + window_step_s)

                average_amplitude_raw = average_spectrum_in_window(
                    spec_log, frame_times, window_start_s, window_duration_s
                )
                average_amplitude_norm = normalize_amplitudes(average_amplitude_raw)
                root_freq = None
                full_ratio_to_amp.clear()
                manual_ratio_to_amp.clear()
                hover_text = (
                    f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                    f"mode={mode.upper()} | moved window and reset capture | click to select root"
                )

        mouse_x, mouse_y = pygame.mouse.get_pos()
        if plot_rect.collidepoint(mouse_x, mouse_y):
            freq_hz = x_to_freq(
                mouse_x,
                plot_rect.left,
                plot_rect.width,
                view_min_freq,
                view_max_freq,
            )
            freq_idx = int(np.argmin(np.abs(frequencies - freq_hz)))
            freq_exact = float(frequencies[freq_idx])
            amp = float(average_amplitude_raw[freq_idx])
            hover_freq = freq_exact
            hover_text = (
                f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                f"mode={mode.upper()} | freq={freq_exact:7.2f} Hz | amplitude={amp:7.4f}"
            )
        else:
            hover_freq = None
            hover_text = (
                f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                f"mode={mode.upper()} | Move mouse over graph. Left/Right arrows shift by 0.1s."
            )

        for event in events:
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and plot_rect.collidepoint(event.pos)
            ):
                root_candidate = x_to_freq(
                    event.pos[0],
                    plot_rect.left,
                    plot_rect.width,
                    view_min_freq,
                    view_max_freq,
                )
                root_idx = int(np.argmin(np.abs(frequencies - root_candidate)))
                clicked_freq = float(frequencies[root_idx])
                clicked_amp = float(average_amplitude_raw[root_idx])

                if root_freq is None:
                    root_freq = clicked_freq
                    full_ratio_to_amp.clear()
                    manual_ratio_to_amp.clear()

                    # Root is also a selected note at ratio 1.0.
                    if mode == "full":
                        full_ratio_to_amp[1.0] = clicked_amp
                    else:
                        manual_ratio_to_amp[1.0] = clicked_amp

                    hover_text = (
                        f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                        f"mode={mode.upper()} | root={root_freq:7.2f} Hz selected | points=1"
                    )
                else:
                    ratio = float(clicked_freq / root_freq)
                    if mode == "full":
                        full_ratio_to_amp[ratio] = clicked_amp
                        points = len(full_ratio_to_amp)
                    else:
                        manual_ratio_to_amp[ratio] = clicked_amp
                        points = len(manual_ratio_to_amp)
                    hover_text = (
                        f"window={window_start_s:4.2f}-{window_start_s + window_duration_s:4.2f}s | "
                        f"mode={mode.upper()} | root={root_freq:7.2f} Hz | points={points}"
                    )

        draw_view(
            screen,
            frequencies,
            average_amplitude_norm,
            hover_text,
            hover_freq,
            view_min_freq,
            view_max_freq,
        )
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main() -> None:
    if not AUDIO_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Audio file does not exist: {AUDIO_FILE_PATH}\n"
            "Update AUDIO_FILE_PATH in spectrogram_viewer.py"
        )

    sample_rate, samples = load_audio_mono(AUDIO_FILE_PATH)
    frequencies, spec_log, frame_times = compute_spectral_frames(
        samples=samples,
        sample_rate=sample_rate,
        nfft=NFFT,
        hop=HOP,
        log_bins=LOG_BINS,
    )
    sample_duration_s = len(samples) / float(sample_rate)
    run_viewer(
        frequencies=frequencies,
        spec_log=spec_log,
        frame_times=frame_times,
        sample_duration_s=sample_duration_s,
    )


if __name__ == "__main__":
    main()
