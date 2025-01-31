import time
import redis
import json
from typing import Any, Callable, Dict, List, Optional
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet

try:
    from wredis.queue import RedisQueueManager
except ImportError:
    logger.warning("wredis is not installed. RedisQueueManager will not be available.")
    RedisQueueManager = None

# 🔐 Encryption key (must be stored securely)
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)


class WMongoAsync:
    """Asynchronous MongoDB client with Redis-based caching and notifications."""

    QUEUE_NAME = "wmongo:notifications:changes"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = "test",
        username: Optional[str] = None,
        password: Optional[str] = None,
        verbose: bool = False,
        # notifications
        enable_notifications: bool = False,
        enable_notification_receiver: bool = False,
        notification_callback: Optional[Callable[[str], None]] = None,
        # Redis
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_db: Optional[int] = None,
    ) -> None:
        """
        Initializes asynchronous MongoDB connection and optional Redis caching & Pub/Sub.

        Args:
            host (str): MongoDB host address.
            port (int): MongoDB port.
            database (str): MongoDB database name.
            username (Optional[str]): MongoDB username.
            password (Optional[str]): MongoDB password.
            verbose (bool): Enable verbose logging.
            enable_notifications (bool): Enable notifications.
            enable_notification_receiver (bool): Enable notification receiver.
            notification_callback (Optional[Callable[[str], None]]): Callback function for notifications.
            redis_host (Optional[str]): Redis host address.
            redis_port (Optional[int]): Redis port.
            redis_db (Optional[int]): Redis database index.
        """
        # Construct MongoDB URI
        if username and password:
            uri = f"mongodb://{username}:{password}@{host}:{port}"
        else:
            uri = f"mongodb://{host}:{port}"

        self.verbose = verbose
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[database]
        self.use_cache = False
        self.enable_notifications = enable_notifications
        self.enable_notification_receiver = enable_notification_receiver
        self.notification_callback = notification_callback

        # Connect to Redis
        self.redis_client = None
        self.redis_queue_manager = None
        if redis_host and redis_port is not None and redis_db is not None:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
                self.redis_client.ping()
                self.use_cache = True
                if RedisQueueManager:
                    self.redis_queue_manager = RedisQueueManager(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        verbose=self.verbose,
                    )
                if self.verbose:
                    logger.info("Redis cache and queue enabled.")
            except (redis.ConnectionError, redis.TimeoutError):
                logger.warning("Redis is unavailable; cache will not be used.")

        if self.verbose:
            logger.info(f"Connected to MongoDB database: {database} at {uri}")

    def listen_notifications(self):
        """Registers the notification callback in Redis Pub/Sub."""
        if self.redis_queue_manager and self.notification_callback:

            @self.redis_queue_manager.on_message(self.QUEUE_NAME)
            def handle_message(record):
                self.notification_callback(record)

            self.redis_queue_manager.start()
            if self.verbose:
                logger.info("Notification receiver started.")

            self.redis_queue_manager.wait()

    async def insert(self, collection: str, document: Dict[str, Any]) -> Any:
        """
        Inserts a document asynchronously and sends a notification if enabled.

        Args:
            collection (str): Collection name.
            document (Dict[str, Any]): Document to insert.

        Returns:
            Any: ID of the inserted document
        """

        result = await self.db[collection].insert_one(document)
        document["_id"] = str(result.inserted_id)

        if self.use_cache:
            self.redis_client.set(
                f"cache:{collection}:{result.inserted_id}", json.dumps(document), ex=300
            )

        if self.verbose:
            logger.info(f"Inserted document ID: {result.inserted_id}")

        if self.enable_notifications:
            await self._send_notification(
                {
                    "database": self.db.name,
                    "collection": collection,
                    "action": "insert",
                    "document": document,
                    "timestamp": time.time(),
                    "id": str(result.inserted_id),
                }
            )

        return result.inserted_id

    async def find(
        self, collection: str, query: Dict[str, Any] = {}
    ) -> List[Dict[str, Any]]:
        """
        Retrieves documents asynchronously, using Redis cache if enabled.

        Args:
            collection (str): Collection name.
            query (Dict[str, Any], optional): Query to filter documents. Defaults to {}.

        Returns:
            List[Dict[str, Any]]: List of documents found.
        """

        cache_key = f"cache:{collection}:{str(query)}"

        if self.use_cache:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding cache data: {e}")

        cursor = self.db[collection].find(query)
        result = [doc async for doc in cursor]
        for doc in result:
            doc["_id"] = str(doc["_id"])

        if self.use_cache:
            self.redis_client.set(cache_key, json.dumps(result), ex=300)

        return result

    async def update(
        self, collection: str, query: Dict[str, Any], update_values: Dict[str, Any]
    ) -> int:
        """
        Updates documents asynchronously and sends a notification if enabled.

        Args:
            collection (str): Collection name.
            query (Dict[str, Any]): Query to match documents for update.
            update_values (Dict[str, Any]): New values to update.

        Returns:
            int: Number of documents
        """

        result = await self.db[collection].update_many(query, {"$set": update_values})
        updated_count = result.modified_count

        if self.verbose:
            logger.info(f"Updated {updated_count} documents in '{collection}'.")

        if self.enable_notifications and updated_count > 0:
            await self._send_notification(
                {
                    "database": self.db.name,
                    "collection": collection,
                    "action": "update",
                    "query": query,
                    "update_values": update_values,
                    "timestamp": time.time(),
                    "modified_count": updated_count,
                }
            )

        return updated_count

    async def delete(self, collection: str, query: Dict[str, Any]) -> int:
        """
        Deletes documents asynchronously and sends a notification if enabled.

        Args:
            collection (str): Collection name.
            query (Dict[str, Any]): Query to match documents for deletion.

        Returns:
            int: Number of documents deleted
        """

        result = await self.db[collection].delete_many(query)
        deleted_count = result.deleted_count

        if self.verbose:
            logger.info(f"Deleted {deleted_count} documents from '{collection}'.")

        if self.enable_notifications and deleted_count > 0:
            await self._send_notification(
                {
                    "database": self.db.name,
                    "collection": collection,
                    "action": "delete",
                    "query": query,
                    "timestamp": time.time(),
                    "deleted_count": deleted_count,
                }
            )

        return deleted_count

    async def _send_notification(self, message: Dict[str, Any]):
        """
        Sends a notification asynchronously via Redis Queue.

        Args:
            message (Dict[str, Any]): Notification message.
        """

        if self.redis_queue_manager:
            try:
                self.redis_queue_manager.publish(self.QUEUE_NAME, message)
                if self.verbose:
                    logger.info(f"Notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    async def close(self) -> None:
        """Closes MongoDB and Redis connections."""
        self.client.close()
        if self.verbose:
            logger.info("MongoDB and Redis connections closed.")

    async def __aenter__(self) -> "WMongoAsync":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()
