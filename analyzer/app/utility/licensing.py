import os
import machineid
import hashlib
from app.utility.logger import get_logger

logger = get_logger()

def get_fingerprint(product: str) -> str:
    node = os.getenv("NODE_NAME")
    if node:
        sha = hashlib.sha256()
        sha.update(node.encode())
        sha.update(product.encode())
        return sha.hexdigest()
    return machineid.hashed_id(product)

def error_handling(err):
    if err:
        logger.error(f"❌ License check failed: {err}")
        os._exit(1)
    else:
        logger.info(f"✅ License is valid")