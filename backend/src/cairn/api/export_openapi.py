"""Print the API's OpenAPI document without starting a server (used by `npm run api:check`)."""

import json
import sys

from cairn.api.app import create_app
from cairn.settings import Settings


def main() -> None:
    # The schema does not depend on settings, so ignore the developer's .env entirely.
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    json.dump(create_app(settings).openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
