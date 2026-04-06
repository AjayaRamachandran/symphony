"""Generate and view a linear-frequency spectral map in pygame."""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pygame

try:
    from scipy.io import wavfile
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "scipy is required for reading audio. Install with: pip install scipy"
    ) from exc


MIN_FREQ_HZ = 100.0
MAX_FREQ_HZ = 5000.0
ANALYSIS_MAX_FREQ_HZ = 5000.0

# Set this to your input audio file path (.wav, .mp3, etc.).
# AUDIO_FILE_PATH = Path(r"inner\\src\\sound\\c6-piano-note.mp3")
mode = "full"
filename = "piano"

AUDIO_FILE_PATH = Path(f"inner\\src\\sound\\sources\\{filename}.mp3")
NFFT = 4096
HOP = 256


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


def compute_linear_spectral_frames(
    samples: np.ndarray,
    sample_rate: int,
    nfft: int = 4096,
    hop: int = 1024,
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

    return freqs_band.astype(np.float32), spec_linear.astype(np.float32), frame_times


def normalize_spectrogram(spec_linear: np.ndarray) -> np.ndarray:
    # Log compression helps reveal weaker content in the color map.
    eps = 1e-10
    spec_db = 20.0 * np.log10(np.maximum(spec_linear, eps))
    low = float(np.percentile(spec_db, 5.0))
    high = float(np.percentile(spec_db, 99.5))
    if high <= low:
        return np.zeros_like(spec_linear, dtype=np.float32)
    spec_norm = (spec_db - low) / (high - low)
    return np.clip(spec_norm, 0.0, 1.0).astype(np.float32)


def x_to_time(x: int, left: int, width: int, total_duration_s: float) -> float:
    frac = np.clip((x - left) / max(width, 1), 0.0, 1.0)
    return float(frac * total_duration_s)


def y_to_freq(y: int, top: int, height: int, min_freq_hz: float, max_freq_hz: float) -> float:
    frac = np.clip((y - top) / max(height, 1), 0.0, 1.0)
    return float(max_freq_hz - frac * (max_freq_hz - min_freq_hz))


def time_to_x(time_s: float, left: int, width: int, total_duration_s: float) -> int:
    if total_duration_s <= 0.0:
        return left
    frac = np.clip(time_s / total_duration_s, 0.0, 1.0)
    return int(left + frac * width)


def freq_to_y(freq_hz: float, top: int, height: int, min_freq_hz: float, max_freq_hz: float) -> int:
    if max_freq_hz <= min_freq_hz:
        return top + height
    frac = np.clip((freq_hz - min_freq_hz) / (max_freq_hz - min_freq_hz), 0.0, 1.0)
    return int(top + (1.0 - frac) * height)


def build_heatmap_surface(
    spec_norm: np.ndarray, plot_width: int, plot_height: int
) -> pygame.Surface:
    n_freqs, n_frames = spec_norm.shape
    out_w = max(plot_width, 1)
    out_h = max(plot_height, 1)

    # Bilinear interpolation for smooth visual scaling.
    x_pos = np.linspace(0.0, float(n_frames - 1), num=out_w, dtype=np.float32)
    y_pos = np.linspace(float(n_freqs - 1), 0.0, num=out_h, dtype=np.float32)
    x0 = np.floor(x_pos).astype(np.int32)
    y0 = np.floor(y_pos).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, n_frames - 1)
    y1 = np.clip(y0 + 1, 0, n_freqs - 1)
    wx = (x_pos - x0)[None, :]
    wy = (y_pos - y0)[:, None]

    a = spec_norm[y0[:, None], x0[None, :]]
    b = spec_norm[y0[:, None], x1[None, :]]
    c = spec_norm[y1[:, None], x0[None, :]]
    d = spec_norm[y1[:, None], x1[None, :]]
    sampled = ((1.0 - wx) * (1.0 - wy) * a) + (wx * (1.0 - wy) * b) + ((1.0 - wx) * wy * c) + (wx * wy * d)

    # Dark blue -> blue -> cyan -> yellow -> warm highlights.
    stops = np.array([0.0, 0.30, 0.60, 0.85, 1.0], dtype=np.float32)
    reds = np.array([8, 30, 60, 255, 255], dtype=np.float32)
    greens = np.array([8, 60, 200, 220, 80], dtype=np.float32)
    blues = np.array([18, 180, 255, 80, 60], dtype=np.float32)

    r = np.interp(sampled, stops, reds).astype(np.uint8)
    g = np.interp(sampled, stops, greens).astype(np.uint8)
    b = np.interp(sampled, stops, blues).astype(np.uint8)

    rgb = np.dstack([r, g, b])
    # surfarray expects shape (width, height, channels).
    rgb_for_surface = np.transpose(rgb, (1, 0, 2))
    return pygame.surfarray.make_surface(rgb_for_surface)


def sample_interpolated_value(spec: np.ndarray, freq_pos: float, frame_pos: float) -> float:
    n_freqs, n_frames = spec.shape
    x0 = int(np.floor(frame_pos))
    y0 = int(np.floor(freq_pos))
    x0 = int(np.clip(x0, 0, n_frames - 1))
    y0 = int(np.clip(y0, 0, n_freqs - 1))
    x1 = min(x0 + 1, n_frames - 1)
    y1 = min(y0 + 1, n_freqs - 1)
    wx = float(np.clip(frame_pos - x0, 0.0, 1.0))
    wy = float(np.clip(freq_pos - y0, 0.0, 1.0))
    return float(
        ((1.0 - wx) * (1.0 - wy) * spec[y0, x0])
        + (wx * (1.0 - wy) * spec[y0, x1])
        + ((1.0 - wx) * wy * spec[y1, x0])
        + (wx * wy * spec[y1, x1])
    )


def print_frequency_time_slice_csv(
    clicked_freq_hz: float,
    frequencies: np.ndarray,
    frame_times: np.ndarray,
    spec_linear: np.ndarray,
) -> None:
    freq_pos = float(np.interp(clicked_freq_hz, frequencies, np.arange(frequencies.size)))
    print(f"\n# clicked_freq_hz={clicked_freq_hz:.2f}")
    print("# time_s,amplitude")
    for t in np.arange(0.0, 1.0 + 1e-9, 0.1):
        t_eval = float(np.clip(t, float(frame_times[0]), float(frame_times[-1])))
        frame_pos = float(np.interp(t_eval, frame_times, np.arange(frame_times.size)))
        amplitude = sample_interpolated_value(spec_linear, freq_pos=freq_pos, frame_pos=frame_pos)
        print(f"{t:.1f},{amplitude:.6f}")


def draw_view(
    screen: pygame.Surface,
    heatmap_surface: pygame.Surface,
    hover_text: str,
    hover_x: int | None,
    hover_y: int | None,
    sample_duration_s: float,
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
        max(10, screen_w - margin_left - margin_right),
        max(10, screen_h - margin_top - margin_bottom),
    )

    screen.fill(bg_color)
    screen.blit(heatmap_surface, plot_rect.topleft)
    pygame.draw.rect(screen, axis_color, plot_rect, width=1)

    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 15)

    title_text = font.render(
        "Spectral Map (100-5000 Hz, linear frequency) - Hover for values",
        True,
        text_color,
    )
    screen.blit(title_text, (margin_left, 14))

    hover_surface = font.render(hover_text, True, (255, 220, 120))
    screen.blit(hover_surface, (margin_left, 34))

    x_tick_count = 7
    for idx in range(x_tick_count):
        frac = idx / max(x_tick_count - 1, 1)
        tick_time = frac * sample_duration_s
        x = int(plot_rect.left + frac * plot_rect.width)
        pygame.draw.line(
            screen, axis_color, (x, plot_rect.bottom), (x, plot_rect.bottom + 6), width=1
        )
        label = small_font.render(f"{tick_time:0.1f}s", True, text_color)
        screen.blit(label, (x - label.get_width() // 2, plot_rect.bottom + 10))

    y_tick_values = [100, 500, 1000, 2000, 3000, 4000, 5000]
    for freq in y_tick_values:
        y = freq_to_y(float(freq), plot_rect.top, plot_rect.height, view_min_freq, view_max_freq)
        pygame.draw.line(
            screen, axis_color, (plot_rect.left - 6, y), (plot_rect.left, y), width=1
        )
        label = small_font.render(f"{freq}", True, text_color)
        screen.blit(label, (plot_rect.left - label.get_width() - 10, y - label.get_height() // 2))

    if hover_x is not None and hover_y is not None:
        pygame.draw.line(
            screen, (100, 200, 255), (hover_x, plot_rect.top), (hover_x, plot_rect.bottom), width=1
        )
        pygame.draw.line(
            screen, (100, 200, 255), (plot_rect.left, hover_y), (plot_rect.right, hover_y), width=1
        )

    x_label = font.render("Time elapsed (s)", True, text_color)
    screen.blit(
        x_label,
        (plot_rect.centerx - x_label.get_width() // 2, screen_h - margin_bottom + 36),
    )

    y_label = font.render("Frequency (Hz, linear scale)", True, text_color)
    y_label_rot = pygame.transform.rotate(y_label, 90)
    screen.blit(y_label_rot, (12, plot_rect.centery - y_label_rot.get_height() // 2))

    return plot_rect


def run_viewer(
    frequencies: np.ndarray,
    spec_linear: np.ndarray,
    spec_norm: np.ndarray,
    frame_times: np.ndarray,
    sample_duration_s: float,
) -> None:
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((1200, 700))
    pygame.display.set_caption("Spectral Map Viewer")

    view_min_freq = MIN_FREQ_HZ
    view_max_freq = min(MAX_FREQ_HZ, float(np.max(frequencies)))

    # Build once and reuse until window size changes.
    screen_w, screen_h = screen.get_size()
    margin_left = 88
    margin_right = 32
    margin_top = 56
    margin_bottom = 72
    plot_width = max(10, screen_w - margin_left - margin_right)
    plot_height = max(10, screen_h - margin_top - margin_bottom)
    heatmap_surface = build_heatmap_surface(spec_norm, plot_width, plot_height)

    hover_text = "Move mouse over graph to read elapsed time, frequency, and amplitude."
    hover_x = None
    hover_y = None

    clock = pygame.time.Clock()
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        plot_rect = draw_view(
            screen=screen,
            heatmap_surface=heatmap_surface,
            hover_text=hover_text,
            hover_x=hover_x,
            hover_y=hover_y,
            sample_duration_s=sample_duration_s,
            view_min_freq=view_min_freq,
            view_max_freq=view_max_freq,
        )

        mouse_x, mouse_y = pygame.mouse.get_pos()
        if plot_rect.collidepoint(mouse_x, mouse_y):
            # Pixel-accurate sample position in spectrogram index space.
            mouse_x_local = mouse_x - plot_rect.left
            mouse_y_local = mouse_y - plot_rect.top
            x_frac = np.clip(mouse_x_local / max(plot_rect.width - 1, 1), 0.0, 1.0)
            y_frac = np.clip(mouse_y_local / max(plot_rect.height - 1, 1), 0.0, 1.0)
            frame_pos = x_frac * max(spec_linear.shape[1] - 1, 0)
            freq_pos = (1.0 - y_frac) * max(spec_linear.shape[0] - 1, 0)

            amp_raw = sample_interpolated_value(spec_linear, freq_pos=freq_pos, frame_pos=frame_pos)
            amp_norm = sample_interpolated_value(spec_norm, freq_pos=freq_pos, frame_pos=frame_pos)

            time_exact = float(np.interp(frame_pos, np.arange(frame_times.size), frame_times))
            freq_exact = float(np.interp(freq_pos, np.arange(frequencies.size), frequencies))

            hover_x = mouse_x
            hover_y = mouse_y
            hover_text = (
                f"time elapsed={time_exact:7.3f} s | "
                f"freq={freq_exact:7.2f} Hz | "
                f"amplitude={amp_raw:9.4f} | "
                f"heat={amp_norm:5.3f}"
            )
        else:
            hover_x = None
            hover_y = None
            hover_text = "Move mouse over graph to read elapsed time, frequency, and amplitude."

        for event in events:
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and plot_rect.collidepoint(event.pos)
            ):
                click_y_local = event.pos[1] - plot_rect.top
                y_frac = np.clip(click_y_local / max(plot_rect.height - 1, 1), 0.0, 1.0)
                freq_pos = (1.0 - y_frac) * max(spec_linear.shape[0] - 1, 0)
                clicked_freq_hz = float(np.interp(freq_pos, np.arange(frequencies.size), frequencies))
                print_frequency_time_slice_csv(
                    clicked_freq_hz=clicked_freq_hz,
                    frequencies=frequencies,
                    frame_times=frame_times,
                    spec_linear=spec_linear,
                )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main() -> None:
    if not AUDIO_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Audio file does not exist: {AUDIO_FILE_PATH}\n"
            "Update AUDIO_FILE_PATH in spectral_map_viewer.py"
        )

    sample_rate, samples = load_audio_mono(AUDIO_FILE_PATH)
    frequencies, spec_linear, frame_times = compute_linear_spectral_frames(
        samples=samples,
        sample_rate=sample_rate,
        nfft=NFFT,
        hop=HOP,
    )
    spec_norm = normalize_spectrogram(spec_linear)
    sample_duration_s = len(samples) / float(sample_rate)
    run_viewer(
        frequencies=frequencies,
        spec_linear=spec_linear,
        spec_norm=spec_norm,
        frame_times=frame_times,
        sample_duration_s=sample_duration_s,
    )


if __name__ == "__main__":
    main()
