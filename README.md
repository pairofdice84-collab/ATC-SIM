# APPROACH

A browser-based air traffic control radar simulator built around a live
cyber-attack scenario: somewhere in the sector, one track is a **spoofed ADS-B
injection** and another is a **real aircraft being hijacked**. Telling them
apart is the exercise.

Inspired by the ADS-B security work demonstrated at the DEFCON Aerospace
Village.

![scope](https://img.shields.io/badge/radar-42_NM-25e08a) ![voice](https://img.shields.io/badge/voice-72_clips-7db8ff) ![no build](https://img.shields.io/badge/build-none-lightgrey)

---

## The problem it poses

ADS-B has no authentication. Any transmitter can broadcast any position under
any identity, and every receiver on the network will display it as fact. That
is not a bug in this simulator — it is the real protocol.

So the scope shows you two anomalies that look superficially similar and are
nothing alike:

|  | 👻 Spoofed track | 🆘 Hijacked aircraft |
| --- | --- | --- |
| Altitude | steps 2,000–4,000 ft **between sweeps** | smooth, ~1,800 fpm |
| Implied vertical rate | 100,000+ fpm — impossible | normal |
| Primary radar | **decorrelates** from the datablock | **correlates perfectly** |
| Squawk | invalid octal (8/9) or duplicated | valid, then **7500** |
| Radio | dead air, always | answers, then goes NORDO |
| What's wrong | no aircraft exists | the aircraft is real, the *intent* isn't |

**A spoof breaks physics. A hijack breaks the clearance.**

The discriminator is primary radar. Skin paint doesn't care what a transponder
claims — everything else on the datablock is Mode C, reported by the aircraft
itself, and therefore forgeable. Misclassify and you pay for it: scramble
fighters at the ghost and the real threat keeps flying at the Strip.

Meanwhile traffic keeps calling for clearances on a 42-second timer. The
emergency does not wait for you to work the routine traffic.

---

## Running it

Clips are fetched over HTTP, so this needs a server — opening `index.html`
from disk falls back to synthesized speech.

```bash
python serve.py 8000
```

Then open <http://localhost:8000>. No build step, no dependencies for the sim
itself.

---

## Controls

| | |
| --- | --- |
| Click a target | select it |
| `SPACE` | pause |
| `1× / 2× / 4×` | time compression |
| Hold `T` | push-to-talk (needs https or localhost) |
| `☰ COMMANDS` | full briefing, including how to read altitude |

Target panel shows `PRIMARY` (correlated / NM off) and `VERT RATE` — the two
numbers that settle ghost vs. real.

---

## Voice

Transmissions are spliced from pre-rendered word clips and run through a
WebAudio chain that models a VHF air-band radio — band-limited, driven,
hard-limited, with PTT clicks and squelch tails. Three speakers, three
profiles:

| Voice | Character |
| --- | --- |
| Controller | 280–3200 Hz, moderate drive |
| Cockpit | 380–2600 Hz, narrower and grittier |
| Nellis Control | 420–2900 Hz, hardest clipping — cuts across the civilian frequency |

This is why the clips exist at all: browser `speechSynthesis` output cannot be
routed into WebAudio, so it can only ever have noise layered *around* it.
Decoded audio buffers can be filtered like any other signal.

### Rebuilding the voice

`voice/` holds the whole pipeline. Generate the scripts, record each as one
long take with `<break>` tags between phrases, then split:

```bash
cd voice
python make_scripts.py                              # writes the scripts to record
python split_clips.py atc    raw/atc.mp3            # cut into named clips
python split_clips.py pilot  raw/pilot.mp3
python split_clips.py nellis raw/nellis-calm.mp3 --only nl_copy-nl_yourtfc
python split_clips.py nellis raw/nellis-hot.mp3  --only nl_klaxon-nl_hold
```

The splitter calibrates its silence floor from the recording itself, reports
which phrase a synthesis engine dropped when the count is short, and refuses
to write rather than producing misnamed clips. `--gap` tunes the phrase
separator (whole sentences need more than single words); `--skip` accepts a
known-missing entry; `--only` re-cuts one section.

See `voice/NELLIS-RECORDING-NOTES.md` for voice selection and settings —
notably that spliced word clips want *high* stability for consistency, while
whole shouted lines want *low* stability for range.

---

## Layout

```
index.html              sim, render loop, scenario
serve.py                local dev server (no-cache)
voice/
  radio.js              clip loading, splicing, VHF signal chain
  phraseology.js        sim state -> ordered clip names
  vocab.py              the recorded vocabulary (order is significant)
  make_scripts.py       generates recording scripts
  split_clips.py        cuts a long take into named clips
  clips/{atc,pilot,nellis}/
```

---

Built with [Claude Code](https://claude.com/claude-code).
