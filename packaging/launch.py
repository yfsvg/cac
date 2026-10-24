"""PyInstaller entry point. It lives outside the package because building from
`focusguard/__main__.py` would put `focusguard/` on sys.path, and `focusguard/platform`
would then shadow the stdlib `platform` module."""

from focusguard.__main__ import main

main()
