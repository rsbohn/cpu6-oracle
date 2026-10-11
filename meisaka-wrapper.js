#!/usr/bin/env node
/* JSON-lines adapter for the extracted Meisaka UMCPU6 core. */
const fs = require('fs');
const path = require('path');
const { UMCPU6 } = require('./build/meisaka-core.js');

const C = 1, N = 2, Z = 4, I = 8;
const CC_V = 128, CC_M = 64, CC_F = 32, CC_L = 16;
function u16(v) { return v & 0xffff; }
function parseNum(v) { return typeof v === 'string' ? parseInt(v, 16) : (v || 0); }
function flagsToCc(flags) {
  return (flags & C ? CC_L : 0) | (flags & N ? CC_M : 0) |
         (flags & Z ? CC_V : 0) | (flags & I ? CC_F : 0);
}
function ccToFlags(cc) {
  return (cc & CC_L ? C : 0) | (cc & CC_M ? N : 0) |
         (cc & CC_V ? Z : 0) | (cc & CC_F ? I : 0);
}
function load(req) {
  const s = req.state || {}, c = new UMCPU6();
  c.level = (s.ipl || 0) & 15;
  c.cc = flagsToCc(s.flags || 0);
  c.pc = u16(parseNum(s.pc));
  const regs = (s.regs || []).concat([0,0,0,0,0,0,0,0]).slice(0, 8).map(parseNum);
  const r = c.registers[c.level];
  [r.a, r.b, r.x, r.y, r.z, r.s, r.c, r.p] = regs.map(u16);
  for (const item of s.memory || []) {
    const a = parseNum(item.address), bytes = typeof item.bytes === 'string' ? Buffer.from(item.bytes.replace(/\s/g, ''), 'hex') : Buffer.from(item.bytes || []);
    for (let i = 0; i < bytes.length; ++i) c.mem.writemeta((a + i) & 0xffff, bytes[i]);
  }
  return c;
}
function state(c, before, halted = false) {
  const r = c.registers[c.level];
  const regs = [r.a, r.b, r.x, r.y, r.z, r.s, r.c, r.p].map(v => v.toString(16).toUpperCase().padStart(4, '0'));
  const writes = [];
  for (let a = 0x100; a < 0x10000; ++a) {
    const now = c.mem.memory[a], old = before[a];
    if (now !== old) writes.push({address: a, old, new: now});
  }
  return {pc: c.pc, ipl: c.level, flags: ccToFlags(c.cc), regs, writes, halted};
}
function handle(req) {
  if (req.op !== 'step') return {ok: false, error: 'only op=step is supported'};
  const c = load(req), before = c.mem.memory.slice(), op = c.fetch(c.pc);
  // fetch(address) is a non-advancing probe; step() performs the architectural fetch.
  let halted = false, error = null;
  try { c.step(); }
  catch (e) {
    if (e === 0 && op === 0) halted = true;
    else error = e instanceof Error ? e.message : `oracle exception: ${String(e)}`;
  }
  const out = {ok: error === null, backend: 'reference', source: 'Meisaka Emu 0.22 UMCPU6.step', instruction: op.toString(16).toUpperCase().padStart(2, '0'), state: state(c, before, halted)};
  if (error) out.error = error;
  return out;
}
for (const line of require('fs').readFileSync(0, 'utf8').split(/\r?\n/)) {
  if (line.trim()) process.stdout.write(JSON.stringify(handle(JSON.parse(line))) + '\n');
}
