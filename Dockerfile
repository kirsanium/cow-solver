FROM python:3.10

RUN apt-get update && apt-get install gcc libc-dev -y

WORKDIR /app

# First copy over the requirements.txt and install dependencies, this makes
# building subsequent images easier.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy full source (see .dockerignore)
COPY src/ ./src/

CMD [ "python3", "-m" , "src._server"]
