# Compatibility shim so code/tests that import "dls" continue to work.
# Re-exports everything from backend.dls, including "private" names (leading underscore)
# because some tests import underscored helpers directly (legacy-style).
from backend import dls as _dls

# Copy everything from backend.dls into this module's globals, excluding dunders
for _name in dir(_dls):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_dls, _name)

# Also keep a reference to the original module object if callers expect it
backend_dls = _dls
