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