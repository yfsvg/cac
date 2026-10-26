from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# The backdrop is one svg (assets/backdrop.svg) with @name colours in it,
# day and night just fill those in differently. "Shown" ones are 0 or 1 to hide a part.
BACKDROP_FILE = Path(__file__).parent / "assets" / "backdrop.svg"
DESIGN_WIDTH = 500
DESIGN_HEIGHT = 1000

DAY = {
    "skyTop": "#5FB6F2", "skyMid": "#9DD2F7", "skyMidAt": "0.35", "skyBottom": "#BFE0F6",
    "glow": "#FFE282", "glowStrength": "0.59", "glowSize": "140",
    "body": "#FFD84D", "bite": "white",
    "hill0": "#A9D9B9", "hill1": "#8FCDA5", "hill2": "#79C092",
    "ridge0": "#2A2163", "ridge1": "#211A50", "ridge2": "#191340",
    "starsShown": "0", "cloudsShown": "1", "hillsShown": "1", "ridgesShown": "0",
}

NIGHT = {
    "skyTop": "#0B0824", "skyMid": "#171139", "skyMidAt": "0.5", "skyBottom": "#261D5A",
    "glow": "#DCD2FF", "glowStrength": "0.27", "glowSize": "120",
    "body": "#F5E9C8", "bite": "black",
    "hill0": "#A9D9B9", "hill1": "#8FCDA5", "hill2": "#79C092",
    "ridge0": "#2A2163", "ridge1": "#211A50", "ridge2": "#191340",
    "starsShown": "1", "cloudsShown": "0", "hillsShown": "0", "ridgesShown": "1",
}

savedPictures = {}


def coloredBackdrop(colors):
    svgText = BACKDROP_FILE.read_text(encoding="utf-8")
    # longest names first so @skyMid doesnt eat the start of @skyMidAt
    for name in sorted(colors, key=len, reverse=True):
        svgText = svgText.replace("@" + name, colors[name])
    return QSvgRenderer(QByteArray(svgText.encode("utf-8")))


def backdropPicture(width, height, dark, pixelRatio):
    key = (width, height, dark, pixelRatio)
    if key not in savedPictures:
        savedPictures.clear()
        picture = QPixmap(int(width * pixelRatio), int(height * pixelRatio))
        picture.setDevicePixelRatio(pixelRatio)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer = coloredBackdrop(NIGHT if dark else DAY)
        scale = width / DESIGN_WIDTH
        # sky + stars stretch to fill, sun/moon/clouds stick to the top, hills stick to the bottom
        renderer.render(painter, "sky", QRectF(0, 0, width, height))
        renderer.render(painter, "stars", QRectF(0, 0, width, height * 0.75))
        topBox = renderer.boundsOnElement("top")
        renderer.render(painter, "top", QRectF(topBox.x() * scale, topBox.y() * scale, topBox.width() * scale, topBox.height() * scale))
        groundBox = renderer.boundsOnElement("ground")
        groundTop = height - (DESIGN_HEIGHT - groundBox.y()) * scale
        renderer.render(painter, "ground", QRectF(0, groundTop, width, groundBox.height() * scale))
        painter.end()
        savedPictures[key] = picture
    return savedPictures[key]
