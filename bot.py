import asyncio
import json
from os import path
import traceback
import plisio
import requests
import hmac
import hashlib

from telegram import (
    Update,
    # InputMedia,
    InputMediaPhoto,
    # ReplyKeyboardRemove,
    LabeledPrice,
    Message
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters,
    PreCheckoutQueryHandler
)

import database

import g4f_connector
import gemini_connector
import openai_connector

import keyboards as kb

import config





import time
def timing_wrapper(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Function {func.__name__} took {(end - start):.6f} seconds to run.")
        return result
    return wrapper










async def prev_msg_answered(user_id: int, context: CallbackContext, chat_id: int):    
    return db.get_attribute(select="prev_msg_answered", from_='users', value=user_id)

@timing_wrapper
async def db_msg_delete(what_to_delete, user_id, chat_id, context):
    msg_id_to_delete = db.get_attribute(from_="users", value=user_id, select = what_to_delete)
    
    if msg_id_to_delete != -1:
        await delete_message(chat_id, msg_id_to_delete, context)
        db.set_user_attribute(user_tg_id = user_id, key = what_to_delete, value = -1)


async def delete_message(chat_id, message_id, context):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id = message_id)
    except: pass

async def register_user_if_not_exist(update: Update, context: CallbackContext, user, user_id: int, chat_id: int):
    if not db.is_user_exist(user_tg_id = user_id, raise_exception=False):
        db.add_new_user(
            user_tg_id = user_id,
            chat_id = chat_id,
            username=user.username or "Unknown")


# /start special entry function
# THE WHOLE CODE IS BUILD WITH THE ASSUMPTION THAT THE USER WILL START FROM HERE
async def start_handle(update: Update, context: CallbackContext) -> None:
    if update is None or update.message is None:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await db_msg_delete("msg_id_with_kb", user_id, chat_id, context)
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    await db_msg_delete("invoice_msg_id", user_id, chat_id, context)
    await delete_message(chat_id=chat_id, message_id = update.message.id, context=context)

    db.end_dialog(user_tg_id=user_id)
    
    if db.is_user_exist(user_tg_id = user_id, raise_exception=False):
        db.set_user_attribute(user_tg_id = user_id, key = "prev_msg_answered", value = False)
        start_wait_text = await context.bot.send_message(chat_id=chat_id, text=START_WAIT_TEXT.format(config.start_wait_time))
        db.set_user_attribute(user_tg_id = user_id, key="start_dialogue_msg_id", value = start_wait_text.id)
        await asyncio.sleep(config.start_wait_time)
        db.set_user_attribute(user_tg_id = user_id, key = "prev_msg_answered", value = True)    
    else:
        await register_user_if_not_exist(update, context, user = update.effective_user , user_id = user_id, chat_id=chat_id)
    
    
    await db_msg_delete("msg_id_with_kb", user_id, chat_id, context)
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    
    
    msg = await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=PATH_TO_MAIN_MENU_PICTURE,
                                reply_markup= kb.start_menu(db.get_balance_USD(user_id)),
                                disable_notification=True,
                            )
    db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb




# Move to main menu in all cases except /start (in case when update.message.from_user is NoneType)
async def back_to_main_menu(update: Update, context: CallbackContext, user_id: int, chat_id: int) -> None:
    if update is None:
        return
    
    if not await prev_msg_answered(user_id = user_id, context = context, chat_id = chat_id):
        return
    
    # Remove keyboard
    try:
        await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id = db.get_attribute(from_="users", value=user_id, select = "msg_id_with_kb"))
    except: pass
    
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    await db_msg_delete("invoice_msg_id", user_id, chat_id, context)
    
    db.end_dialog(user_tg_id=user_id)
    
    msg = await context.bot.send_photo(
        chat_id=chat_id,
        photo=PATH_TO_MAIN_MENU_PICTURE,
        reply_markup = kb.start_menu(db.get_balance_USD(user_id)),
        disable_notification=True,
    )
    db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb



async def invoice_handler(update: Update, context: CallbackContext) -> None:
    if update is None:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not await prev_msg_answered(user_id = user_id, context = context, chat_id = chat_id):
        await delete_message(chat_id=chat_id, message_id = update.message.id, context=context)
        return
    
    msg_id_with_kb = db.get_attribute(from_="users", value=user_id, select = "msg_id_with_kb")
    if db.get_attribute(from_ = "users", value=user_id, select="current_dialog_id") == -1:
        await delete_message(chat_id=chat_id, message_id = msg_id_with_kb, context=context)
    else:
        try: await context.bot.edit_message_reply_markup(chat_id = chat_id, message_id=msg_id_with_kb, reply_markup=None)
        except: pass
    
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    await db_msg_delete("invoice_msg_id", user_id, chat_id, context)
    
    
    # delete /pay 10 text itself
    await delete_message(chat_id=chat_id, message_id = update.message.id, context=context)
    
    data = update.message.text.strip().split()  # ['/pay', '10']
    
    try:
        user_amount = float(data[1])
        if user_amount <= config.payments_MIN_INVOICE_USDT or data[0] != '/pay' or len(data)!=2:
            raise ValueError(data)
        if user_amount == int(user_amount):
            user_amount = int(user_amount)
    except:
        error_msg = await context.bot.send_message(chat_id=chat_id, text=INVALID_USAGE_OF_PAY_TEXT)
        db.set_user_attribute(user_tg_id=user_id, key = "invoice_msg_id", value = error_msg.id)
        return
    
    # Generate the request signature
    sign_data = config.payments_CURRENCY + str(user_amount) + config.payments_HEADER + config.payments_DESCRIPTION
    signature = hmac.new(bytes(config.payments_API_KEY, 'utf-8'), bytes(sign_data, 'utf-8'), hashlib.sha256).hexdigest()

    payload = {
        "payment_currencies": config.payments_PAYMENT_CURRENCIES,
        "currency": config.payments_CURRENCY,
        "amount": user_amount,
        "description": config.payments_DESCRIPTION,
        "header": config.payments_HEADER,
        "payer": config.payments_PAYER,
        "is_convert_payments": config.payments_IS_CONVERT_PAYMENTS,
        "data": config.payments_DATA,
        "sign": signature
    }
    
    response = requests.post(config.payments_URL, headers=config.payments_headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        reply = response.json()
        if reply["result"] == 'success':
            db.create_invoice(user_tg_id = user_id, invoice_id=reply["id"], amount = user_amount, currency= config.payments_CURRENCY)
            invoice_msg = await context.bot.send_message(chat_id=chat_id, text=INVOICE_MSG_TEXT.format(user_amount), reply_markup = kb.payment_button(payment_link = reply["link"]))
            db.set_user_attribute(user_tg_id=user_id, key = "invoice_msg_id", value = invoice_msg.id)
            return
    
    db.insert_error(response.text)
    await start_handle(update, context)





async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    if update is None:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    query = update.callback_query
    
    await query.answer() # prevents errors

    callback = json.loads(query.data)
    
    from_ = callback["from"]
    to_ = callback.get("to")
    model_ = callback.get("model")
    
    # If responce is awaited do not answer
    if not await prev_msg_answered(user_id = user_id, context = context, chat_id = chat_id):
        return
    
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    await db_msg_delete("invoice_msg_id", user_id, chat_id, context)
    
    if to_ == "balance":
        msg = await context.bot.send_message(chat_id = chat_id, text = HOW_TO_TOP_UP_TEXT)
        db.set_user_attribute(user_tg_id=user_id, key = "invoice_msg_id", value = msg.id)
    
    # from MAIN MENU to CHOOSE MODEL
    elif from_ == "main_menu" and to_ == "choose_model":
        await query.edit_message_media(media=CHOOSE_MODEL_PICTURE, reply_markup=kb.choose_model()) # edit does not change the message_id -> no need to change message_id_with_kb

    # to MAIN MENU
    elif to_ == "main_menu":
        if from_ == "ch_m":
            await query.edit_message_media(media=MAIN_MENU_PICTURE, reply_markup= kb.start_menu(db.get_balance_USD(user_id)))  # edit does not change the message_id -> no need to change message_id_with_kb
        elif from_ == "gpt_resp":
            await query.edit_message_reply_markup(reply_markup=None)
            # Back to main menu ends dialog automatically
            await back_to_main_menu(update = update, context = context, user_id=user_id, chat_id=chat_id)
        elif from_ == "payment_button":
            # delete original message
            await delete_message(chat_id=chat_id, message_id = query.message.message_id, context=context)
            await back_to_main_menu(update = update, context = context, user_id=user_id, chat_id=chat_id)
        else:
            raise ValueError(f"Unknown from_ {from_} to_ = {to_}")
    
    # from CHOOSE MODEL to CHAT with GPT
    elif from_== "ch_m" and model_ in ["free_GPT", "oai_4_t"]:
        # Delete CHOOSE MODEL menu
        await delete_message(chat_id=chat_id, message_id = query.message.message_id, context=context)

        chat_msg_with_kb = await context.bot.send_message(
                            chat_id = chat_id, 
                            text = START_CHAT_MESSAGE.format(get_user_friendly_model_name[model_]),
                            reply_markup=kb.main_menu_only()
                        )
        
        # Initialize the dialog in dialog_db
        # Update dialog_id, model, msg_id_with_kb in user
        db.start_new_dialog(user_tg_id=user_id, model=model_, msg_id_with_kb=chat_msg_with_kb.id) # Initialize the dialog in the "dialog" db + Hash (dialog_id) goes to the user's dict in the "user" db and the current model is saved
    
    # from CHAT to NEW CHAT
    elif from_ == "gpt_resp" and to_ == "new_chat":
        # Safe remove inline keyboard from the last response message
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Ends current dialogue in DB
        db.end_dialog(user_tg_id=user_id)
        
        chat_msg_with_kb = await context.bot.send_message(
                                    chat_id = chat_id, 
                                    text = START_CHAT_MESSAGE.format(get_user_friendly_model_name[model_]),
                                    reply_markup=kb.main_menu_only()
                                )

        # Initialize the dialog in dialog_db
        # Hash (dialog_id), model, msg_id_with_kb goes to user_db
        db.start_new_dialog(user_tg_id=user_id, model=model_ , msg_id_with_kb=chat_msg_with_kb.id)
    
    
    # from CHAT to REGENERATE
    elif from_ == "gpt_resp" and to_ == "gpt_regen":
        # No need to remove inline keyboard IN GENERAL CASE as it will be done in message_handle()
        
        # Check if previous dialog is not empty
        dialog_messages = db.get_dialog_messages(user_tg_id=user_id)
        if not dialog_messages:
            await context.bot.send_message(chat_id, NO_DIALOGUE_MESSAGE)
            return
        
        # delete last dialogue message
        db.delete_last_answer_from_current_dialogue(user_tg_id=user_id)
        
        await message_handle(update, context, message=dialog_messages[-1]["user"])
    
    # Wrong Button
    else:
        if config.production != True: print(f"Unknown button: from_ {from_}, to {to_}")
        await start_handle(update, context)        





async def message_handle(update: Update, context: CallbackContext, message=None):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Сheck if message is edited (to avoid AttributeError: 'NoneType' object has no attribute 'from_user')
    if update.edited_message or update.message is None:
        return
    
    # Check is the prevoius dialog message is answered if not-delete message from the user
    if not await prev_msg_answered(user_id = user_id, context = context, chat_id = chat_id):
        await delete_message(chat_id=chat_id, message_id = update.message.id, context=context)
        return
    
    # Check that message is not empty    
    _message = message or update.message.text # "Привет" <class 'str'>. update.message.text is used as message is usually None
    if not _message or len(_message) == 0:
        await context.bot.send_message(chat_id=chat_id, text = NO_MESSAGE_MESSAGE)
        return

    # Check for the right mode    
    current_dialog_id = db.get_attribute(from_ = "users", value=user_id, select="current_dialog_id")
    if current_dialog_id == -1: # current_dialog_id = -1 if end_dialog() was triggered
        await delete_message(chat_id=chat_id, message_id = update.message.id, context=context)
        return
    
    current_model = db.get_attribute(from_ = "dialogues", select="model", where='id', value = current_dialog_id)
    
    # AFTER ALL CHECKS set prev_msg_answered to False
    db.set_user_attribute(user_tg_id = user_id, key = "prev_msg_answered", value = False)   
    
    # Safe remove inline keyboard from the last chatGPT response message
    msg_id_with_kb = db.get_attribute(from_ = "users", value = user_id, select="msg_id_with_kb")
    await context.bot.edit_message_reply_markup(chat_id = chat_id, message_id=msg_id_with_kb, reply_markup=None)
    
    dialog_messages = db.get_dialog_messages(current_dialog_id=current_dialog_id)

    # Delete start dialogue message
    await db_msg_delete("start_dialogue_msg_id", user_id, chat_id, context)
    await db_msg_delete("invoice_msg_id", user_id, chat_id, context)

    
    # Respond to message with FREE_GPT
    async def g4f_message_handle():
        placeholder_message = await context.bot.send_message(chat_id=chat_id, text = FREE_GPT_PLACEHOLDER_MESSAGE)
        
        status, answer = await g4f_connector.FreeChatGPT(model=current_model).send_message_stream(_message, dialog_messages=dialog_messages)

        answer = answer[:4096]
        
        # update messages in DB
        db.add_message_to_dialogue(current_dialog_id=current_dialog_id, user_message=_message, bot_message=answer)
        
        # Safe message edit
        edit = await context.bot.edit_message_text(
                                                    answer, 
                                                    chat_id=chat_id,
                                                    message_id=placeholder_message.message_id,
                                                    reply_markup=kb.gpt_responce(model=current_model)
                                                    )
        
        db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = edit.id) # sets last message with kb
    
    
    # Respond to message with GOOGLE GEMINI
    async def gemini_message_handle():
        answer, prev_answer = "", ""
        
        placeholder_message = await context.bot.send_message(chat_id=chat_id, text = FREE_GPT_PLACEHOLDER_MESSAGE)
        
        gen = gemini_connector.Gemini(model=current_model).send_message_stream(_message, dialog_messages=dialog_messages)

        async for gen_item in gen:
            answer = gen_item
            
            answer = answer[:4096]  # telegram message limit

            if prev_answer==answer:
                await asyncio.sleep(0.5)  # wait a bit to avoid flooding
                continue
            
            await context.bot.edit_message_text(answer, chat_id=chat_id, message_id=placeholder_message.message_id)
            
            prev_answer = answer
        
        
        # update messages in DB
        db.add_message_to_dialogue(current_dialog_id=current_dialog_id, user_message=_message, bot_message=answer)
        
        # Safe message edit
        edit = await context.bot.edit_message_reply_markup(
                                                    chat_id=chat_id,
                                                    message_id=placeholder_message.message_id,
                                                    reply_markup=kb.gpt_responce(model=current_model),
                                                    )
        
        db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = edit.id) # sets last message with kb
    
    
    
    # Respond to message with OpenAI model
    async def openai_message_handle():
        # too low money for dialog start
        user_balance = db.get_balance_USD(user_tg_id = user_id)
        if user_balance <= config.min_balance_to_start_chat_USD:
            await context.bot.send_message(chat_id, NOT_ENOUGH_MONEY_MESSAGE.format(user_balance))
            return
        
        n_input_tokens, n_output_tokens = 0, 0
        answer, prev_answer = "", ""
        
        placeholder_message = await context.bot.send_message(chat_id=chat_id, text = PAID_MODELS_PLACEHOLDER_MESSAGE_TEXT, protect_content = True)
        
        gen = openai_connector.ChatGPT(model=current_model).send_message_stream(_message, dialog_messages=dialog_messages)
        
        async for gen_item in gen:
            answer, n_input_tokens, n_output_tokens, n_first_dialog_messages_removed = gen_item
            
            answer = answer[:4096]  # telegram message limit
            
            if prev_answer==answer:
                await asyncio.sleep(0.5)  # wait a bit to avoid flooding
                continue
            
            await context.bot.edit_message_text(answer, chat_id=chat_id, message_id=placeholder_message.message_id)
            
            prev_answer = answer
        
        
        # update messages in DB
        db.add_message_to_dialogue(current_dialog_id=current_dialog_id, user_message=_message, bot_message=answer)
        
        new_balance = db.update_n_used_tokens_and_balance_USD(user_tg_id = user_id, current_model_as_in_keyboard = current_model, n_input_tokens = n_input_tokens, n_output_tokens = n_output_tokens, current_dialog_id=current_dialog_id, current_model=current_model)
        
        # After the responce is complete, edit the message reply markup to get inline buttons
        edit_kb = await context.bot.edit_message_reply_markup(
                                                    chat_id=chat_id,
                                                    message_id=placeholder_message.message_id, 
                                                    reply_markup=kb.gpt_responce(model=current_model, balance_USD = new_balance),
                                                )
        db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = edit_kb.id) # sets last message with kb
    
    
    
    
    try:
        if current_model == "free_4":
            task = asyncio.create_task(g4f_message_handle())
        elif current_model == "gemini-pro":
            task = asyncio.create_task(gemini_message_handle())
        elif current_model == "oai_4_t":
            task = asyncio.create_task(openai_message_handle())
        else:
            raise ValueError(f"current_model = {current_model}")
        
        await task
    
    except:
        error = str(traceback.format_exc())
        if config.production != True: print(error)
        db.set_user_attribute(user_tg_id = user_id, key = "prev_msg_answered", value = True)
        db.insert_error(error)
        await context.bot.send_message(chat_id=chat_id, text = FAIL_TO_GENERATE_RESP_MESSAGE)
        # back_to_main_menu ends the dialogue
        await back_to_main_menu(update = update, context = context, user_id=user_id, chat_id=chat_id)
        return
    
    
    db.set_user_attribute(user_tg_id = user_id, key = "prev_msg_answered", value = True)







async def post_init(application: Application):
    await application.bot.set_my_commands([]) # hide default blue menu button to the left of the keyboard with commands list




async def error_handle(update: Update, context: CallbackContext) -> None:
    error = str(traceback.format_exc())
    if config.production != True: print(error)
    db.insert_error(error)
    await start_handle(update, context)






def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )


    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handle))


    application.add_handler(CommandHandler("start", start_handle))
    application.add_handler(CommandHandler("pay", invoice_handler))

    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
    
    application.add_error_handler(error_handle)


    application.run_polling()





# Delete dialogue history from these models
LIST_OF_FREE_GPTS = [
    "free_4",
    "gemini-pro"
]


get_user_friendly_model_name = {
    "gemini-pro" : "Google Gemini Pro",
    "free_4" : "Free Chat GPT-4",
    "oai_4_t" : "OpenAI GPT-4 Turbo"
}




NOT_ENOUGH_MONEY_MESSAGE = "На Вашем счёте {} RUB что не достаточно для начала нового диалога.\nПополните баланс."
START_CHAT_MESSAGE = "New Chat has been started!\nHello, I am the {} model!\nAsk me whatever you want on any language!\n(type the question in the chat)"
NO_DIALOGUE_MESSAGE = "You have not started any dialogue yet🤷‍♂️\nType your question in the chat!"
WAIT_FOR_PREV_QUESTION_TO_ANSWER_MESSAGE = "Wait for an answer ⏳"
NO_MESSAGE_MESSAGE = "Your message is empty 🥲"
WRONG_CURRENCY_MESSAGE = "Ваша валюта оплаты ({}) не Российский RUB.\nНапишите в поддержку и мы вам поможем!"
FAIL_TO_GENERATE_RESP_MESSAGE = "Something went wrong 🥲\nPlease try again or contact the Support."
FREE_GPT_PLACEHOLDER_MESSAGE = "Wait for the answer.\nThank you for your patience..."
FREE_TEXT_TO_IMG_PLACEHOLDER_MESSAGE = "Please hold on for the image.\nIn the absence of traffic, it should arrive in about 20 seconds.\nWe appreciate your patience."
PAID_MODELS_PLACEHOLDER_MESSAGE_TEXT = "(Для экономии баланса чаще нажимайте кнопку 'Новый чат'.\nОна сбрасывает контекст, уменьшая ваш вопрос (контекст считается как чать вопроса))\n..."
SERVERS_ARE_BUSY_TEXT = "Currently, we're facing increased traffic.\nPlease click 'Regenerate' to check if the server is available."
START_WAIT_TEXT = "The /start command has been activated (likely due to the internal error).\nThe bot will be reset to get rid of errors.\nPlease wait for {} seconds.\nThank you!"
HOW_TO_TOP_UP_TEXT = "To add funds to your account, use the /pay command followed by the amount in USD.\nFor instance, /pay 10 will generate an invoice for $10.\nIf you lack cryptocurrency but wish to top up, write to Support."
INVALID_USAGE_OF_PAY_TEXT = "You have used /pay command incorrectly.\nMin. top-up is $4.\nAn example how to top up by $10:\n/pay 10"
INVOICE_MSG_TEXT = "Your invoice for ${}"

PATH_TO_MAIN_MENU_PICTURE = path.join("assets", "main_menu.png")
MAIN_MENU_PICTURE = InputMediaPhoto(media=open(PATH_TO_MAIN_MENU_PICTURE, 'rb'))

PATH_TO_CHOOSE_MODEL_PICTURE = path.join("assets", "choose_model.png")
CHOOSE_MODEL_PICTURE = InputMediaPhoto(media=open(PATH_TO_CHOOSE_MODEL_PICTURE, 'rb'))


db = database.Database()
client = plisio.PlisioAioClient(api_key=config.pliso_api_secret)

if __name__ == "__main__":
    run_bot()