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


def get_cursor_info():
    try:
        x, y = auto.GetCursorPos()
        c = auto.ControlFromPoint(x, y)
        r = c.BoundingRectangle
        return {'position': [x, y], 'text': (c.Name or '')[:80],
                'control_type': c.ControlTypeName or 'unknown',
                'class_name': c.ClassName or 'unknown',
                'bounds': [r.left, r.top, r.right, r.bottom],
                'over_element_id': None}
    except Exception:
        try:
            x, y = auto.GetCursorPos()
            pos = [x, y]
        except Exception:
            pos = [-1, -1]
        return {'position': pos, 'text': '', 'control_type': 'unknown',
                'class_name': 'unknown', 'bounds': [], 'over_element_id': None}


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


def filter_elements_for_llm(elements):
    out = []
    for e in elements:
        if e['interactive'] and e['type'] not in ('code_content', 'text_label'):
            out.append(e)
    return out


def cursor_over(cursor_info, elements):
    cx, cy = cursor_info['position']
    if cx < 0 or cy < 0:
        return None
    for e in elements:
        x1, y1, x2, y2 = e['bounds']
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            return e['id']
    return None


def analyze_live_screen():
    start = time.time()
    print("Capturing live screen...")
    shot = ImageGrab.grab(all_screens=False)
    W, H = shot.size
    image = shot.convert("RGB")
    cursor_info = get_cursor_info()

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
    cursor_info['over_element_id'] = cursor_over(cursor_info, elements)
    screen_state = detect_screen_state(elements, window_info)

    by_type = {}
    for e in elements:
        by_type[e['type']] = by_type.get(e['type'], 0) + 1

    return {
        'metadata': {'timestamp': datetime.now().isoformat(), 'image_size': [W, H],
                     'dpi_scale': round(get_dpi_scale(), 3), 'coordinate_space': 'physical_pixels',
                     'processing_time_seconds': round(time.time() - start, 2),
                     'total_elements': len(elements), 'source': 'live_screen_capture'},
        'cursor': cursor_info,
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
    print(f"Cursor at: {result['cursor']['position']} over element: {result['cursor']['over_element_id']}")
    print(f"Total elements: {result['metadata']['total_elements']}")
    print(f"High confidence: {result['summary']['high_confidence_count']}")
    print(f"Element types: {result['summary']['by_type']}")
    print("Saved to: live_screen_analysis.json")