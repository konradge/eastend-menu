#!/usr/bin/env python3
"""
Screenshot script for the eastend drink menu.

Captures the menu page with headless Chrome as PNG:
  - menu-16x9.png        16:9 (1920x1080)  -> for TV / screen display
  - menu-a4-landscape.png  A4 landscape, ~200 DPI -> for printing

Usage:
  python3 screenshot.py                     # both shots, horizontal card
  python3 screenshot.py --page vertical     # use the vertical card instead
  python3 screenshot.py --url http://...    # take a remote page instead of
                                            # starting a local server
"""

import argparse
import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES = {"vertical": "/", "horizontal": "/horizontal/"}


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("error: no Chrome/Chromium binary found (looked for google-chrome, chromium, ...)")


def start_local_server(directory: str) -> str:
    """Serve `directory` on a random free port in a background thread.

    Needed because the page fetches menu.json / qrcode.svg, which does not
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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--page", choices=PAGES, default="horizontal",
                        help="which card to capture (default: horizontal)")
    parser.add_argument("--url", help="capture this URL instead of starting a local server")
    parser.add_argument("--output-dir", default=BASE_DIR,
                        help="where to write the PNG files (default: script directory)")
    args = parser.parse_args()

    chrome = find_chrome()
    os.makedirs(args.output_dir, exist_ok=True)

    if args.url:
        base_url = args.url.rstrip("/")
        page_url = base_url + PAGES[args.page]
        print(f"capturing {page_url}")
    else:
        base = start_local_server(BASE_DIR)
        page_url = base + PAGES[args.page]
        print(f"capturing {page_url}")

    suffix = f"-{args.page}" if args.page != "horizontal" else ""

    # 16:9 (1920x1080) -> for screen display, 1x scale is already plenty
    shoot(chrome, page_url, 1920, 1080, 1, os.path.join(args.output_dir, f"menu-16x9{suffix}.png"))

    # A4 landscape: 1123x794 CSS px at 96 dpi; 2x scale => 2246x1588 px (~200 dpi)
    shoot(chrome, page_url, 1123, 794, 2, os.path.join(args.output_dir, f"menu-a4-landscape{suffix}.png"))


if __name__ == "__main__":
    main()
