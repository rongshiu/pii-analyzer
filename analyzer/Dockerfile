# === Stage 1: Build and compile app ===
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm AS builder

# Set working directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Internal shared package from a private repo (not publicly available)
RUN --mount=type=secret,id=github_token \
    pip install \
    "git+https://$(cat /run/secrets/github_token)@github.com/ORG/INTERNAL-SHARED-PACKAGE.git@main#subdirectory=pkg/python"

# Hugging Face preload
RUN --mount=type=secret,id=hugging_face_hub_token \
    export HUGGING_FACE_HUB_TOKEN=$(cat /run/secrets/hugging_face_hub_token) && python3 <<EOF
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

models = ["org/address-detector"]
token = os.environ.get("HUGGING_FACE_HUB_TOKEN")

print(f"Using HF token: {bool(token)}")
for m in models:
    print(f"Preloading {m}...")
    AutoTokenizer.from_pretrained(m, token=token, cache_dir="/app/cache")
    AutoModelForSequenceClassification.from_pretrained(m, token=token, cache_dir="/app/cache")
EOF

# Copy code — split by location
COPY app/ ./app/
COPY swift_library/ ./swift_library/
COPY main.py ./main.py

ARG VERSION=dev
ARG COMMIT=none
ARG BUILD_TIME=unknown

RUN sed -i "s/__version__ = .*/__version__ = \"$VERSION\"/" ./app/utility/version.py && \
    sed -i "s/__commit__ = .*/__commit__ = \"$COMMIT\"/" ./app/utility/version.py && \
    sed -i "s/__build_time__ = .*/__build_time__ = \"$BUILD_TIME\"/" ./app/utility/version.py 

# PyInstaller
RUN pip install pyinstaller
RUN pyinstaller \
    --onefile \
    --console \
    --noconfirm \
    --name=pii-analyzer \
    --collect-submodules=app \
    --collect-submodules=transformers.models \
    --collect-submodules=presidio_analyzer \
    --add-data "/app/cache:app/cache" \
    --add-data "/usr/local/lib/python3.12/site-packages/en_core_web_lg/en_core_web_lg-3.8.0:_internal/app/en_core_web_lg" \
    --add-data "/usr/local/lib/python3.12/site-packages/presidio_analyzer/conf:presidio_analyzer/conf" \
    --add-data "swift_library/:swift_library/" \
    --hidden-import=asyncpg.pgproto.pgproto \
    --hidden-import=uuid \
    --hidden-import=ipaddress \
    --runtime-tmpdir "/app/" \
    main.py

# === Stage 2: Final image with only binary ===
FROM public.ecr.aws/docker/library/debian:bookworm-slim

# Create working dir
WORKDIR /app

# Create a non-root user and group
RUN apt-get update && apt-get install -y ca-certificates curl

RUN chown 65532:65532 /app

COPY --from=builder /app/dist/pii-analyzer /app/pii-analyzer

USER 65532:65532

# Expose port
EXPOSE 3000

# Run the compiled binary
ENTRYPOINT ["./pii-analyzer"]
