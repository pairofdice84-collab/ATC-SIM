"""Writes the text scripts to paste into ElevenLabs.

Each phrase is followed by an explicit break tag so the splitter has a clean,
unambiguous silence to cut on.

Every phrase is terminated with a period. Without it the engine reads short
entries as trailing sentence fragments and de-emphasizes them, which made
isolated digits come out too quiet to detect at all.
"""
import io
import os

from vocab import (ATC_ORDER, PILOT_ORDER, NELLIS_CALM, NELLIS_HOT,
                   DIGITS, NUMWORDS)

BREAK = '<break time="1.5s" />'
HERE = os.path.dirname(os.path.abspath(__file__))


def write_script(order, filename, label):
    path = os.path.join(HERE, filename)
    lines = []
    for _name, text in order:
        spoken = text if text.rstrip().endswith((".", "?", "!")) else text + "."
        lines.append(f"{spoken} {BREAK}")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{label}: {len(order)} phrases -> {filename}")


write_script(ATC_ORDER, "atc-script.txt", "ATC voice")
write_script(PILOT_ORDER, "pilot-script.txt", "PILOT voice")
write_script(NELLIS_CALM, "nellis-1-calm.txt", "NELLIS pass 1 (controlled)")
write_script(NELLIS_HOT, "nellis-2-hot.txt", "NELLIS pass 2 (shouted)")

# Short re-record covering just the section that tends to drop out, so a
# problem run can be patched with --only instead of regenerating everything.
write_script(DIGITS + NUMWORDS, "digits-script.txt", "DIGITS patch")
