"""Minimal aggregate-only PNG line plots without an optional plotting dependency."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def line_plot(path: Path, series: list[list[tuple[float, float]]]) -> None:
    """Write a compact unlabeled aggregate line plot; reports carry exact values."""
    width, height, margin = 640, 420, 35
    pixels = [[(255, 255, 255) for _ in range(width)] for _ in range(height)]
    colors = [(20, 90, 170), (190, 50, 40), (40, 140, 70), (130, 70, 160)]
    def mark(x: int, y: int, color):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < width and 0 <= y + dy < height:
                    pixels[y + dy][x + dx] = color
    for x in range(margin, width - margin):
        pixels[height - margin][x] = (80, 80, 80)
    for y in range(margin, height - margin):
        pixels[y][margin] = (80, 80, 80)
    for index, points in enumerate(series):
        previous = None
        for x_value, y_value in points:
            point = (
                margin + int(max(0, min(1, x_value)) * (width - 2 * margin)),
                height - margin - int(max(0, min(1, y_value)) * (height - 2 * margin)),
            )
            if previous:
                steps = max(abs(point[0] - previous[0]), abs(point[1] - previous[1]), 1)
                for step in range(steps + 1):
                    x = round(previous[0] + (point[0] - previous[0]) * step / steps)
                    y = round(previous[1] + (point[1] - previous[1]) * step / steps)
                    mark(x, y, colors[index % len(colors)])
            mark(*point, colors[index % len(colors)])
            previous = point
    _png(path, pixels)
