import os

__version__ = "dev"
__commit__ = "none"
__build_time__ = "unknown"

from license_sdk import Security

security = Security()

# Licensing identifiers are supplied at build/deploy time, never committed.
# setKeyAccount(version, dev_value, prod_value) selects the pair to use based on
# __version__, which the Dockerfile rewrites during a release build.
__keygen_account__ = security.setKeyAccount(
    __version__,
    os.environ.get("KEYGEN_ACCOUNT_ID_DEV", ""),
    os.environ.get("KEYGEN_ACCOUNT_ID_PROD", ""),
)
__keygen_product__ = security.setKeyAccount(
    __version__,
    os.environ.get("KEYGEN_PRODUCT_ID_DEV", ""),
    os.environ.get("KEYGEN_PRODUCT_ID_PROD", ""),
)
__keygen_token__ = security.setKeyAccount(
    __version__,
    os.environ.get("KEYGEN_TOKEN_DEV", ""),
    os.environ.get("KEYGEN_TOKEN_PROD", ""),
)
__keygen_public_key__ = security.setKeyAccount(
    __version__,
    os.environ.get("KEYGEN_PUBLIC_KEY_DEV", ""),
    os.environ.get("KEYGEN_PUBLIC_KEY_PROD", ""),
)
