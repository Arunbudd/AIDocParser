from app.db import engine
from app.document import Base

Base.metadata.create_all(bind=engine)
print("Database tables created.")
