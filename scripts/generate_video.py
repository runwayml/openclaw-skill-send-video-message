#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "runwayml>=4.0.0",
#   "httpx>=0.27.0",
# ]
# ///
"""
Generate an avatar video from text.

Flow: text -> Runway TTS (audio URL) -> Runway avatar_videos (video URL) -> download .mp4

Usage:
  uv run generate_video.py --text "Hello, how are you?"
  uv run generate_video.py --text "Hi there" --voice "Arjun"
  uv run generate_video.py --text "Hi there" --avatar-id "your-uuid"
  uv run generate_video.py --text "Hi there" --output /tmp/my-video.mp4
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


POLL_INTERVAL = 3
POLL_TIMEOUT = 600
DEFAULT_PRESET = "game-host"
DEFAULT_VOICE = "Maya"
DEFAULT_BASE_URL = "https://api.dev.runwayml.com"
API_VERSION = "2024-11-06"


def get_config(key: str, default: str | None = None) -> str | None:
    config_path = Path.home() / ".openclaw" / "runway-avatar.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            if key in config:
                return config[key]
        except (json.JSONDecodeError, KeyError):
            pass
    return default


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
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] {status}...")
        time.sleep(POLL_INTERVAL)
    print(f"Error: Task {task_id} timed out after {POLL_TIMEOUT}s.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate an avatar video from text")
    parser.add_argument("--text", "-t", required=True, help="Text for the avatar to speak")
    parser.add_argument("--preset-id", help="Runway preset avatar ID (default: game-host)")
    parser.add_argument("--avatar-id", help="Custom avatar ID (overrides --preset-id)")
    parser.add_argument("--voice", "-v", help="TTS voice preset name (default: Maya)")
    parser.add_argument("--output", "-o", help="Output file path (default: /tmp/runway-avatar-<timestamp>.mp4)")
    parser.add_argument("--api-key", "-k", help="Runway API key (overrides env)")
    parser.add_argument("--base-url", help="API base URL (overrides env)")
    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    base_url = resolve_base_url(args.base_url)

    # Precedence: explicit --avatar-id > explicit --preset-id (ignores saved avatar) > saved/env avatar > default preset
    if args.avatar_id:
        avatar_id = args.avatar_id
        preset_id = args.preset_id or os.environ.get("RUNWAY_AVATAR_PRESET", DEFAULT_PRESET)
    elif args.preset_id:
        avatar_id = None
        preset_id = args.preset_id
    else:
        avatar_id = os.environ.get("RUNWAY_AVATAR_ID") or get_config("avatar_id")
        preset_id = os.environ.get("RUNWAY_AVATAR_PRESET", DEFAULT_PRESET)
    voice_preset = (
        args.voice
        or os.environ.get("RUNWAY_VOICE_PRESET", DEFAULT_VOICE)
    )

    from runwayml import RunwayML
    import httpx

    client = RunwayML(api_key=api_key, base_url=base_url)

    text_preview = args.text[:60] + ("..." if len(args.text) > 60 else "")
    print(f"Generating video: \"{text_preview}\"")

    print(f"  Step 1/3: Text-to-speech (voice: {voice_preset})...")
    tts_task = client.text_to_speech.create(
        model="eleven_multilingual_v2",
        prompt_text=args.text,
        voice={"type": "runway-preset", "preset_id": voice_preset},
    )
    tts_result = poll_task(client, tts_task.id)
    audio_url = tts_result.output[0]

    if avatar_id:
        avatar_config = {"type": "custom", "avatarId": avatar_id}
        label = f"custom ({avatar_id[:8]}...)"
    else:
        avatar_config = {"type": "runway-preset", "presetId": preset_id}
        label = f"preset ({preset_id})"

    print(f"  Step 2/3: Avatar video (avatar: {label})...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": API_VERSION,
    }
    body = {
        "model": "gwm1_avatars",
        "avatar": avatar_config,
        "inputAudio": audio_url,
    }

    with httpx.Client(timeout=60) as http:
        resp = http.post(f"{base_url}/v1/avatar_videos", headers=headers, json=body)
        if resp.status_code >= 400:
            print(f"Error: avatar_videos returned {resp.status_code}: {resp.text}", file=sys.stderr)
            sys.exit(1)
        video_task_id = resp.json()["id"]

    video_result = poll_task(client, video_task_id)
    video_url = video_result.output[0]

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_path = Path(f"/tmp/runway-avatar-{timestamp}.mp4")

    print(f"  Step 3/3: Downloading video...")
    with httpx.Client(timeout=120, follow_redirects=True) as http:
        dl = http.get(video_url)
        dl.raise_for_status()
        output_path.write_bytes(dl.content)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nDone! Video saved: {output_path} ({size_mb:.1f} MB)")
    print(f"MEDIA: {output_path}")


if __name__ == "__main__":
    main()
