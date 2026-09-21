FROM public.ecr.aws/docker/library/python:3.10-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    gcc \
    g++ \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pip packages
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Internal shared package from a private repo (not publicly available)
RUN --mount=type=secret,id=github_token \
    pip install \
    "git+https://$(cat /run/secrets/github_token)@github.com/ORG/INTERNAL-SHARED-PACKAGE.git@main#subdirectory=pkg/python"

# Copy your app code
COPY app/ /app/
WORKDIR /app

ARG VERSION=dev
ARG COMMIT=none
ARG BUILD_TIME=unknown

RUN sed -i "s/__version__ = .*/__version__ = \"$VERSION\"/" ./utility/version.py && \
    sed -i "s/__commit__ = .*/__commit__ = \"$COMMIT\"/" ./utility/version.py && \
    sed -i "s/__build_time__ = .*/__build_time__ = \"$BUILD_TIME\"/" ./utility/version.py 

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]