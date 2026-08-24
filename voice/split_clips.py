"""Split a long ElevenLabs recording into individual named phrase clips.

Usage:
    python split_clips.py atc   raw/atc.wav
    python split_clips.py pilot raw/pilot.wav

    # only part of the vocabulary (for regenerating a problem section):
    python split_clips.py atc raw/digits.wav --only d0-flightlevel

Accepts WAV or MP3 (MP3 needs the `soundfile` package). The silence floor is
calibrated from the recording itself, so quiet takes no longer need the
thresholds hand-tuned. Each clip is trimmed and peak-normalized, which also
evens out TTS that speaks isolated words more softly than full phrases.
"""
import os
import sys
import wave

import numpy as np

from vocab import ATC_ORDER, PILOT_ORDER, NELLIS_ORDER

VOICES = {"atc": ATC_ORDER, "pilot": PILOT_ORDER, "nellis": NELLIS_ORDER}

HERE = os.path.dirname(os.path.abspath(__file__))

# Seconds of silence that separates two entries. Single words need a small
# value; whole sentences need a larger one, or the pause at an internal period
# splits one line into several. Override per-run with --gap.
MIN_SILENCE = 0.30
DEFAULT_GAP = {"atc": 0.30, "pilot": 0.30, "nellis": 0.80}
MIN_PHRASE = 0.08      # seconds; shorter runs are treated as clicks
PAD = 0.04             # seconds kept around each phrase
TARGET_PEAK = 0.89     # peak each written clip is normalized to
ENV_WIN = 0.02         # seconds; amplitude envelope smoothing window


def load_audio(path):
    """Return (mono float32 samples, sample rate)."""
    if path.lower().endswith(".wav"):
        with wave.open(path, "rb") as w:
            n_ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            raw = w.readframes(w.getnframes())
        dtype = {1: np.uint8, 2: "<i2", 4: "<i4"}.get(width)
        if dtype is None:
            raise SystemExit(f"unsupported sample width: {width} bytes")
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if width == 1:
            data = (data - 128.0) / 128.0
        else:
            data /= float(2 ** (8 * width - 1))
        if n_ch > 1:
            data = data.reshape(-1, n_ch).mean(axis=1)
        return data, rate

    try:
        import soundfile as sf
    except ImportError:
        raise SystemExit("non-WAV input needs: python -m pip install soundfile")
    data, rate = sf.read(path, always_2d=True, dtype="float32")
    return data.mean(axis=1), rate


def write_wav(path, samples, rate):
    peak = float(np.max(np.abs(samples))) or 1.0
    pcm = np.clip(samples * (TARGET_PEAK / peak) * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def calibrate_floor(env):
    """Pick a silence threshold from the recording's own level distribution.

    Digital silence between phrases sits orders of magnitude below even a
    softly spoken word, so the low percentile lands firmly in the silence and
    scaling it up clears the noise without reaching real speech.
    """
    noise = np.percentile(env, 20)
    speech = np.percentile(env[env > noise], 75) if (env > noise).any() else env.max()
    floor = max(noise * 8.0, speech * 0.02)
    return float(min(floor, speech * 0.25))


def find_segments(env, rate, floor):
    loud = env > floor
    if not loud.any():
        return []

    edges = np.flatnonzero(np.diff(loud.astype(np.int8)))
    bounds = np.concatenate(([0], edges + 1, [len(loud)]))

    min_sil = int(MIN_SILENCE * rate)
    segments, cur = [], None
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        if loud[s]:
            cur = s if cur is None else cur
        elif cur is not None and (e - s) >= min_sil:
            segments.append((cur, s))
            cur = None
    if cur is not None:
        segments.append((cur, len(loud)))

    min_len = int(MIN_PHRASE * rate)
    return [(s, e) for s, e in segments if (e - s) >= min_len]


def report_gaps(segments, rate, window=3):
    """Flag oversized gaps, which mean a phrase was too quiet to detect.

    Break length legitimately differs between sections of the script, so each
    gap is judged against its local neighbours rather than a global median -
    otherwise every phrase in a wider-spaced section reads as a false hit.
    """
    if len(segments) < 3:
        return []
    gaps = [(segments[i][0] - segments[i - 1][1]) / rate for i in range(1, len(segments))]

    hits = []
    for i, g in enumerate(gaps):
        lo, hi = max(0, i - window), min(len(gaps), i + window + 1)
        local = [x for j, x in enumerate(gaps[lo:hi], start=lo) if j != i]
        typical = float(np.median(local)) if local else g
        if typical > 0 and g > typical * 1.55:
            hits.append((i + 1, g, max(1, round(g / typical) - 1)))
    return hits


def resolve_order(voice, only, skip=()):
    order = VOICES[voice]
    names = [n for n, _ in order]

    if only:
        a, b = only.split("-", 1) if "-" in only else (only, only)
        if a not in names or b not in names:
            raise SystemExit(f"--only names must be from: {', '.join(names)}")
        order = order[names.index(a): names.index(b) + 1]

    if skip:
        unknown = [s for s in skip if s not in names]
        if unknown:
            raise SystemExit(f"--skip names must be from: {', '.join(names)}")
        order = [(n, t) for n, t in order if n not in skip]
    return order


def main():
    argv = sys.argv[1:]

    def flag(name):
        val = next((a.split("=", 1)[1] for a in argv if a.startswith(f"--{name}=")), None)
        if val is None and f"--{name}" in argv:
            idx = argv.index(f"--{name}")
            if idx + 1 < len(argv):
                val = argv[idx + 1]
        return val

    only, skip_raw, gap_raw = flag("only"), flag("skip"), flag("gap")
    skip = tuple(s for s in (skip_raw or "").split(",") if s)

    consumed = {only, skip_raw, gap_raw}
    args = [a for a in argv if not a.startswith("--") and a not in consumed]

    if len(args) != 2:
        raise SystemExit(__doc__)
    voice, src = args[0].lower(), args[1]
    if voice not in VOICES:
        raise SystemExit("voice must be one of: " + ", ".join(VOICES))
    if not os.path.isfile(src):
        raise SystemExit(f"no such file: {src}")

    global MIN_SILENCE
    MIN_SILENCE = float(gap_raw) if gap_raw else DEFAULT_GAP.get(voice, 0.30)

    order = resolve_order(voice, only, skip)
    if skip:
        print(f"skipping (known missing): {', '.join(skip)}")
    data, rate = load_audio(src)

    win = max(1, int(ENV_WIN * rate))
    env = np.convolve(np.abs(data), np.ones(win) / win, mode="same")
    floor = calibrate_floor(env)
    segments = find_segments(env, rate, floor)

    print(f"{os.path.basename(src)}: {len(data)/rate:.1f}s @ {rate}Hz")
    print(f"calibrated silence floor: {floor:.5f}")
    print(f"detected {len(segments)} phrases, expected {len(order)}")

    if len(segments) != len(order):
        print("\n!! Count mismatch - nothing written.")
        for idx, gap, missing in report_gaps(segments, rate):
            near = order[idx][1] if idx < len(order) else "?"
            print(f"   gap of {gap:.2f}s before segment {idx} - "
                  f"{missing} phrase(s) likely inaudible there (near \"{near}\")")
        print("\n   Detected segments:")
        for i, (s, e) in enumerate(segments):
            label = order[i][1] if i < len(order) else "???"
            print(f"     {i:3d}  {s/rate:6.2f}-{e/rate:6.2f}  "
                  f"pk={env[s:e].max():.4f}  | {label}")
        print("\n   Re-record the affected section and re-run with --only")
        return 1

    out_dir = os.path.join(HERE, "clips", voice)
    os.makedirs(out_dir, exist_ok=True)
    for (name, text), (s, e) in zip(order, segments):
        write_wav(os.path.join(out_dir, f"{name}.wav"), data[s:e], rate)
        print(f"  {name:14s} {(e-s)/rate:5.2f}s  pk={env[s:e].max():.4f}  \"{text}\"")

    print(f"\nwrote {len(order)} clips -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
