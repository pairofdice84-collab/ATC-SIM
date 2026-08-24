/* Radio voice engine.
 *
 * Plays transmissions by splicing pre-rendered ElevenLabs word clips and
 * running them through a WebAudio chain that models a VHF air-band radio.
 *
 * This is the whole reason for the clip pipeline: speechSynthesis output
 * cannot be routed into WebAudio, so the previous version could only layer
 * hiss *around* the voice. Decoded AudioBuffers can be filtered, driven and
 * compressed like any other signal, so the radio character is applied to the
 * voice itself.
 *
 * Requires the page to be served over http - clips are fetched, so file://
 * will not work.
 */
const RADIO = (function () {
  'use strict';

  const CLIP_BASE = 'voice/clips';

  // Per-voice signal character. The controller sits on a ground transmitter
  // with a decent antenna; the aircraft is a noisier, narrower cockpit rig.
  const PROFILES = {
    atc: {
      hp: 280, lp: 3200, presence: 1800, presenceGain: 5.0,
      drive: 1.8, gain: 1.00, noise: 0.020,
    },
    pilot: {
      hp: 380, lp: 2600, presence: 1600, presenceGain: 7.0,
      drive: 3.0, gain: 1.10, noise: 0.034,
    },
    // Military UHF landline: hardest-clipped and hottest of the three, so
    // Nellis cuts across the civilian frequency rather than blending with it.
    nellis: {
      hp: 420, lp: 2900, presence: 2000, presenceGain: 8.5,
      drive: 4.2, gain: 1.18, noise: 0.030,
    },
  };

  // Timing is the difference between "spliced words" and "someone talking".
  // Digits inside one number run together the way a controller says
  // "two eight three"; the pause goes between units instead.
  const timing = {
    digitGap: 0.085,   // between consecutive digits of the same number
    unitGap: 0.190,    // between phrase units (callsign | instruction | value)
    leadIn: 0.140,     // carrier open before the first word
    tail: 0.180,       // carrier held after the last word
    rate: 1.0,         // clip playback rate; below 1 also lowers pitch
  };

  const isDigit = (name) => /^d\d$/.test(name);

  /** Pause to insert after clip `i` of `names`. */
  function gapAfter(names, i) {
    const cur = names[i];
    const next = names[i + 1];
    if (next === undefined) return 0;
    // A run of digits is one spoken number - keep it tight.
    if (isDigit(cur) && isDigit(next)) return timing.digitGap;
    return timing.unitGap;
  }

  let ctx = null;
  const clips = { atc: {}, pilot: {}, nellis: {} };
  let noiseBuffer = null;
  let ready = false;
  let enabled = true;

  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }

  /* ---------- loading ---------- */

  async function fetchClip(voice, name) {
    const res = await fetch(`${CLIP_BASE}/${voice}/${name}.wav`);
    if (!res.ok) throw new Error(`${voice}/${name}: HTTP ${res.status}`);
    return getCtx().decodeAudioData(await res.arrayBuffer());
  }

  async function load(manifest, onProgress) {
    const jobs = [];
    for (const voice of Object.keys(manifest)) {
      for (const name of manifest[voice]) {
        jobs.push(
          fetchClip(voice, name)
            .then((buf) => { clips[voice][name] = buf; })
            .catch((err) => { console.warn('clip failed:', err.message); })
        );
      }
    }
    let done = 0;
    const total = jobs.length;
    jobs.forEach((j) => j.then(() => onProgress && onProgress(++done, total)));
    await Promise.all(jobs);

    const a = getCtx();
    noiseBuffer = a.createBuffer(1, a.sampleRate * 2, a.sampleRate);
    const nd = noiseBuffer.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;

    ready = true;
    return { loaded: Object.values(clips).reduce((n, o) => n + Object.keys(o).length, 0), total };
  }

  /* ---------- signal chain ---------- */

  function softClipCurve(k) {
    const n = 1024;
    const curve = new Float32Array(n);
    const norm = Math.tanh(k);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1;
      curve[i] = Math.tanh(x * k) / norm;
    }
    return curve;
  }

  function buildChain(a, p) {
    const hp = a.createBiquadFilter();
    hp.type = 'highpass'; hp.frequency.value = p.hp;

    const presence = a.createBiquadFilter();
    presence.type = 'peaking';
    presence.frequency.value = p.presence;
    presence.Q.value = 1.2;
    presence.gain.value = p.presenceGain;

    const lp = a.createBiquadFilter();
    lp.type = 'lowpass'; lp.frequency.value = p.lp;

    const shaper = a.createWaveShaper();
    shaper.curve = softClipCurve(p.drive);
    shaper.oversample = '4x';

    // Heavy limiting is what gives radio speech its flat, always-loud quality.
    const comp = a.createDynamicsCompressor();
    comp.threshold.value = -24;
    comp.knee.value = 6;
    comp.ratio.value = 12;
    comp.attack.value = 0.003;
    comp.release.value = 0.12;

    const out = a.createGain();
    out.gain.value = p.gain;

    hp.connect(presence).connect(lp).connect(shaper).connect(comp).connect(out);
    return { input: hp, output: out };
  }

  /* ---------- one-shot effects ---------- */

  function keyClick(a, at, dest) {
    const osc = a.createOscillator();
    const g = a.createGain();
    osc.type = 'square';
    osc.frequency.value = 1200;
    g.gain.setValueAtTime(0.13, at);
    g.gain.exponentialRampToValueAtTime(0.001, at + 0.03);
    osc.connect(g).connect(dest);
    osc.start(at);
    osc.stop(at + 0.035);
  }

  function squelch(a, at, dest) {
    const src = a.createBufferSource();
    src.buffer = noiseBuffer;
    const bp = a.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = 1700; bp.Q.value = 0.9;
    const g = a.createGain();
    g.gain.setValueAtTime(0.22, at);
    g.gain.exponentialRampToValueAtTime(0.001, at + 0.07);
    src.connect(bp).connect(g).connect(dest);
    src.start(at, Math.random() * 1.5, 0.09);
  }

  /* ---------- transmission ---------- */

  /** Lay out the clips on a timeline: [{buf, offset}], plus total length. */
  function schedule(voice, names) {
    const present = names.filter((n) => clips[voice][n]);
    const items = [];
    let t = 0;
    present.forEach((name, i) => {
      const buf = clips[voice][name];
      items.push({ buf, offset: t });
      t += buf.duration / timing.rate + gapAfter(present, i);
    });
    return { items, duration: t };
  }

  /**
   * Play a sequence of clip names as one keyed transmission.
   * Resolves when the carrier drops.
   */
  function transmit(voice, names) {
    if (!enabled || !ready) return Promise.resolve();
    const a = getCtx();
    if (a.state === 'suspended') a.resume();

    const profile = PROFILES[voice] || PROFILES.atc;
    const chain = buildChain(a, profile);
    chain.output.connect(a.destination);

    const start = a.currentTime + 0.05;
    const plan = schedule(voice, names);
    if (plan.duration <= 0) return Promise.resolve();
    const end = start + timing.leadIn + plan.duration + timing.tail;

    // Dry effects bypass the voice chain so the click stays crisp.
    keyClick(a, start, a.destination);
    squelch(a, start + 0.02, a.destination);

    // Carrier hiss for the length of the transmission.
    const hiss = a.createBufferSource();
    hiss.buffer = noiseBuffer;
    hiss.loop = true;
    const hissBp = a.createBiquadFilter();
    hissBp.type = 'bandpass';
    hissBp.frequency.value = profile.presence;
    hissBp.Q.value = 0.5;
    const hissGain = a.createGain();
    hissGain.gain.setValueAtTime(0.0001, start);
    hissGain.gain.exponentialRampToValueAtTime(profile.noise, start + 0.04);
    hissGain.gain.setValueAtTime(profile.noise, end - 0.05);
    hissGain.gain.exponentialRampToValueAtTime(0.0001, end);
    hiss.connect(hissBp).connect(hissGain).connect(a.destination);
    hiss.start(start);
    hiss.stop(end + 0.05);

    const speechStart = start + timing.leadIn;
    plan.items.forEach(({ buf, offset }) => {
      const src = a.createBufferSource();
      src.buffer = buf;
      src.playbackRate.value = timing.rate;
      src.connect(chain.input);
      src.start(speechStart + offset);
    });

    squelch(a, end, a.destination);

    return new Promise((resolve) => {
      setTimeout(() => {
        try { chain.output.disconnect(); } catch (e) { /* already gone */ }
        resolve();
      }, (end - a.currentTime + 0.12) * 1000);
    });
  }

  /** Carrier opens and closes with nothing on it - an unanswered call. */
  function deadAir(voice) {
    if (!enabled || !ready) return Promise.resolve();
    const a = getCtx();
    if (a.state === 'suspended') a.resume();
    const start = a.currentTime + 0.05;
    const end = start + 0.5 + Math.random() * 0.3;
    keyClick(a, start, a.destination);
    squelch(a, start + 0.02, a.destination);
    squelch(a, end, a.destination);
    return new Promise((r) => setTimeout(r, (end - a.currentTime + 0.15) * 1000));
  }

  /**
   * Adjust delivery live, e.g. RADIO.setTiming({unitGap: 0.24}).
   * rate below 1.0 slows the words themselves but also drops pitch, so
   * widen the gaps first and only reach for rate if it still sounds rushed.
   */
  function setTiming(patch) {
    Object.assign(timing, patch || {});
    return { ...timing };
  }

  return {
    load,
    transmit,
    deadAir,
    getCtx,
    setTiming,
    getTiming: () => ({ ...timing }),
    isReady: () => ready,
    setEnabled: (v) => { enabled = v; },
    isEnabled: () => enabled,
    has: (voice, name) => Boolean(clips[voice] && clips[voice][name]),
  };
})();
