#!/usr/bin/env node
/* Build a Node-loadable UMCPU6 core from a checked-out Meisaka source tree.
 * The source itself is not copied into this repository. */
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const source = process.env.MEISAKA_SOURCE || process.argv[2];
if (!source) {
  console.error('usage: MEISAKA_SOURCE=/path/to/Emu\\ 0.22/src/cen.ts npm run build-meisaka');
  process.exit(2);
}
const text = fs.readFileSync(source, 'utf8');
function between(start, end) {
  const a = text.indexOf(start);
  const b = text.indexOf(end, a);
  if (a < 0 || b < 0) throw new Error(`cannot extract ${start} .. ${end}`);
  return text.slice(a, b);
}

const pieces = [
  between('function sbyte(', 'function sword('),
  between('function LevelRegisters(', 'interface ICCPU'),
  between('class SysMem implements', 'class ROM512'),
  between('const enum OPM', 'const annotation_data'),
  between('const enum ARITH_OP', 'const editors:'),
  between('class UMCPU6 implements', 'class CPU6'),
];
const prelude = `
const editors = {};
const mcsim = { memfault: 0, parity: 0, reg: {b: 0} };
const bpl = { writemeta() {} };
let um_enable_sync = false;
function handle_break() { return false; }
function softlog() {}
function hex(v, l = 2) { return (v >>> 0).toString(16).toUpperCase().padStart(l, '0'); }
const annotation_data = new Map();
`;
const postlude = `
module.exports = { UMCPU6, SysMem };
`;
const input = prelude + pieces.join('\n') + postlude;
const output = ts.transpileModule(input, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
  fileName: 'meisaka-core.ts'
}).outputText;
const out = path.resolve(__dirname, '..', 'build', 'meisaka-core.js');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, output);
console.log(out);
