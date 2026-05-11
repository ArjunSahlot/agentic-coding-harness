#!/usr/bin/env python3
"""Agentic Coding Harness -- entry point.

Usage:
    python main.py                           # start server, load model interactively via UI
    python main.py --model models/qwen-3.5-2b  # pre-load a model on startup
    python main.py --port 9000               # custom port
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import uvicorn

from server.app import create_app
from server.state import AppState


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
WEB_DIST = WEB_DIR / "dist" / "index.html"


def build_frontend(*, force: bool = False) -> None:
    """Build the React app so the API server is the single app entry point."""
    package_json = WEB_DIR / "package.json"
    if not package_json.exists():
        logging.warning("Frontend package.json not found; skipping frontend build")
        return

    source_files = list((WEB_DIR / "src").rglob("*")) + [WEB_DIR / "index.html", WEB_DIR / "vite.config.ts"]
    newest_source = max((p.stat().st_mtime for p in source_files if p.exists() and p.is_file()), default=0)
    dist_time = WEB_DIST.stat().st_mtime if WEB_DIST.exists() else 0
    if WEB_DIST.exists() and not force and dist_time >= newest_source:
        logging.info("Frontend build is current; serving %s", WEB_DIST)
        return

    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    logging.info("Building frontend for single-port serving...")
    try:
        subprocess.run([npm, "run", "build"], cwd=WEB_DIR, check=True)
    except FileNotFoundError:
        logging.warning("npm was not found; install Node.js or run `cd web && npm run build` manually")
    except subprocess.CalledProcessError as exc:
        if WEB_DIST.exists():
            logging.warning("Frontend build failed (%s); serving existing dist", exc.returncode)
        else:
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Coding Harness")
    parser.add_argument("--model", type=str, default=None, help="Path to model directory to load on startup")
    parser.add_argument("--models-dir", type=str, default="models", help="Directory containing local models")
    parser.add_argument("--device", type=str, default="cuda", help="Device to load model on (cuda, cpu)")
    parser.add_argument("--quantize", type=str, default=None, choices=["4bit", "8bit"], help="Load model quantized (requires bitsandbytes)")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"])
    parser.add_argument("--no-frontend-build", action="store_true", help="Skip building web/dist before serving")
    parser.add_argument("--force-frontend-build", action="store_true", help="Rebuild web/dist even when it looks current")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    state = AppState()
    state.models_dir = args.models_dir

    if args.model:
        logging.info("Pre-loading model: %s", args.model)
        state.engine.load(args.model, device=args.device, quantization=args.quantize)

    if not args.no_frontend_build:
        build_frontend(force=args.force_frontend_build)

    app = create_app(state)

    logging.info("Starting server and frontend at http://%s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
