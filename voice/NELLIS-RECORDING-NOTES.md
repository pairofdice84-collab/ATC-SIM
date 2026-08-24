# Nellis Control — recording notes

Two passes, two very different deliveries. Record them separately: ElevenLabs
applies stability to a whole generation, so one setting cannot give you both a
calm command voice and a genuine shout.

---

## Voice selection

Look for a **male, American, 30s–50s** voice described as *authoritative*,
*commanding*, *narrator-deep*, or *announcer*. Military controller energy —
someone who runs a room.

**Avoid** anything tagged *narration*, *audiobook*, *soothing*, *calm*, or
*intimate*. Those voices de-emphasise and swallow shouted lines; that is
exactly what caused dropped words in the earlier ATC recordings.

If a voice sounds good but the shouted pass comes out flat, the voice itself
is the limit — pick a more dynamic one rather than fighting the settings.

---

## Pass 1 — controlled  (`nellis-1-calm.txt`, 7 lines)

Command voice. Unhurried, clipped, in charge. Not angry — this person has done
this before.

| Setting | Value |
|---|---|
| Stability | **55** |
| Similarity | 75 |
| Style exaggeration | **10** |
| Speed | **0.95** — slightly slow reads as authority |

Save as: `raw/nellis-calm.mp3`

---

## Pass 2 — shouted  (`nellis-2-hot.txt`, 4 lines)

This is the scramble order. It should be **shouted**, not read. The caps and
exclamation marks in the script are deliberate — ElevenLabs responds to them.

| Setting | Value |
|---|---|
| Stability | **35** — low is what buys emotional range |
| Similarity | 75 |
| Style exaggeration | **45** — pushes intensity |
| Speed | **1.10** — urgency |

Save as: `raw/nellis-hot.mp3`

**Why low stability here:** high stability flattens delivery toward a neutral
read. That is correct for the ATC/pilot word clips, which get spliced together
and must match each other. These lines are whole utterances played on their
own, so inconsistency between them costs nothing and range is worth everything.

**Listen before splitting.** If `SCRAMBLE!` does not sound genuinely urgent,
drop stability to 25 and regenerate. If it distorts or goes unhinged, raise to
45. This one is worth two or three attempts.

---

## Splitting

```
cd C:\Users\Junebug15\radar-sim\voice
python split_clips.py nellis raw/nellis-calm.mp3 --only nl_copy-nl_yourtfc
python split_clips.py nellis raw/nellis-hot.mp3  --only nl_klaxon-nl_hold
```

Both write into `clips/nellis/`. Expect **7** and **4** segments. A count
mismatch means a line was dropped or two ran together — the tool prints the
timings and refuses to write rather than producing misnamed clips.

---

## The lines

### Pass 1 — controlled

| Clip | Line | Fires when |
|---|---|---|
| `nl_copy` | "Nellis Control. We have your hijack code. Stand by." | you declare the hijack |
| `nl_cleared` | "Viper flight, cleared to intercept. Vectors on you now." | right after the scramble |
| `nl_nordo` | "Target squawking seven five zero zero. NORDO. Deviating from course." | during the run-in |
| `nl_tally` | "Viper Zero One, tally the target. Closing." | fighters acquire |
| `nl_visual` | "Viper Zero One is visual. Cockpit unresponsive." | on join |
| `nl_shadow` | "Nellis has the track. Viper flight in the block, shadowing." | escort established |
| `nl_yourtfc` | "Approach, work your traffic. We have this one." | handing you back |

### Pass 2 — shouted

| Clip | Line | Fires when |
|---|---|---|
| `nl_klaxon` | "KLAXON! KLAXON! KLAXON! ALERT FIVE — BATTLE STATIONS!" | scramble begins |
| `nl_notdrill` | "THIS IS NOT A DRILL! THIS IS NOT A DRILL!" | immediately after |
| `nl_scramble` | "SCRAMBLE! SCRAMBLE! SCRAMBLE! DEPLOY THE FIGHTER JETS! LAUNCH! LAUNCH! LAUNCH!" | the launch order |
| `nl_hold` | "WEAPONS HOLD! REPEAT — WEAPONS HOLD!" | on join, holding fire |

---

## A note on the phraseology

Real alert scrambles are urgent but disciplined — "SCRAMBLE" repeated three
times is authentic, and so is `WEAPONS HOLD`, which is the order that keeps a
shadowing intercept from becoming a shootdown. "Deploy the fighter jets" is
not standard USAF phrasing; it is in there because you asked for it and it
lands. If you ever want the stricter version, the realistic substitute is
"LAUNCH THE ALERT BIRDS!"
