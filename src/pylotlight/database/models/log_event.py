from sqlalchemy import Column, Integer, String, DateTime, JSON
from pylotlight.database.session import Base

class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    source = Column(String, index=True)
    source_type = Column(String, index=True)
    log_level = Column(String, index=True)
    message = Column(String)
    status_type = Column(String)
    additional_data = Column(JSON)
