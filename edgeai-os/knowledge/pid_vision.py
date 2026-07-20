"""
P&ID / engineering-drawing vision — real OpenCV pipeline (not a stub).

Extracts from a drawing image:
  - candidate equipment SYMBOLS (circles ≈ pumps/instruments, rectangles ≈
    vessels/valves) via Hough circles + contour analysis,
  - LINES (piping connectivity) via Hough line transform,
  - equipment TAGS (P-101A, V-204 …) via Tesseract OCR when available.

Honest scope: tuned for clean, digitally-rendered P&IDs (like the bundled
sample); accuracy on scanned/messy legacy drawings will be modest. That is the
industry-standard hard problem — this is a credible pipeline demonstrating the
approach, with detected tags flowing into the same knowledge graph as document
entities.
"""

from __future__ import annotations

import os
import re

_TAG_RE = re.compile(r"\b([A-Z]{1,3})-(\d{2,4})([A-Z]?)\b")
# PID/DWG/REV excluded so drawing numbers (DWG-PID-0007) aren't read as equipment.
_NON_EQUIPMENT_PREFIXES = {"MNT", "RPT", "LOG", "DOC", "WO", "RFI", "STD", "SEC",
                           "PID", "DWG", "REV"}


def _cv2():
    import cv2  # noqa: F401
    return cv2


def analyze_pid(image_path: str) -> dict:
    """Analyze a P&ID/drawing image. Returns symbols, lines, tags, and a summary."""
    cv2 = _cv2()
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # --- circles (pumps / instruments bubbles) ---
    blur = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40,
                               param1=120, param2=40,
                               minRadius=int(min(h, w) * 0.015),
                               maxRadius=int(min(h, w) * 0.12))
    circle_syms = []
    if circles is not None:
        for c in circles[0]:
            circle_syms.append({"type": "circle_symbol", "x": int(c[0]), "y": int(c[1]), "r": int(c[2])})

    # --- rectangles (vessels / valve bodies) via contours ---
    edges = cv2.Canny(gray, 60, 160)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rect_syms = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (h * w) * 0.0005 or area > (h * w) * 0.2:
            continue
        approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, bw, bh = cv2.boundingRect(approx)
            rect_syms.append({"type": "rect_symbol", "x": int(x), "y": int(y),
                              "w": int(bw), "h": int(bh)})

    # --- piping lines ---
    lines = cv2.HoughLinesP(edges, 1, 3.14159 / 180, threshold=80,
                            minLineLength=int(min(h, w) * 0.1), maxLineGap=8)
    n_lines = 0 if lines is None else len(lines)

    # --- OCR tag extraction (optional) ---
    tags, ocr_used = [], False
    try:
        import pytesseract

        cmd = os.environ.get("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        # Two passes: default layout + sparse-text mode (psm 11) — drawings
        # scatter short labels, which the default page model often misses.
        # Upscale 2x first; small tag text OCRs far better at higher resolution.
        big = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        text = (pytesseract.image_to_string(big) + "\n"
                + pytesseract.image_to_string(big, config="--psm 11"))
        ocr_used = True
        for m in _TAG_RE.finditer(text or ""):
            if m.group(1) not in _NON_EQUIPMENT_PREFIXES and m.group(0) not in tags:
                tags.append(m.group(0))
    except Exception:
        pass

    return {
        "image": os.path.basename(image_path),
        "size": {"w": w, "h": h},
        "symbols": {"circles": len(circle_syms), "rectangles": len(rect_syms),
                    "detail": (circle_syms + rect_syms)[:50]},
        "piping_lines": n_lines,
        "equipment_tags": tags,
        "ocr_used": ocr_used,
        "summary": (f"{len(circle_syms)} circular symbol(s), {len(rect_syms)} rectangular "
                    f"symbol(s), {n_lines} piping line segment(s), "
                    f"{len(tags)} equipment tag(s){'' if ocr_used else ' (OCR unavailable)'}"),
    }


def ingest_pid(image_path: str, graph) -> dict:
    """Analyze a drawing and write its equipment tags into the knowledge graph
    (same graph as document entities → cross-modal linkage: a tag seen in both
    a P&ID and a maintenance report resolves to one node)."""
    result = analyze_pid(image_path)
    node_ids = []
    for tag in result["equipment_tags"]:
        node_ids.append(graph.add_entity("equipment_tag", tag, source_doc=image_path))
    # Co-membership edges: tags on one drawing are physically related.
    for i, a in enumerate(node_ids):
        for b in node_ids[i + 1:]:
            graph.add_relationship(a, b, relation="on_same_drawing")
    result["graph_nodes_added"] = len(node_ids)
    return result
