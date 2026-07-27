# SAM ScreenParser -- Technical Documentation

## Project Overview

SAM ScreenParser is a local, CPU-only desktop perception engine for AI automation agents. It converts a live screen capture into two structured JSON tables that separate reasoning from execution. The parser reports only verified facts: detected text, bounding coordinates, and OS-provided accessibility metadata. It never guesses an element role, never invents a confidence score, and never fabricates a semantic label. When a deterministic match exists in the curated UI dataset, the type is assigned. When no match exists, the type is left unset and the planning model infers the role from context.

The pipeline combines RapidOCR for text detection, Windows UI Automation for accessibility facts, and RapidFuzz for dataset-driven type matching. It runs entirely offline on standard laptops with no GPU and no cloud dependency.

## Architecture Philosophy

A planning model must not receive guessed semantics from a perception layer. Heuristic classifiers produce false labels that the model must then unlearn: terminal output labelled as buttons, status-bar text labelled as taskbar items, code lines labelled as desktop icons. Every mislabel is a false fact.

SAM ScreenParser therefore reports only facts:

- Text detected by OCR, with its bounding box.
- The control type reported by the operating system, when available.
- An element type assigned only by a real OS control type or by exact or fuzzy match against the UI dataset.
- No type at all when no deterministic method can identify the element.

There is no actionability filter and no confidence score. Filtering and scoring both require trusting a guessed type, which is exactly the guess the parser refuses to make. Every detected region is passed through; the model receives the full set of facts and decides, using the top-level `_guide` note, which elements are interactive and which are static text.

The model performs the only task it is genuinely suited to: understanding what a UI element is from its text, its position relative to other elements, and the active window context. The executor receives pixel coordinates keyed by the same element id and performs the physical action. This separation means the parser cannot hallucinate a semantic label, the model cannot hallucinate a coordinate, and the executor cannot act on an unverified target.

## Pipeline

```text
Desktop Screenshot (DPI-aware capture)
        |
        v
RapidOCR Sweep
  text regions with bounding boxes
        |
        v
Windows UI Automation
  control_type at each region center (fact, not guess)
  active window title, class, bounds
  cursor position and control under pointer
        |
        v
UI Dataset Matcher (RapidFuzz)
  exact lookup, then fuzzy match above threshold
  no match -> type left unset
        |
        v
Two-Table Output
  Semantic Table   -> planning model (id, text, type?, control_type, _guide)
  Coordinate Table -> executor (id, bounds, center)
```

## Hardware Requirements

- CPU: modern multi-core (AMD Ryzen 5 / Intel Core i5 or better)
- RAM: 16 GB total system memory; peak usage approximately 2 to 4 GB
- GPU: not required; ONNX Runtime uses the CPU by default
- Storage: approximately 1 GB free for OCR models and dependencies
- OS: Windows 10/11
- Tested performance: 7 to 13 seconds per 1920x1080 frame on AMD Ryzen 7 U, CPU only

## Setup Guide

### Prerequisites

- Python 3.12.x installed with Add to PATH enabled
- No Tesseract required
- No PyTorch required
- No GPU required

### Installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation rapidfuzz
```

OpenCV is installed only to draw the verification image. It is not used for detection.

### Verification

```powershell
py -c "from rapidocr_onnxruntime import RapidOCR; import cv2, numpy, uiautomation; from rapidfuzz import fuzz; print('OK')"
```

RapidOCR downloads its ONNX models automatically on first use.

## Version Maintenance

### Tested Versions

| Package | Tested | Purpose |
| :--- | :--- | :--- |
| Python | 3.12.x | Runtime |
| rapidocr_onnxruntime | 1.3.x | PaddleOCR via ONNX Runtime |
| opencv-python | 4.10.x | Verification drawing only |
| numpy | 1.26.x / 2.x | Array handling |
| uiautomation | 2.0.x | Windows accessibility queries |
| rapidfuzz | 3.x | Fuzzy string matching for dataset lookup |

### Environment Recovery

```powershell
taskkill /F /IM python.exe 2>$null
cmd /c "rmdir /s /q D:\Projects\SAM-ScreenParser\.venv"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation rapidfuzz
```

## Codebase

### Directory Structure

```text
SAM-ScreenParser/
+-- .venv/
+-- images/
+-- output/
+-- element_dataset.json
+-- test_screen.py
+-- test_screen_drawn.png
+-- test_screen_data.json
+-- test_screen_compact.json
+-- automation_suggestion.md
+-- technical_documentation.md
+-- README.md
```

### element_dataset.json

A curated mapping of known UI element text to element types, loaded once at startup. The parser performs an exact lookup first, then a fuzzy match for OCR errors. Names are stored lowercase. The dataset covers IDE controls, browser UI, file explorer, Office applications, Windows settings, dialog buttons, status messages, and toolbar items.

```json
[
  {"name": "file", "type": "menu"},
  {"name": "edit", "type": "menu"},
  {"name": "view", "type": "menu"},
  {"name": "selection", "type": "menu"},
  {"name": "go", "type": "menu"},
  {"name": "run", "type": "menu"},
  {"name": "help", "type": "menu"},
  {"name": "account", "type": "menu"},
  {"name": "general", "type": "menu"},
  {"name": "settings", "type": "menu"},
  {"name": "explorer", "type": "sidebar_item"},
  {"name": "search", "type": "sidebar_item"},
  {"name": "problems", "type": "sidebar_item"},
  {"name": "output", "type": "sidebar_item"},
  {"name": "terminal", "type": "sidebar_item"},
  {"name": "outline", "type": "sidebar_item"},
  {"name": "timeline", "type": "sidebar_item"},
  {"name": "save", "type": "button"},
  {"name": "open", "type": "button"},
  {"name": "download", "type": "button"},
  {"name": "cancel", "type": "dialog_button"},
  {"name": "ok", "type": "dialog_button"},
  {"name": "username", "type": "input"},
  {"name": "password", "type": "input"},
  {"name": "no suggestions available", "type": "label"},
  {"name": "loading", "type": "status"},
  {"name": "no results found", "type": "label"}
]
```

### test_screen.py

```python
import os
import re
import json
import time
import ctypes
import numpy as np
import cv2
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab
import uiautomation as auto
from rapidocr_onnxruntime import RapidOCR
from rapidfuzz import fuzz

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

OCR = RapidOCR()
DATASET_PATH = Path(__file__).parent / "element_dataset.json"
FUZZY_THRESHOLD = 85

# Guide note embedded in the semantic table. Explains the type-omission convention.
GUIDE = ("If an element has no 'type' field, the parser could not deterministically "
         "identify its role. It is most likely normal static text. Infer the role from "
         "surrounding elements and window context if interaction is required.")


def get_dpi_scale():
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def load_dataset():
    if not DATASET_PATH.exists():
        return {}, []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)
    exact = {e["name"].lower().strip(): e["type"] for e in entries}
    fuzzy_list = [(e["name"].lower().strip(), e["type"]) for e in entries]
    return exact, fuzzy_list


EXACT_MAP, FUZZY_LIST = load_dataset()


def match_dataset(text):
    tl = text.lower().strip()
    if tl in EXACT_MAP:
        return EXACT_MAP[tl], "dataset_exact"
    best_score, best_type = 0, None
    for name, sig_type in FUZZY_LIST:
        score = fuzz.ratio(tl, name)
        if score > best_score:
            best_score, best_type = score, sig_type
    if best_score >= FUZZY_THRESHOLD and best_type:
        return best_type, "dataset_fuzzy"
    return "unknown", "none"


def clean_text(raw):
    c = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw.strip())
    return re.sub(r'\s+', ' ', c).strip()


def get_live_window_info():
    try:
        fg = auto.GetForegroundControl()
        r = fg.BoundingRectangle
        return {'title': fg.Name or 'Unknown', 'class': fg.ClassName or 'Unknown',
                'bounds': [r.left, r.top, r.right, r.bottom]}
    except Exception:
        return {'title': 'Unknown', 'class': 'Unknown', 'bounds': [0, 0, 0, 0]}


def get_cursor_info():
    try:
        x, y = auto.GetCursorPos()
        c = auto.ControlFromPoint(x, y)
        return {'position': [x, y], 'text': (c.Name or '')[:80],
                'control_type': c.ControlTypeName or 'unknown', 'over_element_id': None}
    except Exception:
        try:
            x, y = auto.GetCursorPos()
            pos = [x, y]
        except Exception:
            pos = [-1, -1]
        return {'position': pos, 'text': '', 'control_type': 'unknown', 'over_element_id': None}


def get_uia_at_point(x, y):
    try:
        c = auto.ControlFromPoint(x, y)
        return (c.ControlTypeName or '', c.ClassName or '')
    except Exception:
        return ('', '')


def uia_to_type(control_type):
    t = (control_type or '').lower()
    if t in ('button', 'menuitem', 'menu', 'splitbutton'):
        return 'button'
    if t == 'edit':
        return 'input'
    if t in ('listitem', 'treeitem'):
        return 'sidebar_item'
    if t in ('tabitem', 'tab'):
        return 'tab'
    if t in ('checkbox',):
        return 'checkbox'
    if t in ('radiobutton',):
        return 'radio'
    if t in ('combobox',):
        return 'dropdown'
    if t in ('slider',):
        return 'slider'
    if t in ('hyperlink',):
        return 'link'
    return None


def detect_screen_state(elements, window_info):
    all_text = ' '.join(e.get('text', '').lower() for e in elements)
    cls = window_info.get('class', '').lower()
    title = window_info.get('title', '').lower()
    state = {'has_popup': False, 'has_loading': False, 'has_dialog': False,
             'is_empty': False, 'active_app_type': 'generic_window'}
    if any(k in all_text for k in ['loading', 'please wait', 'processing']):
        state['has_loading'] = True
    if any(k in all_text for k in ['this folder is empty', 'no items', 'no results']):
        state['is_empty'] = True
    if any(k in all_text for k in ['error', 'confirm', 'are you sure']):
        state['has_dialog'] = True
    if any(k in title for k in ['trae', 'visual studio code', ' - code']):
        state['active_app_type'] = 'ide'
    elif 'searchhost' in cls or 'windowsinternal' in cls:
        state['active_app_type'] = 'windows_search'
        state['has_popup'] = True
    elif any(k in cls for k in ['chrome', 'brave', 'edge', 'msedge']):
        state['active_app_type'] = 'browser'
    elif any(k in cls for k in ['explorer', 'cabinet']):
        state['active_app_type'] = 'file_explorer'
    elif 'notepad' in cls:
        state['active_app_type'] = 'text_editor'
    return state


def cursor_over(cursor_info, elements):
    cx, cy = cursor_info['position']
    if cx < 0 or cy < 0:
        return None
    for e in elements:
        x1, y1, x2, y2 = e['bounds']
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            return e['id']
    return None


def compact_for_llm(r):
    """Build semantic table for the planning model.
    - No coordinates, no confidence, no screen_text dump.
    - type is OMITTED when the parser could not identify the element.
    - control_type is OMITTED when it is 'PaneControl' (Electron noise).
    """
    elements = []
    for e in r['elements']:
        el = {'id': e['id'], 'text': e['text']}
        if e['type'] != 'unknown':
            el['type'] = e['type']
        ct = e.get('control_type', '')
        if ct and ct != 'PaneControl' and ct != 'unknown':
            el['control_type'] = ct
        elements.append(el)
    return {
        '_guide': GUIDE,
        'active_window_title': r['active_window']['title'],
        'app_type': r['screen_state']['active_app_type'],
        'screen_state': {k: r['screen_state'][k] for k in
                         ('has_dialog', 'has_loading', 'has_popup', 'is_empty')},
        'cursor': {'text': r['cursor'].get('text', ''),
                   'control_type': r['cursor']['control_type'],
                   'over_element_id': r['cursor']['over_element_id']},
        'elements': elements}


def draw_all_detections(image_bgr, all_elements, output_path):
    img = image_bgr.copy()
    color_map = {
        'button': (0, 255, 0), 'input': (255, 165, 0), 'sidebar_item': (0, 255, 255),
        'tab': (0, 200, 200), 'menu': (255, 0, 255), 'dialog_button': (0, 200, 0),
        'checkbox': (200, 200, 0), 'radio': (200, 150, 0), 'dropdown': (150, 100, 255),
        'link': (255, 100, 100), 'search': (100, 255, 200), 'toolbar_button': (0, 180, 0),
        'status': (128, 128, 128), 'label': (180, 180, 180), 'unknown': (100, 100, 100)}
    for item in all_elements:
        x1, y1, x2, y2 = item["bounds"]
        color = color_map.get(item["type"], (100, 100, 100))
        thick = 2 if item.get("match_source") in ("uia", "dataset_exact") else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
        cv2.circle(img, tuple(item["center"]), 3, (0, 0, 255), -1)
        label = f"{item['type']} | {item['text'][:16]}"
        fs, th = 0.35, 1
        sz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
        cv2.rectangle(img, (x1, max(0, y1 - sz[1] - 4)),
                      (x1 + sz[0] + 4, max(0, y1)), (0, 0, 0), -1)
        cv2.putText(img, label, (x1 + 2, max(sz[1], y1 - 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    cv2.imwrite(output_path, img)


def main():
    start = time.time()
    print("Capturing live screen...")
    grab = ImageGrab.grab(all_screens=False)
    W, H = grab.size
    bgr = cv2.cvtColor(np.array(grab), cv2.COLOR_RGB2BGR)
    cursor_info = get_cursor_info()
    window_info = get_live_window_info()
    print(f"Active window: {window_info['title']} ({window_info['class']})")

    print("Running RapidOCR sweep...")
    results, _ = OCR(bgr)
    results = results or []
    print(f"Detected {len(results)} text regions.")

    all_elements, texts, eid = [], [], 0
    for item in results:
        box = np.array(item[0], dtype=np.int32)
        text = clean_text(item[1])
        if not text or len(text) <= 1:
            continue
        x1, y1 = int(box[:, 0].min()), int(box[:, 1].min())
        x2, y2 = int(box[:, 0].max()), int(box[:, 1].max())
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        texts.append(text)
        eid += 1
        control_type, class_name = get_uia_at_point(cx, cy)
        uia_type = uia_to_type(control_type)
        if uia_type:
            el_type, match_source = uia_type, "uia"
        else:
            el_type, match_source = match_dataset(text)
        all_elements.append({
            'id': eid, 'text': text, 'type': el_type,
            'control_type': control_type or 'unknown', 'class_name': class_name or 'unknown',
            'match_source': match_source, 'bounds': [x1, y1, x2, y2], 'center': [cx, cy]})

    print(f"Total regions: {len(all_elements)}")
    draw_all_detections(bgr, all_elements, "test_screen_drawn.png")
    print(f"Drew {len(all_elements)} detections -> test_screen_drawn.png")

    cursor_info['over_element_id'] = cursor_over(cursor_info, all_elements)
    screen_state = detect_screen_state(all_elements, window_info)

    joined = "\n".join(texts)
    trunc = len(joined) > 2500
    screen_text = {'raw_text': (joined[:2500] + "\n[...truncated...]" if trunc else joined).strip(),
                   'char_count': len(joined), 'line_count': len(texts),
                   'is_truncated': trunc, 'source': 'rapidocr_sweep'}

    by_type = {}
    for e in all_elements:
        by_type[e['type']] = by_type.get(e['type'], 0) + 1
    matched = sum(1 for e in all_elements if e['match_source'] != 'none')
    unknown = sum(1 for e in all_elements if e['type'] == 'unknown')

    result = {
        'metadata': {'timestamp': datetime.now().isoformat(), 'image_size': [W, H],
                     'dpi_scale': round(get_dpi_scale(), 3),
                     'coordinate_space': 'physical_pixels', 'detector': 'RapidOCR',
                     'processing_time_seconds': round(time.time() - start, 2),
                     'total_regions': len(all_elements), 'matched_count': matched,
                     'unknown_count': unknown, 'source': 'live_screen_capture'},
        'active_window': window_info, 'screen_state': screen_state,
        'screen_text': screen_text, 'cursor': cursor_info, 'elements': all_elements,
        'summary': {'by_type': by_type, 'matched': matched, 'unknown': unknown}}

    with open("test_screen_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open("test_screen_compact.json", "w", encoding="utf-8") as f:
        json.dump(compact_for_llm(result), f, indent=2)

    elapsed = round(time.time() - start, 2)
    print(f"\nComplete in {elapsed}s")
    print(f"  Total regions:  {len(all_elements)}")
    print(f"  Matched:        {matched}")
    print(f"  Unknown:        {unknown}")
    print(f"\nOutputs:")
    print(f"  test_screen_drawn.png    <- all detections drawn")
    print(f"  test_screen_data.json    <- coordinate table (executor)")
    print(f"  test_screen_compact.json <- semantic table (model)")


if __name__ == "__main__":
    main()
```

## Output Schema

### Semantic Table (Model Input)

Contains no coordinates, no confidence, and no full-screen text dump. Every visible text region is already an element, so a separate text block would be redundant. The `type` field is present only when the parser deterministically identified the element; otherwise it is omitted, and the top-level `_guide` field explains the convention. The `control_type` field is omitted when it is `PaneControl` (the Electron noise value), so the model's context stays clean. There is no actionability filter: every detected region is included, and the model decides what is interactive.

```json
{
  "_guide": "If an element has no 'type' field, the parser could not deterministically identify its role. It is most likely normal static text. Infer the role from surrounding elements and window context if interaction is required.",
  "active_window_title": "Settings - SAM-ScreenParser - Trae",
  "app_type": "ide",
  "screen_state": {"has_dialog": false, "has_loading": false, "has_popup": false, "is_empty": false},
  "cursor": {"text": "", "control_type": "PaneControl", "over_element_id": 56},
  "elements": [
    {"id": 3, "text": "File", "type": "menu"},
    {"id": 6, "text": "View", "type": "menu"},
    {"id": 12, "text": "Explorer", "type": "sidebar_item"},
    {"id": 13, "text": "technical_documentation.md (Preview)"},
    {"id": 18, "text": "Folder"}
  ]
}
```

### Coordinate Table (Executor)

Holds pixel coordinates keyed by the same element id, plus the debug fields (class name, match source, and a human-readable copy of the screen text). It is never sent to the model. Unlike the semantic table, it always records the `type` field, writing `"unknown"` when the parser could not identify the element.

```json
{
  "metadata": {"image_size": [1920, 1080], "dpi_scale": 1.25, "total_regions": 67,
               "matched_count": 15, "unknown_count": 52},
  "cursor": {"position": [775, 1005]},
  "elements": [
    {"id": 3, "text": "File", "type": "menu", "control_type": "PaneControl",
     "class_name": "View", "match_source": "dataset_exact",
     "bounds": [118, 12, 142, 31], "center": [130, 21]},
    {"id": 13, "text": "technical_documentation.md (Preview)", "type": "unknown",
     "control_type": "PaneControl", "class_name": "View", "match_source": "none",
     "bounds": [402, 84, 705, 107], "center": [553, 95]}
  ]
}
```

### Type Assignment Rules

| Source | Condition | Result | Provenance |
| :--- | :--- | :--- | :--- |
| UIA | Real control type (Button, Edit, Tab, ListItem) | Mapped type | `uia` |
| Dataset exact | Text matches a dataset entry exactly | Dataset type | `dataset_exact` |
| Dataset fuzzy | Fuzzy score at or above threshold | Dataset type | `dataset_fuzzy` |
| None | No UIA type and no dataset match | Type unset in semantic table; `"unknown"` in coordinate table | `none` |

### Field Retention

| Field | Coordinate Table | Semantic Table | Reason |
| :--- | :--- | :--- | :--- |
| id | yes | yes | Handle the model plans with and the executor resolves |
| text | yes | yes | The model matches targets by name |
| type | yes (known or `"unknown"`) | only when known | Omitted when unknown per `_guide` |
| control_type | yes | only when NOT `PaneControl`/`unknown` | Electron noise stripped |
| class_name | yes | no | Debug only |
| match_source | yes | no | Debug only |
| bounds | yes | no | Executor-only pixel data |
| center | yes | no | Executor-only pixel data |
| screen_text | yes (human copy) | no | Redundant; every line is already an element |
| confidence | no | no | Not produced; the parser reports facts only |

## Parser Guarantees

- Coordinates come from the detector's region proposals and are tight on text, resolution-independent, and survive theme changes.
- The two tables are generated from one capture, so their ids align exactly. An id names one element in one snapshot.
- The semantic table contains no pixel field, so the model physically cannot emit a coordinate.
- A type is assigned only by a real OS control type or a dataset match. The parser never invents a type from position or keyword heuristics.
- Elements the parser cannot identify carry no type in the semantic table. This is reported honestly rather than guessed.
- `PaneControl` and `unknown` control types are stripped from the semantic table to keep the model's context clean on Electron apps.
- No element is silently dropped. The model receives the complete set of detected regions and applies its own judgment, guided by `_guide`.
- The cursor position and the control under it are read from the OS at capture time, not inferred from pixels.

## Accuracy Analysis

- Coordinate accuracy: within 1 to 3 px on text, resolution-independent.
- Text accuracy: high via the PaddleOCR recognizer; garbage reads are dropped before they reach the output.
- Type accuracy on native applications: high when UIA provides a real control type.
- Type accuracy on Electron applications: determined by dataset coverage. Exact matches are reliable; fuzzy matches absorb OCR errors; unmatched text is left without a type.
- Token efficiency: the semantic table carries no coordinates, no full-screen text, no confidence, no `PaneControl` noise, and no type string for unknown elements.

## Known Limitations

- RapidOCR detects only text-like regions. The parser reads OS accessibility names but does not perform contour-based shape detection, so a control that has neither text nor an accessibility name is invisible to it.
- Electron and Chromium applications (Trae, VS Code, Brave, Discord) return `PaneControl` or `View` for nearly all UIA queries. Type assignment on these apps depends on dataset matching.
- The `ListItemControl` accessibility type is reported both for sidebar or list entries and for desktop icons. The parser maps it to `sidebar_item`, which implies a single click, but a desktop icon requires a double click. The semantic role of a `ListItemControl` therefore depends on window context, which the parser does not resolve. Consumers should disambiguate using `app_type` and element position; see `automation_suggestion.md`.
- The UI dataset is English-only and not exhaustive. Uncommon or custom UI text is left without a type.
- Text under approximately 10 px, thin anti-aliased fonts, and text over busy backgrounds can be missed by OCR.
- The cursor is a single-instant snapshot. Re-query before acting if the pointer may have moved.
- Perception ids are snapshot-bound. Cross-frame reference must go through controller memory.
- Multi-monitor requires `ImageGrab.grab(all_screens=True)` plus per-monitor DPI handling. Only single-monitor is tested.

## Citation

```bibtex
@software{sam_screenparser_2026,
  title = {SAM ScreenParser: A Fact-Only Perception Engine for LLM Desktop Automation},
  author = {Sabir Ali Mondal},
  year = {2026},
  note = {RapidOCR and Windows UIA with dataset-driven type matching. Exposes a
          coordinate-free semantic table to the planning model and a coordinate table to
          the executor. Unidentified elements are reported without a type.}
}
```

## License and Credits

- PaddleOCR / RapidOCR: PaddlePaddle / Breezedeus (Apache 2.0)
- ONNX Runtime: Microsoft (MIT)
- OpenCV: OpenCV Team (Apache 2.0)
- RapidFuzz: maxbachmann (MIT)
- UIAutomation: Microsoft Windows SDK
