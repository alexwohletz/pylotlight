import json
from redis import Redis
from sqlalchemy.orm import Session
from database.session import SessionLocal, engine
from models.log_event import LogEvent as DBLogEvent
from schemas import LogEvent as SchemaLogEvent

redis = Redis(host='redis', port=6379)

def process_logs():
    while True:
        # Pop item from Redis list
        _, log_json = redis.brpop('log_queue')
        log_data = json.loads(log_json)
        log = SchemaLogEvent(**log_data)

        # Store in database
        db = SessionLocal()
        try:
            db_log = DBLogEvent(
                timestamp=log.timestamp,
                source=log.source,
                log_level=log.log_level,
                message=log.message,
                additional_data=log.additional_data
            )
            db.add(db_log)
            db.commit()
        finally:
            db.close()

if __name__ == "__main__":
    process_logs()