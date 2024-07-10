from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
    )
from json import dumps


def start_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Товар в Наличии", callback_data=dumps({"from": "menu", "to": "stock"}))],
        [InlineKeyboardButton("Товар под Заказ", callback_data=dumps({"from": "menu", "to": "order"}))]
    ])


def stock(goods_in_stock: list[tuple]):
    keyboard = []
    for good, price in goods_in_stock:
        keyboard.append([InlineKeyboardButton(f"{good} - {price/1000:.1f}K", callback_data=dumps({"good" : f"{good}"}))])
    
    keyboard.append([InlineKeyboardButton("Назад", callback_data=dumps({"from": "stock", "to" : "menu"}))])

    return InlineKeyboardMarkup(keyboard)


def good_card():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Чат заказа", url='t.me/best_tech_shop')],
        [InlineKeyboardButton("Назад", callback_data=dumps({"from": "good", "to" : "stock"}))],
        ])
