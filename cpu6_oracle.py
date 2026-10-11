#!/usr/bin/env python3
"""Persistent JSONL CPU6 one-step harness."""
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass

SOURCE = "independent Python CPU6 model"
REG_NAMES = ("AX", "BX", "RT", "DX", "EX", "SP", "GX", "HX")
C, N, Z, I = 1, 2, 4, 8


def u16(x): return int(x) & 0xffff

def s8(x): return x - 256 if x & 0x80 else x

@dataclass
class Machine:
    pc: int
    ipl: int
    flags: int
    regs: list[int]
    mem: bytearray
    halted: bool = False

    @classmethod
    def load(cls, state):
        mem = bytearray(65536)
        for item in state.get("memory", []):
            a = int(item["address"], 0) if isinstance(item["address"], str) else item["address"]
            raw = item.get("bytes", "")
            vals = bytes.fromhex(raw) if isinstance(raw, str) else bytes(raw)
            for i, b in enumerate(vals): mem[(a + i) & 0xffff] = b
        regs = [int(x, 16) if isinstance(x, str) else int(x) for x in state.get("regs", [0]*8)]
        regs = [(x & 0xffff) for x in (regs + [0]*8)[:8]]
        return cls(u16(state.get("pc", 0)), int(state.get("ipl", 0)) & 15,
                   int(state.get("flags", 0)) & 15, regs, mem)

    def fetch(self):
        b = self.mem[self.pc]; self.pc = u16(self.pc + 1); return b
    def set_flags(self, value, width, carry=None):
        mask = 0xff if width == 8 else 0xffff
        value &= mask
        self.flags &= ~(N | Z | (C if carry is not None else 0))
        if value == 0: self.flags |= Z
        if value & (0x80 if width == 8 else 0x8000): self.flags |= N
        if carry: self.flags |= C
    def step(self):
        op = self.fetch()
        if op == 0x00: self.halted = True
        elif op == 0x01: pass
        # Meisaka CC_F/CC_L/CC_V/CC_M normalize to biscvit's I/C/Z/N.
        elif op == 0x02: self.flags |= I       # SF
        elif op == 0x03: self.flags &= ~I      # RF
        elif op == 0x04: pass                  # EI (interrupt delivery disabled here)
        elif op == 0x05: pass                  # DI (interrupt delivery disabled here)
        elif op == 0x06: self.flags |= C       # SL
        elif op == 0x07: self.flags &= ~C      # RL
        elif op == 0x08: self.flags ^= C
        elif op == 0x0d: self.regs[2] = self.pc  # PCX / save return PC in RT
        elif 0x10 <= op < 0x20:
            off = s8(self.fetch())
            cond = {0: bool(self.flags&C), 1: not self.flags&C,
                    2: bool(self.flags&I), 3: not self.flags&I,
                    4: bool(self.flags&Z), 5: not self.flags&Z,
                    6: bool(self.flags&N), 7: not self.flags&N,
                    8: not (self.flags&(N|Z)), 9: bool(self.flags&(N|Z))}.get(op & 15, False)
            if cond: self.pc = u16(self.pc + off)
        elif 0x20 <= op < 0x30: self._misc(op, 8)
        elif 0x30 <= op < 0x40: self._misc(op, 16)
        else: raise NotImplementedError(f"opcode {op:02X} is outside the initial deterministic slice")
        return op
    def _misc(self, op, width):
        # RC encodes a byte register in the high nibble and a count in the
        # low nibble. Word RC forms use an even byte-register code (A/B/X...).
        base = 0x20 if width == 8 else 0x30
        if (op & 8) == 0:
            enc = self.fetch()
            regcode = enc >> 4
            count = (enc & 15) + (1 if (op - base) in (0, 1, 4, 5, 6, 7) else 0)
        else:
            regcode = 1 if width == 8 else 0  # implicit AL/AX
            count = 1
        if width == 16 and (regcode & 1):
            raise ValueError(f'odd word register encoding {regcode:X}')
        r = regcode >> 1 if width == 16 else regcode
        word_r = regcode >> 1
        mask = 0xff if width == 8 else 0xffff
        old = ((self.regs[word_r] >> 8) & 0xff if (regcode & 1) == 0 else (self.regs[word_r] & 0xff)) if width == 8 else self.regs[r]
        kind = (op - base) & 7
        if kind == 0:
            value = old + count
            carry = value > mask
        elif kind == 1:
            value, carry = old - count, True
        elif kind == 2: value, carry = 0, None
        elif kind == 3: value, carry = old ^ mask, None
        elif kind == 4: value, carry = old >> count, bool((old >> (count - 1)) & 1)
        elif kind == 5: value, carry = old << count, bool((old >> (width - count)) & 1)
        elif kind == 6: value, carry = (old >> count) | ((self.flags & C) and (1 << (width - count)) or 0), bool((old >> (count - 1)) & 1)
        else: value, carry = (old << count) | (1 if self.flags & C else 0), bool((old >> (width - count)) & 1)
        value &= mask
        if width == 8:
            if regcode & 1: self.regs[word_r] = (self.regs[word_r] & 0xff00) | value
            else: self.regs[word_r] = (value << 8) | (self.regs[word_r] & 0xff)
        else: self.regs[r] = value
        self.set_flags(value, width, carry)

def response(machine, before, backend, op=None, error=None):
    writes = []
    for a, (x, y) in enumerate(zip(before, machine.mem)):
        if x != y: writes.append({"address": a, "old": x, "new": y})
    out = {"ok": error is None, "backend": backend, "source": SOURCE,
           "state": {"pc": machine.pc, "ipl": machine.ipl, "flags": machine.flags,
                     "regs": [f"{x:04X}" for x in machine.regs], "writes": writes,
                     "halted": machine.halted}}
    if op is not None:
        out["instruction"] = f"{op:02X}"
        out["decoded"] = {0x00: "HALT", 0x01: "NOP", 0x02: "SF", 0x03: "RF",
                          0x04: "EI", 0x05: "DI", 0x06: "SL", 0x07: "RL",
                          0x08: "CL", 0x0D: "PCX"}.get(op, "CPU6")
    if error: out["error"] = error
    return out

def handle(req, backend):
    if req.get("op") != "step": return {"ok": False, "error": "only op=step is supported"}
    m = Machine.load(req.get("state", {})); before = m.mem[:]
    try: op = m.step(); return response(m, before, backend, op)
    except Exception as e: return response(m, before, backend, error=str(e))

def main():
    p = argparse.ArgumentParser(); p.add_argument("--backend", choices=("implementation",), default="implementation"); p.add_argument("command", nargs="?")
    args = p.parse_args()
    if args.command == "compare": return compare(args)
    for line in sys.stdin:
        if line.strip(): print(json.dumps(handle(json.loads(line), args.backend)), flush=True)

def compare(args):
    raise SystemExit("compare is provided by compare.py")

if __name__ == "__main__": main()
