"""
This is the project's Entry point.
"""
from __future__ import annotations

import argparse
import decimal
import logging
from typing import Any, Callable, Dict, List, Set, Type
from fastapi.datastructures import DefaultPlaceholder
from fastapi.params import Depends
from starlette.routing import BaseRoute
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.routing import APIRoute
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseSettings
from src.util import solver_logging
from src.models.solver_args import SolverArgs

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


async def set_body(request: Request, body: bytes):
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive


async def get_body(request: Request) -> bytes:
    body = await request.body()
    await set_body(request, body)
    return body


class LoggedRoute(APIRoute):

    def __init__(self, path: str, endpoint: Callable[..., Any], *, response_model: Type[Any] | None = None, status_code: int = 200, tags: List[str] | None = None, dependencies: argparse.Sequence[Depends] | None = None, summary: str | None = None, description: str | None = None, response_description: str = "Successful Response", responses: Dict[int | str, Dict[str, Any]] | None = None, deprecated: bool | None = None, name: str | None = None, methods: Set[str] | List[str] | None = None, operation_id: str | None = None, response_model_include: Set[int | str] | Dict[int | str, Any] | None = None, response_model_exclude: Set[int | str] | Dict[int | str, Any] | None = None, response_model_by_alias: bool = True, response_model_exclude_unset: bool = False, response_model_exclude_defaults: bool = False, response_model_exclude_none: bool = False, include_in_schema: bool = True, response_class: Response | DefaultPlaceholder = ..., dependency_overrides_provider: argparse.Any | None = None, callbacks: List[BaseRoute] | None = None) -> None:
        super().__init__(path, endpoint, response_model=response_model, status_code=status_code, tags=tags, dependencies=dependencies, summary=summary, description=description, response_description=response_description, responses=responses, deprecated=deprecated, name=name, methods=methods, operation_id=operation_id, response_model_include=response_model_include, response_model_exclude=response_model_exclude, response_model_by_alias=response_model_by_alias, response_model_exclude_unset=response_model_exclude_unset, response_model_exclude_defaults=response_model_exclude_defaults, response_model_exclude_none=response_model_exclude_none, include_in_schema=include_in_schema, response_class=response_class, dependency_overrides_provider=dependency_overrides_provider, callbacks=callbacks)
        self.log_index = 0

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            await set_body(request, await request.body())
            req = await get_body(request)
            solver_logging.log_to_json('requests.log', req, self.log_index)
            logging.info(req)
            response: Response = await original_route_handler(request)
            solver_logging.log_to_json('response.log', response.body, self.log_index)
            self.log_index += 1
            return response

        return custom_route_handler


solver_logging.set_stdout_logging()
app = FastAPI(title="Batch auction solver")
router = APIRouter(route_class=LoggedRoute)
app.add_middleware(GZipMiddleware)


# ++++ Endpoints: ++++
@router.get("/health", status_code=200)
def health() -> bool:
    """Convenience endpoint to check if server is alive."""
    return True


@router.post("/notify", response_model=bool)
async def notify(request: Request) -> bool:
    """Print response from notify endpoint."""
    print(f"Notify request {await request.json()}")
    return True


@router.post("/solve")
async def solve(problem: dict, request: Request):  # type: ignore
    """API POST solve endpoint handler"""
    logging.debug(f"Received solve request {await request.json()}")
    trivial_solution = {
        "solutions": []
    }
    gas_price = int(problem['effectiveGasPrice'])
    orders = problem['orders']
    found_solution = False
    for o in orders:
        if o['sellToken'] == o['buyToken']:
            found_solution = True
            break
    if not found_solution:
        print("\n\n*************\n\nReturning solution: " + str(trivial_solution))
        return trivial_solution
    
    gas_cost = 150000 * gas_price
    token = o['sellToken']
    sell_amount = int(o['sellAmount'])
    buy_amount = int(o['buyAmount'])
    tokens = problem['tokens']
    native_price = int(tokens[token]['referencePrice'])
    fee_in_sell = int(gas_cost * 10**18 / native_price)
    
    if sell_amount - fee_in_sell <= buy_amount:
        return trivial_solution
    
    solution = {
        'solutions': [
            {
                'id': 0,
                'prices': {token: '1'},
                'trades': [
                    {
                        'kind': 'fulfillment',
                        'order': o['uid'],
                        'fee': str(fee_in_sell),
                        'executedAmount': str(sell_amount - fee_in_sell)
                    }
                ],
                'interactions': [],
                'score': {
                    'kind': 'solver',
                    'score': str((sell_amount - fee_in_sell - buy_amount) * native_price // 10**18)
                }
            }
        ]
    }
    print("\n\n*************\n\nReturning solution: " + str(solution))
    return solution


app.include_router(router)


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
