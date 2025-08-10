from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models_base import Base
from app.document import Document
from app.document_chunk import DocumentChunk

USE_SQLITE_FOR_DEMO = True

if USE_SQLITE_FOR_DEMO:
    DATABASE_URL = "sqlite:///./demo.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    DATABASE_URL = "postgresql://postgres:admin@localhost:5432/postgres?options=-csearch_path=public"
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Auto-create all tables
Base.metadata.create_all(bind=engine)
