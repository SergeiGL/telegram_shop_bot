from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
    )
from json import dumps


def start_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Товар в Наличии", callback_data=dumps({"from": "menu", "to": "stock"}))],
        [InlineKeyboardButton("Заказать Товар", callback_data=dumps({"from": "menu", "to": "order"}))]
    ])


def stock_models(models_in_stock: list[str]):
    if models_in_stock!=[]:
        keyboard = []
        for model in models_in_stock:
            keyboard.append([InlineKeyboardButton(model, callback_data=dumps({"model" : model}))])
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data=dumps({"from": "stock", "to" : "menu"}))])

        return InlineKeyboardMarkup(keyboard)
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Товара нет в наличии", callback_data=dumps({"from": "stock", "to" : "menu"}))]])


def stock_versions(model: str, versions_in_stock: list[str]):
    if versions_in_stock!=[]:
        def convert_to_pairs(versions_list, keyboard):
            n = len(versions_list)
            for i in range(0, n - 1, 2):
                keyboard.append([
                                InlineKeyboardButton(versions_list[i], callback_data=dumps({"gd_mdl" : model, "gd_vsn" : versions_list[i]})),
                                InlineKeyboardButton(versions_list[i+1], callback_data=dumps({"gd_mdl" : model, "gd_vsn" : versions_list[i+1]}))
                                ])
            if n % 2 != 0:  # if the list has an odd number of elements
                keyboard.append([
                                InlineKeyboardButton(versions_list[-1], callback_data=dumps({"gd_mdl" : model, "gd_vsn" : versions_list[-1]})),
                                InlineKeyboardButton(" ", callback_data=dumps({"from": -1}))
                                ])
        
        keyboard = []
        convert_to_pairs(versions_in_stock, keyboard)
        
        keyboard.append([InlineKeyboardButton("Назад", callback_data=dumps({"from": "vers", "to" : "stock"}))])
        return InlineKeyboardMarkup(keyboard)
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Товара нет в наличии", callback_data=dumps({"from": "vers", "to" : "stock"}))]])


def good_card(model: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Купить", url='t.me/best_tech_shop')],
        [InlineKeyboardButton("Назад", callback_data=dumps({"from": "good", "to": "vers", "modl" : model}))],
        ])

def pricetable():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Заказать", url='t.me/best_tech_shop')],
        [InlineKeyboardButton("Назад", callback_data=dumps({"from": "pricetable", "to": "start"}))],
        ])