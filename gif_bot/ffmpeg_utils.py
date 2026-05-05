"""
ffmpeg_utils.py – Dynamic FFmpeg filter-graph builder.

Filter-graph construction logic
================================
The -vf (video filter) chain is built as a list of filter strings that are
joined with commas.  Order matters:

  1. setpts  – speed adjustment (must come first so reverse sees correct PTS)
  2. reverse – play backwards
  3. hflip   – mirror
  4. scale   – wide mode  (scale=iw*1.5:ih, then setsar=1)
  5. color filter – hue (b&w) or negate
  6. drawtext – text overlay (last, so it sits on top)

For the output container we use MP4 (H.264 + no audio) because Telegram
renders it as a looping silent animation (the "GIF" bubble).  We send it
via send_animation() which tells Telegram to treat it as a GIF.
"""

import os
import uuid
import asyncio
import subprocess
import logging

from config import FONTS_DIR, FONTS, SPEED_MAP, TEMP_DIR, WATERMARK

logger = logging.getLogger(__name__)


# ── coordinate helpers ────────────────────────────────────────────────────────

_POS_MAP = {
    # (x_expr, y_expr)  – uses FFmpeg drawtext variables: w, h, tw, th
    "tl": ("10",                    "10"),
    "tc": ("(w-tw)/2",              "10"),
    "tr": ("w-tw-10",               "10"),
    "ml": ("10",                    "(h-th)/2"),
    "mc": ("(w-tw)/2",              "(h-th)/2"),
    "mr": ("w-tw-10",               "(h-th)/2"),
    "bl": ("10",                    "h-th-10"),
    "bc": ("(w-tw)/2",              "h-th-10"),
    "br": ("w-tw-10",               "h-th-10"),
}


def _escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter value."""
    # Order matters: backslash first
    for ch in ("\\", ":", "'", "[", "]", "{", "}", ",", ";"):
        text = text.replace(ch, f"\\{ch}")
    return text


def build_filter_graph(state: dict) -> str:
    """
    Build the complete FFmpeg -vf filter string from the editor state dict.

    state keys:
        text        str | None
        position    str  e.g. "bc"
        font        str  e.g. "IRANSans"
        color       str  e.g. "white"
        filter      str  "normal" | "bw" | "negative"
        speed       str  "x0.5" | "x1" | "x2" | "x4"
        reverse     bool
        mirror      bool
        wide        bool
    """
    filters = []

    # 1. Speed
    speed = state.get("speed", "x1")
    pts_factor = SPEED_MAP.get(speed, "1.0")
    if pts_factor != "1.0":
        filters.append(f"setpts={pts_factor}*PTS")

    # 2. Reverse
    if state.get("reverse"):
        filters.append("reverse")

    # 3. Mirror
    if state.get("mirror"):
        filters.append("hflip")

    # 4. Wide mode – stretch width by 1.5×, keep height
    if state.get("wide"):
        filters.append("scale=iw*3/2:ih,setsar=1")

    # 5. Color filter
    color_filter = state.get("filter", "normal")
    if color_filter == "bw":
        filters.append("hue=s=0")          # desaturate → grayscale
    elif color_filter == "negative":
        filters.append("negate")

    # 6. Text overlay
    text = state.get("text")
    if text:
        pos_key = state.get("position", "bc")
        x_expr, y_expr = _POS_MAP.get(pos_key, _POS_MAP["bc"])

        font_name = state.get("font", "IRANSans")
        font_path = FONTS.get(font_name, list(FONTS.values())[0])
        # Escape colons in font path for Windows compatibility
        font_path_escaped = font_path.replace("\\", "/").replace(":", "\\:")

        color_key = state.get("color", "white")
        # rainbow → white text with colored outline (simple approximation)
        if color_key == "rainbow":
            font_color = "white"
            border_color = "0x00FF00"
        else:
            font_color = color_key
            border_color = "black" if color_key != "black" else "white"

        escaped_text = _escape_drawtext(text)

        drawtext = (
            f"drawtext="
            f"fontfile='{font_path_escaped}':"
            f"text='{escaped_text}':"
            f"fontcolor={font_color}:"
            f"fontsize=h/10:"          # 10% of video height
            f"borderw=3:"
            f"bordercolor={border_color}:"
            f"x={x_expr}:y={y_expr}"
        )
        filters.append(drawtext)

        # Watermark (small, bottom-left corner)
        wm_escaped = _escape_drawtext(WATERMARK)
        watermark = (
            f"drawtext="
            f"text='{wm_escaped}':"
            f"fontcolor=white@0.5:"
            f"fontsize=h/25:"
            f"borderw=1:"
            f"bordercolor=black@0.5:"
            f"x=5:y=h-th-5"
        )
        filters.append(watermark)

    return ",".join(filters) if filters else "null"


async def process_gif(input_path: str, state: dict) -> str:
    """
    Run FFmpeg asynchronously and return the path to the processed MP4.

    Raises RuntimeError if FFmpeg fails.
    """
    output_filename = f"{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)

    vf = build_filter_graph(state)

    cmd = [
        "ffmpeg",
        "-y",                   # overwrite without asking
        "-i", input_path,
        "-vf", vf,
        "-an",                  # strip audio (GIFs are silent)
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "28",           # quality: lower = better (18-28 typical)
        "-pix_fmt", "yuv420p",  # broad compatibility
        "-movflags", "+faststart",
        output_path,
    ]

    logger.debug("FFmpeg cmd: %s", " ".join(cmd))

    loop = asyncio.get_event_loop()
    try:
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,        # 2-minute hard limit
            ),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 120 seconds.")

    if proc.returncode != 0:
        logger.error("FFmpeg stderr: %s", proc.stderr)
        raise RuntimeError(f"FFmpeg failed (code {proc.returncode}):\n{proc.stderr[-500:]}")

    return output_path


def cleanup(*paths: str) -> None:
    """Delete temporary files, ignoring errors."""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
