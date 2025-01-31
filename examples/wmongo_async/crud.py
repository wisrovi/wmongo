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