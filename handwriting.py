#!/usr/bin/env python3
"""OCR handwriting via LightOnOCR GGUF using a local llama.cpp server."""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_IMAGE = SCRIPT_DIR / "assignment3.JPG"
DEFAULT_URL = "http://localhost:8080/v1/chat/completions"
DEFAULT_MODEL = "../LightOnOCR-2-1B-Q4_K_M.gguf"
DEFAULT_PROMPT = ""
DEFAULT_MIME = "image/jpeg"


def encode_image(image_path: Path) -> str:
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode()

def get_first_model_id(url: str) -> str | None:
    models_url = url.rsplit("/", 2)[0] + "/models"
    response = requests.get(models_url, timeout=30)
    response.raise_for_status()
    data = response.json()
    try:
        return data["data"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Handwriting OCR via LightOnOCR")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE, help="Path to image")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Server URL")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Max tokens")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature")
    parser.add_argument("--top-k", type=int, default=0, help="Top-k")
    parser.add_argument("--top-p", type=float, default=0.9, help="Top-p")
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_PROMPT,
        help="Optional text prompt (some OCR models accept images only)",
    )
    parser.add_argument("--image-mime", type=str, default=DEFAULT_MIME, help="MIME type")
    parser.add_argument("--auto-model", action="store_true", help="Use first /v1/models id")
    parser.add_argument("--debug", action="store_true", help="Print request/response info")
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")

    image_base64 = encode_image(args.image)
    model_id = args.model
    if args.auto_model:
        server_model = get_first_model_id(args.url)
        if server_model:
            model_id = server_model
    if args.debug:
        print(f"Image: {args.image} ({args.image.stat().st_size} bytes)")
        print(f"Model: {model_id}")

    content = []
    if args.prompt.strip():
        content.append({"type": "text", "text": args.prompt})
    content.append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:{args.image_mime};base64,{image_base64}"},
        }
    )

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
    }

    response = requests.post(args.url, json=payload, timeout=300)
    response.raise_for_status()
    data = response.json()
    if args.debug:
        print(f"Response keys: {list(data.keys())}")

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Unexpected response: {data}") from exc

    print(text.strip())


if __name__ == "__main__":
    main()

# From LLaMA: ./venv/bin/python TestLLMs/handwriting.py --auto-model --debug
# From llama.cpp: ./build/bin/llama-server -m ../LightOnOCR-2-1B-Q4_K_M.gguf --mmproj ../mmproj-LightOnOCR-2-1B-Q8_0.gguf -c 8192 --temp 0.2 --top-k 0 --top-p 0.9