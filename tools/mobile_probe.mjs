// Emulasi HP lewat Chrome DevTools Protocol, lalu ukur viewport + ambil screenshot.
// Pakai: node tools/mobile_probe.mjs <url> <out.png> [width] [height] [waitMs] [mobile 1/0] [js-aksi]
// Contoh: node tools/mobile_probe.mjs http://127.0.0.1:8080/ hp.png 375 812 18000 1 "window.switchCharacter('3d')"
// Butuh Node 22+ (WebSocket bawaan) dan Chrome. Mencetak innerWidth vs clientWidth, deteksi HP, elemen yang melebar.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, out, W = '375', H = '812', WAIT = '20000', MOBILE = '1', ACTION = ''] = process.argv.slice(2);
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const prof = mkdtempSync(join(tmpdir(), 'mobile-probe-'));
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, ['--headless=new', `--remote-debugging-port=${port}`, '--no-proxy-server',
  '--enable-unsafe-swiftshader', `--user-data-dir=${prof}`, 'about:blank'], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
let targets;
for (let i = 0; i < 150; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch {}
  await sleep(200);
}
const page = targets.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map(); const logs = [];
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.type + ': ' + m.params.args.map(a => a.value ?? a.description).join(' '));
  if (m.method === 'Runtime.exceptionThrown') logs.push('EXC: ' + m.params.exceptionDetails.exception?.description);
};
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: +W, height: +H, deviceScaleFactor: MOBILE === '1' ? 3 : 1, mobile: MOBILE === '1' });
await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await send('Emulation.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36' });
await send('Page.enable');
await send('Page.navigate', { url });
await sleep(+WAIT);
if (ACTION) { await send('Runtime.evaluate', { expression: ACTION }); await sleep(3000); }

const probe = `JSON.stringify({
  innerWidth, innerHeight,
  clientWidth: document.documentElement.clientWidth, clientHeight: document.documentElement.clientHeight,
  scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight,
  visualViewport: visualViewport && [visualViewport.width, visualViewport.height, visualViewport.scale],
  isMobile: window.isMobileLayout && window.isMobileLayout(),
  sheet: window.chatSheetHeight && window.chatSheetHeight(),
  live2dCanvas: (c => c && [c.style.width, c.style.height, c.width, c.height])(document.getElementById('live2d-canvas')),
  threeCanvas: (c => c && [c.style.width, c.style.height, c.width, c.height])(document.getElementById('three-canvas')),
  mode: window.activeWaifuType, collapsed: document.getElementById('chat-panel').classList.contains('collapsed'),
  model: window.waifuModel && [Math.round(waifuModel.x), Math.round(waifuModel.y), +waifuModel.scale.x.toFixed(4)],
  wide: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1).map(e => e.tagName + '#' + e.id + '.' + e.className + ' right=' + Math.round(e.getBoundingClientRect().right)).slice(0, 10)
})`;
const r = await send('Runtime.evaluate', { expression: probe, returnByValue: true });
console.log(JSON.stringify(JSON.parse(r.result.result.value), null, 1));
if (logs.length) console.log('--- console ---\n' + logs.slice(-15).join('\n'));
const shot = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
ws.close(); proc.kill();
process.exit(0);
