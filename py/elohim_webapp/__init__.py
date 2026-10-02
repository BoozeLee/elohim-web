"""elohim_webapp: Pyodide-compatible web surface for elohim.

Replaces the FastAPI layer in the original monorepo. The bridge module
exposes the API surface as plain Python functions that JavaScript calls
through ``pyodide.runPythonAsync``.
"""