import time
import redis
import jwt
import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from loguru import logger
from pymongo import MongoClient
from cryptography.fernet import Fernet
from .jwt import JWT_SECRET

try:
    from wredis.queue import RedisQueueManager
except ImportError:
    logger.warning("wredis is not installed. RedisQueueManager will not be available.")
    RedisQueueManager = None

# 🔐 Encryption Key (Should be securely stored)
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)


class TokenManager:
    """Handles JWT authentication."""

    @staticmethod
    def generate_token(user_id: str, role: str, expires_in: int = 3600) -> str:
        """Generate a JWT token.

        Args:
            user_id (str): The user ID.
            role (str): The role associated with the user.
            expires_in (int, optional): Token expiration time in seconds. Defaults to 3600.

        Returns:
            str: The generated JWT token.
        """
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token.

        Args:
            token (str): The JWT token to verify.

        Returns:
            Optional[Dict[str, Any]]: Decoded token data if valid, otherwise None.
        """
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            logger.error("Token expired.")
            return None
        except jwt.InvalidTokenError:
            logger.error("Invalid token.")
            return None


class WMongo:
    """Synchronous MongoDB client with dynamic permissions, notifications, and encryption."""

    QUEUE_NAME = "wmongo:notifications:changes"

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "test",
        username: Optional[str] = None,
        password: Optional[str] = None,
        verbose: bool = False,
        read_only: bool = False,
        enable_notifications: bool = False,
        enable_notification_receiver: bool = False,
        notification_callback: Optional[Callable[[str], None]] = None,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_db: Optional[int] = None,
    ) -> None:
        """Initialize MongoDB connection and Redis configuration.

        Args:
            uri (str, optional): MongoDB URI. Defaults to "mongodb://localhost:27017".
            database (str, optional): MongoDB database name. Defaults to "test".
            username (Optional[str], optional): MongoDB username. Defaults to None.
            password (Optional[str], optional): MongoDB password. Defaults to None.
            verbose (bool, optional): Enable verbose logging. Defaults to False.
            read_only (bool, optional): Enable read-only mode. Defaults to False.
            enable_notifications (bool, optional): Enable notifications for changes. Defaults to False.
            enable_notification_receiver (bool, optional): Enable receiving notifications. Defaults to False.
            notification_callback (Optional[Callable[[str], None]], optional): Callback for received notifications. Defaults to None.
            redis_host (Optional[str], optional): Redis host. Defaults to None.
            redis_port (Optional[int], optional): Redis port. Defaults to None.
            redis_db (Optional[int], optional): Redis database index. Defaults to None.
        """
        self.verbose = verbose
        self.read_only = read_only
        self.enable_notifications = enable_notifications
        self.enable_notification_receiver = enable_notification_receiver
        self.notification_callback = notification_callback

        # Connect to MongoDB
        self.client = MongoClient(uri, username=username, password=password)
        self.db = self.client[database]

        # Configure Redis
        self.use_cache = False
        if redis_host and redis_port is not None and redis_db is not None:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
                self.redis_client.ping()
                self.use_cache = True
                if self.verbose:
                    logger.info("Redis cache enabled.")
            except (redis.ConnectionError, redis.TimeoutError):
                self.use_cache = False
                logger.warning("Redis is unavailable; cache will not be used.")

        # Configure RedisQueueManager for notifications
        self.redis_queue_manager = None
        if self.enable_notifications or self.enable_notification_receiver:
            if RedisQueueManager is not None:
                self.redis_queue_manager = RedisQueueManager(
                    host=redis_host, port=redis_port, db=redis_db, verbose=self.verbose
                )
                if self.verbose:
                    logger.info("RedisQueueManager initialized.")
            else:
                logger.error(
                    "RedisQueueManager is not available. Ensure wredis is installed."
                )

    def insert(self, collection: str, document: Dict[str, Any]) -> Any:
        """Insert a document into a MongoDB collection and send a notification if enabled.

        Args:
            collection (str): The collection to insert the document into.
            document (Dict[str, Any]): The document to insert.

        Returns:
            Any: The ID of the inserted document.
        """

        if self.read_only:
            raise PermissionError("Database is in read-only mode!")

        result = self.db[collection].insert_one(document)
        document["_id"] = str(result.inserted_id)

        if self.use_cache:
            self.redis_client.set(
                f"cache:{collection}:{result.inserted_id}", json.dumps(document), ex=300
            )

        if self.verbose:
            logger.info(f"Inserted document ID: {result.inserted_id}")

        if self.enable_notifications:
            self._send_notification(
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

    def find(self, collection: str, query: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """Retrieve documents from a MongoDB collection based on a query.

        Args:
            collection (str): The collection to query.
            query (Dict[str, Any], optional): The query to filter documents. Defaults to {}.

        Returns:
            List[Dict[str, Any]]: A list of documents that match the query.
        """

        cache_key = f"cache:{collection}:{str(query)}"

        if self.use_cache:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding cache data: {e}")

        result = list(self.db[collection].find(query))
        for doc in result:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        if self.use_cache:
            self.redis_client.set(cache_key, json.dumps(result), ex=300)

        return result

    def update(
        self, collection: str, query: Dict[str, Any], update_values: Dict[str, Any]
    ) -> int:
        """Update documents in a MongoDB collection that match a query and send a notification if enabled.

        Args:
            collection (str): The collection to update.
            query (Dict[str, Any]): The query to filter documents.
            update_values (Dict[str, Any]): The values to update in the matching documents.

        Returns:
            int: The number of documents updated.
        """

        if self.read_only:
            raise PermissionError("Database is in read-only mode!")

        result = self.db[collection].update_many(query, {"$set": update_values})
        updated_count = result.modified_count

        if self.verbose:
            logger.info(
                f"Updated {updated_count} documents in collection '{collection}'."
            )

        if self.enable_notifications and updated_count > 0:
            self._send_notification(
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

    def delete(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete documents from a MongoDB collection that match a query and send a notification if enabled.

        Args:
            collection (str): The collection to delete documents from.
            query (Dict[str, Any]): The query to filter documents for deletion.

        Returns:
            int: The number of documents deleted.
        """

        if self.read_only:
            raise PermissionError("Database is in read-only mode!")

        result = self.db[collection].delete_many(query)
        deleted_count = result.deleted_count

        if self.verbose:
            logger.info(
                f"Deleted {deleted_count} documents from collection '{collection}'."
            )

        if self.enable_notifications and deleted_count > 0:
            if self.enable_notifications and deleted_count > 0:
                self._send_notification(
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

    def _send_notification(self, message: Dict[str, Any]):
        """Send a notification message to the Redis queue.

        Args:
            message (Dict[str, Any]): The notification message to send.
        """

        if self.redis_queue_manager:
            try:
                self.redis_queue_manager.publish(self.QUEUE_NAME, message)
                if self.verbose:
                    logger.info(f"Notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    def has_permission(self, user_id: str, collection: str) -> bool:
        """Verify if a user has access to a collection based on their role.

        Args:
            user_id (str): The user ID.
            collection (str): The collection to verify access to.

        Returns:
            bool: True if the user has access, otherwise False.
        """

        user_role = self.db["roles"].find_one({"user_id": user_id})

        if not user_role:
            if self.verbose:
                logger.warning(f"User {user_id} not found in roles collection.")
            return False

        has_access = collection in user_role.get("collections", [])
        if self.verbose:
            logger.info(f"User {user_id} access to {collection}: {has_access}")

        return has_access

    def listen_notifications(self) -> None:
        """Start listening for notifications using RedisQueueManager."""
        if self.redis_queue_manager and self.notification_callback:

            @self.redis_queue_manager.on_message(self.QUEUE_NAME)
            def handle_message(record: str) -> None:
                self.notification_callback(record)

            self.redis_queue_manager.start()
            if self.verbose:
                logger.info("Notification receiver started.")

            self.redis_queue_manager.wait()

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data.

        Args:
            data (str): Data to be encrypted.

        Returns:
            str: Encrypted data.
        """
        return cipher_suite.encrypt(data.encode()).decode()

    def decrypt(self, data: str) -> str:
        """Decrypt encrypted data.

        Args:
            data (str): Encrypted data.

        Returns:
            str: Decrypted data.
        """
        return cipher_suite.decrypt(data.encode()).decode()

    def close(self) -> None:
        """Close MongoDB and Redis connections."""
        self.client.close()
        if self.verbose:
            logger.info("MongoDB and Redis connections closed.")

    def __enter__(self) -> "WMongo":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
