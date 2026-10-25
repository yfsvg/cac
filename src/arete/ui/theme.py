# massive list of material you themes. Palette generated with claude
# FOR THIS PROJECT we're probably not going to edit this for dark mode but its a nice way to keep coding simple with the new material you design

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

COLORS = {
    "primary": "#1E88E5",
    "onPrimary": "#FFFFFF",
    "primaryContainer": "#D3EBFF",
    "onPrimaryContainer": "#06345C",
    "secondary": "#4E6577",
    "secondaryContainer": "#E1F0FB",
    "onSecondaryContainer": "#0E2A3D",
    "tertiary": "#B98000",
    "tertiaryContainer": "#FFEFC2",
    "onTertiaryContainer": "#4A3300",
    "error": "#D9434B",
    "errorContainer": "#FFE1E0",
    "onErrorContainer": "#5C0F13",

    "greenContainer": "#DDF3CF",
    "onGreenContainer": "#173D08",
    "green": "#3D8F1E",
    "orangeContainer": "#FFE3CC",
    "onOrangeContainer": "#4A2200",
    "orange": "#B9580C",
    "blueContainer": "#D6E8FB",
    "onBlueContainer": "#062C55",
    "blue": "#1B6FC1",

    # surfaces
    "surface": "#EEF7FF",
    "surfaceContainerLow": "#FFFFFF",
    "surfaceContainer": "#F6FBFF",
    "surfaceContainerHigh": "#E8F3FC",
    "surfaceContainerHighest": "#D5E7F5",
    "onSurface": "#10283A",
    "onSurfaceVariant": "#47606F",
    "outline": "#7D93A3",
    "outlineVariant": "#C2D8E8",
    "scrim": "rgba(29, 27, 32, 140)",
    "chipBackground": "rgba(255, 255, 255, 170)",
    "primaryHover": "#42A0EE",
    "primaryShadow": "#1565B0",
    "trail": "#FFC23D",
    "trailShadow": "#D99A0B",
    "boss": "#D94E66",
}


# dark mode, same names
DARK = {
    "primary": "#5FE0B8",
    "onPrimary": "#04342C",
    "primaryContainer": "#3B2E80",
    "onPrimaryContainer": "#ECE6FF",
    "secondary": "#B5A9E6",
    "secondaryContainer": "#2E2560",
    "onSecondaryContainer": "#E6E0FF",
    "tertiary": "#FF8CC2",
    "tertiaryContainer": "#5A2149",
    "onTertiaryContainer": "#FFD9EA",
    "error": "#FF8A8F",
    "errorContainer": "#6B1F2A",
    "onErrorContainer": "#FFDADC",

    "greenContainer": "#1D4A3A",
    "onGreenContainer": "#CFF7E4",
    "green": "#6FE3B0",
    "orangeContainer": "#5C3214",
    "onOrangeContainer": "#FFE0C8",
    "orange": "#FFB577",
    "blueContainer": "#1C3C6E",
    "onBlueContainer": "#D8E9FF",
    "blue": "#8CC4FF",

    "surface": "#140F30",
    "surfaceContainerLow": "#1E1844",
    "surfaceContainer": "#251E50",
    "surfaceContainerHigh": "#2D255D",
    "surfaceContainerHighest": "#372E6B",
    "onSurface": "#EEEAFF",
    "onSurfaceVariant": "#B9B0DE",
    "outline": "#8579B8",
    "outlineVariant": "#3E3480",
    "scrim": "rgba(0, 0, 0, 160)",
    "chipBackground": "rgba(0, 0, 0, 90)",
    "primaryHover": "#85EBCB",
    "primaryShadow": "#2FA98A",
    "trail": "#5FE0B8",
    "trailShadow": "#2FA98A",
    "boss": "#FF6FA8",
}

currentTheme = "light"





# current theme stuff, light/dark/system

def setTheme(themeName):
    global currentTheme
    currentTheme = themeName


def getTheme():
    return currentTheme


def getColors():
    if currentTheme == "dark":
        return DARK
    return COLORS


def systemTheme():
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"


def resolveTheme(choice, systemThemeName):
    if choice == "system":
        return systemThemeName
    return choice


def choiceFor(themeName, systemThemeName):
    if themeName == systemThemeName:
        return "system"
    return themeName







# swaps @colourName for the real colour

def applyTheme(styleText):
    # parse longest names first
    colors = getColors()
    tokenNames = sorted(colors.keys(), key=len, reverse=True)


    for tokenName in tokenNames:

        styleText = styleText.replace("@" + tokenName, colors[tokenName])
    return styleText
