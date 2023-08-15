# Python runtime image to execute rest4mqtt

FROM debian:12-slim

ARG version

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN set -ex \
    && apt update && apt install -y python3-paho-mqtt \
    && apt autoremove -y \
    && apt clean -y \
    && rm -rf /var/lib/apt/lists/*

COPY rest4mqtt.py /usr/local/rest4mqtt/
RUN echo -n $version > /usr/local/rest4mqtt/VERSION

WORKDIR /usr/local/rest4mqtt/
ENTRYPOINT ["python3", "/usr/local/rest4mqtt/rest4mqtt.py"]