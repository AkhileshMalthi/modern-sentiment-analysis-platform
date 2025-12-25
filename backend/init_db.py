import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from models.database import Base

async def init_database():
    """Initialize database tables"""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://sentiment_user:secure_password_123@localhost:5432/sentiment_db")
    
    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_database())
