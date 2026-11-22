// Markdown tables from results/<label>/*.json (and analysis.json when present).
//   node summarize.cjs <label> [<label2>]   → one table per label; with two, a before/after delta.
const fs = require('fs');
const path = require('path');

const root = process.env.BENCH_RESULTS || path.join(__dirname, '..', 'results', 'quest_italian');
const VOICES = ['it_IT-paola-medium', 'it_IT-serena-high', 'it_IT-aurora-medium', 'it_IT-giorgio-high'];

const med = (a) => {
    const x = a.filter((v) => v != null && !Number.isNaN(v)).sort((p, q) => p - q);
    if (!x.length) return null;
    const m = Math.floor(x.length / 2);
    return x.length % 2 ? x[m] : (x[m - 1] + x[m]) / 2;
};
const r0 = (v) => (v == null ? '–' : Math.round(v));

function load(label) {
    const dir = path.join(root, label);
    const out = {};
    for (const v of VOICES) {
        const f = path.join(dir, `${v}.json`);
        if (fs.existsSync(f)) out[v] = JSON.parse(fs.readFileSync(f, 'utf8')).results;
    }
    const af = path.join(dir, 'analysis.json');
    return { data: out, analysis: fs.existsSync(af) ? JSON.parse(fs.readFileSync(af, 'utf8')) : {} };
}

function metrics(results, analysis) {
    const by = (c) => results.filter((r) => r.case === c && !r.error);
    const rtfs = results.flatMap((r) => (r.server || []).filter((s) => !s.cold).map((s) => s.rtf));
    const cold = by('cold')[0] || {};
    const joins = (analysis || []).flatMap((a) => (a.case === 'long' || a.case === 'stream-long' ? a.joins || [] : []));
    const asr = (analysis || []).filter((a) => a.cer != null);
    const ia = by('interrupt');
    return {
        coldFirst: cold.firstFrameMs,
        coldAudible: cold.audibleMs,
        short: med([...by('short1'), ...by('short2')].map((r) => r.audibleMs)),
        medium: med(by('medium').map((r) => r.audibleMs)),
        numbers: med(by('numbers').map((r) => r.audibleMs)),
        long: med(by('long').map((r) => r.audibleMs)),
        stream: med(by('stream-long').map((r) => r.audibleMs)),
        rtf: med(rtfs),
        underruns: results.reduce((a, r) => a + (r.underruns || 0), 0),
        gapMs: results.reduce((a, r) => a + (r.gapTotalMs || 0), 0),
        joinSilence: med(joins.map((j) => j.silenceMs)),
        afterInterrupt: med(by('after-interrupt').map((r) => r.audibleMs)),
        lateFrames: ia.reduce((a, r) => a + (r.lateFrames || 0), 0),
        cer: asr.length ? asr.reduce((a, x) => a + x.cer, 0) / asr.length : null,
        accentsMissed: [...new Set(asr.flatMap((x) => x.accentedMissed || []))].join(' ') || '–',
        errors: results.filter((r) => r.error).length,
    };
}

function table(label) {
    const { data, analysis } = load(label);
    const rows = [];
    rows.push(`### ${label}`);
    rows.push('');
    rows.push(
        '| Voice | Cold first frame / audible | Warm audible: short · medium · numbers · long | HV5 stream | RTF (warm) | Underruns (gap ms) | Join silence | Next reply after stop | CER | Accented words missed |'
    );
    rows.push('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |');
    const all = {};
    for (const v of VOICES) {
        if (!data[v]) continue;
        const m = (all[v] = metrics(data[v], analysis[v]));
        rows.push(
            `| ${v} | ${r0(m.coldFirst)} / ${r0(m.coldAudible)} ms | ${r0(m.short)} · ${r0(m.medium)} · ${r0(m.numbers)} · ${r0(m.long)} ms | ${r0(m.stream)} ms | ${m.rtf == null ? '–' : m.rtf.toFixed(3)} | ${m.underruns} (${m.gapMs}) | ${r0(m.joinSilence)} ms | ${r0(m.afterInterrupt)} ms | ${m.cer == null ? '–' : m.cer.toFixed(3)} | ${m.accentsMissed} |` +
                (m.errors ? ` ⚠ ${m.errors} errors` : '')
        );
    }
    return { text: rows.join('\n'), all };
}

const labels = process.argv.slice(2);
const tabs = labels.map(table);
console.log(tabs.map((t) => t.text).join('\n\n'));
if (tabs.length === 2) {
    console.log(`\n### ${labels[1]} − ${labels[0]} (audible ms; negative is faster)\n`);
    console.log('| Voice | short | medium | numbers | long | stream | underruns |');
    console.log('| --- | --- | --- | --- | --- | --- | --- |');
    for (const v of VOICES) {
        const a = tabs[0].all[v];
        const b = tabs[1].all[v];
        if (!a || !b) continue;
        const d = (k) => (a[k] == null || b[k] == null ? '–' : Math.round(b[k] - a[k]));
        console.log(`| ${v} | ${d('short')} | ${d('medium')} | ${d('numbers')} | ${d('long')} | ${d('stream')} | ${a.underruns} → ${b.underruns} |`);
    }
}
