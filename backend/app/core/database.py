from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True if "sqlite" not in settings.DATABASE_URL else False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    import app.models.camera  # noqa: F401
    import app.models.event   # noqa: F401
    import app.models.face    # noqa: F401
    import app.models.user    # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

