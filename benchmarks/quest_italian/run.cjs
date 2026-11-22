// Usage (via run_all.sh): node run.cjs <voice> <label> '<client cfg json>'
// One voice, one fresh SonicAgent process: cold first reply, then warm cases, HV5 stream,
// interruption + next reply. Writes results/<label>-<voice>.json and per-turn WAVs.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const voice = process.argv[2];
const label = process.argv[3] || 'baseline';
const cfg = process.argv[4] || '{}'; // client settings overrides, e.g. {"jitterMs":200}
const REPS = Number(process.env.REPS || 3);
const outDir = path.join(process.env.BENCH_RESULTS || path.join(__dirname, '..', 'results', 'quest_italian'), label);
fs.mkdirSync(path.join(outDir, 'wav'), { recursive: true });

const T = {
    short1: 'Certo, ci penso io.',
    short2: 'Sì, è già fatto!',
    medium: 'Il treno parte alle 7:45 dal binario 3 e costa 12,50 €. Perché non prenoti adesso? Così sarai in città già venerdì.',
    numbers: 'Il 25% degli studenti ha preso 30 e lode; la temperatura era di -3,5 °C il 24/12/2026.',
    long:
        "Allora, ecco il programma di domani. Alle 9:30 c'è la riunione con il dott. Rossi, che durerà circa un'ora e mezza. " +
        "Dopo pranzo, verso le 14:15, passiamo all'università per ritirare i documenti: ricordati la carta d'identità! " +
        'Il biglietto del museo costa 18 € a persona, ma con la tessera studenti si paga il 50% in meno. ' +
        "La sera, se non piove, possiamo cenare in quel piccolo caffè vicino al Duomo; dicono che il tiramisù sia il più buono della città. " +
        'Che ne pensi, ti va bene così?',
};

function wav(frames) {
    // Concatenate the PCM16 exactly as delivered, in arrival order per phrase.
    const bufs = frames.map((f) => Buffer.from(f.b64, 'base64'));
    const data = Buffer.concat(bufs);
    const rate = frames.length ? frames[0].rate : 22050;
    const h = Buffer.alloc(44);
    h.write('RIFF', 0);
    h.writeUInt32LE(36 + data.length, 4);
    h.write('WAVEfmt ', 8);
    h.writeUInt32LE(16, 16);
    h.writeUInt16LE(1, 20);
    h.writeUInt16LE(1, 22);
    h.writeUInt32LE(rate, 24);
    h.writeUInt32LE(rate * 2, 28);
    h.writeUInt16LE(2, 32);
    h.writeUInt16LE(16, 34);
    h.writeUInt32LE(data.length, 40);
    h.write('data', 36);
    return Buffer.concat([h, data]);
}

function summarize(name, rep, r) {
    const s = r.stats || {};
    const ev = r.events || [];
    // Phrase boundaries as the client saw them: tts.started / audio.meta / audio.done per phrase.
    const phrases = {};
    for (const e of ev) {
        if (!e.turn_id) continue;
        const p = (phrases[e.turn_id] = phrases[e.turn_id] || {});
        if (e.type === 'tts.started') p.started = e.t;
        if (e.type === 'tts.audio.meta') p.firstFrame = e.t;
        if (e.type === 'tts.audio.done') Object.assign(p, { done: e.t, audioMs: e.audio_ms });
    }
    const frames = r.frames || [];
    const out = {
        case: name,
        rep,
        error: r.error,
        playerKind: r.playerKind,
        firstFrameMs: s.firstAudioAt && s.requestAt ? s.firstAudioAt - s.requestAt : null,
        audibleMs: r.onStart,
        endMs: r.onEnd,
        audioMs: (s.server || []).reduce((a, x) => a + (x.audioMs || 0), 0),
        underruns: s.underruns,
        gaps: (r.gaps || []).map((g) => Math.round(g.ms)),
        gapTotalMs: Math.round((r.gaps || []).reduce((a, g) => a + g.ms, 0)),
        cold: s.cold,
        voice: s.voice,
        server: s.server,
        phrases: Object.keys(phrases).length,
        stopAt: r.stopAt,
        lateFrames: r.stopAt != null ? frames.filter((f) => f.t > r.stopAt).length : undefined,
        llmDoneAt: r.llmDoneAt,
    };
    if (frames.length) {
        const file = path.join(outDir, 'wav', `${voice}-${name}-${rep}.wav`);
        fs.writeFileSync(file, wav(frames));
        out.wav = file;
        // Per-phrase segment lengths (bytes) for boundary analysis offline.
        const segs = [];
        let cur = null;
        for (const f of frames) {
            if (f.seq === 0) segs.push((cur = { bytes: 0 }));
            if (cur) cur.bytes += Buffer.from(f.b64, 'base64').length;
        }
        out.segmentSamples = segs.map((x) => x.bytes / 2);
    }
    return out;
}

(async () => {
    const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
    const p = await b.newPage();
    p.on('pageerror', (e) => console.log('[pageerror]', e.message));
    await p.goto(`http://127.0.0.1:${process.env.WWW_PORT || 8090}/bench.html?ob=${process.env.OB_PORT || 8702}&cfg=` + encodeURIComponent(cfg));
    const results = [];
    const run = async (name, rep, fn) => {
        const r = await fn();
        const s = summarize(name, rep, r);
        results.push(s);
        console.log(
            `${voice} ${name}#${rep} first=${s.firstFrameMs} audible=${s.audibleMs && Math.round(s.audibleMs)} ` +
                `end=${s.endMs && Math.round(s.endMs)} audio=${s.audioMs} underruns=${s.underruns} gaps=${JSON.stringify(s.gaps)} ` +
                `rtf=${JSON.stringify((s.server || []).map((x) => x.rtf))} ${s.error || ''}`
        );
        await new Promise((res) => setTimeout(res, 300));
    };
    // Cold: the first reply of a fresh process, model not loaded, no client warm call.
    await run('cold', 0, () => p.evaluate(([t, v]) => benchSpeak(t, v), [T.short1, voice]));
    for (let rep = 1; rep <= REPS; rep++) {
        for (const k of ['short1', 'short2', 'medium', 'numbers', 'long'])
            await run(k, rep, () => p.evaluate(([t, v]) => benchSpeak(t, v), [T[k], voice]));
    }
    // HV5: the same long reply arriving as tokens (~45 ms per word, a quick cloud LLM).
    for (let rep = 1; rep <= REPS; rep++)
        await run('stream-long', rep, () => p.evaluate(([t, v]) => benchStream(t, v, 45), [T.long, voice]));
    // Interruption: stop the long reply 1.5 s into playback, then the next reply at once.
    for (let rep = 1; rep <= REPS; rep++) {
        await run('interrupt', rep, () => p.evaluate(([t, v]) => benchSpeak(t, v, { stopAfterMs: 1500 }), [T.long, voice]));
        await run('after-interrupt', rep, () => p.evaluate(([t, v]) => benchSpeak(t, v), [T.short2, voice]));
    }
    // A turn spoken in another voice than the one under test is a harness error, not a result.
    const wrong = results.filter((r) => r.voice && r.voice !== voice);
    if (wrong.length) console.log(`WARNING ${wrong.length} turns used another voice: ${[...new Set(wrong.map((r) => r.voice))]}`);
    fs.writeFileSync(path.join(outDir, `${voice}.json`), JSON.stringify({ voice, label, cfg, texts: T, results }, null, 1));
    await b.close();
})();
