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
