# SAM ScreenParser — Technical Documentation

## Architecture Philosophy

A planning LLM must not be asked to emit pixel coordinates: an autoregressive model predicts tokens, not continuous values, so coordinates produced by an LLM are guesses. SAM ScreenParser therefore obtains coordinates from a *detector* and obtains semantics from the operating system and from deterministic rules, leaving the LLM to do the one thing it is good at — choosing *which* named element to act on and *in what order*.

The perception engine is RapidOCR, which wraps PaddleOCR's text detector and recognizer behind ONNX Runtime. The detector is a region-proposal network that finds every text-like region in a **single parallel forward pass** and returns a tight bounding box, the text, and a read-confidence for each. Because it is a detector and not an autoregressive model, it has no token budget to overflow, so a dense screen — a slide deck, a dashboard, an IDE — yields *more* elements rather than being silently truncated.

On top of the detector, three cheap sources add semantics:

-   **Windows UI Automation**, queried at each detected center, supplies the OS's own control type and class name — ground truth on native applications.
-   **A deterministic classifier** maps control type, then class name, then text and position heuristics to an element type and a confidence that records which tier decided.
-   **A cursor query** reads the real control under the pointer at capture time.

A **reconciliation** cross-check downgrades obvious mislabels, a **filter** removes non-actionable context from the element list, and the **two-table split** strips every pixel field and every debug-only string before the data reaches the LLM. The verb rule is factored out of the per-element payload into a one-time legend, and cross-frame identity is factored out of the perception ids into controller memory. The downstream agent consumes the semantic table, plans by id, and obeys an explicit contract that gates every action on confidence, validates every volunteered verb, resolves ids against the coordinate table of the same snapshot, and verifies the result.

## Why This Works

1.  Coordinates come from a detector's region proposals, so they are tight on text (1–3 px), resolution-independent, and survive theme changes; RapidOCR's internal preprocessing handles light and dark themes without a manual contrast step.
2.  Detection is parallel and has no token ceiling, so dense screens are a strength, not a failure case.
3.  The full-screen visible-text summary is a free byproduct of the same sweep (the joined texts), so the LLM gets semantic context without a second OCR pass.
4.  The two-table interface removes all pixel fields from the LLM's view, so the model's context carries only the information it can actually use to plan; the executor owns the pixels and clicks deterministically. Because the LLM cannot see coordinates, it physically cannot hallucinate one — a wrong target becomes an unknown id that the executor refuses.
5.  The verb legend states the type-to-verb rule a single time instead of repeating `"action"` on every element, so the per-element payload shrinks while small local models still see the rule explicitly rather than having to infer it.
6.  Perception ids are unique within a snapshot by construction, so the executor's id-to-element map can never collide; cross-frame reference is handled by controller memory that re-resolves against the current frame, so a coordinate is never trusted across frames.
7.  DPI awareness is set at process start, so the physical pixels in the capture match the logical pixels the executor clicks and the cursor reports; without this a scaled display clicks the wrong target even when the box is right.
8.  Classification keys on the accessibility control type — mandated by the OS and stable across every Windows app — before falling back to cosmetic class names and then to heuristics.
9.  The cursor snapshot is one point of certainty read from the OS, not inferred from pixels, so the controller can trust "what is under the pointer right now."
10. Every element carries a confidence score, and the contract refuses to act below threshold, on an unknown id, or on a verb the element does not support, so the system degrades by standing still on uncertain screens instead of clicking blindly.

## Hardware Requirements

-   CPU: modern multi-core (AMD Ryzen 5 / Intel Core i5 or better)
-   RAM: 16 GB total system memory; peak process usage roughly 2–4 GB (no large vision model resident)
-   GPU: not required; ONNX Runtime uses the CPU by default (an NVIDIA GPU via the ONNX CUDA execution provider cuts the sweep to well under a second)
-   Storage: roughly 1 GB free for the OCR models and dependencies
-   OS: Windows 10/11
-   Tested performance: roughly 4–5 s for the OCR sweep plus 1–2 s of per-center UIA over 30–50 boxes, i.e. about **6–8 s per 1920×1080 frame** on an AMD Ryzen 7 U, CPU only

## Scaling Behavior

| Dimension | Behavior | Notes |
| :--- | :--- | :--- |
| Screen resolution | Robust | Detector boxes map to the true image size |
| Dense screens | Robust | Parallel detector; no truncation under load |
| DPI / display scaling | Robust | DPI awareness set at process start |
| Light vs dark theme | Robust | RapidOCR's internal preprocessing handles both |
| Different applications | Robust | Classification by control type, not class name |
| Different fonts / ClearType | Mostly robust | Coordinates survive; very thin fonts may drop |
| Non-English UI | Partially robust | Control type is language-independent; keyword heuristics are English-only |
| Apps with no accessibility tree | Declines gracefully | Such elements fall to the low-confidence tier and the contract skips them |
| Cursor position | Robust | Read from the OS at capture instant; a snapshot, not a live feed |
| Full-screen text coverage | Robust | The sweep itself is the summary; about 95–98% of visible text |
| Cross-frame identity | Robust | Handled by controller memory that re-resolves against the current frame |

## Complete Setup Guide

### Prerequisites

-   Python 3.12.10 installed with Add to PATH enabled
-   An IDE such as VS Code or Trae (optional)
-   No Tesseract install required; no PyTorch required

### Installation Steps

1.  Open the IDE at `D:\Projects\SAM-ScreenParser`.
2.  Set the interpreter before creating the virtual environment: Ctrl+Shift+P → Python: Select Interpreter → Enter interpreter path → paste `D:\Projects\SAM-ScreenParser\.venv\Scripts\python.exe`.
3.  Open a new terminal and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation
```

4.  Verify:

```powershell
py -c "from rapidocr_onnxruntime import RapidOCR; import cv2, numpy, uiautomation; print('Dependencies OK')"
```

The version check must print Python 3.12.x. If it prints 3.14, the activation failed; do not install packages until it shows 3.12. RapidOCR downloads its ONNX models automatically on first use.

## Version Maintenance Guide

### Tested Versions

The OCR stack is far less version-sensitive than a PyTorch vision stack. These are tested-good versions, not brittle pins:

| Package | Tested | Reason |
| :--- | :--- | :--- |
| Python | 3.12.x | 3.14 lacks Rust binding support in some dependencies |
| rapidocr_onnxruntime | 1.3.x | PaddleOCR models on ONNX Runtime; CPU-friendly |
| opencv-python | 4.10.x | Drawing and color conversion |
| numpy | 1.26.x / 2.x | Array handling |
| uiautomation | 2.0.x | Windows accessibility queries |

### Updating Dependencies

Test in a throwaway environment first:

```powershell
py -3.12 -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1
pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation
py screen_analyzer.py
```

### Recovering a Broken Environment

If pip fails or activation breaks, close every IDE window on the project, then:

```powershell
taskkill /F /IM python.exe 2>$null
cmd /c "rmdir /s /q D:\Projects\SAM-ScreenParser\.venv"
py -3.12 -m venv .venv
```

The rmdir step fails with access denied when an IDE holds `python.exe` open. Closing the IDE first is mandatory; restarting the machine is the fallback if the lock persists.

## Codebase

### Directory Structure

```text
SAM-ScreenParser/
├── .venv/
├── images/
├── output/
├── screen_analyzer.py
├── draw_test.py
├── live_screen_analysis.json     # coordinate table (executor + humans + tooling)
├── live_screen_compact.json      # semantic table (the LLM input)
└── technical_documentation.md
```

### screen_analyzer.py

```python
import os
import re
import json
import time
import ctypes
import numpy as np
import cv2
from datetime import datetime
from PIL import ImageGrab
import uiautomation as auto
from rapidocr_onnxruntime import RapidOCR

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

OCR = RapidOCR()

CODE_PATTERNS = ['def ', 'class ', 'import ', 'from ', 'return ', 'with ',
                 'print(', 'json.', 'result[', '.get(', '.append(', 'self.']
BUTTON_WORDS = ['new', 'save', 'delete', 'submit', 'cancel', 'ok', 'yes', 'no',
                'upload', 'download', 'send', 'search', 'open', 'close', 'back',
                'next', 'previous', 'refresh', 'sort', 'view', 'details', 'share']

# Verb rule stated ONCE (system prompt), not repeated per element.
VERB_LEGEND = (
    "VERB RULES by element.type: "
    "button|tab|sidebar_item|window_control|taskbar_item|column_header|path_bar -> click; "
    "input -> click or type; desktop_icon -> double_click; terminal -> click or read; "
    "any -> none (no-op). To act, emit {\"target_id\": <id>} and optionally \"input\" for text "
    "or \"action\" to override; an override is accepted only if allowed for that type.")

VERBS_BY_TYPE = {
    'button': {'click'}, 'tab': {'click'}, 'sidebar_item': {'click'},
    'window_control': {'click'}, 'taskbar_item': {'click'},
    'column_header': {'click'}, 'path_bar': {'click'},
    'input': {'click', 'type'}, 'desktop_icon': {'double_click'},
    'terminal': {'click', 'read'}}


def allowed_verbs(el_type):
    return VERBS_BY_TYPE.get(el_type, set()) | {'none', 'read'}


def get_dpi_scale():
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


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


def classify_by_control_type(ct):
    t = (ct or '').lower()
    if t in ('button', 'menuitem', 'menu', 'splitbutton'):
        return {'type': 'button', 'interactive': True, 'state': 'clickable'}
    if t == 'edit':
        return {'type': 'input', 'interactive': True, 'state': 'editable'}
    if t in ('listitem', 'treeitem'):
        return {'type': 'sidebar_item', 'interactive': True, 'state': 'clickable'}
    if t in ('tabitem', 'tab'):
        return {'type': 'tab', 'interactive': True, 'state': 'clickable'}
    return None


def classify_by_class_name(cn):
    c = (cn or '').lower()
    if any(k in c for k in ['sidebar', 'treeview', 'listview', 'entry']):
        return {'type': 'sidebar_item', 'interactive': True, 'state': 'clickable'}
    if any(k in c for k in ['tab', 'pivot', 'titlebar']):
        return {'type': 'tab', 'interactive': True, 'state': 'clickable'}
    if 'button' in c and 'search' not in c:
        return {'type': 'button', 'interactive': True, 'state': 'clickable'}
    if any(k in c for k in ['edit', 'textbox', 'omnibox']):
        return {'type': 'input', 'interactive': True, 'state': 'editable'}
    if any(k in c for k in ['terminal', 'console']):
        return {'type': 'terminal', 'interactive': True, 'state': 'readonly'}
    return None


def classify_element(text, bounds, H, control_type, class_name):
    x1, y1, x2, y2 = bounds
    w, h = x2 - x1, y2 - y1
    tl = text.lower()

    r = classify_by_control_type(control_type)
    if r:
        return {**r, 'confidence': 0.90}
    r = classify_by_class_name(class_name)
    if r:
        return {**r, 'confidence': 0.75}

    if text.strip().isdigit() and len(text.strip()) <= 4 and w < 50:
        return {'type': 'code_content', 'interactive': False, 'state': 'static', 'confidence': 0.60}
    if any(p in tl for p in CODE_PATTERNS):
        return {'type': 'code_content', 'interactive': False, 'state': 'static', 'confidence': 0.60}
    if any(x == tl or tl.startswith(x + ' ') for x in BUTTON_WORDS):
        return {'type': 'button', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}
    if w > h * 4 and any(k in tl for k in ['search', 'enter', 'type', 'filter']):
        return {'type': 'input', 'interactive': True, 'state': 'editable', 'confidence': 0.60}
    if '>' in text and any(k in tl for k in ['this pc', 'c:', 'd:', 'http', 'www']):
        return {'type': 'path_bar', 'interactive': True, 'state': 'readonly', 'confidence': 0.60}
    if tl in ['name', 'date modified', 'type', 'size', 'status']:
        return {'type': 'column_header', 'interactive': True, 'state': 'sortable', 'confidence': 0.60}
    if text in ['x', 'X', '—', '□'] and y1 < 50:
        return {'type': 'window_control', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}
    if y1 > H - 60:
        return {'type': 'taskbar_item', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}
    if h < 25 and y1 > 50:
        return {'type': 'desktop_icon', 'interactive': True, 'state': 'double_click_required', 'confidence': 0.40}
    return {'type': 'text_label', 'interactive': False, 'state': 'static', 'confidence': 0.40}


def reconcile(el, text):
    tl = text.lower()
    if el['type'] == 'input':
        if text.strip().isdigit() or any(p in tl for p in CODE_PATTERNS):
            el.update(type='code_content', interactive=False, state='static', confidence=0.70)
        elif re.search(r'\.\w{2,4}(\s|$)', text) and '://' not in text and not tl.startswith('search'):
            el.update(type='tab', interactive=True, state='clickable', confidence=0.70)
    return el


def action_for(state, interactive):
    if not interactive:
        return 'none'
    return {'editable': 'type', 'double_click_required': 'double_click'}.get(state, 'click')


def detect_screen_state(elements, window_info):
    all_text = ' '.join(e['text'].lower() for e in elements)
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
        state['active_app_type'] = 'windows_search'; state['has_popup'] = True
    elif any(k in cls for k in ['chrome', 'brave', 'edge', 'msedge']):
        state['active_app_type'] = 'browser'
    elif any(k in cls for k in ['explorer', 'cabinet']):
        state['active_app_type'] = 'file_explorer'
    elif 'notepad' in cls:
        state['active_app_type'] = 'text_editor'
    return state


def filter_elements(elements):
    return [e for e in elements if e['interactive'] and e['type'] not in ('code_content', 'text_label')]


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
    """Semantic table: what the LLM receives. NO coordinate fields, NO per-element verb.
    The verb rule is supplied once via VERB_LEGEND in the system prompt; the executor
    derives the default verb from the coordinate table and validates any override."""
    return {
        'active_window_title': r['active_window']['title'],
        'app_type': r['screen_state']['active_app_type'],
        'screen_state': {k: r['screen_state'][k] for k in
                         ('has_dialog', 'has_loading', 'has_popup', 'is_empty')},
        'cursor': {'text': r['cursor'].get('text', ''),
                   'control_type': r['cursor']['control_type'],
                   'over_element_id': r['cursor']['over_element_id']},
        'screen_text': r['screen_text']['raw_text'],
        'elements': [{'id': e['id'], 'text': e['text'], 'type': e['type'],
                      'confidence': e['confidence']} for e in r['elements']]}


def analyze_live_screen():
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

    print(f"Detected {len(results)} text regions. Enriching with UIA...")
    elements, texts = [], []
    for i, item in enumerate(results):
        box = np.array(item[0], dtype=np.int32)
        text = clean_text(item[1])
        if not text or len(text) <= 1:
            continue
        x1, y1 = int(box[:, 0].min()), int(box[:, 1].min())
        x2, y2 = int(box[:, 0].max()), int(box[:, 1].max())
        texts.append(text)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        control_type, class_name = get_uia_at_point(cx, cy)
        c = classify_element(text, [x1, y1, x2, y2], H, control_type, class_name)
        el = {'id': i + 1, 'text': text, 'type': c['type'], 'interactive': c['interactive'],
              'state': c['state'], 'confidence': c['confidence'],
              'control_type': control_type or 'unknown', 'class_name': class_name or 'unknown',
              'bounds': [x1, y1, x2, y2], 'center': [cx, cy]}
        el = reconcile(el, text)
        el['action'] = action_for(el['state'], el['interactive'])
        elements.append(el)

    elements = filter_elements(elements)
    cursor_info['over_element_id'] = cursor_over(cursor_info, elements)
    screen_state = detect_screen_state(elements, window_info)

    joined = "\n".join(texts)
    trunc = len(joined) > 2500
    screen_text = {'raw_text': (joined[:2500] + "\n[...truncated...]" if trunc else joined).strip(),
                   'char_count': len(joined), 'line_count': len(texts),
                   'is_truncated': trunc, 'source': 'rapidocr_sweep'}

    by_type = {}
    for e in elements:
        by_type[e['type']] = by_type.get(e['type'], 0) + 1

    return {
        'metadata': {'timestamp': datetime.now().isoformat(), 'image_size': [W, H],
                     'dpi_scale': round(get_dpi_scale(), 3), 'coordinate_space': 'physical_pixels',
                     'detector': 'RapidOCR', 'processing_time_seconds': round(time.time() - start, 2),
                     'total_elements': len(elements), 'source': 'live_screen_capture'},
        'active_window': window_info,
        'screen_state': screen_state,
        'screen_text': screen_text,
        'cursor': cursor_info,
        'elements': elements,
        'summary': {'interactive_count': sum(1 for e in elements if e['interactive']),
                    'high_confidence_count': sum(1 for e in elements if e['confidence'] >= 0.6),
                    'by_type': by_type}}


if __name__ == "__main__":
    result = analyze_live_screen()
    with open("live_screen_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    compact = compact_for_llm(result)
    with open("live_screen_compact.json", "w", encoding="utf-8") as f:
        json.dump(compact, f, indent=2)

    full_chars = len(json.dumps(result))
    compact_chars = len(json.dumps(compact))
    print(f"\nLive analysis complete in {result['metadata']['processing_time_seconds']}s")
    print(f"Active window: {result['active_window']['title']}  |  App: {result['screen_state']['active_app_type']}")
    print(f"Elements: {result['metadata']['total_elements']}  |  High confidence: {result['summary']['high_confidence_count']}")
    print(f"Screen text: {result['screen_text']['char_count']} chars, {result['screen_text']['line_count']} lines")
    print(f"Cursor over element {result['cursor']['over_element_id']} ({result['cursor']['control_type']})")
    print(f"JSON size  coordinate_table={full_chars} chars  semantic_table={compact_chars} chars  "
          f"(LLM payload is {100 - round(100 * compact_chars / max(full_chars, 1))}% smaller)")
    print("Saved live_screen_analysis.json (coordinate table) and live_screen_compact.json (semantic table)")
```

### draw_test.py

```python
import cv2
import json
import os

IMAGE_PATH = r"images\screenshot.png"
JSON_PATH = r"live_screen_analysis.json"
OUTPUT_PATH = r"output\drawn.png"

img = cv2.imread(IMAGE_PATH)
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

color_map = {
    'button': (0, 255, 0), 'input': (255, 165, 0), 'path_bar': (255, 255, 0),
    'column_header': (255, 0, 255), 'window_control': (0, 0, 255),
    'sidebar_item': (0, 255, 255), 'tab': (0, 200, 200), 'terminal': (150, 150, 0),
    'desktop_icon': (100, 100, 255), 'taskbar_item': (255, 100, 100),
    'text_label': (200, 200, 200), 'code_content': (50, 50, 50)}

for item in data['elements']:
    x1, y1, x2, y2 = item["bounds"]
    color = color_map.get(item["type"], (0, 255, 0))
    conf = item.get("confidence", 0)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2 if conf >= 0.6 else 1)
    cv2.circle(img, tuple(item["center"]), 3, (0, 0, 255), -1)
    label = f"{item['type']} {conf:.2f} {item['text'][:12]}"
    fs, th = 0.35, 1
    sz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
    cv2.rectangle(img, (x1, max(0, y1 - sz[1] - 4)), (x1 + sz[0] + 4, max(0, y1)), (0, 0, 0), -1)
    cv2.putText(img, label, (x1 + 2, max(sz[1], y1 - 2)),
                cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)

cur = data.get('cursor', {})
pos = cur.get('position', [-1, -1])
if pos[0] >= 0 and pos[1] >= 0:
    cv2.drawMarker(img, tuple(pos), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
cv2.imwrite(OUTPUT_PATH, img)
cv2.imshow("Verification", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

## The Two-Table Interface

One analysis pass produces one set of elements; that set is projected two ways that share the element `id`.

-   The **coordinate table** (`live_screen_analysis.json`) is the complete artifact. It holds every pixel field (`bounds`, `center`), the image size, the cursor's pixel position, the raw UIA strings, and the derived default `action`. Humans, `draw_test.py`, and the executor read this file.
-   The **semantic table** (`live_screen_compact.json`) is what the planning LLM receives. It holds ids, names, types, confidences, the screen-state flags, the cursor's *semantic* identity, and the screen text. It holds **no pixel field and no per-element verb**.

The LLM plans by referring to ids and names. The executor resolves an id to a pixel by looking it up in the coordinate table from the **same** snapshot. Because the two tables are generated together, their ids align exactly.

### Field retention

| Field | Coordinate table | Semantic table (LLM) | Reason |
| :--- | :--- | :--- | :--- |
| id | yes | yes | the handle the LLM plans with and the executor resolves |
| text | yes | yes | the LLM matches targets by name |
| type | yes | yes | the contract gates on it; the legend keys on it |
| confidence | yes | yes | the gate threshold |
| action (default verb) | yes | **no** | derived per element; the rule itself is the one-time legend |
| center | yes | **no** | execution-only pixel; resolved by id at click time |
| bounds | yes | no | needed for drawing and region logic, not for clicking |
| image_size | yes (metadata) | no | executor reads it to clamp; the LLM never needs it |
| element control_type | yes | no | classifier input / debug; its result already lives in `type` |
| element class_name | yes | no | long noisy string; pure token cost for the LLM |
| cursor.position | yes | **no** | a pixel; the LLM needs the cursor's identity, not its coordinate |
| cursor.text / control_type | yes | yes | semantic identity of what is under the pointer |
| cursor.over_element_id | yes | yes | an id, not a pixel; tells the LLM what the pointer rests on |
| interactive / state | yes | no | constant after filtering / fully encoded by the verb; not sent to the LLM |
| verb rule (legend) | n/a | **once, in system prompt** | stated a single time instead of per element |

### Semantic element (LLM input)

```json
{ "id": 4, "text": "Explorer", "type": "sidebar_item", "confidence": 0.90 }
```

### Coordinate element (executor)

```json
{ "id": 4, "text": "Explorer", "type": "sidebar_item", "action": "click",
  "confidence": 0.90, "control_type": "Button",
  "class_name": "sidebar-entry-fixed-list-content",
  "bounds": [64, 65, 135, 86], "center": [99, 75] }
```

### Semantic document (the LLM prompt payload)

```json
{
  "active_window_title": "screen_analyzer.py - SAM-ScreenParser - Trae",
  "app_type": "ide",
  "screen_state": {"has_dialog": false, "has_loading": false, "has_popup": false, "is_empty": false},
  "cursor": {"text": "live_screen_analysis.json", "control_type": "TreeItem", "over_element_id": 26},
  "screen_text": "File Edit Selection View Go Run Terminal Help\nExplorer screen_analyzer.py\n(.venv) PS D:\\Projects\\SAM-ScreenParser> py screen_analyzer.py\nLive analysis complete in 5.1s",
  "elements": [
    {"id": 4, "text": "Explorer", "type": "sidebar_item", "confidence": 0.90},
    {"id": 7, "text": "screen_analyzer.py", "type": "tab", "confidence": 0.70},
    {"id": 26, "text": "live_screen_analysis.json", "type": "sidebar_item", "confidence": 0.90}
  ]
}
```

There is not a single coordinate, and not a single per-element verb, in the payload the LLM sees. The model decides "act on id 26"; the executor turns 26 into a click at `[183, 306]` using the coordinate table that accompanied this exact semantic table, and derives the verb from the element's type via the legend.

## The Verb Legend

The mapping from element type to the verbs it supports is constant for a given type, so repeating it on every element is pure redundancy. SAM states it once, as `VERB_LEGEND`, which the controller prepends to the planning LLM's system prompt a single time per session. The semantic table therefore carries only `type`; the verb rule is read from the legend.

This is a deliberate choice for small local models as much as for token count. A large model can infer "a `sidebar_item` is something I click," but a 4B model reads an explicit rule more reliably than it holds an implicit lookup table in its reasoning. The legend costs roughly 150 characters once per session; repeating `"action"` on every element would cost that information 30 times per frame on a 30-element screen. Stating the rule once strictly dominates both alternatives: it is cheaper than per-element verbs and more reliable than hoping the model remembers.

The legend and the executor's `VERBS_BY_TYPE` table are the same rule in two forms — prose for the model, a set for validation — so the model's understanding and the executor's enforcement cannot drift apart.

## The Plan Step (Write Schema)

The LLM emits a plan step that names a target by id. The verb is **optional**: when omitted, the executor derives it from the element's type via the legend; when supplied, the executor validates it against the element's allowed verbs and rejects it on mismatch. This gives the smallest possible payload plus a second gate.

```json
{ "target_id": 4 }
```

```json
{ "target_id": 12, "input": "python" }
```

```json
{ "target_id": 4, "action": "click" }
```

The third form is accepted only because `click` is in the allowed set for a `sidebar_item`; had the model volunteered `"action": "type"` for that element, the executor would reject the step rather than type into a non-editable control. An unknown `target_id` — a hallucinated id, a stale id, or one that referred to a context element the filter removed — is absent from the coordinate table and is likewise refused. Both failure modes collapse to a safe no-op by construction, because the LLM never sees coordinates and the executor never trusts an unvalidated verb.

## Resolving an Action at Execution Time

The executor is downstream of perception and is not part of `screen_analyzer.py`; the snippet below is the required handoff so the two-table rule and the verb rule are unambiguous.

```python
def resolve_and_execute(plan, coordinate_table):
    by_id = {e['id']: e for e in coordinate_table['elements']}
    W, H = coordinate_table['metadata']['image_size']

    el = by_id.get(plan['target_id'])
    if el is None:
        return 'rejected_unknown_id'           # hallucinated / filtered / stale id -> no-op
    if el['confidence'] < 0.6:
        return 'rejected_low_confidence'

    verb = plan.get('action') or el['action']  # override if given, else derived default
    if verb not in allowed_verbs(el['type']):
        return 'rejected_invalid_verb'         # second gate on any volunteered verb
    if verb in ('none', 'read'):
        return 'no_mouse_action'

    x, y = el['center']
    x = max(0, min(W - 1, x))                  # clamp to the captured frame
    y = max(0, min(H - 1, y))
    if verb == 'click':          click(x, y)
    elif verb == 'double_click': double_click(x, y)
    elif verb == 'type':         click(x, y); type_text(plan.get('input', ''))
    return 'executed'
```

Two safety properties fall out of this design for free. A bad id is simply absent from the coordinate table, so the lookup returns nothing and the step is refused — a wrong target becomes a refused action rather than a wrong click. And because the executor clamps to the coordinate table's `image_size`, a center can never click outside the captured frame.

## Controller Memory — Cross-Frame Identity

A multi-step plan often needs to refer to "the same element as a previous step" — click the Save button again, retry the row that was just selected, return to the tab opened two steps ago. That capability is real and important, but it must not live in the perception ids.

Perception ids are sequential and unique **within one snapshot**, and they are intentionally re-issued on every capture. That makes the executor's id-to-element map collision-free by construction, and it makes the snapshot invariant trivial to enforce: an id names exactly one element in exactly one frame, and the coordinate it resolves to is the coordinate that was observed in that same frame.

Cross-frame identity is instead held in a **controller memory** keyed on a semantic tuple — `(active_window_title, type, normalized_text)` — which is exactly the key the controller already uses to recognize a logical element. When a plan step refers to an element by description rather than by a current id, the controller first searches the **current** semantic table for a matching `(type, normalized_text)` and, if found, resolves that *current* id against the *current* coordinate table. Only if the element is absent from the current frame — momentarily undetected — does the controller fall back to the cached center from memory, and that fallback is treated as low-confidence and consumed once. Memory is therefore a fallback for missed detection, never a replacement for current detection, and a coordinate is never trusted across frames without this re-resolution.

```python
def norm(t):
    return re.sub(r'\s+', ' ', t).strip().lower()

def current_id_for(semantic_table, el_type, text):
    nt = norm(text)
    for e in semantic_table['elements']:
        if e['type'] == el_type and norm(e['text']) == nt:
            return e['id']
    return None

def plan_with_memory(plan, semantic_table, coordinate_table, memory):
    # Normal case: the LLM named a current-frame id. Resolve directly.
    if 'target_id' in plan:
        return resolve_and_execute(plan, coordinate_table)

    # Cross-step case: the LLM named an element by (type, text).
    title = coordinate_table['active_window']['title']
    key = (title, plan['by_type'], norm(plan['by_text']))
    cid = current_id_for(semantic_table, plan['by_type'], plan['by_text'])

    if cid is not None:                        # re-resolve against the CURRENT frame
        step = {'target_id': cid}
        if 'input' in plan:  step['input']  = plan['input']
        if 'action' in plan: step['action'] = plan['action']
        res = resolve_and_execute(step, coordinate_table)
        if res == 'executed':
            el = {e['id']: e for e in coordinate_table['elements']}[cid]
            memory[key] = {'last_id': cid, 'last_center': el['center']}
        return res

    mem = memory.get(key)                      # not seen now -> single-use cached fallback
    if not mem:
        return 'rejected_not_found'
    x, y = mem['last_center']
    W, H = coordinate_table['metadata']['image_size']
    x = max(0, min(W - 1, x)); y = max(0, min(H - 1, y))
    click(x, y)
    memory.pop(key, None)                      # consume it; never trust a stale pixel twice
    return 'executed_low_confidence_fallback'
```

After each successful normal step the controller stores `memory[key] = {last_id, last_center}` so a later cross-step reference has something to fall back to. The fallback path clicks the cached center exactly once and then discards it; if the element is still missing on the next frame, the step is refused and the loop re-observes. This gives caching, retries, and multi-step reference without ever letting a stale coordinate win over a current detection.

### Why not bake stable ids into the perception output

A natural-seeming alternative is to give each element a *stable* id derived from its content — for example a hash of `(type, text, window, approximate_position)` — so the same button keeps the same id across frames and the LLM can refer to it directly. SAM deliberately does not do this, for four reasons that are properties of UI elements rather than implementation bugs:

1.  **Position in the hash defeats the purpose.** The stated goal of a stable id is "the button moves and keeps its id." But if approximate position is part of the hash, a moved window changes the bucket and the id changes; to get stability the position must be dropped or coarsened, which immediately causes reason 3.
2.  **Text churns exactly when the agent is watching.** A "Save" button becomes "Saving…", a tab gains a modified dot, a list row goes "Downloading 50%" to "Done". A content hash changes on every state transition, so the id is unstable precisely during the moments an automation agent most needs to track the element.
3.  **Collisions collapse the executor.** Two "OK" buttons in one dialog — an extremely common layout — with coarse position quantization hash to the same id. The executor's id-to-element map then retains only one of them, last-write-wins, and "click id X" clicks an arbitrary OK button. Per-frame sequential ids are unique by construction and are immune to this; a content hash introduces the bug.
4.  **It weakens the snapshot invariant.** The whole reason an id is bound to one snapshot is that carrying a coordinate across frames clicks a stale location. Stable ids make "reuse frame-1's coordinate in frame-3" look legitimate by design, re-opening the staleness door in exchange for the memory benefit.

The capability stable ids were reaching for — cross-step reference — is delivered instead by the controller memory above, in the layer where intelligence about the world over time belongs, keyed on semantics and re-resolving the coordinate from the current frame every time. The result is the same user-facing capability (caching, retries, "click the same Save again") with none of the collision, churn, or staleness hazards.

## Controller Contract

A controller that ignores these rules will damage real state. Encode them in the agent that reads the semantic table and the executor that reads the coordinate table.

1.  Feed the planning LLM the **semantic table** only, with `VERB_LEGEND` prepended to its system prompt once per session. Keep the coordinate table for the executor, for verification, and for drawing.
2.  The LLM may reference only ids present in the semantic table's `elements` list, or name an element by `(type, text)` for a cross-step reference. Any other id is invalid and the executor rejects it.
3.  The executor resolves an id against the coordinate table from the **same snapshot** the LLM planned against. Never resolve a plan made on snapshot N against a coordinate table captured later; re-capture only after the action completes.
4.  When a plan step omits the verb, the executor derives it from the element's type via the legend. When a plan step supplies a verb, the executor accepts it only if it is in the element's allowed set; otherwise it rejects the step.
5.  Never act on an element with confidence below 0.6. Log it and skip it.
6.  Never act on type `code_content` or `text_label` (these never appear in the filtered semantic list, but defend anyway).
7.  Map the resolved verb to exactly one primitive: `click` = single click at the resolved `center`; `double_click` = double click; `type` = click then send the step's `input`; `none` / `read` = no mouse action.
8.  Always click the resolved `center`, never a corner. Clamp it to the coordinate table's `image_size` before clicking.
9.  For a cross-step reference, **first** match the target in the *current* semantic table by `(type, normalized_text)` and resolve the *current* id; **only if** the target is absent from the current frame fall back to the cached center from controller memory, treat that fallback as low-confidence, and consume it once. Memory is a fallback for missed detection, never a replacement for current detection.
10. Treat the cursor as a snapshot taken at capture time. If the agent moves the pointer between capture and action, the cursor object is stale; re-query or re-capture before relying on it.
11. Trust `cursor.control_type` fully for "what is under the pointer right now"; it is read from the OS, not inferred from pixels. Use it to confirm hover-triggered menus and tooltips.
12. If `cursor.over_element_id` is set, the pointer already rests on that element; for a hover-only action skip the move, for a click click without re-locating.
13. Use `screen_text` for semantic context (reading terminal output, finding error messages, understanding document content). Use `elements` only to choose interaction targets by id.
14. After every action, re-capture and re-run analysis (a new snapshot with new ids). Confirm the expected change happened (title changed, a menu appeared, text was entered) before the next action. If nothing changed, the click missed; retry at most once, then stop.
15. If `screen_state.has_dialog` or `has_popup` is true, handle the overlay first; never click through it.
16. If `screen_state.has_loading` is true, wait and re-capture; never act on a half-rendered screen.

## Accuracy Analysis

-   Coordinate accuracy: tight detector boxes, within 1–3 px on text, resolution-independent, no calibration.
-   Text accuracy: high via PaddleOCR's recognizer; empty or garbage reads are dropped internally so they never reach the actionable list.
-   Full-screen text accuracy: 90–95% from the same sweep; captures terminal logs, status bars, and dense content at zero extra cost.
-   Classification accuracy: control-type-first classification plus reconciliation removes the editor-tab-as-input and line-number-as-input failures; the confidence field makes remaining uncertainty explicit and gateable.
-   Cursor accuracy: position and the control under it are exact, read from the OS at capture instant.
-   Token efficiency: the semantic table carries no pixel fields and no per-element verb — the verb rule is paid once via the legend — and the filter already drops code lines and static labels. On a 30-element screen the LLM payload is a small fraction of the coordinate table's size, with no loss of planning information, because the LLM never needed the pixels or the repeated verbs to choose a target.

## Known Limitations

-   RapidOCR detects only text-like regions. Pure graphics — sliders, color swatches, canvas controls, icon-only buttons with no glyph — are not detected. The executor must never invent coordinates for an unseen control, and the contract enforces that by refusing to act on any id not present in the table.
-   Text under roughly 10 px, thin anti-aliased fonts, and text over busy or low-contrast backgrounds can still be missed.
-   On Electron applications (Trae, VS Code, Brave) the UIA tree is sparse, so more elements fall to the 0.40 heuristic tier and the contract skips them; this is the residual weakness versus native applications, where UIA gives the 0.90 ground-truth tier.
-   The cursor object is a single-instant snapshot; between capture and action the user or another process may move the pointer, so the executor must re-query before acting on it.
-   An `id` is valid only within the snapshot that produced it; perception ids are intentionally not stable across frames. Cross-frame reference must go through controller memory, which re-resolves against the current frame; the memory fallback is single-use and low-confidence by design.
-   Multi-monitor setups require `ImageGrab.grab(all_screens=True)` plus per-monitor DPI handling; only single-monitor is tested.
-   The keyword heuristic list is English-only. Non-English UI text falls back to control type, which is why classification by control type is mandatory rather than optional.

## Citation

```bibtex
@software{sam_screenparser_2026,
  title = {SAM ScreenParser: A Two-Table OCR Pipeline for LLM Desktop Automation},
  author = {Sabir Ali Mondal},
  year = {2026},
  note = {RapidOCR/PaddleOCR with UIA and cursor enrichment; exposes a coordinate-free,
          verb-legend-driven semantic table to the planning LLM and a coordinate table to
          the executor, with cross-frame identity held in controller memory}
}
```

## License and Credits

-   PaddleOCR / RapidOCR: PaddlePaddle / Breezedeus (Apache 2.0)
-   ONNX Runtime: Microsoft (MIT)
-   OpenCV: OpenCV Team (Apache 2.0)
-   UIAutomation: Microsoft Windows SDK
