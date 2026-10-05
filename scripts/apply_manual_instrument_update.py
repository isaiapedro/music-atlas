"""Set the cropped panel position for one instrument image.

Usage:
  python3 scripts/apply_manual_instrument_update.py --name Rubab \
    --image-focus 'center top' \
    --rebuild
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "instrument_images.json"
WEB = ROOT / "web" / "data" / "instrument_images.json"


def helpers():
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from apply_manual_genre_update import bust_browser_cache, image_focus, write_json
    from apply_manual_record_update import running_bind_host
    return bust_browser_cache, image_focus, write_json, running_bind_host


def load_instruments():
    path = RESEARCH if RESEARCH.exists() else WEB
    payload = json.loads(path.read_text(encoding="utf-8"))
    instruments = payload.get("instruments")
    if not isinstance(instruments, dict):
        instruments = {}
    return {"version": 1, "instruments": instruments}


def match_name(instruments: dict, name: str) -> str:
    if name in instruments:
        return name
    lowered = name.casefold()
    hits = [key for key in instruments if key.casefold() == lowered]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"unknown instrument {name}")


def apply_instrument_focus(payload: dict, name: str, focus: str) -> str:
    key = match_name(payload.get("instruments") or {}, name)
    record = payload["instruments"][key]
    if not isinstance(record, dict):
        raise ValueError(f"{key} has no image record")
    record["focus"] = focus
    return key


def main():
    bust_browser_cache, image_focus, write_json, running_bind_host = helpers()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Instrument name as shown on the genre panel")
    parser.add_argument("--image-focus", required=True, help="object-position, e.g. 'center top' or '50% 20%'")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--allow-mvp-lock", action="store_true", help="Override MVP country lock after deliberate review")
    args = parser.parse_args()
    try:
        from mvp_locks import assert_instrument_unlocked
        assert_instrument_unlocked(args.name.strip(), allow=args.allow_mvp_lock)
        focus = image_focus(args.image_focus)
        payload = load_instruments()
        key = apply_instrument_focus(payload, args.name.strip(), focus)
    except ValueError as exc:
        parser.error(str(exc))
    write_json(WEB, payload)
    RESEARCH.parent.mkdir(parents=True, exist_ok=True)
    write_json(RESEARCH, payload)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bust_browser_cache(stamp)
    print(f"updated {key}")
    print(f"image-focus: {focus}")
    if args.rebuild:
        environment = os.environ.copy()
        environment["ATLAS_BIND_HOST"] = running_bind_host()
        subprocess.run(
            ["docker", "compose", "up", "--build", "-d", "--wait"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        print(f"rebuilt atlas on {environment['ATLAS_BIND_HOST']}:5186")
    else:
        print("browser data updated; pass --rebuild to refresh the running container")


if __name__ == "__main__":
    main()
