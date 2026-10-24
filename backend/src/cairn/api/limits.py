"""Cap upload request bodies before multipart parsing spools them (design §8.2, §13)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from cairn.errors import TooLarge

OVERHEAD = 1024 * 1024  # multipart boundaries and headers


class UploadLimit:
    """Refuses a POST to `.../documents` whose body is larger than the case could ever hold:
    early on Content-Length, and while streaming when the client sends none."""

    def __init__(self, app: ASGIApp, limit: int):
        self.app = app
        self.limit = limit + OVERHEAD

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not str(scope["path"]).endswith("/documents")
        ):
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is not None and int(declared) > self.limit:
            await _too_large(scope, receive, send)
            return
        seen = 0

        async def counted() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.limit:
                    raise TooLarge("the upload is larger than a case can hold")
            return message

        await self.app(scope, counted, send)


async def _too_large(scope: Scope, receive: Receive, send: Send) -> None:
    from fastapi.responses import JSONResponse

    body = {
        "error": {"code": "case_too_large", "message": "the upload is larger than a case can hold"}
    }
    await JSONResponse(status_code=413, content=body)(scope, receive, send)
