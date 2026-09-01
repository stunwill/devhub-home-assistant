from . import main as core
from .release_execution import register_release_execution_routes
from .version import APP_VERSION

# Keep the mature core API intact while the supervised Release Execution
# surface is registered as a focused extension.
core.APP_VERSION = APP_VERSION
app = core.app
register_release_execution_routes(app)
