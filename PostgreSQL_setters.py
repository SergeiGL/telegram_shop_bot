import psycopg2
import config
from random import randint

description = '💰 Актуальная цена\n(обновляется ежедневно)\n\n✅ Только ОРИГИНАЛЬНАЯ и НОВАЯ техника\n\n📍Самовывоз: 1 мин от метро "Москва Сити" и "Деловой Центр"\n<code class="text">1-й Красногвардейский проезд, 22с1</code>\n\n🚚 Доставка: Любая курьерская служба\n(100% предоплата)\n\n✈️ Экспресс доставка по Москве и МО в день заказа\n\n🛒Жмите "Купить"\n⏱Ответим за 2 минуты!'

if __name__ == "__main__":
    conn = psycopg2.connect(
            host = config.pg_conf_keys['host'],
            dbname = config.pg_conf_keys['dbname'],
            user = config.pg_conf_keys['user'],
            password = config.pg_conf_keys['password'],
            port = config.pg_conf_keys['port'],
            )
    
    conn.autocommit = True
    
    with conn.cursor() as cursor:
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
                            VALUES (%s, %s) ON CONFLICT (specification_name) DO NOTHING;""", (specification_name, randint(20_000, 500_000)))
                
                cursor.execute(
                    """INSERT INTO goods(
                        specification_name,
                        model,
                        version,
                        description,
                        quantity_in_stock,
                        photo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (specification_name) DO NOTHING;""", (specification_name, model, version, description, 1 , \
                    "AgACAgIAAxkDAAICsmaSy6tKQVNlmjxRrOoxKpvMKHksAALA5DEbtAOYSCe9BcUYgO4sAQADAgADdwADNQQ"))
    
    conn.close()

