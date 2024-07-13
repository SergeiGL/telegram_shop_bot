import psycopg2
import redis
from psycopg2.extras import DictCursor
import config
import json
from base64 import b64encode
import multiprocessing




def validate_text(text):
    return text.replace("'", " ").replace('"', " ")


class Database:
    def __init__(self):
        self.redis_conn = redis.StrictRedis(
                host=config.redis_config["host"], 
                port=config.redis_config["port"], 
                db=config.redis_config["db"],
                decode_responses=True)  # Ensures that Redis will return a string (instead of bytes)
        
        self.redis_updater_process = multiprocessing.Process(
            target=self.redis_updater,
            args=(config.redis_config, config.pg_config, config.production)
            )
        self.redis_updater_process.start()
        
        
        self.pg_conn = psycopg2.connect(
                host = config.pg_config["host"],
                dbname = config.pg_config["dbname"],
                user = config.pg_config["user"],
                password = config.pg_config["password"],
                port = config.pg_config["port"])
        self.pg_conn.autocommit = True
    
    
    def __del__(self):
        self.pg_conn.close()
        self.redis_conn.close()
        
        self.redis_updater_process.terminate()
        self.redis_updater_process.join()  # Wait for the process to actually terminate
        
        print("Connections closed")
    
    def add_new_user_if_not_exist(self, tg_id: int, chat_id: int, username: str):
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""SELECT EXISTS (SELECT 1 FROM users WHERE tg_id = %s) AS user_exists;""", (tg_id, ))
            
            if not cursor.fetchone()[0]: # True or False depending on whether user exusts or not
                cursor.execute(
                        """INSERT INTO users (
                                tg_id,
                                chat_id,
                                username
                                ) VALUES (%s, %s, %s);""", (tg_id, chat_id, validate_text(username)))
    
    
    def set_user_attribute(self, tg_id: int, key: str, value) -> None:
        with self.pg_conn.cursor() as cursor:
            cursor.execute(
                        f"""UPDATE users
                            SET {key} = %s
                            WHERE tg_id = %s;""", (value, tg_id))
            affected_rows = cursor.rowcount
        
        if affected_rows == 0:
            raise ValueError(f"DB: error in setting value\nset_user_attribute(self, {tg_id}: int, {key}: str, {value}: Any)")
    
    
    def get_attribute(self, select: str, from_: str, value: int, where: str = "tg_id") -> object:
        with self.pg_conn.cursor() as cursor:
            cursor.execute(f"""SELECT {select} FROM {from_} WHERE {where} = %s;""", (value, ))
            value = cursor.fetchone()
        
        if (value is None) or (value[0] is None): # value = None if tg_id not found 
            raise ValueError(f"DB: not found a value\nget_attribute(self, {from_}: str, {value}: int, {select}: str)")
        else:
            return value[0]
    
    def get_stock_models(self):
        cache_key = "models"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not config.production: print("DB request")
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""SELECT DISTINCT model from goods WHERE quantity_in_stock > 0 ORDER BY model""")
                res = cursor.fetchall()
                models = [model for (model,) in res]
                self.redis_conn.set(cache_key, json.dumps(models))
                return models
    
    def get_stock_versions(self, model):
        cache_key = f"version{model}"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not config.production: print("DB request")
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""SELECT version from goods WHERE quantity_in_stock > 0 AND model = %s ORDER BY version""", (model, ))
                res = cursor.fetchall()
                versions = [vers for (vers,) in res]
                self.redis_conn.set(cache_key, json.dumps(versions))
                return versions
    
    def get_good_data(self, model : str, version: str):
        cache_key = f"good{model}{version}"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not config.production: print("DB request")
            with self.pg_conn.cursor(cursor_factory=DictCursor) as cursor:
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
                
                good_data_dict = dict(good_data)
                
                # Handle photo object as it cannot be directly stored in redis
                good_data_dict["photo"] = b64encode(good_data_dict["photo"].tobytes()).decode('utf-8')
                
                self.redis_conn.set(cache_key, json.dumps(good_data_dict))
                return good_data_dict
    
    def insert_error(self, error_text: str):
        with self.pg_conn.cursor() as cursor:
            cursor.execute("INSERT INTO errors(error) VALUES (%s);", (validate_text(error_text), ))
    
    
    def redis_updater(self, redis_config, pg_config, is_in_production): 
        import psycopg2
        import redis
        import select
        from time import sleep
        import traceback
        from datetime import datetime
                
        while True:
            try:
                with redis.StrictRedis(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    db=redis_config["db"],
                    decode_responses=True
                    ) as redis_client:
                    with psycopg2.connect(
                        dbname=pg_config["dbname"],
                        user=pg_config["user"],
                        password=pg_config["password"],
                        host=pg_config["host"],
                        port=pg_config["port"]
                        ) as pg_conn:
                        
                        pg_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                        
                        def clear_redis_db():
                            redis_client.flushdb()
                            print(f"All Redis keys cleared - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")
                        
                        with pg_conn.cursor() as cur:
                            cur.execute("LISTEN table_change;")
                        
                        print("Start listening for table changes...")
                        while True:
                            if select.select([pg_conn], [], [], None) == ([], [], []):
                                print("ERROR\nselect.select([conn], [], [], None) == ([], [], [])")
                            else:
                                pg_conn.poll()
                                while pg_conn.notifies:
                                    notify = pg_conn.notifies.pop(0)
                                    if not is_in_production: print(f"Table changed: {notify.payload} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")
                                    clear_redis_db()
                                    break  # Ensure we only clear once per batch of notifications
            except Exception:
                error = "ERROR\nRedis_updater:\n" + str(traceback.format_exc())
                print(error)
                sleep(600)