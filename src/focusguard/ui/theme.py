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
    # frosted glass boxes over the mountain, #AARRGGBB
    "frostTint": "#B8FFFFFF",
    "frostBorder": "#D9FFFFFF",
    "frostHover": "#33FFFFFF",
    "primaryHover": "#7965AF",
}


# dark mode, same names
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
    "frostTint": "#A61C1C20",
    "frostBorder": "#33FFFFFF",
    "frostHover": "#1AFFFFFF",
    "primaryHover": "#E0D2FF",
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







# climb colour, green at the bottom -> blue halfway -> purple at the peak
# overwrites primary in both themes so buttons/sliders/numbers all follow how high u are

CLIMB_COLORS = ["#2E9E5B", "#2F6FD6", "#7A4BD6"]


def mixColor(firstColor, secondColor, amount):
    mixedColor = "#"
    for index in (1, 3, 5):
        firstValue = int(firstColor[index:index + 2], 16)
        secondValue = int(secondColor[index:index + 2], 16)
        mixedColor = mixedColor + format(round(firstValue + (secondValue - firstValue) * amount), "02X")
    return mixedColor


def climbAccent(climbFraction):
    if climbFraction < 0:
        climbFraction = 0
    if climbFraction > 1:
        climbFraction = 1

    # first half is green -> blue, second half is blue -> purple
    if climbFraction <= 0.5:
        return mixColor(CLIMB_COLORS[0], CLIMB_COLORS[1], climbFraction * 2)
    return mixColor(CLIMB_COLORS[1], CLIMB_COLORS[2], (climbFraction - 0.5) * 2)


def setClimbAccent(climbFraction):
    accentColor = climbAccent(climbFraction)

    # light mode
    COLORS["primary"] = accentColor
    COLORS["primaryHover"] = mixColor(accentColor, "#FFFFFF", 0.2)
    COLORS["onPrimary"] = "#FFFFFF"

    # dark mode needs a lighter version or blue/purple text vanishes on the dark glass
    lightAccent = mixColor(accentColor, "#FFFFFF", 0.5)
    DARK["primary"] = lightAccent
    DARK["primaryHover"] = mixColor(accentColor, "#FFFFFF", 0.65)
    DARK["onPrimary"] = "#16141C"




# swaps @colourName for the real colour

def applyTheme(styleText):
    # parse longest names first
    colors = getColors()
    tokenNames = sorted(colors.keys(), key=len, reverse=True)


    for tokenName in tokenNames:

        styleText = styleText.replace("@" + tokenName, colors[tokenName])
    return styleText
