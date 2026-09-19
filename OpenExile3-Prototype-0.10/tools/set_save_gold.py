#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from openexile3.save import parse_save_bytes, set_gold_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a copy of an Exile III save with a different gold value."
    )
    parser.add_argument("save", type=Path)
    parser.add_argument("--gold", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    src = args.save.resolve()
    dst = args.output.resolve()
    if src == dst:
        raise SystemExit("Refusing to overwrite the input save. Use a different --output path.")
    if dst.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {dst}")

    original = args.save.read_bytes()
    modified = set_gold_bytes(original, args.gold)
    check = parse_save_bytes(modified)
    if check.gold != args.gold:
        raise RuntimeError("Post-write verification failed")
    args.output.write_bytes(modified)
    print(f"Wrote {args.output} with gold={check.gold}")
    print("Input save was not modified.")


if __name__ == "__main__":
    main()
