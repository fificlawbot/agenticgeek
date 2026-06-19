// Usage: node merge-json.js <target.json> <source.json>
// Merges source INTO target: add missing keys, union arrays by identity,
// recurse objects, keep existing scalars. Idempotent.
const fs = require('fs');
const [, , targetPath, sourcePath] = process.argv;

const source = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
const target = fs.existsSync(targetPath)
  ? JSON.parse(fs.readFileSync(targetPath, 'utf8'))
  : {};

function ident(v) {
  if (v && typeof v === 'object' && typeof v.name === 'string') return 'name:' + v.name;
  return JSON.stringify(v);
}

function mergeArray(tArr, sArr) {
  const seen = new Set(tArr.map(ident));
  for (const item of sArr) {
    if (!seen.has(ident(item))) { tArr.push(item); seen.add(ident(item)); }
  }
  return tArr;
}

function merge(t, s) {
  for (const [k, sv] of Object.entries(s)) {
    if (!(k in t)) { t[k] = sv; continue; }
    const tv = t[k];
    if (Array.isArray(tv) && Array.isArray(sv)) mergeArray(tv, sv);
    else if (tv && sv && typeof tv === 'object' && typeof sv === 'object'
             && !Array.isArray(tv) && !Array.isArray(sv)) merge(tv, sv);
    // else: scalar/type-mismatch -> keep existing target value
  }
  return t;
}

fs.mkdirSync(require('path').dirname(targetPath), { recursive: true });
fs.writeFileSync(targetPath, JSON.stringify(merge(target, source), null, 2) + '\n');
console.log('  merged -> ' + targetPath);
