# CPU6 differential oracle

A standalone CPU6 one-instruction differential harness. It uses a persistent JSON-lines protocol and keeps the deterministic core suite separate from MMU, interrupts, clock, and device behavior.

This is an independent implementation inspired by, and behaviorally informed by, the Meisaka Emu 0.22 CPU6 emulator. It does not include the original Meisaka source code. See [NOTICE.md](NOTICE.md) and [meisaka-provenance.json](meisaka-provenance.json).

## Run

```sh
cd ~/build/cpu6-oracle
# Test implementation (Python model)
python3 cpu6_oracle.py --backend implementation < cases.jsonl
# Reference backend (Meisaka UMCPU6; requires the optional Node build below)
node meisaka-wrapper.js < cases.jsonl
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

`flags` uses the normalized CPU6 `C/N/Z/I` bit layout (`1/2/4/8`). Memory is byte-addressed and sparse; omitted bytes read as zero. Responses include normalized post-step state, decoded opcode information, and memory writes as `{address, old, new}` records. The Meisaka implementation is the `reference` backend; the Python model is the `implementation` backend.

## Current status

The first slice implements deterministic low/control operations, relative branches, and 8/16-bit register increment/decrement/clear/not/shift/rotate operations. The `reference` backend is the actual Meisaka UMCPU6 implementation, loaded through the optional Node extraction build. The `implementation` backend is the independent Python model under test. Differential comparisons should use Meisaka as the reference and Python as the implementation.

Meisaka source identity: `UMCPU6.step` from Meisaka Emu 0.22; SHA-256
`dbe1f84e1d91346eada5a7fa0d11f1a525f24c3b2848fa69dad282138df9cf94`.

## Licensing

The oracle source in this repository is independent work and is licensed under
the [MIT License](LICENSE). Meisaka attribution and the original CenRE License
are documented in [NOTICE.md](NOTICE.md), with the full license text in
[THIRD_PARTY_LICENSES/CenRE.txt](THIRD_PARTY_LICENSES/CenRE.txt).
