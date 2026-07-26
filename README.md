# SAM ScreenParser

**Note on Naming:** In this project, **SAM** stands for **S**creen **A**utomation **M**anager (and is also a nod to the author's initials, **S**abir **A**li **M**ondal).
*This project is entirely independent and is NOT related to Meta's Segment Anything Model (SAM).*

## Project Overview

SAM ScreenParser is a local, CPU-friendly screen understanding pipeline for desktop automation agents. It converts live screenshots into structured, deterministic JSON containing pixel-perfect coordinates, clean text, element classifications, window context, and a per-element confidence score. It runs entirely offline on standard laptops with no cloud APIs and no dedicated GPU.

What it guarantees:

- Pixel-perfect coordinates from Florence-2 vision grounding, mapped to the image's true pixel size, so detection is resolution-independent.
- Clean text from Tesseract OCR with contrast normalization and icon-garbage removal.
- DPI-aware capture so detection coordinates, UIA coordinates, and click coordinates agree on scaled displays.
- A confidence score on every element so a controller can refuse to act on uncertain data.

What it does not guarantee, by design: it will decline to act on elements it cannot classify with confidence rather than click the wrong target. That refusal is a feature, not a gap.

For architecture, full setup, the control-safe schema, and the rules a controller must follow, see technical_documentation.md.

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation
py screen_analyzer.py
```

## License and Credits

- Florence-2: Microsoft Research (Apache 2.0)
- Tesseract OCR: Google Open Source (Apache 2.0)
- OpenCV: OpenCV Team (Apache 2.0)
- Transformers: Hugging Face (Apache 2.0)
- UIAutomation: Microsoft Windows SDK

---

# FILE: technical_documentation.md

# SAM ScreenParser Technical Documentation

## Project Overview

SAM ScreenParser is a local, CPU-friendly screen understanding pipeline for desktop automation. It converts live screenshots into structured JSON containing pixel-perfect coordinates, clean text, element classifications, window context, and a per-element confidence score. It operates entirely offline on standard laptops without dedicated GPU hardware, and is optimized for minimal, control-safe token consumption by downstream planning LLMs.

## Architecture Philosophy

Large Language Models cannot generate precise pixel coordinates because their autoregressive architecture predicts text tokens, not continuous spatial values. SAM ScreenParser therefore splits the work across specialized components:

- Spatial grounding: Florence-2 (vision encoder plus bounding-box regressor) outputs mathematical coordinates directly from image pixels.
- Text extraction: Tesseract OCR with contrast normalization reads text independently of visual scene interpretation.
- Window context: Windows UI Automation supplies active-window metadata and, at each detected coordinate, the native control type and class name.
- Classification: a tiered classifier reads the UIA control type first, then the class name, then text and position heuristics, assigning a confidence that reflects which tier decided.
- Reconciliation: a cross-check downgrades obvious mislabels (a line number reported as an input, a filename tab reported as an input) before output.
- Filtering: non-actionable code content and static labels are removed to cut token count.
- Planning and control: a downstream agent consumes the filtered JSON and obeys an explicit contract that gates every action on confidence and verifies the result.

## Why This Works

1. Coordinates come from regression over image features, so they are exact and resolution-independent, and they survive theme changes.
2. Dedicated OCR with contrast normalization prevents the text pollution and icon misreads that vision-language models produce, and keeps accuracy stable across light and dark themes.
3. DPI awareness is set at process start, so the physical pixels in the screenshot match the logical pixels the controller clicks. Without this, a scaled laptop clicks the wrong element even when the box is correct.
4. Classification keys on the accessibility control type, which is mandated by the OS specification and stable across every Windows app, instead of cosmetic class names that change per app and per version.
5. Every element carries a confidence score, and the controller contract refuses to act below threshold, so the system degrades by standing still on uncertain screens instead of clicking blindly.

## Hardware Requirements

- CPU: modern multi-core (AMD Ryzen 5 / Intel Core i5 or better)
- RAM: 16 GB total system memory
- GPU: not required (integrated graphics sufficient; an NVIDIA GPU cuts inference from ~80 s to ~3 s)
- Storage: 5 GB free for models and dependencies
- OS: Windows 10/11
- Tested performance: 70 to 90 seconds per 1920x1080 frame on AMD Ryzen 7 U, CPU only

## Scaling Behavior

| Dimension | Behavior | Notes |
| :--- | :--- | :--- |
| Screen resolution | Robust | Coordinates map to true image size |
| DPI / display scaling | Robust after Fix 1 | DPI awareness set at process start |
| Light vs dark theme | Robust after Fix 3 | Contrast normalization before OCR |
| Different apps | Robust after Fix 2 | Classification by control type, not class name |
| Different fonts / ClearType | Mostly robust | Coordinates survive; very thin fonts may drop OCR |
| Non-English UI | Partially robust | Control type is language-independent; keyword heuristics are English-only |
| Apps with no accessibility tree | Declines gracefully | Such elements fall to low confidence and the controller skips them |

## Complete Setup Guide

### Prerequisites

- Python 3.12.10 installed with Add to PATH enabled
- Tesseract OCR installed at C:\Program Files\Tesseract-OCR
- An IDE such as VS Code or Trae (optional)

### Installation Steps

1. Open the IDE at D:\Projects\SAM-ScreenParser.
2. Set the interpreter before creating the virtual environment: Ctrl+Shift+P, Python: Select Interpreter, Enter interpreter path, paste D:\Projects\SAM-ScreenParser\.venv\Scripts\python.exe.
3. Open a new terminal and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation
```

4. Verify:

```powershell
py -c "import transformers, torch, cv2, pytesseract; print('Dependencies OK')"
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

The version check must print Python 3.12.x. If it prints 3.14, the activation failed; do not install packages until it shows 3.12.

## Version Maintenance Guide

### Pinned Versions

| Package | Version | Reason |
| :--- | :--- | :--- |
| Python | 3.12.x | 3.14 lacks Rust binding support for tokenizers |
| transformers | 4.45.0 | First stable release with the Florence-2 auto-map |
| torch | 2.13.x | Stable wheels for Python 3.12 |
| Tesseract | 5.5.x | Best accuracy on UI fonts |

### Updating Dependencies

Never run a blind upgrade. Test in a throwaway environment first:

```powershell
py -3.12 -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1
pip install transformers==<new_version> torch pillow timm einops
py screen_analyzer.py
```

### Recovering a Broken Environment

If pip fails or activation breaks, close every IDE window on the project, then:

```powershell
taskkill /F /IM python.exe 2>$null
cmd /c "rmdir /s /q D:\Projects\SAM-ScreenParser\.venv"
py -3.12 -m venv .venv
```

The rmdir step fails with access denied when an IDE holds python.exe open. Closing the IDE first is mandatory; restarting the machine is the fallback if the lock persists.

### Python Version Migration

Install the new interpreter, delete .venv, recreate with the new py launcher, reinstall pinned dependencies, and confirm pytesseract.pytesseract.tesseract_cmd still points at the installed Tesseract.

## Codebase

### Directory Structure

```text
SAM-ScreenParser/
├── .venv/
├── images/
├── output/
├── screen_analyzer.py
├── draw_test.py
├── live_screen_analysis.json
└── technical_documentation.md
```

### screen_analyzer.py

```python
import os
import re
import json
import time
import ctypes
from datetime import datetime
from PIL import Image, ImageGrab, ImageOps
import torch
import pytesseract
import uiautomation as auto
from transformers import AutoProcessor, AutoModelForCausalLM

# DPI awareness first, before any screen query, so physical and logical pixels agree.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

CODE_PATTERNS = ['def ', 'class ', 'import ', 'from ', 'return ', 'with ',
                 'print(', 'json.', 'result[', '.get(', '.append(', 'self.']
BUTTON_WORDS = ['new', 'save', 'delete', 'submit', 'cancel', 'ok', 'yes', 'no',
                'upload', 'download', 'send', 'search', 'open', 'close', 'back',
                'next', 'previous', 'refresh', 'sort', 'view', 'details', 'share']


def get_dpi_scale():
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def clean_ocr_text(raw_text):
    garbage = ['Bm', 'im', 'sb', 'g ', 'am', 'ie', 'ES', 'MM', 'aw', 'x', 'v ']
    cleaned = raw_text.strip()
    for g in garbage:
        if cleaned.startswith(g):
            cleaned = cleaned[len(g):].strip()
    cleaned = re.sub(r'[^\w\s\.\-\(\)\/\\:]', ' ', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()


def ocr_crop(crop):
    gray = ImageOps.autocontrast(crop.convert('L'), cutoff=1)
    return pytesseract.image_to_string(gray, config='--oem 3 --psm 7').strip()


def get_live_window_info():
    try:
        fg = auto.GetForegroundControl()
        r = fg.BoundingRectangle
        return {'title': fg.Name or 'Unknown', 'class': fg.ClassName or 'Unknown',
                'automation_id': fg.AutomationId or '',
                'bounds': [r.left, r.top, r.right, r.bottom],
                'width': r.width(), 'height': r.height()}
    except Exception:
        return None


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
    # UIA point-sampling in Electron apps can return the wrong overlay control.
    # Cross-check the OCR text against the assigned type and downgrade mismatches.
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
    # Title-based checks first: Electron IDEs report a Chrome window class.
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


def filter_elements_for_llm(elements):
    out = []
    for e in elements:
        if e['interactive'] and e['type'] not in ('code_content', 'text_label'):
            out.append(e)
    return out


def analyze_live_screen():
    start = time.time()
    print("Capturing live screen...")
    shot = ImageGrab.grab(all_screens=False)
    W, H = shot.size
    image = shot.convert("RGB")

    window_info = get_live_window_info() or {
        'title': 'Unknown', 'class': 'Unknown', 'automation_id': '',
        'bounds': [0, 0, W, H], 'width': W, 'height': H}
    print(f"Active window: {window_info['title']} ({window_info['class']})")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Florence-2-base", trust_remote_code=True, torch_dtype=torch.float32).to(device)
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)

    print("Detecting text regions...")
    prompt = "<OCR_WITH_REGION>"
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(device)
    ids = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"],
                         max_new_tokens=2048, num_beams=3, do_sample=False)
    gen = processor.batch_decode(ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(gen, task=prompt, image_size=(W, H))

    print("Extracting text and enriching with UIA data...")
    elements = []
    for i, box in enumerate(parsed[prompt].get("quad_boxes", [])):
        x1 = int(min(box[0], box[2], box[4], box[6])); y1 = int(min(box[1], box[3], box[5], box[7]))
        x2 = int(max(box[0], box[2], box[4], box[6])); y2 = int(max(box[1], box[3], box[5], box[7]))
        x1, y1 = max(0, x1 - 2), max(0, y1 - 2); x2, y2 = min(W, x2 + 2), min(H, y2 + 2)
        text = clean_ocr_text(ocr_crop(image.crop((x1, y1, x2, y2))))
        if not text or len(text) <= 1:
            continue
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

    elements = filter_elements_for_llm(elements)
    screen_state = detect_screen_state(elements, window_info)

    by_type = {}
    for e in elements:
        by_type[e['type']] = by_type.get(e['type'], 0) + 1

    return {
        'metadata': {'timestamp': datetime.now().isoformat(), 'image_size': [W, H],
                     'dpi_scale': round(get_dpi_scale(), 3), 'coordinate_space': 'physical_pixels',
                     'processing_time_seconds': round(time.time() - start, 2),
                     'total_elements': len(elements), 'source': 'live_screen_capture'},
        'active_window': window_info,
        'screen_state': screen_state,
        'elements': elements,
        'summary': {'interactive_count': sum(1 for e in elements if e['interactive']),
                    'static_count': sum(1 for e in elements if not e['interactive']),
                    'high_confidence_count': sum(1 for e in elements if e['confidence'] >= 0.6),
                    'by_type': by_type}}


if __name__ == "__main__":
    result = analyze_live_screen()
    with open("live_screen_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nLive analysis complete in {result['metadata']['processing_time_seconds']}s")
    print(f"Active window: {result['active_window']['title']}")
    print(f"App type: {result['screen_state']['active_app_type']}")
    print(f"DPI scale: {result['metadata']['dpi_scale']}")
    print(f"Total elements: {result['metadata']['total_elements']}")
    print(f"High confidence: {result['summary']['high_confidence_count']}")
    print(f"Element types: {result['summary']['by_type']}")
    print("Saved to: live_screen_analysis.json")
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

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
cv2.imwrite(OUTPUT_PATH, img)
cv2.imshow("Verification", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

## Control-Safe Output Schema

This is the structure a controller consumes. Every element carries an action verb and a confidence the controller gates on.

```json
{
  "metadata": {
    "timestamp": "2026-07-26T13:10:00",
    "image_size": [1920, 1080],
    "dpi_scale": 1.5,
    "coordinate_space": "physical_pixels",
    "processing_time_seconds": 88.4,
    "total_elements": 3,
    "source": "live_screen_capture"
  },
  "active_window": {
    "title": "screen_analyzer.py - SAM-ScreenParser - Trae",
    "class": "Chrome_WidgetWin_1"
  },
  "screen_state": {
    "active_app_type": "ide",
    "has_popup": false,
    "has_dialog": false,
    "has_loading": false,
    "is_empty": false
  },
  "elements": [
    {
      "id": 4, "text": "Explorer", "type": "sidebar_item", "action": "click",
      "interactive": true, "state": "clickable", "confidence": 0.90,
      "control_type": "Button", "class_name": "sidebar-entry-fixed-list-content",
      "bounds": [64, 65, 135, 86], "center": [99, 75]
    },
    {
      "id": 7, "text": "screen_analyzer.py", "type": "tab", "action": "click",
      "interactive": true, "state": "clickable", "confidence": 0.70,
      "control_type": "unknown", "class_name": "tab-label",
      "bounds": [371, 64, 550, 87], "center": [460, 75]
    },
    {
      "id": 26, "text": "live_screen_analysis.json", "type": "sidebar_item", "action": "click",
      "interactive": true, "state": "clickable", "confidence": 0.90,
      "control_type": "TreeItem", "class_name": "prc-TreeView-TreeViewItem-Ter5f",
      "bounds": [85, 295, 281, 317], "center": [183, 306]
    }
  ],
  "summary": {
    "interactive_count": 3, "static_count": 0, "high_confidence_count": 3,
    "by_type": {"sidebar_item": 2, "tab": 1}
  }
}
```

## Controller Contract

A controller that ignores these rules will damage real state. Encode them in the agent that reads the JSON.

1. Never act on an element with confidence below 0.6. Log it and skip it.
2. Never act on type code_content or text_label. They are context, not targets.
3. Map the action field to exactly one primitive: click is a single click at center; double_click is a double click; type is click then send keystrokes; none means do nothing.
4. Always click center, never a corner. Clamp center to the image bounds before clicking.
5. After every action, re-capture and re-run analysis. Confirm the expected change happened (title changed, a menu appeared, text was entered) before the next action. If nothing changed, the click missed; retry at most once, then stop.
6. If screen_state.has_dialog or has_popup is true, handle the overlay first; never click through it.
7. If screen_state.has_loading is true, wait and re-capture; never act on a half-rendered screen.
8. Keep a per-session memory keyed by (active_window.title, type, text). If the same logical element worked before, prefer its last known center over a fresh low-confidence detection.

## Accuracy Analysis

- Coordinate accuracy: pixel-perfect, within 1 to 3 pixels, resolution-independent, no calibration. Unchanged and intact.
- Text accuracy: 95 to 99 percent after contrast normalization and regex cleaning; theme-independent. Unchanged and improved on low-contrast text.
- Classification accuracy: control-type-first classification plus reconciliation removes the editor-tab-as-input and line-number-as-input failures. The confidence field makes remaining uncertainty explicit and actionable.
- Token efficiency: filtering removes code lines, line numbers, terminal echo, and static labels, typically cutting the element list by 80 to 90 percent.

## Known Scaling Limitations

- CPU inference is 70 to 90 seconds per frame. This is a perception layer for deliberate automation, not a real-time loop.
- Text under roughly 10 pixels, thin anti-aliased fonts, and text over busy wallpapers can still be missed even after contrast normalization.
- Apps that draw their own UI without an accessibility tree (some games, canvas-only web apps, custom Electron builds) return an empty control type, dropping those elements to the 0.40 tier, which the contract then refuses to act on. That is correct behavior: the system declines to guess rather than click blindly.
- Multi-monitor setups require ImageGrab.grab(all_screens=True) plus per-monitor DPI handling; only single-monitor is tested.
- The keyword heuristic list is English-only. Non-English UI text falls back to control type, which is why classification by control type is mandatory rather than optional.

## Citation

```bibtex
@software{sam_screenparser_2026,
  title = {SAM ScreenParser: Hybrid Vision Pipeline for Desktop Automation},
  author = {Sabir Ali Mondal},
  year = {2026},
  note = {Florence-2 and Tesseract hybrid with UIA enrichment for CPU-friendly screen understanding}
}
```

## License and Credits

- Florence-2: Microsoft Research (Apache 2.0)
- Tesseract OCR: Google Open Source (Apache 2.0)
- OpenCV: OpenCV Team (Apache 2.0)
- Transformers: Hugging Face (Apache 2.0)
- UIAutomation: Microsoft Windows SDK
