#!/bin/bash

NODE_URL=https://sepolia.infura.io/v3/00ee25ac930d41eaa328a0b8bea763c2
SHADOW_API=https://api.cow.fi/sepolia/
(nohup python -m src._server > server.log & exit)

# https://github.com/cowprotocol/services repo is next to this folder
cd ../services
(nohup cargo run -p driver -- --config playground/driver.toml --ethrpc $NODE_URL > driver.log & exit)
(nohup cargo run --bin autopilot -- --skip-event-sync true --node-url $NODE_URL --shadow $SHADOW_API \
 --drivers "test|http://localhost:11088/test" > autopilot.log & exit)

# then use `ps aux | grep [autopilot|driver|_server] to identify processes and kill them if needed`
