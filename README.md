# wmongo

**wmongo** is a library for python control of MongoDB databases.

# Description

wmongo simplifies the use of MongoDB databases in Python. It provides a simple interface to the MongoDB database, allowing you to easily insert, update, and delete data.

## Installation

To install the library, use `pip`:

```bash
pip install wmongo
```

# Description

The **wmongo** library offers a number of general-purpose modules.

# License

MIT

This project is licensed under the MIT License. See the `LICENSE` file for details.

# Examples

This directory contains a collection of examples that demonstrate the usage of various modules and functionalities in this project. Each subfolder corresponds to a specific module and includes example scripts to help you understand how to use that module.

## Directory Structure

The examples are organized as follows:

```
examples/
    wmongo_async/
        crud.py
        notification_receiver.py
    wmongo/
        crud.py
        delete_and_notify.py
        insert_and_notify.py
        notifaction_receiver.py
        update_and_notify.py
```

## How to Use

1. Navigate to the module folder of interest, e.g., `examples/module1/`.
2. Open the `README.md` in that folder to get detailed information about the examples.
3. Run the scripts directly using:
   ```bash
   python example1.py
   ```

## Modules and Examples

### wmongo

#### Description

This module demonstrates specific functionalities.

- **crud.py**: Example demonstrating functionality.

```python
from typing import List
from wmongo import WMongo
from pydantic import BaseModel

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "uri": "mongodb://localhost:27017",
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
}


# Pydantic model for user data validation
class UserModel(BaseModel):
    name: str
    age: int


# Insert a user synchronously
user_data = UserModel(name="Bob", age=25).dict()
with WMongo(database="mydb", verbose=False, **credentials) as wm:
    if wm.has_permission(user_id="123", collection="users"):
        wm.insert("users", {"name": "Alice", "age": 30})
    else:
        print("Access Denied")


# Insert a user synchronously with Redis caching
with WMongo(database="mydb", verbose=False, **credentials) as wm:
    wm.update("users", {"name": "Bob"}, {"age": 26})

# Read, update, and delete operations within the context manager
with WMongo(database="mydb", verbose=False, **credentials) as wm:
    # Delete user
    wm.delete("users", {"name": "Bob"})


# Pydantic model for user data validation
class UserRole(BaseModel):
    user_id: str
    role: int
    collections: List[str]
```

- **delete_and_notify.py**: Example demonstrating functionality.

```python
from wmongo import WMongo
from pydantic import BaseModel

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}

notifications = {
    "enable_notifications": True,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


# Pydantic model for user data validation
class UserModel(BaseModel):
    name: str
    age: int


# Insert a user synchronously
user_data = UserModel(name="Bob", age=25).dict()
with WMongo(database="mydb", verbose=True, **credentials) as wm:
    if wm.has_permission(user_id="123", collection="users"):
        wm.delete("users", {"name": "Alice"})
    else:
        print("Access Denied")
```

- **insert_and_notify.py**: Example demonstrating functionality.

```python
from wmongo import WMongo
from pydantic import BaseModel

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}

notifications = {
    "enable_notifications": True,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


# Pydantic model for user data validation
class UserModel(BaseModel):
    name: str
    age: int


# Insert a user synchronously
user_data = UserModel(name="Bob", age=25).dict()
with WMongo(database="mydb", verbose=False, **credentials) as wm:
    if wm.has_permission(user_id="123", collection="users"):
        wm.insert("users", {"name": "Alice", "age": 30})
    else:
        print("Access Denied")
```

- **notifaction_receiver.py**: Example demonstrating functionality.

```python
from wmongo import WMongo

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}


def my_notification_callback(message: str):
    print(f"📩 Notification Received: {message}")


notifications = {
    "enable_notification_receiver": True,
    "notification_callback": my_notification_callback,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


# Este script solo escuchará notificaciones
with WMongo(
    database="mydb",
    verbose=False,
    **credentials,
) as wm:
    print("Listening for notifications...")
    wm.listen_notifications()
```

- **update_and_notify.py**: Example demonstrating functionality.

```python
from wmongo import WMongo
from pydantic import BaseModel

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}

notifications = {
    "enable_notifications": True,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


# Pydantic model for user data validation
class UserModel(BaseModel):
    name: str
    age: int


# Insert a user synchronously
user_data = UserModel(name="Bob", age=25).dict()
with WMongo(database="mydb", verbose=True, **credentials) as wm:
    if wm.has_permission(user_id="123", collection="users"):
        wm.update("users", {"name": "Alice"}, {"age": 31})
    else:
        print("Access Denied")
```

### wmongo_async

#### Description

This module demonstrates specific functionalities.

- **crud.py**: Example demonstrating functionality.

```python
from wmongo import WMongoAsync
import asyncio

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}

notifications = {
    "enable_notifications": True,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


async def insert_example():
    async with WMongoAsync(database="mydb", verbose=False, **credentials) as wm:
        doc_id = await wm.insert("users", {"name": "Alice", "age": 30})
        print(f"Inserted document with ID: {doc_id}")


asyncio.run(insert_example())


async def find_example():
    async with WMongoAsync(database="mydb", verbose=False, **credentials) as wm:
        users = await wm.find("users", {"age": {"$gte": 20}})  # Usuarios con edad >= 20
        print(f"Users found: {users}")


asyncio.run(find_example())


async def update_example():
    async with WMongoAsync(database="mydb", verbose=False, **credentials) as wm:
        updated_count = await wm.update("users", {"name": "Alice"}, {"age": 35})
        print(f"Updated {updated_count} documents.")


asyncio.run(update_example())




async def delete_example():
    async with WMongoAsync(database="mydb", verbose=False, **credentials) as wm:
        deleted_count = await wm.delete("users", {"name": "Alice"})
        print(f"Deleted {deleted_count} documents.")

asyncio.run(delete_example())
```

- **notification_receiver.py**: Example demonstrating functionality.

```python
from wmongo import WMongoAsync
import asyncio

# Credentials stored in a dictionary for easy reuse
mongo_credentials = {
    "username": "root",
    "password": "example",
}

redis_credentials = {
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
}


def my_notification_callback(message: str):
    print(f"📩 Notification Received: {message}")


notifications = {
    "enable_notification_receiver": True,
    "notification_callback": my_notification_callback,
}

credentials = {
    **mongo_credentials,
    **redis_credentials,
    **notifications,
}


async def listen_for_notifications():
    async with WMongoAsync(database="mydb", verbose=False, **credentials) as wm:
        print("Listening for notifications...")
        wm.listen_notifications()


asyncio.run(listen_for_notifications())
```
