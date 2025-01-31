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
