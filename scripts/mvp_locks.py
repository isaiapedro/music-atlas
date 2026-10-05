"""Load and enforce MVP country locks so reviewed presentation is not overwritten."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKS_PATH = ROOT / "research" / "mvp_country_locks.json"


def load_locks():
    if not LOCKS_PATH.exists():
        return {"version": 1, "locks": []}
    return json.loads(LOCKS_PATH.read_text(encoding="utf-8"))


def locked_rows():
    return list(load_locks().get("locks") or [])


def locked_countries():
    return {row["country"] for row in locked_rows()}


def locked_genre_ids():
    ids = set()
    for row in locked_rows():
        ids.update(row.get("published_genre_ids") or [])
        ids.update(row.get("listening_room_genre_ids") or [])
    return ids


def locked_instrument_names():
    names = set()
    for row in locked_rows():
        names.update(row.get("instrument_names") or [])
    return names


def locked_record_ids():
    ids = set()
    for row in locked_rows():
        ids.update(row.get("manual_record_selection_ids") or [])
    return ids


def lock_for_country(code):
    for row in locked_rows():
        if row.get("country") == code:
            return row
    return None


def lock_for_genre(genre_id):
    for row in locked_rows():
        if genre_id in (row.get("published_genre_ids") or []):
            return row
        if genre_id in (row.get("listening_room_genre_ids") or []):
            return row
    return None


def lock_for_instrument(name):
    for row in locked_rows():
        if name in (row.get("instrument_names") or []):
            return row
    return None


def lock_for_record(record_id):
    for row in locked_rows():
        if record_id in (row.get("manual_record_selection_ids") or []):
            return row
    return None


def refuse(lock, target, allow=False):
    if allow or lock is None:
        return
    flag = lock.get("allow_explicit_override_flag") or "--allow-mvp-lock"
    raise SystemExit(
        f"MVP lock protects {lock['country']} ({target}). "
        f"Pass {flag} only after deliberate human review. "
        f"See research/mvp_country_locks.json and research/INDEX.md."
    )


def assert_genre_unlocked(genre_id, allow=False):
    refuse(lock_for_genre(genre_id), f"genre {genre_id}", allow)


def assert_instrument_unlocked(name, allow=False):
    refuse(lock_for_instrument(name), f"instrument {name}", allow)


def assert_record_unlocked(record_id, allow=False):
    refuse(lock_for_record(record_id), f"record {record_id}", allow)


def assert_country_unlocked(code, allow=False):
    refuse(lock_for_country(code), f"country {code}", allow)


def protected_fields(genre_id):
    lock = lock_for_genre(genre_id)
    if not lock:
        return set()
    return set(lock.get("protected_fields") or [])


def catalogue_lock_violations(before_entries, after_entries, allow=False):
    if allow:
        return []
    before = {item["id"]: item for item in before_entries}
    after = {item["id"]: item for item in after_entries}
    violations = []
    for genre_id in locked_genre_ids():
        old = before.get(genre_id)
        new = after.get(genre_id)
        if old is None and new is None:
            continue
        if old is None or new is None:
            violations.append(f"{genre_id}: published MVP genre missing after write")
            continue
        for field in protected_fields(genre_id):
            if old.get(field) != new.get(field):
                violations.append(f"{genre_id}.{field}")
    return violations


def assert_catalogue_preserves_locks(before_entries, after_entries, allow=False):
    violations = catalogue_lock_violations(before_entries, after_entries, allow=allow)
    if violations:
        joined = ", ".join(violations[:12])
        raise SystemExit(
            "MVP lock would be overwritten: "
            f"{joined}. Pass --allow-mvp-lock only after deliberate human review."
        )
