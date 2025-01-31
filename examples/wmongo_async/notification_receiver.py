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
