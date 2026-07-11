from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .nodes.wildcard_refresh import wildcard_refresh_state

from aiohttp import web
from server import PromptServer

__version__ = "0.3.0"

WEB_DIRECTORY = "./web"


@PromptServer.instance.routes.post("/dynamicprompts-lite/wildcards/refresh")
async def refresh_wildcards(request):
    try:
        result = wildcard_refresh_state.refresh()
        return web.json_response(
            {
                "changed": result.changed,
                "revision": result.revision,
                "file_count": result.file_count,
            },
        )
    except OSError as error:
        return web.json_response({"error": str(error)}, status=500)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
