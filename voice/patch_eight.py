"""Recover a single usable "Eight" clip for the ATC voice.

The bare word kept getting dropped by the narration voice, so eight-patch.txt
offers it five ways. Run:

    python patch_eight.py raw/atc-eight.mp3

Takes 0 and 1 in that script are the bare word; the rest are fallbacks that
only get used if both bare takes failed to render. The chosen take is
tight-trimmed, because a trailing pause inflates an isolated word well beyond
the length of the digits it will be spliced against.
"""
import glob
import os
import sys
import wave

import numpy as np

from split_clips import (
    load_audio, calibrate_floor, find_segments, write_wav, ENV_WIN,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# Positions in eight-patch.txt, best first. The bare renderings splice most
# cleanly; "Number eight" / "Eight thousand" carry a neighbouring word and are
# only worth cutting into if the bare takes came out silent.
BARE_TAKES = (0, 1)
TRIM_REL = 0.06   # fraction of peak below which trailing audio is dropped
TRIM_PAD = 0.03   # seconds kept after the last loud sample


def tight_trim(seg, env_seg, rate):
    """Drop leading/trailing near-silence that padding pulled in."""
    thr = env_seg.max() * TRIM_REL
    loud = np.flatnonzero(env_seg > thr)
    if loud.size == 0:
        return seg
    pad = int(TRIM_PAD * rate)
    a = max(0, loud[0] - pad)
    b = min(len(seg), loud[-1] + pad)
    return seg[a:b]


def existing_digit_range():
    durs = []
    for f in glob.glob(os.path.join(HERE, "clips", "atc", "d?.wav")):
        with wave.open(f, "rb") as w:
            durs.append(w.getnframes() / w.getframerate())
    return (min(durs), max(durs)) if durs else None


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python patch_eight.py <recording>")
    src = sys.argv[1]
    if not os.path.isfile(src):
        raise SystemExit(f"no such file: {src}")

    data, rate = load_audio(src)
    win = max(1, int(ENV_WIN * rate))
    env = np.convolve(np.abs(data), np.ones(win) / win, mode="same")
    segments = find_segments(env, rate, calibrate_floor(env))
    if not segments:
        raise SystemExit("no audio detected - the voice dropped every take")

    print(f"{os.path.basename(src)}: {len(data)/rate:.1f}s, {len(segments)} take(s)")

    best, best_peak, best_idx = None, -1.0, None
    for i in BARE_TAKES:
        if i >= len(segments):
            continue
        s, e = segments[i]
        clip = tight_trim(data[s:e], env[s:e], rate)
        peak = float(np.max(np.abs(clip)))
        print(f"  take {i}: {(e-s)/rate:.3f}s raw -> {len(clip)/rate:.3f}s trimmed, pk={peak:.4f}")
        if peak > best_peak:
            best, best_peak, best_idx = clip, peak, i

    if best is None:
        raise SystemExit("both bare takes are missing - re-record eight-patch.txt")

    dur = len(best) / rate
    rng = existing_digit_range()
    if rng:
        print(f"\nother ATC digits run {rng[0]:.3f}-{rng[1]:.3f}s; this is {dur:.3f}s")
        if dur > rng[1] * 2.2:
            print("  note: noticeably longer than its neighbours - listen before committing")

    out = os.path.join(HERE, "clips", "atc", "d8.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_wav(out, best, rate)
    print(f"\nwrote {out} from take {best_idx} ({dur:.3f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
