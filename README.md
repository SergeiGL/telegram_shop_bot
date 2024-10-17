# [install]
python3 -m venv create bot_venv
pip install -r requirements.txt

sudo cp tech_shop_bot.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable tech_shop_bot.service

# [before run]
sudo systemctl status redis-server.service
sudo systemctl status postgresql
sudo systemctl status tech_shop_bot.service

# [run]
sudo systemctl start tech_shop_bot.service




# Create config.py file

```
is_in_production = False


if is_in_production:
    telegram_bot_token = ""
    
    telegram_alerts_chats = [""]
    telegram_alerts_token = ""
    
    good_picture_sample_file_id = ""
    menu_anim_file_id = ''
    
    order_description_text = ""
    
    is_drop_all_tables = False
    is_set_tables = False
    
    pg_conf_keys = {
        'host': "localhost",
        'dbname': "tech_shop_prod",
        'user': "sergei",
        'password': "",
        'port': "5432",
    }


else:
    telegram_bot_token = ""
    
    telegram_alerts_chats = [""]
    telegram_alerts_token = ""
    
    good_picture_sample_file_id = ""
    menu_anim_file_id = ''
    
    order_description_text = ""
    
    is_drop_all_tables = True
    is_set_tables = True
    
    
    pg_conf_keys = {
        'host': "localhost",
        'dbname': "tech_shop_dev",
        'user': "sergei",
        'password': "",
        'port': "5432",
    }



redis_conf_keys = {
        "host" : "localhost",
        "port" : "6379",
        "db" :  "1"
    }
```