import psycopg2
import config
from tabulate import tabulate


if __name__ == "__main__":
    
    conn = psycopg2.connect(
                    host = config.pg_config['host'],
                    dbname = config.pg_config['dbname'],
                    user = config.pg_config['user'],
                    password = config.pg_config['password'],
                    port = config.pg_config['port'],
                    )

    conn.autocommit = True
    cursor = conn.cursor()
    
    def drop_all_tables():
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables")
            return
        
        drop_query = "DROP TABLE IF EXISTS {} CASCADE;".format(
            ', '.join([f'"{table[0]}"' for table in tables]))
        
        cursor.execute(drop_query)
    
    drop_all_tables()
    
    
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
                photo BYTEA NOT NULL,
                description VARCHAR(500) NOT NULL,
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
    
    
    cursor.close()
    conn.close()