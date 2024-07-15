import psycopg2
import config
from tabulate import tabulate
from random import randint

is_drop_all_tables = True
is_set_tables = True


good_description = """
💰 Актуальная цена\n(обновляется ежедневно)\n
✅ Только ОРИГИНАЛЬНАЯ и НОВАЯ техника\n
📍Самовывоз: 1 мин от метро "Москва Сити" и "Деловой Центр"\n
<code class="text">1-й Красногвардейский проезд, 22с1</code>\n
🚚 Доставка: Любая курьерская служба\n(100% предоплата)\n
✈️ Экспресс доставка по Москве и МО в день заказа\n
🛒Жмите "Купить"\n⏱Ответим за 2 минуты!"""



if __name__ == "__main__":
    conn = psycopg2.connect(
                    host = config.pg_conf_keys['host'],
                    dbname = config.pg_conf_keys['dbname'],
                    user = config.pg_conf_keys['user'],
                    password = config.pg_conf_keys['password'],
                    port = config.pg_conf_keys['port'],
                    )

    conn.autocommit = True
    cursor = conn.cursor()
    
    if is_drop_all_tables:
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables")
        else:
            drop_query = "DROP TABLE IF EXISTS {} CASCADE;".format(
                ', '.join([f'"{table[0]}"' for table in tables]))
            
            cursor.execute(drop_query)
    
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users(
                user_id BIGINT PRIMARY KEY NOT NULL,
                chat_id BIGINT NOT NULL,
                username VARCHAR(100) NOT NULL,
                
                first_seen timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                
                msg_id_with_kb BIGINT DEFAULT -1 NOT NULL
                );""")
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS supplier_prices (
                specification_name VARCHAR(125) PRIMARY KEY,
                price_USD INTEGER DEFAULT 0 NOT NULL,
                margin_stock real DEFAULT 20.0 NOT NULL,
                margin_order real DEFAULT 15.0 NOT NULL
                );""")
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS goods (
                specification_name VARCHAR(125) PRIMARY KEY,
                model VARCHAR(25) NOT NULL,
                version VARCHAR(25) NOT NULL,
                quantity_in_stock INTEGER DEFAULT 0 NOT NULL,
                description VARCHAR(500) NOT NULL,
                photo VARCHAR(255) NOT NULL,
                FOREIGN KEY (specification_name) REFERENCES supplier_prices(specification_name),
                UNIQUE (model, version)
                );""")

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_model ON goods (model);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_version ON goods (version);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_quantity_in_stock ON goods (quantity_in_stock);""")
    
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS exchange_rates(
                pair VARCHAR(20) PRIMARY KEY NOT NULL,
                exch_rate real DEFAULT 150 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS errors(
                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                error TEXT NOT NULL
                );""")

# -- Create a function to notify changes
    cursor.execute(
        """CREATE OR REPLACE FUNCTION notify_table_change() RETURNS trigger AS $$
            BEGIN
                PERFORM pg_notify('table_change', TG_TABLE_NAME);
                RETURN NEW;
            END;
        $$ LANGUAGE plpgsql;""")
    
    try:
        cursor.execute(
            """CREATE TRIGGER goods_change_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON goods
                    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();""")
    except psycopg2.errors.DuplicateObject: pass
    
    try:
        cursor.execute(
            """CREATE TRIGGER supplier_prices_change_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON supplier_prices
                    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();""")
    except psycopg2.errors.DuplicateObject: pass

    try:
        cursor.execute(
            """CREATE TRIGGER exchange_rates_change_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON exchange_rates
                    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();""")
    except psycopg2.errors.DuplicateObject: pass

    cursor.execute(
        """
        SELECT 
            tbl.schemaname AS schema_name,
            tbl.tablename AS table_name,
            tgr.tgname AS trigger_name
        FROM 
            pg_tables tbl
        LEFT JOIN 
            pg_class cl ON cl.relname = tbl.tablename
        LEFT JOIN 
            pg_trigger tgr ON tgr.tgrelid = cl.oid
        LEFT JOIN 
            pg_namespace nsp ON cl.relnamespace = nsp.oid
        WHERE 
            tbl.schemaname NOT IN ('pg_catalog', 'information_schema')
            AND (tgr.tgname IS NULL OR tgr.tgname !~ '^RI_ConstraintTrigger')
        ORDER BY 
            tbl.schemaname, tbl.tablename, tgr.tgname;""")
    print(tabulate(cursor.fetchall())+ "\n\n\n")
    
    
    cursor.execute(
        """
        SELECT 
            tbl.schemaname AS schema_name,
            tbl.tablename AS table_name,
            tgr.tgname AS trigger_name
        FROM 
            pg_tables tbl
        LEFT JOIN 
            pg_class cl ON cl.relname = tbl.tablename
        LEFT JOIN 
            pg_trigger tgr ON tgr.tgrelid = cl.oid
        LEFT JOIN 
            pg_namespace nsp ON cl.relnamespace = nsp.oid
        WHERE 
            tbl.schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 
            tbl.schemaname, tbl.tablename, tgr.tgname;""")
    print(tabulate(cursor.fetchall())+ "\n\n\n")
    
    if is_set_tables:
        cursor.execute("""
                INSERT INTO exchange_rates (pair, exch_rate)
                VALUES (%s, %s)
                ON CONFLICT (pair) DO UPDATE SET exch_rate = EXCLUDED.exch_rate;""", ("BUY USDT", 100))
            
        for model in ["iPhone 15", "iPhone 14"]:
            for version in ["256GB ⬜", "512GB ⬛", "PRO 256GB ⬜", "PRO 512GB ⬛"]:
                specification_name = model + " " + version
                cursor.execute(
                    """INSERT INTO supplier_prices(
                            specification_name,
                            price_usd)
                            VALUES (%s, %s) ON CONFLICT (specification_name) DO NOTHING;""", (specification_name, randint(200, 1000)))
                
                cursor.execute(
                    """INSERT INTO goods(
                        specification_name,
                        model,
                        version,
                        description,
                        quantity_in_stock,
                        photo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (specification_name) DO NOTHING;""", (specification_name, model, version, good_description, 1 , \
                    "AgACAgIAAxkDAAICsmaSy6tKQVNlmjxRrOoxKpvMKHksAALA5DEbtAOYSCe9BcUYgO4sAQADAgADdwADNQQ"))
    
    cursor.close()
    conn.close()
