import psycopg2
from psycopg2.extras import DictCursor
import config
import redis
import json


def validate_text(text):
    return text.replace("'", " ").replace('"', " ")


class Database:
    def __init__(self):
        self.redis = redis.StrictRedis(
                host=config.redis_config["host"], 
                port=config.redis_config["port"], 
                db=config.redis_config["db"],
                decode_responses=True  # Ensures that Redis will return a string (instead of bytes)
            )
        
        self.conn = psycopg2.connect(
                host = config.pg_config["host"],
                dbname = config.pg_config["dbname"],
                user = config.pg_config["user"],
                password = config.pg_config["password"],
                port = config.pg_config["port"],
            )
        
        self.conn.autocommit = True
    
    def __del__(self):
        self.conn.close()
        print("Connection closed")
    
    def add_new_user_if_not_exist(self, tg_id: int, chat_id: int, username: str):
        with self.conn.cursor() as cursor:
            cursor.execute("""SELECT EXISTS (SELECT 1 FROM users WHERE tg_id = %s) AS user_exists;""", (tg_id, ))
            
            if not cursor.fetchone()[0]: # True or False depending on whether user exusts or not
                cursor.execute(
                        """INSERT INTO users (
                                tg_id,
                                chat_id,
                                username
                                ) VALUES (%s, %s, %s);""", (tg_id, chat_id, validate_text(username)))
    
    
    def set_user_attribute(self, tg_id: int, key: str, value) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                        f"""UPDATE users
                            SET {key} = %s
                            WHERE tg_id = %s;""", (value, tg_id))
            affected_rows = cursor.rowcount
        
        if affected_rows == 0:
            raise ValueError(f"DB: error in setting value\nset_user_attribute(self, {tg_id}: int, {key}: str, {value}: Any)")
    
    
    def get_attribute(self, select: str, from_: str, value: int, where: str = "tg_id") -> object:
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT {select} FROM {from_} WHERE {where} = %s;""", (value, ))
            value = cursor.fetchone()
        
        if (value is None) or (value[0] is None): # value = None if tg_id not found 
            raise ValueError(f"DB: not found a value\nget_attribute(self, {from_}: str, {value}: int, {select}: str)")
        else:
            return value[0]
    
    def get_stock_models(self):
        cache_key = "get_stock_models"
        
        cached_result = self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            print("DB request")
            with self.conn.cursor() as cursor:
                cursor.execute("""SELECT DISTINCT model from goods WHERE quantity_in_stock > 0 ORDER BY model""")
                res = cursor.fetchall()
                models = [model for (model,) in res]
                self.redis.set(cache_key, json.dumps(models))
                return models
    
    def get_stock_versions(self, model):
        cache_key = f"get_stock_versions{model}"
        
        cached_result = self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            print("DB request")
            with self.conn.cursor() as cursor:
                cursor.execute("""SELECT version from goods WHERE quantity_in_stock > 0 AND model = %s ORDER BY version""", (model, ))
                res = cursor.fetchall()
                versions = [vers for (vers,) in res]
                self.redis.set(cache_key, json.dumps(versions))
                return versions
    
    def get_good_data(self, model : str, version: str):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT g.specification_name, g.model, g.version, g.description, g.photo, sp.price_USD, sp.margin_order,
                    (SELECT exch_rate FROM exchange_rates WHERE pair = 'BUY USDT') AS exch_rate
                FROM goods g
                JOIN supplier_prices sp ON g.specification_name = sp.specification_name
                WHERE g.model = %s AND g.version = %s AND g.quantity_in_stock > 0
            """, (model, version))
            
            good_data = cursor.fetchone()
            
            if good_data is None:
                return False
            
            return dict(good_data)
    
    
    def insert_error(self, error_text: str):
        with self.conn.cursor() as cursor:
            cursor.execute("INSERT INTO errors(error) VALUES (%s);", (validate_text(error_text), ))