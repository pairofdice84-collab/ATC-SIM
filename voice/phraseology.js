/* Turns simulator state into ordered clip names for RADIO.transmit().
 *
 * Mirrors the text phraseology the comms log already prints, so what is heard
 * and what is written stay in step.
 */
const PHRASE = (function () {
  'use strict';

  // KPHX has no recorded name clip yet, so position reports for Phoenix
  // traffic simply omit the field rather than leaving a silent gap.
  const AIRPORT_CLIP = { KLAS: 'ap_klas', KVGT: 'ap_kvgt' };
  const airportClips = (id) => (AIRPORT_CLIP[id] ? [AIRPORT_CLIP[id]] : []);

  const digitClips = (n) => String(n).split('').map((d) => 'd' + d);

  /** Heading is always spoken as three digits: 90 -> "zero niner zero". */
  const headingClips = (h) =>
    digitClips(String(Math.round(h)).padStart(3, '0'));

  /** Altitude, matching altWords(): flight levels above 18000, else thousands. */
  function altitudeClips(ft) {
    ft = Math.round(ft / 100) * 100;
    if (ft >= 18000) return ['flightlevel'].concat(digitClips(ft / 100));

    const thousands = Math.floor(ft / 1000);
    const hundreds = (ft % 1000) / 100;
    let out = [];
    if (thousands) out = out.concat(digitClips(thousands), ['thousand']);
    if (hundreds) out = out.concat(['d' + hundreds, 'hundred']);
    return out.length ? out : ['d0'];
  }

  const callsignClip = (p) => 'cs_' + p.cs.trim();

  /** Where the aircraft is in its flight, as the pilot would report it. */
  function positionClips(p) {
    if (p.phase === 'ARRIVING') return ['inbound'].concat(airportClips(p.dest));
    if (p.phase === 'DEPARTING') return ['departing'].concat(airportClips(p.origin));
    return ['enroute'].concat(airportClips(p.dest));
  }

  /** Controller instruction. Call after the target alt/heading is updated. */
  function atc(p, action) {
    const cs = callsignClip(p);
    switch (action) {
      case 'query':   return [cs, 'say_alt'];
      case 'climb':   return [cs, 'climb_m'].concat(altitudeClips(p.tAlt));
      case 'descend': return [cs, 'desc_m'].concat(altitudeClips(p.tAlt));
      case 'left':    return [cs, 'turn_l'].concat(headingClips(p.tHdg));
      case 'right':   return [cs, 'turn_r'].concat(headingClips(p.tHdg));
      default:        return null;
    }
  }

  /** Pilot readback. Readbacks end with the callsign, as on a real frequency. */
  function pilot(p, action) {
    const cs = callsignClip(p);
    switch (action) {
      case 'query': {
        if (p.alt < p.tAlt) {
          return [cs, 'climbing']
            .concat(altitudeClips(p.alt), ['for'], altitudeClips(p.tAlt), positionClips(p));
        }
        if (p.alt > p.tAlt) {
          return [cs, 'descending'].concat(altitudeClips(p.alt), positionClips(p));
        }
        return [cs, 'level'].concat(altitudeClips(p.alt), positionClips(p));
      }
      case 'climb':   return ['climb_m'].concat(altitudeClips(p.tAlt), [cs]);
      case 'descend': return ['desc_m'].concat(altitudeClips(p.tAlt), [cs]);
      case 'left':    return ['left_hdg'].concat(headingClips(p.tHdg), [cs]);
      case 'right':   return ['right_hdg'].concat(headingClips(p.tHdg), [cs]);
      default:        return null;
    }
  }

  /** Nellis lines, in the order the intercept plays them. */
  const NELLIS = {
    copy: 'nl_copy', cleared: 'nl_cleared', nordo: 'nl_nordo',
    tally: 'nl_tally', visual: 'nl_visual', shadow: 'nl_shadow',
    yourtfc: 'nl_yourtfc',
    klaxon: 'nl_klaxon', notdrill: 'nl_notdrill',
    scramble: 'nl_scramble', hold: 'nl_hold',
  };

  /** Every clip name the engine may need, for preloading. */
  function manifest(planes) {
    const digits = ['d0','d1','d2','d3','d4','d5','d6','d7','d8','d9'];
    const nums = ['thousand', 'hundred', 'flightlevel'];
    const callsigns = planes.map(callsignClip);
    return {
      atc: callsigns.concat(digits, nums,
        ['say_alt', 'climb_m', 'desc_m', 'turn_l', 'turn_r', 'radar_ct']),
      pilot: callsigns.concat(digits, nums,
        ['climb_m', 'desc_m', 'left_hdg', 'right_hdg', 'climbing', 'descending',
         'level', 'for', 'inbound', 'departing', 'enroute', 'ap_klas', 'ap_kvgt']),
      nellis: Object.values(NELLIS),
    };
  }

  return { atc, pilot, manifest, altitudeClips, headingClips, NELLIS };
})();
