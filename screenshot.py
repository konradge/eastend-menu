#!/usr/bin/env python3
"""
Screenshot script for the eastend drink menu.

Captures the menu pages with headless Chrome as PNG (all full-bleed,
no grey border):
  - menu-16x9.png           16:9 (1920x1080)     -> horizontal card, for TV
  - menu-a4-landscape.png   A4 landscape, ~200dpi -> horizontal card, for print
  - menu-a4-portrait.png    A4 portrait,  ~200dpi -> vertical card, for print

Usage:
  python3 screenshot.py                    # all three shots from local files
  python3 screenshot.py --url http://...   # capture a remote deployment instead
"""

import argparse
import http.server
import os
import shutil
import subprocess
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES = {"horizontal": "/horizontal/", "vertical": "/"}


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("error: no Chrome/Chromium binary found (looked for google-chrome, chromium, ...)")


def start_local_server(directory: str) -> str:
    """Serve `directory` on a random free port in a background thread.

    Needed because the pages fetch menu.json / qrcode.svg, which does not
    work over file:// URLs.
    """

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}"


def shoot(chrome: str, url: str, width: int, height: int, scale: int, out: str) -> None:
    cmd = [
        chrome,
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
        f"--screenshot={out}",
        "--virtual-time-budget=3000",  # wait for fetch + render to finish
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"error: screenshot failed:\n{result.stderr.strip()}")
    print(f"  {out}  ({width * scale}x{height * scale} px)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", help="capture this URL instead of starting a local server")
    parser.add_argument("--output-dir", default=BASE_DIR,
                        help="where to write the PNG files (default: script directory)")
    args = parser.parse_args()

    chrome = find_chrome()
    os.makedirs(args.output_dir, exist_ok=True)

    if args.url:
        base_url = args.url.rstrip("/")
    else:
        base_url = start_local_server(BASE_DIR)
    print(f"capturing from {base_url}")

    # ?shot switches the page into full-bleed mode (no border / grey frame)
    h_page = f"{base_url}{PAGES['horizontal']}?shot"
    v_page = f"{base_url}{PAGES['vertical']}?shot"

    # 16:9 (1920x1080) -> horizontal card for screen display
    shoot(chrome, h_page, 1920, 1080, 1, os.path.join(args.output_dir, "menu-16x9.png"))

    # A4 landscape: 1123x794 CSS px at 96 dpi; 2x scale => 2246x1588 px (~200 dpi)
    shoot(chrome, h_page, 1123, 794, 2, os.path.join(args.output_dir, "menu-a4-landscape.png"))

    # A4 portrait: 794x1123 CSS px at 96 dpi; 2x scale => 1588x2246 px (~200 dpi)
    shoot(chrome, v_page, 794, 1123, 2, os.path.join(args.output_dir, "menu-a4-portrait.png"))


if __name__ == "__main__":
    main()
