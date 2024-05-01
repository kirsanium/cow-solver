"""
This is the project's Entry point.
"""
from __future__ import annotations

import argparse
import decimal
import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic_settings import BaseSettings

from src.models.batch_auction import BatchAuction
from src.util.schema import (
    BatchAuctionModel,
    SolutionModel,
)
from src.util import solver_logging

# Set decimal precision.
decimal.getcontext().prec = 100

# Holds parameters passed on the command line when invoking the server.
# These will be merged with request solver parameters
SERVER_ARGS = None


# ++++ Interface definition ++++


# Server settings: Can be overridden by passing them as env vars or in a .env file.
# Example: PORT=8001 python -m src._server
class ServerSettings(BaseSettings):
    """Basic Server Settings"""

    host: str = "0.0.0.0"
    port: int = 8000


server_settings = ServerSettings()
solver_logging.set_stdout_logging(logging.DEBUG)

# ++++ Endpoints: ++++

app = FastAPI(title="Batch auction solver")
app.add_middleware(GZipMiddleware)


@app.get("/health", status_code=200)
def health() -> bool:
    """Convenience endpoint to check if server is alive."""
    return True


@app.post("/notify", response_model=bool)
async def notify(request: Request) -> bool:
    """Print response from notify endpoint."""
    print(f"Notify request {await request.json()}")
    return True


@app.post("/solve", response_model=SolutionModel)
async def solve(problem: BatchAuctionModel, request: Request):  # type: ignore
    """API POST solve endpoint handler"""
    logging.debug(f"Received solve request {await request.json()}")
    batch = BatchAuction.from_dict(problem.model_dump(mode='json'))
    print("Received Batch Auction", batch.name)

    # 1. Solve BatchAuction: update batch_auction with
    solution = batch.solve()

    print("\n\n*************\n\nReturning solution: " + str(solution))
    return {'solutions': [solution]}


# ++++ Server setup: ++++


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # TODO - enable flag to write files to persistent storage
    # parser.add_argument(
    #     "--write_auxiliary_files",
    #     type=bool,
    #     default=False,
    #     help="Write auxiliary instance and optimization files, or not.",
    # )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        help="Log level",
    )

    SERVER_ARGS = parser.parse_args()
    uvicorn.run(
        "__main__:app",
        host=server_settings.host,
        port=server_settings.port,
        log_level=SERVER_ARGS.log_level,
    )
