// Usage: node clean-settings.js <settings.json>  -> cleaned JSON on stdout
const fs = require('fs');
const [, , path] = process.argv;
const DEAD = /astha[.-]tarun[@-]gmail/i;

function clean(node) {
  if (Array.isArray(node)) {
    return node
      .filter(v => !(typeof v === 'string' && DEAD.test(v)))
      .map(clean);
  }
  if (node && typeof node === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      if (typeof v === 'string' && DEAD.test(v)) continue; // drop dead-account values
      out[k] = clean(v);
    }
    return out;
  }
  return node;
}

const data = JSON.parse(fs.readFileSync(path, 'utf8'));
process.stdout.write(JSON.stringify(clean(data), null, 2) + '\n');
