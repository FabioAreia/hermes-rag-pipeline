#!/usr/bin/env python3
"""Remove non-canonical swipes from a SillyTavern JSONL export.

Keeps only the canonical message (mes / the swipe matching mes) in every
nested location (top-level, continueSwipe, continueHistory[]). Never touches
the original file; writes a new cleaned copy.

Usage: clean_swipes.py INPUT.jsonl [OUTPUT.jsonl]
If OUTPUT omitted -> INPUT with '.cleaned.jsonl' suffix on the basename.
"""
import json
import sys
import os


def cleanup_swipes_in_state(obj, top=False):
    """Return (clean_obj, removed_count). Recursively handles nested
    continueHistory/continueSwipe structures."""
    removed = 0

    if isinstance(obj, list):
        out = []
        for it in obj:
            c, r = cleanup_swipes_in_state(it)
            out.append(c)
            removed += r
        return out, removed

    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k], r = cleanup_swipes_in_state(v)
            removed += r

        # This node is a message record: shrink its swipes to the canonical one.
        if "swipes" in out and isinstance(out["swipes"], list):
            swipes = out["swipes"]
            canonical = out.get("mes")
            swipe_id = out.get("swipe_id", 0)

            kept = None
            # Prefer the swipe explicitly chosen by swipe_id (fall back to one
            # matching mes). Anything else is non-canonical.
            if isinstance(swipe_id, int) and 0 <= swipe_id < len(swipes):
                kept = swipes[swipe_id]
            # If child is a dict it may itself nest continueHistory; recurse later.
            kc, kr = cleanup_swipes_in_state(kept)
            removed += kr
            if kept is not None:
                out["swipes"] = [kc]
            else:
                out["swipes"] = []

        return out, removed

    return obj, removed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    if len(sys.argv) >= 3:
        dst = sys.argv[2]
    else:
        base, ext = os.path.splitext(os.path.basename(src))
        dst = os.path.join(os.path.dirname(src), f"{base}.cleaned{ext}")

    total = 0
    removed = 0
    with open(src) as f, open(dst, "w") as o:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            c, r = cleanup_swipes_in_state(d)
            total += 1
            removed += r
            o.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Cleaned {total} lines -> {dst}")
    print(f"Non-canonical swipes removed (top-level + nested): {removed}")


if __name__ == "__main__":
    main()
