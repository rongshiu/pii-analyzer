import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Get database connection parameters from environment variables
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = "5432"  # Default PostgreSQL port
POSTGRES_DB = os.environ.get("POSTGRES_DB", "pii_scanner_db")

# Construct the database URL
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create the session factory
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency to get an async DB session
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
