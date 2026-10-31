"""Process entrypoint for Hugging Face Spaces and the local voice image.

Inference stays in ``sonicagent_rt``. This file only exposes the ASGI app on
the port Docker Spaces expect.
"""

from __future__ import annotations

import os

from sonicagent_rt.api.app_factory import create_app

app = create_app()


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1)


if __name__ == "__main__":
    main()
