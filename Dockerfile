# MCP server for the oregon-records-retention corpus (HTTP transport).
#
#   docker build -t oregon-records-retention-mcp .
#   docker run -p 8000:8000 oregon-records-retention-mcp
#
# The corpus is baked in at build time; rebuild the image to pick up new commits.
#
# BUILD FROM A SHALLOW CLONE, not your working tree. `.git` cannot be excluded — it is a
# RUNTIME dependency, because the FTS cache key is `git rev-parse HEAD` plus a hash of
# `git status --porcelain`, and corpus_overview() shells out to `git log -1`. A depth-1
# clone keeps git working and the image small:
#
#   git clone --depth 1 --branch main https://github.com/OregonAI/oregon-records-retention build/
#   docker build -t oregon-records-retention-mcp build/
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /repo
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-build the FTS index so the first request is instant. This corpus is 76 schedules, so
# it is quick — but the step also fails the BUILD if content is missing, rather than
# shipping an image that starts fine and answers nothing.
RUN python3 -c "\
from corpus_toolkit import config as config_mod; \
from corpus_toolkit.mcp.framework import CorpusFramework; \
CorpusFramework(config_mod.load('_meta/corpus.yml')).ensure_index()"
EXPOSE 8000

# --path and --public-hostname both matter behind the tunnel and are easy to omit:
#   * A Cloudflare Tunnel matches on path but does NOT strip it. Routing
#     /oregon-records-retention here forwards the whole path, so the server must mount at
#     that same prefix or every request 404s.
#   * Without --public-hostname the SDK's DNS-rebinding guard rejects the forwarded Host
#     header with 421 Invalid Host header.
# Override either at `docker run` for a different hostname or a dedicated-host deployment
# (in which case pass --path /mcp).
CMD ["corpus-mcp-serve", "--config", "_meta/corpus.yml", "--http", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--path", "/oregon-records-retention/mcp", \
     "--public-hostname", "oregonai.morficflux.com"]
