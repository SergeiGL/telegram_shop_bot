from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from json import dumps




def start_menu(balance_USD: float):
    keyboard = [
            [
                InlineKeyboardButton("Choose AI model", callback_data=dumps({"from": "main_menu", "to": "choose_model"})), 
            ],
            [
                # InlineKeyboardButton("Инфо",  web_app=telegram.WebAppInfo(url="https://sergeigl.github.io/")), 
                InlineKeyboardButton(f"${balance_USD:.1f}", callback_data=dumps({"from": "main_menu", "to": "balance"})),
                InlineKeyboardButton("Support",  url='t.me/GPT_instant_bot_support'),
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)



def choose_model():
    keyboard = [
            [
                InlineKeyboardButton("Free GPT 4", callback_data=dumps({"from": "ch_m", "model" : "free_4"}))
            ],
            [
                InlineKeyboardButton("Google Gemini Pro", callback_data=dumps({"from": "ch_m", "model" : "gemini-pro"}))
            ],
            [
                InlineKeyboardButton("OpenAI GPT 4 Turbo", callback_data=dumps({"from": "ch_m", "model" : "oai_4_t"}))
            ],
            # [
                # InlineKeyboardButton("OpenAI 3.5 turbo", callback_data=dumps({"from": "ch_m", "to": "3.5_t", "model" : "3.5_t"})), 
                # InlineKeyboardButton("OpenAI 4 turbo", callback_data=dumps({"from": "ch_m", "to": "4_t", "model" : "4_t"}))
            # ],
            [
                InlineKeyboardButton("Main Menu", callback_data=dumps({"from": "ch_m", "to": "main_menu"}))
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)


def main_menu_only():
    keyboard = [
            [
                InlineKeyboardButton("Main Menu", callback_data=dumps({"from": "gpt_resp", "to": "main_menu"}))
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)


def gpt_responce(model: str, balance_USD: float = None):
    keyboard = [
                [
                    InlineKeyboardButton("Regenerate Answer", callback_data=dumps({"from": "gpt_resp", "to": "gpt_regen", "model" : model})), 
                ],
                [
                    InlineKeyboardButton("New Chat (forget context)", callback_data=dumps({"from": "gpt_resp", "to": "new_chat", "model": model}))
                ],
                [
                    InlineKeyboardButton("Main Menu", callback_data=dumps({"from": "gpt_resp", "to": "main_menu"}))
                ]
            ]
    
    if balance_USD != None:
        keyboard[0].append(InlineKeyboardButton(f"${balance_USD:.1f}", callback_data=dumps({"from": "gpt_resp", "to": "balance"})))
    
    return InlineKeyboardMarkup(keyboard)


def payment_button(payment_link: str):
    keyboard = [
                [InlineKeyboardButton("Pay With Crypto",  web_app=WebAppInfo(url=payment_link))
            ],
            [
                InlineKeyboardButton("Main Menu", callback_data=dumps({"from": "payment_button", "to": "main_menu"}))
            ]
        ]
    return InlineKeyboardMarkup(keyboard)
