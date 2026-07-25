"""
===============================================================================
Project: SAM ScreenParser

Goal
-------------------------------------------------------------------------------
This project aims to convert a screenshot into a complete, compact, structured,
and deterministic screen representation that another AI agent can understand
and use for desktop automation.

Instead of asking an LLM to directly click or reason from raw images every time,
the vision model acts as a "Screen Parser".

The parser should:
- Understand the complete screen.
- Detect every visible object.
- Preserve visual hierarchy.
- Extract all readable text.
- Describe interaction state.
- Provide approximate coordinates.
- Never hallucinate hidden content.
- Never intentionally ignore visible objects.
- Produce consistent output for the same screenshot.

The output will later be parsed by another automation agent capable of:
- Mouse movement, Clicking, Double-clicking, Drag & Drop
- Keyboard typing, Scrolling
- Screen comparison, UI state tracking, Task planning

Long-term Goal
-------------------------------------------------------------------------------
Screenshot -> Vision LLM (ScreenParser) -> Structured Screen Description
         -> Planning LLM -> Python Desktop Automation Agent
===============================================================================
"""

import base64
import sys
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from openai import OpenAI

KOBOLDCPP_EXE = r"D:\Download\Projects\qwen 3.5 4b\koboldcpp.exe"
MODEL_GGUF = r"D:\Download\Projects\qwen 3.5 4b\Qwen3.5-4B-UD-Q4_K_XL.gguf"
MMPROJ_GGUF = r"D:\Download\Projects\qwen 3.5 4b\mmproj-BF16.gguf"

API_URL = "http://localhost:5001/v1"
API_KEY = "dummy"
MODEL_NAME = "Qwen3.5-4B"

BASE_DIR = Path(__file__).parent.resolve()
IMAGE_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"

SYSTEM_PROMPT = """You are ScreenParser.

Convert any screenshot into a complete, compact, and deterministic screen representation for another AI agent.

Observe only what is visible. Never assume the platform, application, or UI type. Never invent hidden or occluded content. If uncertain, write UNCERTAIN instead of guessing.

Include every visible object exactly once. Preserve the visual hierarchy, reading order, spatial relationships, and interaction state. Extract all readable text.

Return only the following sections:

1. Screen Summary
2. Interaction Summary
3. Layout
4. Objects
For every object include:
- ID
- Description
- Visible Text
- Center (@x,y)
- Bounds
- Confidence
- Interactive
- State
- Parent
5. OCR
6. Relationships

Return only the structured representation."""

def start_server():
    print("Starting KoboldCPP server...")
    cmd = [
        KOBOLDCPP_EXE,
        "--model", MODEL_GGUF,
        "--mmproj", MMPROJ_GGUF,
        "--jinja",
        "--jinjathink", "false",
        "--threads", "8",
        "--port", "5001",
        "--host", "127.0.0.1"
    ]
    
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        
    subprocess.Popen(cmd, creationflags=creationflags)

def wait_for_server(timeout=180):
    print("Waiting for server to initialize...")
    start_time = time.time()
    url = f"{API_URL}/models"
    
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print("Server is ready.")
                    return True
        except (urllib.error.URLError, Exception):
            time.sleep(3)
            
    print("Error: Server failed to start within the timeout period.")
    sys.exit(1)

def load_and_encode_image():
    if not IMAGE_DIR.exists():
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    image_files = [f for f in IMAGE_DIR.iterdir() if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"Error: No images found in {IMAGE_DIR}")
        sys.exit(1)
        
    image_path = image_files[0]
    print(f"Loading image: {image_path.name}")
    
    ext = image_path.suffix.lower()
    mime_map = {".png": "image/png", ".webp": "image/webp", ".bmp": "image/bmp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
        
    return image_base64, mime_type

def main():
    print("SAM ScreenParser initialized.")
    
    start_server()
    wait_for_server()
    
    image_base64, mime_type = load_and_encode_image()
    
    client = OpenAI(base_url=API_URL, api_key=API_KEY)
    
    print("Sending image to vision model...")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Parse this screenshot into the required screen representation."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Error: API request failed. Details: {e}")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    screen_data = response.choices[0].message.content
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "screen-data.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(screen_data)
        
    print(f"Processing complete. Time elapsed: {elapsed:.2f}s")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
