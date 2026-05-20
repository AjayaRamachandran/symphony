# Window-management backends for the Symphony pywebview host.
#
# Submodules:
#   win64_winman  - Win32 / DWM frameless window, drag-source, drop-target.
#   macos_winman  - macOS / AppKit peer with the same call surface.
#
# main.py picks the platform-specific module at import time and aliases it as
# ``win_c`` so the rest of the codebase can call ``winman.<fn>(...)`` without
# branching on sys.platform.
