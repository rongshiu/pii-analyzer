from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List

async def get_allowed_data_elements(
    db: AsyncSession, account_id: str, service: str
) -> List[str]:
    query = text("""
        SELECT data_elements 
        FROM pii_scanner.detection_specifications
        WHERE account_id = :account_id AND service = :service
    """)
    result = await db.execute(query, {
        "account_id": account_id,
        "service": service
    })
    row = result.fetchone()
    return row[0] if row else []
