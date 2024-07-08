import psycopg2
import config

# Delete dialogue history from these models
LIST_OF_FREE_MODELS = [
    "free_4",
    "gemini-pro",
    "f_txt_img"
]


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
    
    
    # Reset user dialog settings
    def end_dialog(self, user_tg_id: int) -> None:
        # Get current dialogue ID
        current_dialog_id = self.get_attribute(from_ = "users", select = "current_dialog_id", value = user_tg_id)
        
        if current_dialog_id==-1:
            return
        
        model = self.get_attribute(from_ = "dialogues", select = "model", where='id', value = current_dialog_id)
        
        # delete messages for free models
        if model.lower() in LIST_OF_FREE_MODELS:
            with self.conn.cursor() as cursor:
                # First delete from messages are tables are related
                cursor.execute(f"""DELETE FROM messages WHERE dialog_id = {current_dialog_id};""")
                cursor.execute(f"""DELETE FROM dialogues WHERE id = {current_dialog_id};""")
        
        # Update user's table to have 
        self.set_user_attribute(user_tg_id = user_tg_id, key = "current_dialog_id", value = -1)

    
    # After the full responce is generated, trigger this function to update n_tokens_used and balance
    def update_n_used_tokens_and_balance_USD(self, user_tg_id: int, current_model_as_in_keyboard: str, n_input_tokens: int, n_output_tokens: int, current_dialog_id:int, current_model: str) -> None:
        old_balance =  self.get_attribute(from_ = "users",  value = user_tg_id, select = "balance_usd")
        
        # Gets input and output token prices for a specific model
        input_token_price, output_token_price = self.get_openai_prices_per_token_by_model(current_model_as_in_keyboard)
        
        # Price of usage
        price_of_tokens_used = n_input_tokens * input_token_price + n_output_tokens*output_token_price
        new_balance = old_balance - price_of_tokens_used
        self.set_user_attribute(user_tg_id = user_tg_id, key = "balance_usd",  value = new_balance)
        
        # Logg usage values
        with self.conn.cursor() as cursor:
            cursor.execute(f"INSERT INTO paid_models_usage(tg_id, n_input_tokens_used, n_output_tokens_used, dialog_id, model, price) VALUES (%s, %s, %s, %s, %s, %s);", (user_tg_id, n_input_tokens, n_output_tokens, current_dialog_id, current_model, price_of_tokens_used))
        
        return new_balance


    # Gets a dict of all messages with a given dialog_id
    def get_dialog_messages(self, current_dialog_id = None, user_tg_id = None) -> list:
        
        # Is user is passed -> we do not know the current_dialog_id. Need 1 more request
        if user_tg_id != None:
            current_dialog_id = self.get_attribute(from_ = "users", select = "current_dialog_id", value = user_tg_id)
        
        with self.conn.cursor() as cursor:
            cursor.execute(f"""SELECT user_message, bot_message, date FROM messages WHERE dialog_id = {current_dialog_id};""")
            messages = cursor.fetchall()
        
        return [{'user': user, 'bot': bot, 'date': date.replace(tzinfo=None)} for user, bot, date in messages]

    
    def add_message_to_dialogue(self, current_dialog_id: int, user_message: str, bot_message: str) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                        f"""INSERT INTO messages(
                        dialog_id,
                        user_message,
                        bot_message
                    ) VALUES ({current_dialog_id}, '{valid_text(user_message)}', '{valid_text(bot_message)}');""")
    
    def delete_last_answer_from_current_dialogue(self, user_tg_id: int):
        # Get current_dialog_id
        current_dialog_id = self.get_attribute(from_ = "users", value = user_tg_id, select = "current_dialog_id")
        
        with self.conn.cursor() as cursor:
            cursor.execute(f"""DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE dialog_id = {current_dialog_id} ORDER BY date DESC LIMIT 1);""")

    
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

