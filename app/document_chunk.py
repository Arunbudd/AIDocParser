import os
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models_base import Base  # shared Base

USE_SQLITE_FOR_DEMO = os.getenv("USE_SQLITE_FOR_DEMO", "true").lower() == "true"

if USE_SQLITE_FOR_DEMO:
    from sqlalchemy import Text as JSONType
else:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(JSONType, nullable=False)

    document = relationship("Document", back_populates="chunks")
