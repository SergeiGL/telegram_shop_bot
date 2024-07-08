
import psycopg2
import config

conn = psycopg2.connect(
                host = config.db_config['host'],
                dbname = config.db_config['dbname'],
                user = config.db_config['user'],
                password = config.db_config['password'],
                port = config.db_config['port'],
                )

conn.autocommit = True
cursor = conn.cursor()



# ---------------------------------------------------- CREATE ALL NECESSARY TABLES: ----------------------------------------------------
try:
    cursor.execute(
        """CREATE TABLE users(
                                tg_id BIGINT PRIMARY KEY NOT NULL,
                                chat_id BIGINT NOT NULL,
                                username varchar(100) NOT NULL,

                                first_seen timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                last_seen timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,

                                prev_msg_answered bool DEFAULT True NOT NULL,
                                
                                start_dialogue_msg_id BIGINT DEFAULT -1 NOT NULL,
                                invoice_msg_id BIGINT DEFAULT -1 NOT NULL,
                                msg_id_with_kb BIGINT DEFAULT -1 NOT NULL,
                                
                                current_dialog_id BIGINT DEFAULT -1 NOT NULL,

                                balance_usd real DEFAULT 0.5 NOT NULL

                                );""")
except: pass

try:
    cursor.execute(
        """CREATE TABLE dialogues(
                id BIGSERIAL PRIMARY KEY NOT NULL,
                tg_id BIGINT REFERENCES users(tg_id) NOT NULL,
                model varchar(100) NOT NULL,
                start_time timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
                );""")
except: pass

try:
    cursor.execute(
        """CREATE TABLE messages (
                id BIGSERIAL PRIMARY KEY NOT NULL,
                dialog_id BIGINT REFERENCES dialogues(id) NOT NULL,
                user_message TEXT,
                bot_message TEXT,
                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
                );""")
except: pass

try:
    cursor.execute(
        """CREATE TABLE paid_models_usage (
                tg_id BIGINT NOT NULL REFERENCES users(tg_id),
                n_input_tokens_used BIGINT DEFAULT 0 NOT NULL,
                n_output_tokens_used BIGINT DEFAULT 0 NOT NULL,
                dialog_id BIGINT NOT NULL,
                model varchar(100) NOT NULL,
                price real NOT NULL,
                time timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
                );""")
except: pass

try:
    cursor.execute(
        """CREATE TABLE top_ups(
                id BIGSERIAL PRIMARY KEY NOT NULL,
                is_paid bool DEFAULT False NOT NULL,
                tg_id BIGINT NOT NULL REFERENCES users(tg_id),
                invoice_id varchar(100),
                amount real,
                currency varchar(100) NOT NULL,
                time timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
                );""")
except: pass


try:
    cursor.execute(
        """CREATE TABLE exchange_rate(
                pair varchar(100) PRIMARY KEY NOT NULL,
                rate real DEFAULT 100 NOT NULL
                );""")
except: pass

try:
    cursor.execute(
        """CREATE TABLE model_pricing(
                                model varchar(100) PRIMARY KEY NOT NULL,
                                input_price real NOT NULL,
                                output_price real NOT NULL
                                );""")
except: pass


try:
    cursor.execute(
        """CREATE TABLE errors(
                                error TEXT,
                                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
                                );""")
except: pass


cursor.close()
conn.close()