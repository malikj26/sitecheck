FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    golang \
    && rm -rf /var/lib/apt/lists/*

RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

ENV PATH="/root/go/bin:${PATH}"

COPY pyproject.toml README.md requirements.txt ./
COPY sitecheck ./sitecheck
COPY examples ./examples

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "sitecheck.cli"]