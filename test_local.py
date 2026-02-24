"""Local test script for pdf-engine-toolbox.

Usage:
    Step 1 - Start the app (one time):
        docker compose up

    Step 2 - Test any PDF file:
        python test_local.py "D:/path/to/your/file.pdf"

    Output will be saved to:
        test_output/<filename>/
            pdf_info.json
            thumbnails.json
            text_extract.json
            text_search.json
            detect_blank_pages.json
            table_extraction.json
            ocr.json

    Examples:
        python test_local.py "D:/Backups/tax-examples/Stella/A1x_-_NVIDIA_equities.pdf"
        python test_local.py "D:/Backups/tax-examples/Stella/Lobritz_Michael_-_2023_U_S_Tax_Filing_CLIENT_COPY.pdf"
"""

import hashlib
import hmac
import http.server
import json
import os
import pathlib
import sys
import threading
import time

import httpx

# Config
BASE_URL = "http://localhost:8000"
SECRET = "local-dev-secret-change-me"


def sign_request(method: str, path: str, body: bytes) -> dict[str, str]:
    """Generate HMAC-SHA256 signed headers."""
    timestamp = str(int(time.time() * 1000))
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}:{method}:{path}:{body_hash}"
    signature = hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


def test_endpoint(
    name: str, method: str, path: str, body: dict, output_dir: str
) -> dict | None:
    """Send a signed request, print the result, and save JSON to output_dir."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

    body_bytes = json.dumps(body).encode()
    headers = sign_request(method, path, body_bytes)

    start = time.monotonic()
    try:
        with httpx.Client(timeout=180) as client:
            response = client.request(
                method, f"{BASE_URL}{path}", content=body_bytes, headers=headers
            )
        elapsed = (time.monotonic() - start) * 1000

        print(f"  Status: {response.status_code}")
        print(f"  Time:   {elapsed:.0f}ms")

        data = response.json()

        # Save full JSON response
        safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        out_path = os.path.join(output_dir, f"{safe_name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved:  {out_path}")

        if response.status_code == 200:
            if "processing_time_ms" in data:
                print(f"  Server time: {data['processing_time_ms']}ms")
            if "data" in data:
                d = data["data"]
                if "thumbnails" in d:
                    print(f"  Thumbnails: {len(d['thumbnails'])} generated")
                if "pages" in d and "total_words" not in d:
                    print(f"  Pages: {len(d['pages'])}")
                    for p in d["pages"][:3]:
                        text_preview = (
                            p.get("text", "")[:80]
                            .encode("ascii", "replace")
                            .decode()
                            .replace("\n", " ")
                        )
                        print(f"    Page {p.get('page_index', '?')}: {text_preview}...")
                if "total_words" in d:
                    print(
                        f"  Total words: {d['total_words']}, "
                        f"Avg confidence: {d['avg_confidence']}"
                    )
                    # Show first few words per page
                    for p in d.get("pages", []):
                        words = p.get("words", [])
                        pi = p.get("page_index", "?")
                        print(f"    Page {pi}: {len(words)} words")
                        for w in words[:5]:
                            t = w["text"].encode("ascii", "replace").decode()
                            print(f'      "{t}" (conf: {w["confidence"]})')
                        if len(words) > 5:
                            print(f"      ... +{len(words) - 5} more")
                if "tables" in d:
                    print(f"  Tables found: {d['total_count']}")
                    for t in d.get("tables", []):
                        print(
                            f"    Table {t['table_index']}: "
                            f"{t['row_count']}x{t['col_count']}"
                        )
                if "matches" in d:
                    print(f"  Matches: {d['total_matches']}")
                if "page_count" in d:
                    print(f"  Page count: {d['page_count']}")
            return data
        else:
            err = data.get("error", {})
            print(
                f"  Error: {err.get('code', '?')} - "
                f"{err.get('message', response.text[:200])}"
            )
            return data
    except httpx.ConnectError:
        print(f"  ERROR: Cannot connect to {BASE_URL}. Is the server running?")
        print("  Run: docker compose up")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def start_file_server(directory: str, port: int = 9000) -> None:
    """Start a background HTTP file server for the PDF directory."""

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            pass  # Silence request logging

    server = http.server.HTTPServer(("0.0.0.0", port), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def main():
    # ── Parse arguments ──────────────────────────────────────────────
    if len(sys.argv) < 2:
        print("Usage: python test_local.py <path-to-pdf>")
        print()
        print("Examples:")
        print('  python test_local.py "D:/Backups/tax-examples/Stella/A1x_-_NVIDIA_equities.pdf"')
        print('  python test_local.py "D:/Backups/tax-examples/Stella/Lobritz_Michael_-_2023_U_S_Tax_Filing_CLIENT_COPY.pdf"')
        sys.exit(1)

    pdf_path = pathlib.Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    pdf_name = pdf_path.stem  # filename without extension

    # ── Output directory: test_output/<filename>/ ────────────────────
    output_dir = os.path.join(os.path.dirname(__file__), "test_output", pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    # ── Start embedded file server ───────────────────────────────────
    pdf_dir = str(pdf_path.parent)
    pdf_filename = pdf_path.name
    port = 9000

    try:
        start_file_server(pdf_dir, port)
    except OSError:
        # Port already in use — assume file server is already running
        pass

    # URL that Docker container can reach (host.docker.internal maps to host)
    pdf_url = f"http://host.docker.internal:{port}/{pdf_filename}"
    pdf_body = {"source_url": pdf_url}

    print(f"\n  PDF file:   {pdf_path}")
    print(f"  Serving at: {pdf_url}")
    print(f"  Output dir: {output_dir}")

    # ── Health check ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("TEST: Health Check")
    print(f"{'='*60}")
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.json()}")
    except httpx.ConnectError:
        print("  ERROR: Cannot connect. Is the server running?")
        print("  Run: docker compose up")
        sys.exit(1)

    # ── Get page count ───────────────────────────────────────────────
    info = test_endpoint("PDF Info", "POST", "/info", pdf_body, output_dir)
    page_count = 0
    if info and info.get("success"):
        page_count = info.get("data", {}).get("page_count", 0)

    if page_count == 0:
        print("  ERROR: Could not determine page count. Aborting.")
        sys.exit(1)

    max_test_pages = min(3, page_count)
    test_pages = list(range(max_test_pages))
    print(f"\n  Document has {page_count} pages. Testing pages 0-{max_test_pages - 1}.\n")

    # ── Run all tests ────────────────────────────────────────────────
    test_endpoint("Thumbnails", "POST", "/thumbnails", {
        **pdf_body, "pages": test_pages, "width": 200, "format": "webp", "quality": 80,
    }, output_dir)

    test_endpoint("Text Extract", "POST", "/text/extract", {
        **pdf_body, "pages": test_pages,
    }, output_dir)

    test_endpoint("Text Search", "POST", "/text/search", {
        **pdf_body, "query": "total",
    }, output_dir)

    test_endpoint("Detect Blank Pages", "POST", "/pages/detect-blank", pdf_body, output_dir)

    test_endpoint("Table Extraction", "POST", "/text/tables", {
        **pdf_body, "pages": [0], "strategy": "auto",
    }, output_dir)

    test_endpoint("OCR", "POST", "/text/ocr", {
        **pdf_body, "pages": test_pages, "language": "en", "dpi": 300,
    }, output_dir)

    # ── Done ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"ALL TESTS COMPLETE")
    print(f"{'='*60}")
    print(f"\n  Results saved to: {output_dir}\\")
    for f in sorted(os.listdir(output_dir)):
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"    {f:<30s} {size:>10,} bytes")
    print()


if __name__ == "__main__":
    main()
