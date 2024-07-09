from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from json import dumps




def start_menu():
    keyboard = [
            [
                InlineKeyboardButton("Товар в Наличии", callback_data=dumps({"from": "menu", "to": "stock"})), 
            ],
            [
                InlineKeyboardButton("Товар под Заказ", callback_data=dumps({"from": "menu", "to": "order"})),
            ],
            [
                InlineKeyboardButton("Support",  url='t.me/best_tech_shop'),
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)



def stock(goods_in_stock: list[tuple]):
    keyboard = []
    for good, price in goods_in_stock:
        keyboard.append([InlineKeyboardButton(f"{good} - {price/1000:.1f}K", callback_data=dumps({"good" : f"{good}"}))])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data=dumps({"from": "stock", "to" : "menu"}))])

    return InlineKeyboardMarkup(keyboard)

def back_to_stock():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data=dumps({"from": "good", "to" : "stock"}))]])
