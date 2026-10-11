# CPU6 differential oracle

A standalone CPU6 one-instruction differential harness. Its biscvit integration follows the design documented on the `biscvit` branch `cpu6-oracle` (`7afb23c`). It uses a persistent JSON-lines protocol and keeps the deterministic core suite separate from MMU, interrupts, clock, and device behavior.

This is an independent implementation inspired by, and behaviorally informed by, the Meisaka Emu 0.22 CPU6 emulator. It does not include the original Meisaka source code. See [NOTICE.md](NOTICE.md) and [meisaka-provenance.json](meisaka-provenance.json).

## Run

```sh
cd ~/build/cpu6-oracle
python3 cpu6_oracle.py --backend reference < cases.jsonl
python3 cpu6_oracle.py --backend biscvit < cases.jsonl
python3 compare.py --reference reference.jsonl --implementation implementation.jsonl
python3 -m unittest discover -s tests
```

## Run the actual Meisaka UMCPU6 wrapper

The original Meisaka source is not included in this repository. Obtain a
working copy of `Emu 0.22/src/cen.ts`, then build the small Node-compatible
extraction and run its JSON-lines adapter:

```sh
npm install
MEISAKA_SOURCE='/path/to/Emu 0.22/src/cen.ts' npm run build-meisaka
node meisaka-wrapper.js < cases.jsonl
```

The build extracts `UMCPU6`, `SysMem`, the opcode table, register views, and
required helpers without loading the browser UI. Interrupts, clocks, devices,
and parity-break behavior remain disabled for the deterministic core suite.
The generated extraction is ignored by git; the upstream source path and hash
are recorded in `meisaka-provenance.json`.

Each request is one complete instruction:

```json
{"op":"step","events":{"interrupts":false,"clock":false,"devices":false},"state":{"pc":256,"ipl":0,"flags":0,"regs":["0000","0000","0000","0000","0000","FFFE","0000","0000"],"memory":[{"address":256,"bytes":"01"}]}}
```

`flags` uses biscvit's `C/N/Z/I` bit layout (`1/2/4/8`). Memory is byte-addressed and sparse; omitted bytes read as zero. Responses include normalized post-step state, decoded opcode information, and memory writes as `{address, old, new}` records.

## Current status

The first slice implements deterministic low/control operations, relative branches, and 8/16-bit register increment/decrement/clear/not/shift/rotate operations. The `reference` backend is an explicitly isolated executable model informed by Meisaka CPU6 behavior; the source identity is recorded in every response. The `biscvit` backend currently runs the same deterministic model for protocol smoke tests. Native biscvit integration is optional and is intentionally maintained outside this standalone core release; it will require a separate biscvit checkout and .NET SDK.

Meisaka source identity: `UMCPU6.step` from Meisaka Emu 0.22; SHA-256
`dbe1f84e1d91346eada5a7fa0d11f1a525f24c3b2848fa69dad282138df9cf94`.

## Licensing

The oracle source in this repository is independent work and is licensed under
the [MIT License](LICENSE). Meisaka attribution and the original CenRE License
are documented in [NOTICE.md](NOTICE.md), with the full license text in
[THIRD_PARTY_LICENSES/CenRE.txt](THIRD_PARTY_LICENSES/CenRE.txt).
