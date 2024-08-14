from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://pylotlight:pylotlight@postgres/pylotlight"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# This function can be used as a dependency in FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()