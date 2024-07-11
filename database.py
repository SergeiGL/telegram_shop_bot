import psycopg2
from psycopg2.extras import DictCursor
import config


def validate_text(text):
    return text.replace("'", " ").replace('"', " ")


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
                host = config.db_config["host"],
                dbname = config.db_config["dbname"],
                user = config.db_config["user"],
                password = config.db_config["password"],
                port = config.db_config["port"],
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
    
    def get_models_in_stock(self):
        with self.conn.cursor() as cursor:
            cursor.execute("""SELECT DISTINCT model from goods WHERE quantity_in_stock > 0 ORDER BY model""")
            res = cursor.fetchall()
            return [model for (model,) in res]
    
    def get_versions_in_stock(self, model):
        with self.conn.cursor() as cursor:
            cursor.execute("""SELECT version from goods WHERE quantity_in_stock > 0 AND model = %s ORDER BY version""", (model, ))
            res = cursor.fetchall()
            return [vers for (vers,) in res]
    
    def get_good_data(self, full_name, user_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT full_name, model, description, price_rub, photo FROM goods WHERE full_name = %s AND quantity_in_stock > 0", (full_name,))
            good_data = cursor.fetchone()
            if good_data is None:
                return False
            else:
                good_data = dict(good_data)
            
            cursor.execute("""
                UPDATE users
                SET interactions_counter = interactions_counter + 1
                WHERE tg_id = %s;
                """, (user_id, ))
            
            return good_data
    
    
    def insert_error(self, error_text: str):
        with self.conn.cursor() as cursor:
            cursor.execute("INSERT INTO errors(error) VALUES (%s);", (validate_text(error_text), ))

    def get_exhange_rate(self, pair: str):
        with self.conn.cursor() as cursor:
            cursor.execute("""SELECT rate FROM exchange_rate WHERE pair = %s;""", (pair, ))
            return cursor.fetchone()[0]


