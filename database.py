import psycopg2
import config


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
                host = config.db_config["host"],
                dbname = config.db_config["dbname"],
                user = config.db_config["user"],
                password = config.db_config["password"],
                port = config.db_config["port"],
            )
        
        self.conn.autocommit = True # Saves changes autimatically
    
    # Returns:
    # True if user exists
    # False if user does exist
    # Raises exception if user does exist AND raise_exception=True is passed
    def is_user_exist(self, user_tg_id: int, raise_exception: bool):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT EXISTS (SELECT 1 FROM users WHERE tg_id = {user_tg_id}) AS user_exists;""")
            is_user_exist = cursor.fetchone()[0] # Bool value True or False
        
        if is_user_exist:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_tg_id} does not exist")
            else:
                return False
    
    
    # Creates a new user in the "user" db
    # COMPULSORY: Check if USER EXISTS FIRST
    def add_new_user(self, user_tg_id: int, chat_id: int, username: str):
        with self.conn.cursor() as cursor:
            cursor.execute(
                    f"""INSERT INTO users (
                            tg_id,
                            chat_id,
                            username
                            ) VALUES ({user_tg_id}, {chat_id}, '{username}');""")
    
    
    # Updates users table
    def set_user_attribute(self, user_tg_id: int, key: str, value) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                        f"""UPDATE users
                            SET {key} = %s,
                            last_seen = CURRENT_TIMESTAMP
                            WHERE tg_id = %s;""", (value, user_tg_id))
            
            affected_rows = cursor.rowcount

        if affected_rows == 0:
            raise ValueError(f"DB: error in setting value\nset_user_attribute(self, {user_tg_id}: int, {key}: str, {value}: Any)")
    
    
    # Gets user attribute by ID and KEY
    def get_attribute(self, select: str, from_: str, value: int, where: str = "tg_id") -> object:
        with self.conn.cursor() as cursor:
            cursor.execute(
                    f"""SELECT {select} FROM {from_} WHERE {where} = {value};""")
            value = cursor.fetchone()
        
        if value==None or value[0]==None: # value = None if tg_id not found 
            raise ValueError(f"DB: not found a value\nget_attribute(self, {from_}: str, {value}: int, {select}: str)")
        else:
            return value[0]

    
    # Returns balance of a specified user
    def get_balance_USD(self, user_tg_id: int) -> object:
        with self.conn.cursor() as cursor:
            cursor.execute(
                    f"""SELECT balance_usd FROM users WHERE tg_id = {user_tg_id};""")
            value = cursor.fetchone()
        
        if not value or not value[0]: # value = None if tg_id not found 
            raise ValueError(f"DB: not found a value\nget_balance_USD(self, {user_tg_id}: int)")
        else:
            return value[0]
    
    
    # Starts a new dialog with a given model:
    # Initialize the dialog in the "dialog" db
    # Hash (dialog_id) goes to the user's dict in the "user" db and the current model is saved
    def start_new_dialog(self, user_tg_id: int, model: str, msg_id_with_kb: int) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                        f"""INSERT INTO dialogues(
                        tg_id,
                        model
                    ) VALUES ({user_tg_id}, '{model}') RETURNING id;""")
            
            dialogue_id = cursor.fetchone()[0]
        
        
        # Update user's table to get all info about the dialogue
        self.set_user_attribute(user_tg_id = user_tg_id, key="start_dialogue_msg_id", value = msg_id_with_kb)
        self.set_user_attribute(user_tg_id = user_tg_id, key="msg_id_with_kb", value = msg_id_with_kb)
        self.set_user_attribute(user_tg_id = user_tg_id, key = "current_dialog_id", value = dialogue_id)
    
    
    def get_exhange_rate_USD_RUB(self):
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT rate FROM exchange_rate WHERE pair = 'USD_RUB';""")
            return cursor.fetchone()[0]
    
    def create_invoice(self, user_tg_id: int, invoice_id:str, amount: int, currency: str):
        with self.conn.cursor() as cursor:
            cursor.execute(f"INSERT INTO top_ups(tg_id, invoice_id, amount, currency) VALUES (%s, %s, %s, %s);", (user_tg_id, invoice_id, amount, currency,))
    
    def get_openai_prices_per_token_by_model(self, model):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT input_price, output_price FROM model_pricing WHERE model = %s", (model,))
            return cursor.fetchone()

    def insert_error(self, error_text):
        with self.conn.cursor() as cursor:
            cursor.execute(f"INSERT INTO errors(error) VALUES ('{valid_text(error_text)}');")




def valid_text(text):
    return text.replace("'", " ").replace('"', " ")

