import redis
import config

def clear_redis_db():
    try:
        redis_client = redis.StrictRedis(
                host=config.redis_config["host"], 
                port=config.redis_config["port"], 
                db=config.redis_config["db"],
                decode_responses=True  # Ensures that Redis will return a string (instead of bytes)
            )
        
        # Flush the database
        redis_client.flushdb()
        print(f"All keys in Redis database {config.redis_config["db"]} have been cleared.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")



if __name__ == "__main__":
    clear_redis_db()