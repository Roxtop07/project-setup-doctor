from __future__ import annotations

import multiprocessing
import sys

multiprocessing.freeze_support()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SecureCode analysis backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18120)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args()

    import uvicorn
    from main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        workers=1,
    )


if __name__ == "__main__":
    main()
