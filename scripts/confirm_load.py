#!/usr/bin/env python3
"""
Mark bales as Transported and update packing-state.json after load confirmation.

Run after Gareth types 'load confirmed' and the packing sheet has been accepted.

Usage:
    python confirm_load.py \
        --bale-log bale-log.csv \
        --bales 338,339,340,341 \
        --load-number 5 \
        --haulier "Nigel" \
        --date 01/05/2026 \
        --state packing-state.json \
        --output-bale-log bale-log-updated.csv \
        --output-state packing-state-updated.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def load_bale_log(path):
    """Return (fieldnames, rows) from bale-log.csv."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames[:]
        rows = [dict(r) for r in reader]
    return fieldnames, rows


def ensure_transport_fields(fieldnames):
    """Add transport tracking columns if they don't exist yet."""
    for col in ["Transported", "Load Number", "Load Date"]:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames


def mark_transported(rows, bale_numbers, load_number, date_str):
    """
    Set Transported = TRUE for the specified bales.

    Returns (updated_rows, not_found) — not_found lists any bale numbers
    that weren't in the log so Claude can flag them.
    """
    target = set(str(b).strip() for b in bale_numbers)
    found  = set()

    for row in rows:
        bale_no = str(row["Bale No."]).strip()
        if bale_no in target:
            row["Transported"] = "TRUE"
            row["Load Number"]  = str(load_number)
            row["Load Date"]    = date_str
            found.add(bale_no)

    not_found = sorted(target - found)
    return rows, not_found


def sum_net_weights(rows, bale_numbers):
    """Sum Net Weight (kg) for the specified bales."""
    target = set(str(b).strip() for b in bale_numbers)
    total  = 0.0
    for row in rows:
        if str(row["Bale No."]).strip() in target:
            try:
                total += float(row["Net Weight (kg)"])
            except (ValueError, KeyError):
                pass
    return total


def update_state(state_path, load_number, net_weight, haulier, date_str):
    """Read, update, and return the new packing-state dict."""
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)

    state["last_load_number"]  = load_number
    state["running_total_kg"]  = round(
        float(state.get("running_total_kg", 0)) + net_weight, 1
    )
    state["last_load_date"]    = date_str
    state["last_haulier"]      = haulier

    return state


def write_bale_log(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Mark bales as Transported and update packing-state.json"
    )
    parser.add_argument("--bale-log",          required=True,           help="bale-log.csv path")
    parser.add_argument("--bales",             required=True,           help="Comma-separated bale numbers")
    parser.add_argument("--load-number",       required=True, type=int, help="Load number being confirmed")
    parser.add_argument("--haulier",           required=True,           help="Haulier name")
    parser.add_argument("--date",              required=True,           help="Load date DD/MM/YYYY")
    parser.add_argument("--state",             required=True,           help="packing-state.json path")
    parser.add_argument("--output-bale-log",   required=True,           help="Output path for updated bale-log.csv")
    parser.add_argument("--output-state",      required=True,           help="Output path for updated packing-state.json")
    args = parser.parse_args()

    bale_numbers = [b.strip() for b in args.bales.split(",") if b.strip()]

    fieldnames, rows = load_bale_log(args.bale_log)
    fieldnames = ensure_transport_fields(fieldnames)

    rows, not_found = mark_transported(rows, bale_numbers, args.load_number, args.date)

    if not_found:
        print("WARNING — these bale numbers were not found in the log:", file=sys.stderr)
        for b in not_found:
            print(f"  ! Bale {b}", file=sys.stderr)
        # Non-fatal — proceed with the ones that were found

    net_weight = sum_net_weights(rows, bale_numbers)
    new_state  = update_state(args.state, args.load_number, net_weight, args.haulier, args.date)

    write_bale_log(args.output_bale_log, fieldnames, rows)

    with open(args.output_state, "w", encoding="utf-8") as f:
        json.dump(new_state, f, indent=2)

    marked = len(bale_numbers) - len(not_found)
    print(f"OK Marked {marked} bales as Transported (Load {args.load_number})")
    print(f"OK Net weight added: {net_weight:.1f}kg")
    print(f"OK New running total: {new_state['running_total_kg']:.1f}kg")
    print(f"OK Updated files: {args.output_bale_log}, {args.output_state}")


if __name__ == "__main__":
    main()
