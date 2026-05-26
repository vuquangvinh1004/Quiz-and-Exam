"""Generate app_icon.png and app_icon.ico for Quiz Desktop App.

Requires PySide6 (already in requirements.txt).
Run once from the project root:
    python assets/icons/generate_icon.py

Output:
    assets/icons/app_icon.png   (256x256 PNG)
    assets/icons/app_icon.ico   (multi-size ICO: 16,32,48,64,128,256)
"""
from __future__ import annotations

import struct
import sys
import zlib
from io import BytesIO
from pathlib import Path

# ---------------------------------------------------------------------------
# PySide6 is required – start a minimal QApplication for QPainter
# ---------------------------------------------------------------------------
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QPainter,
    QPainterPath,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication

ICONS_DIR = Path(__file__).resolve().parent


def _draw_icon(size: int) -> QImage:
    """Draw a quiz-themed icon at the given pixel size."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # --- Background circle with gradient ---
    grad = QRadialGradient(size * 0.45, size * 0.38, size * 0.55)
    grad.setColorAt(0.0, QColor("#5B8DEF"))   # light blue center
    grad.setColorAt(1.0, QColor("#1A4FA0"))   # dark blue edge
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    margin = max(1, size // 16)
    p.drawEllipse(margin, margin, size - margin * 2, size - margin * 2)

    # --- White rounded rect (paper/card) ---
    card_margin = int(size * 0.18)
    card_w = size - card_margin * 2
    card_h = int(card_w * 1.15)
    card_x = card_margin
    card_y = int((size - card_h) // 2)
    radius = max(2, size // 14)
    p.setBrush(QColor(255, 255, 255, 230))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    path.addRoundedRect(card_x, card_y, card_w, card_h, radius, radius)
    p.drawPath(path)

    # --- Question mark "?" ---
    font_size = max(10, int(size * 0.42))
    font = QFont("Arial", font_size, QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#1A4FA0"))
    fm = QFontMetrics(font)
    text = "?"
    text_rect = fm.boundingRect(text)
    tx = card_x + (card_w - text_rect.width()) // 2 - text_rect.x()
    ty = card_y + (card_h - text_rect.height()) // 2 - text_rect.y()
    p.drawText(tx, ty, text)

    # --- Small colored dots (answer options A B C D) at the bottom of card ---
    dot_colors = ["#FF6B6B", "#4CAF50", "#FFC107", "#2196F3"]
    dot_size = max(3, int(size * 0.06))
    dot_spacing = max(4, int(size * 0.09))
    total_dots_w = len(dot_colors) * dot_size + (len(dot_colors) - 1) * (dot_spacing - dot_size)
    dot_y = card_y + card_h - int(size * 0.12)
    dot_x_start = card_x + (card_w - total_dots_w) // 2
    for i, color in enumerate(dot_colors):
        cx = dot_x_start + i * dot_spacing
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx, dot_y, dot_size, dot_size)

    p.end()
    return img


# ---------------------------------------------------------------------------
# ICO writer (no Pillow needed)
# ---------------------------------------------------------------------------

def _png_bytes_from_qimage(img: QImage) -> bytes:
    """Export QImage to PNG bytes via Qt's own encoder."""
    buf = BytesIO()
    ba = img.bits().tobytes()  # raw ARGB32 little-endian

    # Re-encode via Qt save to buffer approach using QByteArray
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    qba = QByteArray()
    qbuf = QBuffer(qba)
    qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(qbuf, "PNG")
    qbuf.close()
    return bytes(qba)


def _write_ico(png_map: dict[int, bytes], out_path: Path) -> None:
    """Write a multi-size .ico file from a dict of {size: png_bytes}.

    Uses the PNG-in-ICO format (Vista+), which keeps files small.
    """
    sizes = sorted(png_map.keys())
    count = len(sizes)

    # ICO header: 6 bytes
    header = struct.pack("<HHH", 0, 1, count)

    # Directory entries: 16 bytes each
    # Data starts after header + directory
    data_offset = 6 + count * 16
    dir_entries = b""
    image_data = b""

    for sz in sizes:
        png = png_map[sz]
        w = sz if sz < 256 else 0   # ICO uses 0 to mean 256
        h = sz if sz < 256 else 0
        dir_entries += struct.pack(
            "<BBBBHHII",
            w, h,       # width, height (0 = 256)
            0,          # color count (0 = no palette)
            0,          # reserved
            1,          # color planes
            32,         # bits per pixel
            len(png),   # size of image data
            data_offset + len(image_data),  # offset
        )
        image_data += png

    out_path.write_bytes(header + dir_entries + image_data)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)

    sizes = [16, 32, 48, 64, 128, 256]
    png_map: dict[int, bytes] = {}

    for sz in sizes:
        img = _draw_icon(sz)
        png_map[sz] = _png_bytes_from_qimage(img)

    # Save 256x256 PNG for use at runtime
    png_path = ICONS_DIR / "app_icon.png"
    png_path.write_bytes(png_map[256])
    print(f"Saved: {png_path}")

    # Save ICO for PyInstaller EXE
    ico_path = ICONS_DIR / "app_icon.ico"
    _write_ico(png_map, ico_path)
    print(f"Saved: {ico_path}")


if __name__ == "__main__":
    main()
