ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip tzdata font-dejavu \
    && python3 -m pip install --no-cache-dir --break-system-packages --upgrade pip

WORKDIR /app
COPY pyproject.toml README.md LICENSE /app/
COPY wow_forever_bot /app/wow_forever_bot
RUN python3 -m pip install --no-cache-dir --break-system-packages /app

COPY run.sh /run.sh
RUN chmod 0755 /run.sh

CMD ["/run.sh"]
