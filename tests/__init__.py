import os, sys
_SITE = "/opt/data/.local/lib/python3.14/site-packages"
if os.path.isdir(_SITE) and _SITE not in sys.path:
    sys.path.insert(0, _SITE)
