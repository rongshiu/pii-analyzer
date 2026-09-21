# analyzer

PII detection service. Wraps [Microsoft Presidio](https://github.com/microsoft/presidio)
with custom recognisers for Southeast Asian identifiers, plus a transformer-based
address detector.

> Depends on a private internal package and a private HuggingFace model, so it will
> not build from a clean clone. See the [root README](../README.md).

## Build

Both secrets are read via BuildKit secret mounts — they are never baked into a layer.

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=github_token,src="$GITHUB_TOKEN_FILE" \
  --secret id=hugging_face_hub_token,src="$HF_TOKEN_FILE" \
  -t analyzer .
```

`Dockerfile` produces a PyInstaller single-binary image for release.
`Dockerfile.local` is the hot-reload development image.

## Run

```bash
docker run --rm -it \
  -v "$PWD/app:/app/app" \
  -p 3000:3000 \
  -e HF_ADDRESS_DETECTOR_MODEL="$HF_ADDRESS_DETECTOR_MODEL" \
  analyzer
```

Or directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

## Example

```bash
curl --location 'http://0.0.0.0:3000/v1/analyzer' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "include_address": false,
    "input_text": "Name: Jane Doe\nEmail: doe@example.com\nCredit Card: 4111 1111 1111 1111\nPassport: A12345678\nDate of Birth: 1985-07-28\nMyKad: 850728-14-1234\nThailand ID: 1-1017-00203-45-0\nNIK: 7105074205820001"
  }'
```

All values above are synthetic test data.
