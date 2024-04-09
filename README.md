# Setup Project

Clone this repository

```sh
git clone git@github.com:cowprotocol/solver-template-py.git
```

## Install Requirements

1. Python 3.10 (or probably also 3.9)
2. Rust v1.60.0 or Docker

```sh
python3.10 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

# Run Solver Server

```shell
python -m src._server
```

This can also be run via docker with

```sh
docker run -p 8000:8000 gchr.io/cowprotocol/solver-template-py
```

or build your own docker image with

```sh
docker build -t test-solver-image .
```

# Feed an Auction Instance to the Solver

```shell
curl -X POST "http://127.0.0.1:8000/solve" \
  -H  "accept: application/json" \
  -H  "Content-Type: application/json" \
  --data "@data/example.json"
```

# Connect to the orderbook:

## Without Docker

Clone the services project with

```bash
git clone https://github.com/cowprotocol/services.git
cd services
```

```bash
NODE_URL=<NODE_URL>
cargo run --bin autopilot -- --skip-event-sync true --node-url $NODE_URL --shadow https://barn.api.cow.fi/mainnet --drivers "test|http://localhost:11088/test"
cargo run -p driver -- --config playground/driver.toml --ethrpc $NODE_URL
```

# Place an order

Navigate to [barn.cowswap.exchange/](https://barn.cowswap.exchange/#/swap) and place a
tiny (real) order. See your driver pick it up and include it in the next auction being
sent to your solver

# References

- How to Build a Solver: https://docs.cow.fi/tutorials/how-to-write-a-solver
- In Depth Solver
  Specification: https://docs.cow.fi/off-chain-services/in-depth-solver-specification
- Settlement Contract (namely the settle
  method): https://github.com/cowprotocol/contracts/blob/ff6fb7cad7787b8d43a6468809cacb799601a10e/src/contracts/GPv2Settlement.sol#L121-L143
- Interaction Model (Currently missing from this framework): https://github.com/cowprotocol/services/blob/cda5e36db34c55e7bf9eb4ea8b6e36ecb046f2b2/crates/shared/src/http_solver/model.rs#L125-L130
