import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.queue import QueueMessage
from app.schemas.queue import QueueMessageCreate
from app.core.config import settings

logger = logging.getLogger(__name__)

class QueueService:
    """
    Generic Primary DB Queue Service.
    Manages work payloads in MySQL (`queue_messages` table).
    Optional secondary Redis dispatch notification when REDIS_URL is configured.
    """

    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, payload: QueueMessageCreate) -> QueueMessage:
        now = datetime.now(timezone.utc)
        available_at = now + timedelta(seconds=payload.delay_seconds) if payload.delay_seconds > 0 else now

        msg = QueueMessage(
            topic=payload.topic,
            payload_type=payload.payload_type,
            payload=payload.payload,
            status="PENDING",
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            available_at=available_at
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        # Optional Redis secondary dispatch notification
        self._notify_redis_subscribers(msg)

        return msg

    def claim_next_message(self, worker_id: str, topic: str = "default") -> Optional[QueueMessage]:
        """
        Atomically claims next pending message from primary MySQL queue.
        Uses FOR UPDATE locking where supported or optimistic status updates.
        """
        now = datetime.now(timezone.utc)

        # Query next available message
        query = self.db.query(QueueMessage).filter(
            QueueMessage.topic == topic,
            QueueMessage.status == "PENDING",
            QueueMessage.available_at <= now
        ).order_by(QueueMessage.priority.desc(), QueueMessage.created_at.asc())

        # Atomically select & lock
        msg = query.with_for_update(skip_locked=True).first() if not settings.DATABASE_URL.startswith("sqlite") else query.first()

        if msg:
            msg.status = "CLAIMED"
            msg.locked_at = now
            msg.locked_by = worker_id
            msg.attempts += 1
            self.db.commit()
            self.db.refresh(msg)
            return msg
        return None

    def complete_message(self, message_id: str) -> Optional[QueueMessage]:
        msg = self.db.query(QueueMessage).filter(QueueMessage.id == message_id).first()
        if msg:
            msg.status = "COMPLETED"
            msg.locked_at = None
            msg.locked_by = None
            self.db.commit()
            self.db.refresh(msg)
        return msg

    def fail_message(self, message_id: str, error_msg: str) -> Optional[QueueMessage]:
        msg = self.db.query(QueueMessage).filter(QueueMessage.id == message_id).first()
        if msg:
            msg.last_error = error_msg
            now = datetime.now(timezone.utc)
            if msg.attempts >= msg.max_attempts:
                msg.status = "DEAD_LETTER"
                msg.locked_at = None
                msg.locked_by = None
            else:
                # Exponential backoff delay: 5s, 20s, 80s
                backoff_seconds = (4 ** (msg.attempts - 1)) * 5
                msg.status = "PENDING"
                msg.available_at = now + timedelta(seconds=backoff_seconds)
                msg.locked_at = None
                msg.locked_by = None
            self.db.commit()
            self.db.refresh(msg)
        return msg

    def get_queue_status(self) -> Dict[str, Any]:
        counts = self.db.query(QueueMessage.status, func.count(QueueMessage.id)).group_by(QueueMessage.status).all()
        return {status: count for status, count in counts}

    def _notify_redis_subscribers(self, msg: QueueMessage):
        if settings.REDIS_URL:
            try:
                import redis
                r = redis.Redis.from_url(settings.REDIS_URL)
                r.publish(f"jarvis_queue:{msg.topic}", json.dumps({"message_id": msg.id, "type": msg.payload_type}))
            except Exception as e:
                logger.warning(f"Redis notification fallback notice: {e}")
