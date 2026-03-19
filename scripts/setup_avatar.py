#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "runwayml>=4.0.0",
#   "httpx>=0.27.0",
# ]
# ///
"""
Create a custom Runway avatar (one-time setup).

Optionally generates a portrait image via text-to-image, then creates an avatar
with a personality prompt and voice preset. Polls until the avatar is READY.

Usage:
  uv run setup_avatar.py --name "Mochi" --description "A cute cartoon cat, head and shoulders, facing camera"
  uv run setup_avatar.py --name "Mochi" --image-url "https://example.com/photo.jpg" --personality "You are Mochi, a friendly assistant."
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


POLL_INTERVAL = 3
POLL_TIMEOUT = 300
DEFAULT_VOICE = "Maya"
DEFAULT_BASE_URL = "https://api.dev.runwayml.com"
DEFAULT_PERSONALITY = (
    "You are a friendly and helpful assistant. "
    "Be clear, concise, and conversational."
)
API_VERSION = "2024-11-06"
CONFIG_PATH = Path.home() / ".openclaw" / "runway-avatar.json"


def resolve_api_key(arg_key: str | None) -> str:
    key = arg_key or os.environ.get("RUNWAY_API_SECRET")
    if not key:
        print("Error: No API key. Set RUNWAY_API_SECRET or pass --api-key.", file=sys.stderr)
        sys.exit(1)
    return key


def resolve_base_url(arg_url: str | None) -> str:
    return arg_url or os.environ.get("RUNWAY_BASE_URL", DEFAULT_BASE_URL)


def poll_task(client, task_id: str) -> dict:
    """Poll a Runway task until it reaches a terminal state."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        task = client.tasks.retrieve(task_id)
        status = task.status
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED"):
            failure = getattr(task, "failure", None) or "Unknown error"
            print(f"Error: Task {task_id} {status}: {failure}", file=sys.stderr)
            sys.exit(1)
        print(f"  Status: {status}...")
        time.sleep(POLL_INTERVAL)
    print(f"Error: Task {task_id} timed out after {POLL_TIMEOUT}s.", file=sys.stderr)
    sys.exit(1)


def poll_avatar_ready(api_key: str, base_url: str, avatar_id: str) -> dict:
    """Poll GET /v1/avatars/{id} until status is READY."""
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": API_VERSION,
    }
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        with httpx.Client(timeout=30) as http:
            resp = http.get(f"{base_url}/v1/avatars/{avatar_id}", headers=headers)
            if resp.status_code >= 400:
                print(f"Error: GET /v1/avatars/{avatar_id} returned {resp.status_code}: {resp.text}", file=sys.stderr)
                sys.exit(1)
            data = resp.json()

        status = data.get("status", "UNKNOWN")
        if status == "READY":
            return data
        if status == "FAILED":
            print(f"Error: Avatar {avatar_id} failed to process.", file=sys.stderr)
            sys.exit(1)
        print(f"  Avatar status: {status}...")
        time.sleep(POLL_INTERVAL)

    print(f"Error: Avatar {avatar_id} not ready after {POLL_TIMEOUT}s.", file=sys.stderr)
    sys.exit(1)


def save_config(avatar_id: str, name: str):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            pass
    config["avatar_id"] = avatar_id
    config["avatar_name"] = name
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Create a custom Runway avatar")
    parser.add_argument("--name", "-n", required=True, help="Avatar name")
    parser.add_argument(
        "--description", "-d",
        help="Text prompt to generate a portrait image (used if --image-url is not provided)",
    )
    parser.add_argument("--image-url", help="URL of an existing image to use as the avatar")
    parser.add_argument(
        "--personality", "-p",
        default=DEFAULT_PERSONALITY,
        help="Personality prompt for the avatar",
    )
    parser.add_argument("--voice", "-v", default=DEFAULT_VOICE, help="TTS voice preset")
    parser.add_argument("--api-key", "-k", help="Runway API key (overrides env)")
    parser.add_argument("--base-url", help="API base URL (overrides env)")
    args = parser.parse_args()

    if not args.image_url and not args.description:
        print("Error: Provide --description (to generate an image) or --image-url.", file=sys.stderr)
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    base_url = resolve_base_url(args.base_url)

    from runwayml import RunwayML
    import httpx

    client = RunwayML(api_key=api_key, base_url=base_url)

    image_url = args.image_url
    if not image_url:
        print(f"Generating avatar image: \"{args.description}\"...")
        img_task = client.text_to_image.create(
            model="gen4_image",
            prompt_text=args.description,
            ratio="1080:1080",
        )
        print(f"  Image task: {img_task.id}")
        img_result = poll_task(client, img_task.id)
        image_url = img_result.output[0]
        print(f"  Image ready: {image_url[:80]}...")

    print(f"Creating avatar '{args.name}'...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Runway-Version": API_VERSION,
    }
    body = {
        "name": args.name,
        "referenceImage": image_url,
        "personality": args.personality,
        "voice": {
            "type": "runway-live-preset",
            "presetId": args.voice.lower(),
        },
        "imageProcessing": "optimize",
    }

    with httpx.Client(timeout=60) as http:
        resp = http.post(f"{base_url}/v1/avatars", headers=headers, json=body)
        if resp.status_code >= 400:
            print(f"Error: /v1/avatars returned {resp.status_code}: {resp.text}", file=sys.stderr)
            sys.exit(1)
        avatar_data = resp.json()

    avatar_id = avatar_data.get("id") or avatar_data.get("avatarId")
    if not avatar_id:
        print(f"Error: Unexpected response: {json.dumps(avatar_data)}", file=sys.stderr)
        sys.exit(1)

    status = avatar_data.get("status", "UNKNOWN")
    if status != "READY":
        print(f"  Avatar created (status: {status}), waiting for READY...")
        poll_avatar_ready(api_key, base_url, avatar_id)

    save_config(avatar_id, args.name)

    print(f"\nAvatar created successfully!")
    print(f"  Name:   {args.name}")
    print(f"  ID:     {avatar_id}")
    print(f"  Status: READY")
    print(f"  Config: {CONFIG_PATH}")
    print(f"\nThe avatar ID has been saved. generate_video.py will use it automatically.")


if __name__ == "__main__":
    main()
