"""Message queue infrastructure for distributed workers.

Supports multiple backends:
- Redis (default)
- RabbitMQ
- In-memory (for testing)
"""

from app.messagequeue.queue import MessageQueue, QueueBackend, QueueMessage

__all__ = ["MessageQueue", "QueueBackend", "QueueMessage"]
