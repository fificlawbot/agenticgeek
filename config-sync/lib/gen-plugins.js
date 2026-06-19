// Usage: node gen-plugins.js <~/.claude dir>  -> plugins.txt body on stdout
const fs = require('fs');
const path = require('path');
const [, , claudeDir] = process.argv;

const mk = JSON.parse(fs.readFileSync(path.join(claudeDir, 'plugins/known_marketplaces.json'), 'utf8'));
const inst = JSON.parse(fs.readFileSync(path.join(claudeDir, 'plugins/installed_plugins.json'), 'utf8'));

const out = ['# Reinstall after `pull`. Lines are idempotent — Claude skips already-installed.', '', '# Marketplaces'];
for (const [name, m] of Object.entries(mk)) {
  const s = m.source || {};
  const ref = s.repo || s.url || name;
  out.push(`claude plugin marketplace add ${ref}`);
}
out.push('', '# Plugins');
for (const key of Object.keys(inst.plugins || {})) {
  out.push(`claude plugin install ${key}`);
}
process.stdout.write(out.join('\n') + '\n');
