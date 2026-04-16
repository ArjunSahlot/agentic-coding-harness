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
import sys

import uvicorn

from server.app import create_app
from server.state import AppState


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Coding Harness")
    parser.add_argument("--model", type=str, default=None, help="Path to model directory to load on startup")
    parser.add_argument("--models-dir", type=str, default="models", help="Directory containing local models")
    parser.add_argument("--device", type=str, default="cuda", help="Device to load model on (cuda, cpu)")
    parser.add_argument("--quantize", type=str, default=None, choices=["4bit", "8bit"], help="Load model quantized (requires bitsandbytes)")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"])
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

    app = create_app(state)

    logging.info("Starting server at http://%s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
