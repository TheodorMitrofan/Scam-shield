"""python3 -m detector.api [--host 127.0.0.1] [--port 8001]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = str(Path(__file__).resolve().parents[2])
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def main():
    p = argparse.ArgumentParser(description="Start the Scam Shield local detector HTTP API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8001)
    a = p.parse_args()

    try:
        import uvicorn
        from detector.api.app import app

        if app is not None:
            uvicorn.run(app, host=a.host, port=a.port, workers=1)
            return
    except ImportError:
        pass

    from detector.api.app import run_fallback_server

    run_fallback_server(host=a.host, port=a.port)


if __name__ == "__main__":
    main()
