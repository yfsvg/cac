# massive list of material you themes. Palette generated with claude
# FOR THIS PROJECT we're probably not going to edit this for dark mode but its a nice way to keep coding simple with the new material you design

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

COLORS = {
    "primary": "#6750A4",
    "onPrimary": "#FFFFFF",
    "primaryContainer": "#EADDFF",
    "onPrimaryContainer": "#21005D",
    "secondary": "#625B71",
    "secondaryContainer": "#E8DEF8",
    "onSecondaryContainer": "#1D192B",
    "tertiary": "#7D5260",
    "tertiaryContainer": "#FFD8E4",
    "onTertiaryContainer": "#31111D",
    "error": "#B3261E",
    "errorContainer": "#F9DEDC",
    "onErrorContainer": "#410E0B",

    "greenContainer": "#C4EED0",
    "onGreenContainer": "#072711",
    "green": "#1E6B35",
    "orangeContainer": "#FFDBC8",
    "onOrangeContainer": "#331200",
    "orange": "#9A4A12",
    "blueContainer": "#D3E3FD",
    "onBlueContainer": "#041E49",
    "blue": "#1B5FC1",

    # surfaces
    "surface": "#FEF7FF",
    "surfaceContainerLow": "#F7F2FA",
    "surfaceContainer": "#F3EDF7",
    "surfaceContainerHigh": "#ECE6F0",
    "surfaceContainerHighest": "#E6E0E9",
    "onSurface": "#1D1B20",
    "onSurfaceVariant": "#49454F",
    "outline": "#79747E",
    "outlineVariant": "#CAC4D0",
    "scrim": "rgba(29, 27, 32, 140)",
    "chipBackground": "rgba(255, 255, 255, 170)",
    "primaryHover": "#7965AF",
}

DARK = {
    "primary": "#D0BCFF",
    "onPrimary": "#381E72",
    "primaryContainer": "#4F378B",
    "onPrimaryContainer": "#EADDFF",
    "secondary": "#CCC2DC",
    "secondaryContainer": "#4A4458",
    "onSecondaryContainer": "#E8DEF8",
    "tertiary": "#EFB8C8",
    "tertiaryContainer": "#633B48",
    "onTertiaryContainer": "#FFD8E4",
    "error": "#F2B8B5",
    "errorContainer": "#8C1D18",
    "onErrorContainer": "#F9DEDC",

    "greenContainer": "#1F5130",
    "onGreenContainer": "#C4EED0",
    "green": "#8FD8A3",
    "orangeContainer": "#73350A",
    "onOrangeContainer": "#FFDBC8",
    "orange": "#FFB68B",
    "blueContainer": "#0B4A9E",
    "onBlueContainer": "#D3E3FD",
    "blue": "#A8C7FA",

    "surface": "#2E2E2E",
    "surfaceContainerLow": "#333333",
    "surfaceContainer": "#383838",
    "surfaceContainerHigh": "#404040",
    "surfaceContainerHighest": "#4A4A4A",
    "onSurface": "#E6E1E5",
    "onSurfaceVariant": "#CAC4D0",
    "outline": "#938F99",
    "outlineVariant": "#4F4B55",
    "scrim": "rgba(0, 0, 0, 160)",
    "chipBackground": "rgba(0, 0, 0, 90)",
    "primaryHover": "#E0D2FF",
}

currentTheme = "light"


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
    # qt reads the OS light/dark setting on windows and mac, light if it can't tell
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"


# the saved choice is "system", "light" or "dark". a theme only gets saved as an override when it
# differs from the OS, so toggling back to whatever the OS uses goes back to following the OS
def resolveTheme(choice, systemThemeName):
    if choice == "system":
        return systemThemeName
    return choice


def choiceFor(themeName, systemThemeName):
    if themeName == systemThemeName:
        return "system"
    return themeName




def applyTheme(styleText):
    # parse longest names first
    colors = getColors()
    tokenNames = sorted(colors.keys(), key=len, reverse=True)


    for tokenName in tokenNames:

        styleText = styleText.replace("@" + tokenName, colors[tokenName])
    return styleText
