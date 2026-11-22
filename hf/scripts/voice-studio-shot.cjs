// Screenshots of Voice Studio's voice board for one language, desktop and phone width, from the
// files in hf/ui (no server, no token). Look at the frames after any catalog/app.js/style.css
// change: a long credit line, a missing preview button or a card that stretches shows here.
//
//   NODE_PATH=$(npm root -g) node hf/scripts/voice-studio-shot.cjs it-IT /tmp/shots
//
// Writes <out>/<locale>-desktop.png and <locale>-phone.png and prints each card's text.
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const locale = process.argv[2] || 'it-IT';
const out = process.argv[3] || '.';
const ui = path.join(__dirname, '..', 'ui');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wav': 'audio/wav' };

// index.html asks for /ui-assets/…, as the Space serves it.
const server = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    const file = u === '/' ? path.join(ui, 'index.html') : path.join(ui, u.replace(/^\/ui-assets\//, ''));
    if (!file.startsWith(ui) || !fs.existsSync(file)) return res.writeHead(404).end();
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
});

server.listen(0, '127.0.0.1', async () => {
    const port = server.address().port;
    fs.mkdirSync(out, { recursive: true });
    const b = await chromium.launch();
    const p = await b.newPage({ viewport: { width: 1280, height: 1100 }, deviceScaleFactor: 2 });
    p.on('pageerror', (e) => console.log('pageerror', e.message));
    await p.goto(`http://127.0.0.1:${port}/`);
    await p.waitForSelector('#ttsLanguage option', { state: 'attached' });
    await p.selectOption('#ttsLanguage', locale);
    await p.waitForTimeout(300);
    const grid = await p.$('#voiceGrid');
    await grid.evaluate((e) => (e.style.maxHeight = 'none'));
    await grid.screenshot({ path: path.join(out, `${locale}-desktop.png`) });
    console.log(await p.$$eval('.voice-card', (cs) => cs.map((c) => c.innerText.replace(/\s+/g, ' ').trim())));
    await p.setViewportSize({ width: 390, height: 900 });
    await p.waitForTimeout(200);
    await (await p.$('#voiceGrid')).screenshot({ path: path.join(out, `${locale}-phone.png`) });
    await b.close();
    server.close();
});
