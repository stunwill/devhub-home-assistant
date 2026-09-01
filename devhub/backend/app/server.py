from . import main as core
from .release_execution import register_release_execution_routes

# v0.6.0 production entrypoint. Keep the mature core API intact while the
# supervised Release Execution surface is registered as a focused extension.
core.APP_VERSION = "0.6.0"
app = core.app
register_release_execution_routes(app)
