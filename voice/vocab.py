"""Shared vocabulary definition for the ATC voice clip pipeline.

ORDER IS SIGNIFICANT. split_clips.py names the detected audio segments by
their position in these lists, so the ElevenLabs recording must read the
phrases in exactly this order with nothing added or skipped.
"""

# (clip_name, text_to_speak)

DIGITS = [
    ("d0", "Zero"), ("d1", "One"), ("d2", "Two"), ("d3", "Three"),
    ("d4", "Four"), ("d5", "Five"), ("d6", "Six"), ("d7", "Seven"),
    ("d8", "Eight"), ("d9", "Niner"),
]

NUMWORDS = [
    ("thousand", "Thousand"),
    ("hundred", "Hundred"),
    ("flightlevel", "Flight level"),
]

CALLSIGNS = [
    ("cs_UAL482", "United four eight two"),
    ("cs_SWA755", "Southwest seven five five"),
    ("cs_JBU631", "JetBlue six three one"),
    ("cs_DAL119", "Delta one one niner"),
    ("cs_AAL290", "American two niner zero"),
    ("cs_FDX208", "FedEx two zero eight"),
    ("cs_SKW44",  "SkyWest four four"),
    ("cs_NKS822", "Spirit eight two two"),
]

# Controller side
ATC_PHRASES = [
    ("say_alt",  "say altitude and intentions"),
    ("climb_m",  "climb and maintain"),
    ("desc_m",   "descend and maintain"),
    ("turn_l",   "turn left heading"),
    ("turn_r",   "turn right heading"),
    ("radar_ct", "radar contact"),
]

# Pilot readback side
PILOT_PHRASES = [
    ("climb_m",    "climb and maintain"),
    ("desc_m",     "descend and maintain"),
    ("left_hdg",   "left heading"),
    ("right_hdg",  "right heading"),
    ("climbing",   "climbing through"),
    ("descending", "descending through"),
    ("level",      "level"),
    ("for",        "for"),
    ("inbound",    "inbound"),
    ("departing",  "departing"),
    ("enroute",    "enroute"),
    ("ap_klas",    "Harry Reid"),
    ("ap_kvgt",    "North Las Vegas"),
]

# Nellis Control. Whole utterances, never spliced, so unlike the ATC and pilot
# vocabularies these do NOT need to match each other in delivery - which frees
# the recording to use low stability and get real emotional range.
#
# Split into two passes because the delivery is genuinely different:
# controlled command voice vs. a shouted scramble order. ElevenLabs applies
# stability to a whole generation, so one pass cannot do both well.

# Pass 1 - controlled, authoritative, unhurried. Higher stability.
NELLIS_CALM = [
    ("nl_copy",    "Nellis Control. We have your hijack code. Stand by."),
    ("nl_cleared", "Viper flight, cleared to intercept. Vectors on you now."),
    ("nl_nordo",   "Target squawking seven five zero zero. NORDO. Deviating from course."),
    ("nl_tally",   "Viper Zero One, tally the target. Closing."),
    ("nl_visual",  "Viper Zero One is visual. Cockpit unresponsive."),
    ("nl_shadow",  "Nellis has the track. Viper flight in the block, shadowing."),
    ("nl_yourtfc", "Approach, work your traffic. We have this one."),
]

# Pass 2 - shouted. Low stability, style pushed up. Caps are deliberate.
NELLIS_HOT = [
    ("nl_klaxon",   "KLAXON! KLAXON! KLAXON! ALERT FIVE — BATTLE STATIONS!"),
    ("nl_notdrill", "THIS IS NOT A DRILL! THIS IS NOT A DRILL!"),
    ("nl_scramble", "SCRAMBLE! SCRAMBLE! SCRAMBLE! DEPLOY THE FIGHTER JETS! LAUNCH! LAUNCH! LAUNCH!"),
    ("nl_hold",     "WEAPONS HOLD! REPEAT — WEAPONS HOLD!"),
]

ATC_ORDER    = CALLSIGNS + DIGITS + NUMWORDS + ATC_PHRASES
PILOT_ORDER  = CALLSIGNS + DIGITS + NUMWORDS + PILOT_PHRASES
NELLIS_ORDER = NELLIS_CALM + NELLIS_HOT
