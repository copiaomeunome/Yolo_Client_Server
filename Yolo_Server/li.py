import json
import argparse


def parse_pos(pos_str):
    """
    Converts a string like "(263,115),(639,479)" into a tuple (x1, y1, x2, y2).
    """
    parts = pos_str.replace("(", "").replace(")", "").split(",")
    vals = [int(p.strip()) for p in parts]
    if len(vals) != 4:
        raise ValueError(f"Invalid position format: {pos_str}")
    return vals[0], vals[1], vals[2], vals[3]


def boxes_overlap(a, b):
    """
    Checks whether two axis-aligned rectangles overlap.
    a, b: (x1, y1, x2, y2)
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    return inter_x2 > inter_x1 and inter_y2 > inter_y1


def horizontally_aligned(a, b, tolerance=0.2):
    """
    Checks whether two boxes are horizontally aligned, based on the Y coordinate
    of their centers.

    We say they are aligned if the absolute difference between their center Y
    positions is less than or equal to `tolerance * min(height_a, height_b)`.
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    # Heights
    h_a = ay2 - ay1
    h_b = by2 - by1
    ref_h = min(h_a, h_b)

    if ref_h <= 0:
        return False

    # Center Y coordinates
    cy_a = (ay1 + ay2) / 2.0
    cy_b = (by1 + by2) / 2.0

    return abs(cy_a - cy_b) <= tolerance * ref_h


def analyze_log(log_data):
    """
    Receives the original log (a dict) and returns a new dict:
    { timestamp: [event descriptions...] }
    """

    timestamps = sorted(
        log_data.keys(),
        key=lambda t: tuple(map(int, t.split(":")))
    )

    result = {}
    prev_objects = {}
    prev_overlaps = set()
    prev_alignments = set()

    for t in timestamps:
        frame = log_data[t]
        events = []

        objects = {}
        for category, objs in frame.items():
            for o in objs:
                oid = o["ID"]
                bbox = parse_pos(o["pos"])
                objects[(category, oid)] = bbox

        current_keys = set(objects.keys())
        prev_keys = set(prev_objects.keys())

        entered = current_keys - prev_keys
        exited = prev_keys - current_keys

        for cat, oid in sorted(entered):
            events.append(f"{cat} {oid} entered the scene.")

        for cat, oid in sorted(exited):
            events.append(f"{cat} {oid} left the scene.")

        keys = list(objects.keys())
        overlaps = set()
        alignments = set()

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                k1 = keys[i]
                k2 = keys[j]
                box1 = objects[k1]
                box2 = objects[k2]

                if boxes_overlap(box1, box2):
                    pair = frozenset((k1, k2))
                    overlaps.add(pair)

                if horizontally_aligned(box1, box2):
                    pair = frozenset((k1, k2))
                    alignments.add(pair)

        for pair in overlaps - prev_overlaps:
            (cat1, id1), (cat2, id2) = sorted(list(pair))
            events.append(f"{cat1} {id1} is overlapping {cat2} {id2}.")

        for pair in prev_overlaps - overlaps:
            (cat1, id1), (cat2, id2) = sorted(list(pair))
            events.append(f"{cat1} {id1} stopped overlapping {cat2} {id2}.")

        for pair in alignments - prev_alignments:
            (cat1, id1), (cat2, id2) = sorted(list(pair))
            events.append(f"{cat1} {id1} is horizontally aligned with {cat2} {id2}.")

        for pair in prev_alignments - alignments:
            (cat1, id1), (cat2, id2) = sorted(list(pair))
            events.append(
                f"{cat1} {id1} is no longer horizontally aligned with {cat2} {id2}."
            )

        if events:
            result[t] = events

        prev_objects = objects
        prev_overlaps = overlaps
        prev_alignments = alignments

    return result

def log_interpreter(input_log: str, output_log: str):
    with open(input_log, "r", encoding="utf-8") as f:
        log_data = json.load(f)

    if isinstance(log_data, list):

        if "timestamp" in log_data[0]:
            new_log = {}
            for entry in log_data:
                ts = entry["timestamp"]
                frame = {k: v for k, v in entry.items() if k != "timestamp"}
                new_log[ts] = frame
            log_data = new_log

        elif len(log_data) > 0 and isinstance(log_data[0], dict):
            new_log = {}
            for entry in log_data:
                for k, v in entry.items():
                    new_log[k] = v
            log_data = new_log

        else:
            raise ValueError("Unrecognized log format.")

    analyzed = analyze_log(log_data)

    with open(output_log, "w", encoding="utf-8") as f:
        json.dump(analyzed, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Output saved to: {output_log}")
