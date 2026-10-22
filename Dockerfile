FROM ghcr.io/prefix-dev/pixi:0.68.1

LABEL org.opencontainers.image.source="https://github.com/annefou/natura2000-kras-site-evidence"
LABEL org.opencontainers.image.description="Natura 2000 site evidence (Kras, SI3000276): pipeline container"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# git is needed to install healpix-connector from its pinned tag (pixi.toml).
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the pinned environment first (separate from source copy so the lock
# layer is cached across source-only edits).
COPY pixi.toml pixi.lock /app/
RUN pixi install --locked

COPY . /app

# No credentials are needed. The default command runs the analysis from the committed inputs;
# `pixi run rebuild` rebuilds them from source, `pixi run raba` runs the Land Use database layer
# (results stay in results/local/, see README.md § Data licensing).

CMD ["pixi", "run", "snakemake", "--cores", "1"]
