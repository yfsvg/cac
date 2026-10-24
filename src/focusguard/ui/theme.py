# massive list of material you themes. Palette generated with claude
# FOR THIS PROJECT we're probably not going to edit this for dark mode but its a nice way to keep coding simple with the new material you design

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
}




def applyTheme(styleText):
    # parse longest names first
    tokenNames = sorted(COLORS.keys(), key=len, reverse=True)


    for tokenName in tokenNames:

        styleText = styleText.replace("@" + tokenName, COLORS[tokenName])
    return styleText
