# SAM ScreenParser — Technical Documentation

## Project Overview

SAM ScreenParser is a local, CPU-friendly pipeline that converts the live screen into structured, automation-ready data for a planning LLM. In one fast pass it produces tight text-region coordinates, clean text, element classifications, window context, screen state, a per-element confidence score, a cursor snapshot of the real control under the pointer, and a full-screen visible-text summary built at no extra cost from the same OCR sweep. It runs entirely offline on standard laptops with no GPU.

The release is built around a strict separation of **reasoning** from **execution**. The pipeline emits one analysis that is projected two ways, sharing an element `id`:

-   A **semantic table** that the planning LLM reads. It contains ids, names, types, confidences, screen-state flags, the cursor's semantic identity, and the screen text — and **no coordinate fields at all**. The LLM reasons over names and ids and emits a plan step that names a target.
-   A **coordinate table** that the executor reads. It maps each `id` to its pixel `center` and `bounds`, plus image size and the cursor's pixel position. The executor resolves a target id to a pixel and clicks.

Two further conventions keep the LLM's context minimal and the loop robust across frames. The mapping from element type to allowed verbs is stated **once**, as a legend in the system prompt, instead of being repeated on every element. And identity that must persist across frames — "the same Save button as the previous step" — lives in a **controller memory** keyed on semantics, never in the perception ids, which are unique per snapshot by construction.

## Architecture Philosophy

A planning LLM must not be asked to emit pixel coordinates: an autoregressive model predicts tokens, not continuous values, so coordinates produced by an LLM are guesses. SAM ScreenParser therefore obtains coordinates from a *detector* and obtains semantics from the operating system and from deterministic rules, leaving the LLM to do the one thing it is good at — choosing *which* named element to act on and *in what order*.

The perception engine is RapidOCR, which wraps PaddleOCR's text detector and recognizer behind ONNX Runtime. The detector is a region-proposal network that finds every text-like region in a **single parallel forward pass** and returns a tight bounding box, the text, and a read-confidence for each. Because it is a detector and not an autoregressive model, it has no token budget to overflow, so a dense screen — a slide deck, a dashboard, an IDE — yields *more* elements rather than being silently truncated.

On top of the detector, three cheap sources add semantics:

-   **Windows UI Automation**, queried at each detected center, supplies the OS's own control type and class name — ground truth on native applications.
-   **A deterministic classifier** maps control type, then class name, then text and position heuristics to an element type and a confidence that records which tier decided. On Electron/Chromium applications where UIA returns uninformative `PaneControl`/`View`, position-based heuristics are disabled and text-content keyword matching is used instead.
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
8.  Classification keys on the accessibility control type — mandated by the OS and stable across every Windows app — before falling back to cosmetic class names and then to heuristics. On Electron apps where UIA is uninformative, an Electron-aware guard disables position-based heuristics and uses text-content keyword matching instead, preventing cascading misclassification.
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
| Electron/Chromium apps | Handled via guard | Position heuristics disabled; text-keyword fallback used |
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
py test_screen.py
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
├── test_screen.py              # Unified test: capture + classify + draw + write JSON
├── screen_analyzer.py          # Production analyzer (same logic, no drawing)
├── test_screen_drawn.png       # All raw detections drawn (visual verification)
├── test_screen_data.json       # Coordinate table (executor + humans + tooling)
├── test_screen_compact.json    # Semantic table (the LLM input)
└── technical_documentation.md
```

### test_screen.py

This is the single unified test script. It captures the live screen, runs the full perception pipeline, draws **all** raw detections (including filtered-out context) onto the screenshot for visual verification, and writes both JSON tables. Comments before each function explain its role so users can understand the pipeline without reading separate documentation.

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

# DPI awareness MUST be set before any screen capture or UIA query.
# Without this, physical pixels in the screenshot won't match logical
# pixels the executor clicks, causing mis-clicks on scaled displays.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# Single global OCR instance. RapidOCR loads PaddleOCR's detector + recognizer
# models via ONNX Runtime on first use and caches them. Creating it once avoids
# reloading ~80MB of models on every call.
OCR = RapidOCR()

# Queries the OS for the current display DPI scale factor.
# Returns 1.0 as fallback if the query fails.
# Used in metadata so the executor knows whether coordinates are scaled.
def get_dpi_scale():
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0

# Text patterns that identify code content (non-actionable).
# Used by the classifier to filter out editor lines from the actionable list.
CODE_PATTERNS = ['def ', 'class ', 'import ', 'from ', 'return ', 'with ',
                 'print(', 'json.', 'result[', '.get(', '.append(', 'self.']

# Words that identify buttons when UIA provides no useful control type.
# This is the text-content fallback for Electron/Chromium apps.
BUTTON_WORDS = ['new', 'save', 'delete', 'submit', 'cancel', 'ok', 'yes', 'no',
                'upload', 'download', 'send', 'search', 'open', 'close', 'back',
                'next', 'previous', 'refresh', 'sort', 'view', 'details', 'share']

# Verb legend: stated ONCE in the LLM system prompt, not per element.
# This saves ~450 chars/frame on a 30-element screen vs repeating "action".
VERB_LEGEND = (
    "VERB RULES by element.type: "
    "button|tab|sidebar_item|window_control|taskbar_item|column_header|path_bar -> click; "
    "input -> click or type; desktop_icon -> double_click; terminal -> click or read; "
    "any -> none (no-op). To act, emit {\"target_id\": <id>} and optionally \"input\" for text "
    "or \"action\" to override; an override is accepted only if allowed for that type.")

# Maps element types to their allowed verbs. The executor validates any
# volunteered verb against this set. This is the enforcement side of VERB_LEGEND.
VERBS_BY_TYPE = {
    'button': {'click'}, 'tab': {'click'}, 'sidebar_item': {'click'},
    'window_control': {'click'}, 'taskbar_item': {'click'},
    'column_header': {'click'}, 'path_bar': {'click'},
    'input': {'click', 'type'}, 'desktop_icon': {'double_click'},
    'terminal': {'click', 'read'}}


# Returns the set of verbs allowed for a given element type.
# Includes 'none' and 'read' as universal safe verbs.
def allowed_verbs(el_type):
    return VERBS_BY_TYPE.get(el_type, set()) | {'none', 'read'}


# Removes non-printable characters and collapses whitespace.
# Applied to every OCR result before classification.
def clean_text(raw):
    c = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw.strip())
    return re.sub(r'\s+', ' ', c).strip()


# Queries the OS for the active window's title, class, and bounds.
# Returns safe defaults if the query fails (e.g., during screen transitions).
def get_live_window_info():
    try:
        fg = auto.GetForegroundControl()
        r = fg.BoundingRectangle
        return {'title': fg.Name or 'Unknown', 'class': fg.ClassName or 'Unknown',
                'bounds': [r.left, r.top, r.right, r.bottom]}
    except Exception:
        return {'title': 'Unknown', 'class': 'Unknown', 'bounds': [0, 0, 0, 0]}


# Reads the cursor position and the UIA control underneath it.
# Returns semantic identity (text, control_type) plus pixel position.
# The pixel position goes ONLY in the coordinate table, never the semantic table.
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


# Queries UIA at a specific pixel coordinate for control type and class name.
# On native apps this returns ground-truth semantics (Button, Edit, TreeItem).
# On Electron apps this typically returns ("PaneControl", "View") — useless.
# The classifier detects this and switches to text-content heuristics.
def get_uia_at_point(x, y):
    try:
        c = auto.ControlFromPoint(x, y)
        return (c.ControlTypeName or '', c.ClassName or '')
    except Exception:
        return ('', '')


# Tier 1 classifier: maps UIA control type to element type.
# Returns None if the control type is unrecognized, signaling fallback to tier 2.
# Confidence 0.90 because this is OS ground truth.
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


# Tier 2 classifier: maps UIA class name to element type.
# Catches cases where control type is generic but class name is specific.
# Returns None if unrecognized, signaling fallback to tier 3 (heuristics).
# Confidence 0.75 because class names are cosmetic and app-specific.
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


# Tier 3 classifier: text-content and position heuristics.
# THIS IS WHERE THE ELECTRON FIX LIVES.
# When UIA returns PaneControl+View (Electron), position-based heuristics
# (desktop_icon, taskbar_item) are DISABLED because they misfire on Electron layouts.
# Instead, text-content keyword matching identifies sidebar items, tabs,
# terminal output, and status bar text correctly regardless of UIA quality.
def classify_element(text, bounds, H, control_type, class_name):
    x1, y1, x2, y2 = bounds
    w, h = x2 - x1, y2 - y1
    tl = text.lower()

    # Tier 1: UIA control type (ground truth on native apps)
    r = classify_by_control_type(control_type)
    if r:
        return {**r, 'confidence': 0.90}

    # Tier 2: UIA class name (app-specific but often useful)
    r = classify_by_class_name(class_name)
    if r:
        return {**r, 'confidence': 0.75}

    # === ELECTRON GUARD ===
    # PaneControl + View means UIA is useless (Electron/Chromium).
    # Disable position heuristics that would misclassify everything.
    is_electron = (control_type == 'PaneControl' and class_name == 'View')

    # --- Text-content heuristics (work regardless of UIA quality) ---

    # Code content: function defs, imports, method calls
    if text.strip().isdigit() and len(text.strip()) <= 4 and w < 50:
        return {'type': 'code_content', 'interactive': False, 'state': 'static', 'confidence': 0.60}
    if any(p in tl for p in CODE_PATTERNS):
        return {'type': 'code_content', 'interactive': False, 'state': 'static', 'confidence': 0.60}

    # Button keywords (text-content fallback when UIA fails)
    if any(x == tl or tl.startswith(x + ' ') for x in BUTTON_WORDS):
        return {'type': 'button', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}

    # Input fields: wide boxes with search/enter/type/filter text
    if w > h * 4 and any(k in tl for k in ['search', 'enter', 'type', 'filter']):
        return {'type': 'input', 'interactive': True, 'state': 'editable', 'confidence': 0.60}

    # Path bars: contain > and drive letters or URLs
    if '>' in text and any(k in tl for k in ['this pc', 'c:', 'd:', 'http', 'www']):
        return {'type': 'path_bar', 'interactive': True, 'state': 'readonly', 'confidence': 0.60}

    # Column headers in file explorers
    if tl in ['name', 'date modified', 'type', 'size', 'status']:
        return {'type': 'column_header', 'interactive': True, 'state': 'sortable', 'confidence': 0.60}

    # Terminal output patterns (prevents terminal logs from becoming actionable)
    terminal_patterns = ['capturing', 'running', 'detected', 'complete in',
                         'dependencies ok', 'saved ', 'elements:', 'screen text:',
                         'cursor over', 'json size', 'llm payload', 'processed 0/0',
                         'no suggestions', 'waiting for', 'high confidence',
                         'live analysis', 'enriching with', 'drew ']
    if any(p in tl for p in terminal_patterns):
        return {'type': 'text_label', 'interactive': False, 'state': 'static', 'confidence': 0.60}

    # Status bar patterns (prevents editor status from becoming actionable)
    status_patterns = ['ln ', 'col ', 'spaces:', 'utf-8', 'crlf', 'python 3.',
                       'select python interpreter', 'go live', 'cue-pro',
                       'side ai chat', 'inline ai chat']
    if any(p in tl for p in status_patterns):
        return {'type': 'text_label', 'interactive': False, 'state': 'static', 'confidence': 0.60}

    # IDE sidebar keywords (when UIA fails on Electron)
    sidebar_keywords = ['explorer', 'outline', 'timeline', 'folder', 'weights', 'images']
    if tl.strip() in sidebar_keywords or any(tl.strip().startswith(k) for k in sidebar_keywords):
        return {'type': 'sidebar_item', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}

    # Tab keywords in lower panel area (when UIA fails on Electron)
    tab_keywords = ['problems', 'output', 'terminal']
    if tl.strip().lower() in tab_keywords and y1 > H * 0.4:
        return {'type': 'tab', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}

    # === POSITION HEURISTICS (disabled on Electron) ===
    if not is_electron:
        if text in ['x', 'X', '—', '□'] and y1 < 50:
            return {'type': 'window_control', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}
        if y1 > H - 60:
            return {'type': 'taskbar_item', 'interactive': True, 'state': 'clickable', 'confidence': 0.60}
        if h < 25 and y1 > 50:
            return {'type': 'desktop_icon', 'interactive': True, 'state': 'double_click_required', 'confidence': 0.40}

    # Final fallback: static text label (filtered out, not actionable)
    return {'type': 'text_label', 'interactive': False, 'state': 'static', 'confidence': 0.40}


# Post-classification cross-check. Downgrades obvious mislabels:
# - An "input" that contains only digits or code patterns → code_content
# - An "input" that looks like a filename tab → tab
# This prevents the most common false positives from reaching the LLM.
def reconcile(el, text):
    tl = text.lower()
    if el['type'] == 'input':
        if text.strip().isdigit() or any(p in tl for p in CODE_PATTERNS):
            el.update(type='code_content', interactive=False, state='static', confidence=0.70)
        elif re.search(r'\.\w{2,4}(\s|$)', text) and '://' not in text and not tl.startswith('search'):
            el.update(type='tab', interactive=True, state='clickable', confidence=0.70)
    return el


# Derives the default action verb from element state.
# The LLM doesn't need this per-element (see VERB_LEGEND), but the executor
# uses it as the default when the LLM omits the verb in its plan step.
def action_for(state, interactive):
    if not interactive:
        return 'none'
    return {'editable': 'type', 'double_click_required': 'double_click'}.get(state, 'click')


# Detects high-level screen state from element text and window metadata.
# Flags dialogs, loading states, empty screens, and app type.
# The LLM uses these flags to decide whether to act, wait, or handle overlays.
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


# Removes non-actionable elements (code_content, text_label) from the list.
# Only interactive elements survive to reach the LLM's semantic table.
# The drawn image shows ALL elements (before filtering) for visual verification.
def filter_elements(elements):
    return [e for e in elements if e['interactive'] and e['type'] not in ('code_content', 'text_label')]


# Finds which element (if any) the cursor is currently hovering over.
# Sets over_element_id on the cursor object so the LLM knows what's under the pointer.
def cursor_over(cursor_info, elements):
    cx, cy = cursor_info['position']
    if cx < 0 or cy < 0:
        return None
    for e in elements:
        x1, y1, x2, y2 = e['bounds']
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            return e['id']
    return None


# Builds the semantic table (compact projection for the LLM).
# Strips ALL coordinate fields, ALL UIA strings, and per-element verbs.
# The LLM receives only: id, text, type, confidence, screen_text, cursor identity.
def compact_for_llm(r):
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


# Draws ALL raw detections onto the screenshot for visual verification.
# Thick border = actionable (passed filter). Thin border = filtered-out context.
# This runs BEFORE filtering so you see everything the detector found.
# Matches the behavior of the standalone rapidocr_result.png test.
def draw_all_detections(image_bgr, all_elements, output_path):
    img = image_bgr.copy()
    color_map = {
        'button': (0, 255, 0), 'input': (255, 165, 0), 'path_bar': (255, 255, 0),
        'column_header': (255, 0, 255), 'window_control': (0, 0, 255),
        'sidebar_item': (0, 255, 255), 'tab': (0, 200, 200), 'terminal': (150, 150, 0),
        'desktop_icon': (100, 100, 255), 'taskbar_item': (255, 100, 100),
        'text_label': (200, 200, 200), 'code_content': (50, 50, 50)}

    for item in all_elements:
        x1, y1, x2, y2 = item["bounds"]
        color = color_map.get(item["type"], (128, 128, 128))
        conf = item.get("confidence", 0)
        thick = 2 if item.get("interactive", False) else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
        cv2.circle(img, tuple(item["center"]), 3, (0, 0, 255), -1)
        label = f"{item['type']} {conf:.2f} {item['text'][:14]}"
        fs, th = 0.35, 1
        sz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
        cv2.rectangle(img, (x1, max(0, y1 - sz[1] - 4)),
                      (x1 + sz[0] + 4, max(0, y1)), (0, 0, 0), -1)
        cv2.putText(img, label, (x1 + 2, max(sz[1], y1 - 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    cv2.imwrite(output_path, img)


# Main entry point. Captures screen, runs full pipeline, draws all detections,
# writes both JSON tables. This is the unified test — no separate draw script needed.
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
    print(f"Detected {len(results)} raw text regions.")

    print("Enriching with UIA and classifying...")
    all_elements, texts = [], []
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
        all_elements.append(el)

    # Draw ALL raw detections BEFORE filtering (visual verification)
    draw_all_detections(bgr, all_elements, "test_screen_drawn.png")
    print(f"Drew {len(all_elements)} raw detections → test_screen_drawn.png")

    # Filter for LLM-facing tables
    filtered = filter_elements(all_elements)
    cursor_info['over_element_id'] = cursor_over(cursor_info, filtered)
    screen_state = detect_screen_state(filtered, window_info)

    joined = "\n".join(texts)
    trunc = len(joined) > 2500
    screen_text = {'raw_text': (joined[:2500] + "\n[...truncated...]" if trunc else joined).strip(),
                   'char_count': len(joined), 'line_count': len(texts),
                   'is_truncated': trunc, 'source': 'rapidocr_sweep'}

    by_type = {}
    for e in filtered:
        by_type[e['type']] = by_type.get(e['type'], 0) + 1

    result = {
        'metadata': {'timestamp': datetime.now().isoformat(), 'image_size': [W, H],
                     'dpi_scale': round(get_dpi_scale(), 3),
                     'coordinate_space': 'physical_pixels', 'detector': 'RapidOCR',
                     'processing_time_seconds': round(time.time() - start, 2),
                     'total_raw_detections': len(all_elements),
                     'total_actionable_elements': len(filtered),
                     'source': 'live_screen_capture'},
        'active_window': window_info,
        'screen_state': screen_state,
        'screen_text': screen_text,
        'cursor': cursor_info,
        'elements': filtered,
        'summary': {'interactive_count': sum(1 for e in filtered if e['interactive']),
                    'high_confidence_count': sum(1 for e in filtered if e['confidence'] >= 0.6),
                    'by_type': by_type}}

    # Write coordinate table (full artifact for executor + debugging)
    with open("test_screen_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Write semantic table (compact projection for LLM)
    compact = compact_for_llm(result)
    with open("test_screen_compact.json", "w", encoding="utf-8") as f:
        json.dump(compact, f, indent=2)

    elapsed = round(time.time() - start, 2)
    print(f"\n✅ Complete in {elapsed}s")
    print(f"   Raw detections:   {len(all_elements)}")
    print(f"   Actionable:       {len(filtered)}")
    print(f"   Screen text:      {screen_text['char_count']} chars")
    print(f"   Cursor over:      element {cursor_info['over_element_id']}")
    print(f"\n📁 Outputs:")
    print(f"   test_screen_drawn.png    ← ALL raw detections (visual verification)")
    print(f"   test_screen_data.json    ← Coordinate table (executor)")
    print(f"   test_screen_compact.json ← Semantic table (LLM)")


if __name__ == "__main__":
    main()
```

## Control-Safe Output Schema

### Field Retention

| Field | Coordinate Table | Semantic Table (LLM) | Reason |
| :--- | :--- | :--- | :--- |
| id | yes | yes | Handle the LLM plans with and executor resolves |
| text | yes | yes | LLM matches targets by name |
| type | yes | yes | Contract gates on it; legend keys on it |
| confidence | yes | yes | Gate threshold |
| action (default verb) | yes | **no** | Derived per element; rule is the one-time legend |
| center | yes | **no** | Execution-only pixel; resolved by id at click time |
| bounds | yes | no | Needed for drawing and region logic, not clicking |
| image_size | yes (metadata) | no | Executor clamps; LLM never needs it |
| element control_type | yes | no | Classifier input/debug; result lives in `type` |
| element class_name | yes | no | Long noisy string; pure token cost for LLM |
| cursor.position | yes | **no** | Pixel; LLM needs cursor identity, not coordinate |
| cursor.text / control_type | yes | yes | Semantic identity of what is under the pointer |
| cursor.over_element_id | yes | yes | Id, not pixel; tells LLM what pointer rests on |
| interactive / state | yes | no | Constant after filtering / encoded by verb |
| verb rule (legend) | n/a | **once, in system prompt** | Stated single time instead of per element |

### Semantic Element (LLM Input)

```json
{ "id": 4, "text": "Explorer", "type": "sidebar_item", "confidence": 0.90 }
```

### Coordinate Element (Executor)

```json
{ "id": 4, "text": "Explorer", "type": "sidebar_item", "action": "click",
  "confidence": 0.90, "control_type": "Button",
  "class_name": "sidebar-entry-fixed-list-content",
  "bounds": [64, 65, 135, 86], "center": [99, 75] }
```

## Controller Contract

1.  Feed the planning LLM the **semantic table** only, with `VERB_LEGEND` prepended to its system prompt once per session.
2.  The LLM may reference only ids present in the semantic table's `elements` list, or name an element by `(type, text)` for cross-step reference.
3.  The executor resolves an id against the coordinate table from the **same snapshot**. Never resolve across snapshots.
4.  When a plan step omits the verb, derive it from type via the legend. When supplied, validate against `allowed_verbs()`; reject on mismatch.
5.  Never act on confidence below 0.6. Never act on `code_content` or `text_label`.
6.  Always click the resolved `center`, clamped to `image_size`.
7.  For cross-step reference, **first** match in the current semantic table; **only if** absent, fall back to cached center from controller memory (single-use, low-confidence).
8.  Treat cursor as a snapshot. Re-query if pointer moved between capture and action.
9.  Trust `cursor.control_type` fully for hover confirmation.
10. After every action, re-capture. Confirm expected change before next action. Retry missed clicks at most once.
11. Handle dialogs/popups first. Wait if `has_loading`. Never click through overlays.

## Accuracy Analysis

-   Coordinate accuracy: tight detector boxes, within 1–3 px on text, resolution-independent.
-   Text accuracy: high via PaddleOCR's recognizer; garbage reads dropped internally.
-   Full-screen text accuracy: 90–95% from same sweep; captures terminal logs and dense content at zero extra cost.
-   Classification accuracy: control-type-first on native apps; Electron guard + text-keyword fallback prevents cascading misclassification on Chromium apps.
-   Token efficiency: semantic table carries no pixels, no per-element verb, no UIA strings. Legend paid once. Filter drops code and labels.

## Known Limitations

-   RapidOCR detects only text-like regions. Pure graphics, sliders, canvas controls, and icon-only buttons without glyphs are not detected. The contract refuses to act on unseen controls.
-   Text under ~10 px, thin anti-aliased fonts, and text over busy backgrounds can be missed.
-   **Electron/Chromium UIA collapse.** Apps built on Electron (Trae, VS Code, Brave, Discord) expose minimal UIA information. Most elements return `PaneControl`/`View`. The classifier disables position-based heuristics when Electron is detected and uses text-content keyword matching instead. This is less reliable than native UIA but prevents the cascade of mislabels that would otherwise occur. Sidebar items, tabs, terminal output, and status bar text are recognized via keyword patterns.
-   Cursor is a single-instant snapshot; re-query before acting if pointer may have moved.
-   Perception ids are snapshot-bound. Cross-frame reference must go through controller memory.
-   Multi-monitor requires `ImageGrab.grab(all_screens=True)` plus per-monitor DPI; only single-monitor tested.
-   Keyword heuristics are English-only. Non-English falls back to control type.

## Citation

```bibtex
@software{sam_screenparser_2026,
  title = {SAM ScreenParser: A Two-Table OCR Pipeline for LLM Desktop Automation},
  author = {Sabir Ali Mondal},
  year = {2026},
  note = {RapidOCR/PaddleOCR with UIA and cursor enrichment; exposes a coordinate-free,
          verb-legend-driven semantic table to the planning LLM and a coordinate table to
          the executor, with Electron-aware classification and controller memory}
}
```

## License and Credits

-   PaddleOCR / RapidOCR: PaddlePaddle / Breezedeus (Apache 2.0)
-   ONNX Runtime: Microsoft (MIT)
-   OpenCV: OpenCV Team (Apache 2.0)
-   UIAutomation: Microsoft Windows SDK
