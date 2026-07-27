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