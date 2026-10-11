#!/usr/bin/env python3
import argparse, json

def main():
    p = argparse.ArgumentParser(); p.add_argument("--reference", required=True); p.add_argument("--implementation", required=True); args = p.parse_args()
    with open(args.reference) as rf, open(args.implementation) as im:
        for n, (a, b) in enumerate(zip(rf, im), 1):
            x, y = json.loads(a), json.loads(b)
            if x.get("state") != y.get("state") or x.get("ok") != y.get("ok"):
                print(json.dumps({"case": n, "first_difference": first_diff(x, y), "oracle": x, "implementation": y}, indent=2))
                return 1
    print("no differences"); return 0

def first_diff(a, b, path=""):
    if type(a) != type(b) or a != b:
        if isinstance(a, dict) and isinstance(b, dict):
            for k in list(a) + [k for k in b if k not in a]:
                d = first_diff(a.get(k), b.get(k), f"{path}.{k}")
                if d: return d
        return {"field": path or "$", "oracle": a, "implementation": b}
    return None
if __name__ == "__main__": raise SystemExit(main())
