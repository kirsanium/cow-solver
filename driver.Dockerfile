FROM ghcr.io/cowprotocol/services:latest
COPY driver.toml driver.toml
ENTRYPOINT [ "driver" ]