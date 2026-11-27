"""Static hosting for the single-page frontend.

Routes such as /decks/3 only exist in the client-side router: when the
browser requests one directly (page refresh, shared link), no file matches
and index.html is served so the app boots on that route. Paths under /api/
and paths that look like files (last segment with an extension) keep their
404.
"""

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or not _is_client_route(path):
                raise
            return await super().get_response("index.html", scope)


def _is_client_route(path: str) -> bool:
    if path == "api" or path.startswith("api/"):
        return False
    return "." not in path.rsplit("/", 1)[-1]
