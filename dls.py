# Compatibility shim so code/tests that import "dls" continue to work.
# Re-exports everything from backend.dls.
from backend import dls as _dls  # keep the module object available
from backend.dls import *  # re-export public names for legacy imports

# Optional: expose the backend module object for callers that expect a module
dls = _dls
