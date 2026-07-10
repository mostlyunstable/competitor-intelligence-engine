"""Message queue infrastructure for distributed workers.

Supports multiple backends:
- Redis (default)
- RabbitMQ
- In-memory (for testing)
"""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger()


class MessageType(Enum):
    """Message types."""

    COLLECTION = "collection"
    PARSING = "parsing"
    NOTIFICATION = "notification"
    HEALTH_CHECK = "health_check"


class MessageStatus(Enum):
    """Message status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class QueueMessage:
    """Message in the queue."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.COLLECTION
    payload: dict[str, Any] = field(default_factory=dict)
    status: MessageStatus = MessageStatus.PENDING
    created_at: float = field(default_factory=time.time)
    processed_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    max_retries: int = 3
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueMessage:
        """Create from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=MessageType(data.get("message_type", "collection")),
            payload=data.get("payload", {}),
            status=MessageStatus(data.get("status", "pending")),
            created_at=data.get("created_at", time.time()),
            processed_at=data.get("processed_at"),
            completed_at=data.get("completed_at"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class QueueBackend(ABC):
    """Abstract base class for queue backends."""

    @abstractmethod
    async def publish(self, message: QueueMessage) -> bool:
        """Publish a message to the queue."""
        ...

    @abstractmethod
    async def consume(self) -> QueueMessage | None:
        """Consume a message from the queue."""
        ...

    @abstractmethod
    async def ack(self, message_id: str) -> bool:
        """Acknowledge a message."""
        ...

    @abstractmethod
    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge a message."""
        ...

    @abstractmethod
    async def size(self) -> int:
        """Get queue size."""
        ...

    @abstractmethod
    async def purge(self) -> int:
        """Purge all messages."""
        ...


class InMemoryQueueBackend(QueueBackend):
    """In-memory queue backend for testing."""

    def __init__(self) -> None:
        self._queue: list[QueueMessage] = []
        self._processing: dict[str, QueueMessage] = {}

    async def publish(self, message: QueueMessage) -> bool:
        """Publish a message to the queue."""
        self._queue.append(message)
        logger.debug("message_published", message_id=message.message_id)
        return True

    async def consume(self) -> QueueMessage | None:
        """Consume a message from the queue."""
        if not self._queue:
            return None

        message = self._queue.pop(0)
        message.status = MessageStatus.PROCESSING
        message.processed_at = time.time()
        self._processing[message.message_id] = message
        logger.debug("message_consumed", message_id=message.message_id)
        return message

    async def ack(self, message_id: str) -> bool:
        """Acknowledge a message."""
        if message_id in self._processing:
            message = self._processing.pop(message_id)
            message.status = MessageStatus.COMPLETED
            message.completed_at = time.time()
            logger.debug("message_acknowledged", message_id=message_id)
            return True
        return False

    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge a message."""
        if message_id in self._processing:
            message = self._processing.pop(message_id)
            message.retry_count += 1

            if requeue and message.retry_count < message.max_retries:
                message.status = MessageStatus.RETRY
                self._queue.append(message)
                logger.debug(
                    "message_requeued", message_id=message_id, retry_count=message.retry_count
                )
            else:
                message.status = MessageStatus.FAILED
                logger.debug("message_failed", message_id=message_id)
            return True
        return False

    async def size(self) -> int:
        """Get queue size."""
        return len(self._queue)

    async def purge(self) -> int:
        """Purge all messages."""
        count = len(self._queue)
        self._queue.clear()
        self._processing.clear()
        return count


class RedisQueueBackend(QueueBackend):
    """Redis queue backend."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_name: str = "crawl_queue",
    ) -> None:
        self._redis_url = redis_url
        self._queue_name = queue_name
        self._redis = None
        self._processing: dict[str, QueueMessage] = {}

    def _get_redis(self) -> Any:
        """Get Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(self._redis_url)
            except ImportError:
                logger.error("redis_not_installed")
                raise
        return self._redis

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def publish(self, message: QueueMessage) -> bool:
        """Publish a message to Redis queue."""
        try:
            redis = self._get_redis()
            data = json.dumps(message.to_dict())
            await redis.rpush(self._queue_name, data)
            logger.debug("message_published_redis", message_id=message.message_id)
            return True
        except Exception as e:
            logger.error("redis_publish_failed", error=str(e))
            raise  # Raise so tenacity can retry

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )

    async def consume(self) -> QueueMessage | None:
        """Consume a message from Redis queue."""
        try:
            redis = self._get_redis()
            data = await redis.lpop(self._queue_name)
            if data:
                message_dict = json.loads(data)
                message = QueueMessage.from_dict(message_dict)
                message.status = MessageStatus.PROCESSING
                message.processed_at = time.time()
                self._processing[message.message_id] = message
                logger.debug("message_consumed_redis", message_id=message.message_id)
                return message
            return None
        except Exception as e:
            logger.error("redis_consume_failed", error=str(e))
            raise  # Raise so tenacity can retry

    async def ack(self, message_id: str) -> bool:
        """Acknowledge a message (remove from processing)."""
        if message_id in self._processing:
            self._processing.pop(message_id)
            logger.debug("message_acknowledged_redis", message_id=message_id)
            return True
        return False

    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge a message, moving to DLQ if max retries exceeded."""
        if message_id not in self._processing:
            return False

        message = self._processing.pop(message_id)
        message.retry_count += 1
        
        try:
            redis = self._get_redis()
            if requeue and message.retry_count < message.max_retries:
                message.status = MessageStatus.RETRY
                data = json.dumps(message.to_dict())
                await redis.rpush(self._queue_name, data)
                logger.debug("message_requeued_redis", message_id=message_id, retry_count=message.retry_count)
            else:
                message.status = MessageStatus.FAILED
                data = json.dumps(message.to_dict())
                dlq_name = f"{self._queue_name}_dlq"
                await redis.rpush(dlq_name, data)
                logger.debug("message_dlq_redis", message_id=message_id, dlq=dlq_name)
            return True
        except Exception as e:
            logger.error("redis_nack_failed", error=str(e), message_id=message_id)
            return False

    async def size(self) -> int:
        """Get queue size."""
        try:
            redis = self._get_redis()
            result = await redis.llen(self._queue_name)
            return int(result) if result else 0
        except Exception:
            return 0

    async def purge(self) -> int:
        """Purge all messages."""
        try:
            redis = self._get_redis()
            count = await redis.llen(self._queue_name)
            await redis.delete(self._queue_name)
            return int(count) if count else 0
        except Exception:
            return 0


class MessageQueue:
    """Message queue with publisher/subscriber pattern."""

    def __init__(self, backend: QueueBackend | None = None) -> None:
        self._backend = backend or InMemoryQueueBackend()
        self._handlers: dict[MessageType, Callable[[QueueMessage], bool]] = {}
        self._stats = {
            "published": 0,
            "consumed": 0,
            "acknowledged": 0,
            "failed": 0,
        }

    def set_handler(
        self, message_type: MessageType, handler: Callable[[QueueMessage], bool]
    ) -> None:
        """Set a handler for a message type."""
        self._handlers[message_type] = handler
        logger.info("queue_handler_set", message_type=message_type.value)

    async def publish(
        self,
        message_type: MessageType,
        payload: dict[str, Any],
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Publish a message."""
        message = QueueMessage(
            message_type=message_type,
            payload=payload,
            metadata=metadata or {},
        )

        if await self._backend.publish(message):
            self._stats["published"] += 1
            logger.info(
                "message_published",
                message_id=message.message_id,
                message_type=message_type.value,
                payload_keys=list(payload.keys()),
            )
            return message.message_id

        return ""

    async def process_next(self) -> bool:
        """Process the next message in the queue."""
        message = await self._backend.consume()
        if not message:
            return False

        self._stats["consumed"] += 1

        handler = self._handlers.get(message.message_type)
        if not handler:
            logger.warning("no_handler_for_message_type", message_type=message.message_type.value)
            await self._backend.nack(message.message_id, requeue=False)
            self._stats["failed"] += 1
            return False

        try:
            success = handler(message)
            if success:
                await self._backend.ack(message.message_id)
                self._stats["acknowledged"] += 1
                logger.info("message_processed", message_id=message.message_id)
                return True
            else:
                await self._backend.nack(message.message_id, requeue=True)
                self._stats["failed"] += 1
                logger.warning("message_processing_failed", message_id=message.message_id)
                return False
        except Exception as e:
            await self._backend.nack(message.message_id, requeue=True)
            self._stats["failed"] += 1
            logger.error(
                "message_processing_error",
                message_id=message.message_id,
                error=str(e),
            )
            return False

    async def process_all(self, max_messages: int = 100) -> int:
        """Process all messages in the queue."""
        processed = 0
        for _ in range(max_messages):
            if not await self.process_next():
                break
            processed += 1
        return processed

    async def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "stats": self._stats,
            "queue_size": await self._backend.size(),
            "handlers": list(self._handlers.keys()),
        }

    async def purge(self) -> int:
        """Purge all messages."""
        count = await self._backend.purge()
        logger.info("queue_purged", count=count)
        return count


# Global message queue
message_queue = MessageQueue()
