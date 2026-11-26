// Build tools/fsrs/fsrs6.min.js from ts-fsrs and inline it into index.html. v1.0.0 (3.9.0)
// Usage: TS_FSRS=/path/to/ts-fsrs-checkout node tools/fsrs/build.mjs [--esbuild /path/to/esbuild/lib/main.js]
// The checkout must be at COMMIT (git clone https://github.com/open-spaced-repetition/ts-fsrs && git checkout COMMIT).
import path from 'node:path'; import fs from 'node:fs'; import { execSync } from 'node:child_process';
const COMMIT = '828447d065259f53f47fd5580b848e0a0b9c93df';   // ts-fsrs 6.0.1, srs-kit 1.0.1
const HERE = path.dirname(new URL(import.meta.url).pathname), REPO = path.resolve(HERE, '../..');
const TS = process.env.TS_FSRS; if (!TS) { console.error('set TS_FSRS to a ts-fsrs checkout'); process.exit(1); }
const head = execSync('git rev-parse HEAD', { cwd: TS }).toString().trim();
if (head !== COMMIT) { console.error(`ts-fsrs checkout is at ${head}, expected ${COMMIT}`); process.exit(1); }
const ei = process.argv.indexOf('--esbuild');
const { build } = await import(ei > 0 ? process.argv[ei + 1] : 'esbuild');
const P = path.join(TS, 'packages');
const toTs = p => { for (const c of [p, p.replace(/\.js$/, '.ts'), p + '.ts', path.join(p, 'index.ts')]) if (fs.existsSync(c) && fs.statSync(c).isFile()) return c; return null; };
const mono = { name: 'mono', setup(b) {
  b.onResolve({ filter: /^@\// }, a => { const pkg = a.importer.startsWith(path.join(P, 'srs-kit')) ? 'srs-kit' : 'fsrs'; const r = toTs(path.join(P, pkg, 'src', a.path.slice(2))); return r ? { path: r } : undefined; });
  b.onResolve({ filter: /^@open-spaced-repetition\/srs-kit/ }, a => { let sub = a.path.replace('@open-spaced-repetition/srs-kit', '').replace(/^\//, '');
    if (sub.startsWith('chrono/')) sub = 'chrono/presets/' + sub.slice(7);
    const r = toTs(path.join(P, 'srs-kit/src', sub || 'index')); return r ? { path: r } : undefined; });
} };
const out = path.join(HERE, 'fsrs6.min.js');
await build({ entryPoints: [path.join(HERE, 'entry.ts')], bundle: true, format: 'iife', globalName: 'FSRS', target: 'es2019',
  minify: true, legalComments: 'none', define: { 'import.meta.env': '{}' }, plugins: [mono], outfile: out, logLevel: 'error' });
const lic = f => fs.readFileSync(path.join(P, f), 'utf8').trim().replace(/\*\//g, '* /');
const banner = `/* FSRS-6 scheduler built from ts-fsrs ${COMMIT.slice(0, 7)} (tools/fsrs/build.mjs).\n\nts-fsrs:\n${lic('fsrs/LICENSE')}\n\nsrs-kit:\n${lic('srs-kit/LICENSE')}\n*/\n`;
const js = banner + fs.readFileSync(out, 'utf8').trim() + '\n';
fs.writeFileSync(out, js);
const page = path.join(REPO, 'index.html'), html = fs.readFileSync(page, 'utf8');
const A = '<script id="fsrs-vendor">', B = '</script><!-- /fsrs-vendor -->';
const i = html.indexOf(A), j = html.indexOf(B);
if (i < 0 || j < 0) { console.error('index.html has no fsrs-vendor block'); process.exit(1); }
fs.writeFileSync(page, html.slice(0, i + A.length) + '\n' + js + html.slice(j));
console.log(`fsrs6.min.js ${js.length} bytes, inlined into index.html`);
