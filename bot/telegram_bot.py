import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, JobQueue
import joblib
import pandas as pd
from src import utils, preprocessing as p
from scipy.sparse import hstack
from dotenv import load_dotenv
import re
import csv
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or 'PASTE_YOUR_TOKEN_HERE'

ps = utils.get_paths()
m = joblib.load(ps['model'])
v = joblib.load(ps['vectorizer'])

chat_modes = {}
votes = {}
VOTE_THRESHOLD = 1
known_chats = {}
template_topics = set()
template_hint_mode = {}
vote_message_texts = {}

logging.basicConfig(level=logging.INFO)

MENU, CHOOSE_GROUP, CHOOSE_MODE, CHOOSE_GROUP_HINT = range(4)

TEMPLATE_REGEX = re.compile(r'^#\S+.*?(?:\n|\s)+.*?(координатор:?|Координатор:?|координатор:?|КООРДИНАТОР:?)[ ]*[^\n]+$', re.DOTALL)
TEMPLATE_EXAMPLE = '#Ваша_услуга Текст объявления\nКоординатор: Имя'

HINT_DELETE_DELAY = 300

VOTE_LOG_PATH = 'bot_votes.csv'

def log_vote_result(text, label, user_id=None):
    file_exists = os.path.isfile(VOTE_LOG_PATH)
    with open(VOTE_LOG_PATH, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['text', 'label', 'user_id'])
        writer.writerow([text, label, user_id])

async def check_spam(text):
    x = p.clean_text(text)
    d = pd.DataFrame({'text': [x]})
    f = p.extract_features(d.copy())
    X = v.transform(f['text'])
    add = f[[c for c in f.columns if c != 'text']].values
    Xf = hstack([X, add])
    pr = m.predict(Xf)[0]
    proba = m.predict_proba(Xf)[0]
    cl = list(m.classes_)
    return pr == 'spam', proba[cl.index('spam')]

#PRIVATE CHAT HANDLERS
async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton('/guide'), KeyboardButton('/settings')],
    ]
    await update.message.reply_text(
        'Приветствую! Я многофункциональый бот для Telegram-групп.\n\n'
        'Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return MENU

async def guide_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Справочник\n\n'
        '• /start — главное меню\n'
        '• /guide — руководство по пользованию\n'
        '• /settings — переход к возможностям бота.\n'
        '\nМои возможности\n\n'
        '1. автоматически удаляю спам или запускаю голосование\n'
        '2. удаляю сообщения в темах, где включен шаблон\n'
        '(админ может отправить команду /settemplate в тему чата, чтобы включить)\n\n'
        f'   {TEMPLATE_EXAMPLE}\n'
        '\nМожно выбрать, куда я отправлю подсказку неправильно написавшему текст человеку.\n'
        '3. проверяю текст на спам\n'
        '\n'
    )
    return MENU

async def settings_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton('/spamsettings'), KeyboardButton('/templatehintsettings')],
    ]
    await update.message.reply_text(
        'Настройки:\n'
        '• /spamsettings — настройка режима спама (автоудаление/голосование)\n'
        '• /templatehintsettings — настройка способа подсказки шаблона\n'
        'Выберите, что хотите настроить:',
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return MENU

async def spamsettings_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not known_chats:
        await update.message.reply_text('Пока я не был добавлен ни в одну группу или не видел сообщений в группах.')
        return MENU
    buttons = [[KeyboardButton(f'/group_{chat_id}')] for chat_id in known_chats.keys()]
    await update.message.reply_text(
        'Выберите группу для настройки из предложенных:',
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    )
    return CHOOSE_GROUP

async def templatehintsettings_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Для настройки способа подсказки используйте команду:\n/templatehint <режим>\n'
        'где <режим> — private (подсказка отправляется лично пользователю, если он разрешил мне писать), chat (подсказка отправляется в общий чат), both (если я не могу написать пользователю лично, я напишу подсказку в общий чат).\n'
        '\nНапример: /templatehint both'
    )
    return MENU

async def choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.startswith('/group_'):
        await update.message.reply_text('Выберите группу для настройки из предложенных:')
        return CHOOSE_GROUP
    try:
        chat_id = int(text[7:])
    except Exception:
        await update.message.reply_text('Некорректная команда.')
        return CHOOSE_GROUP
    if chat_id not in known_chats:
        await update.message.reply_text('Пока я не был добавлен ни в одну группу или не видел сообщений в группах.')
        return CHOOSE_GROUP
    try:
        member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if member.status not in ('administrator', 'creator'):
            await update.message.reply_text('Вы не админ/владелец этой группы.')
            return MENU
    except Exception as e:
        await update.message.reply_text('Не удалось проверить ваши права в группе.')
        return MENU
    cur_mode = chat_modes.get(chat_id, 'auto')
    btns = [[KeyboardButton('/setmode_auto')], [KeyboardButton('/setmode_vote')]]
    context.user_data['chosen_chat_id'] = chat_id
    await update.message.reply_text(
        f'Текущий режим: {"автоудаление" if cur_mode=="auto" else "голосование"}.\n'
        'Выберите новый режим:',
        reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True, one_time_keyboard=True)
    )
    return CHOOSE_MODE

async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = context.user_data.get('chosen_chat_id')
    if not chat_id:
        await update.message.reply_text('Ошибка выбора группы. Начните заново.')
        return MENU
    if text == '/setmode_auto':
        chat_modes[chat_id] = 'auto'
        await update.message.reply_text('Режим для группы изменён на автоудаление.')
    elif text == '/setmode_vote':
        chat_modes[chat_id] = 'vote'
        await update.message.reply_text('Режим для группы изменён на голосование.')
    else:
        await update.message.reply_text('Пожалуйста, выберите режим через команду.')
        return CHOOSE_MODE
    return MENU

async def templatehint_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not known_chats:
        await update.message.reply_text('Пока я не был добавлен ни в одну группу или не видел сообщений в группах.')
        return MENU
    if not context.args or context.args[0] not in ('private', 'chat', 'both'):
        await update.message.reply_text('Используйте: /templatehint private|chat|both')
        return MENU
    mode = context.args[0]
    buttons = [[KeyboardButton(f'/group_{chat_id}')] for chat_id in known_chats.keys()]
    await update.message.reply_text(
        f'Выберите группу, для которой хотите установить режим подсказки ({mode}):',
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    )
    context.user_data['hint_mode_to_set'] = mode
    return CHOOSE_GROUP_HINT

async def choose_group_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.startswith('/group_'):
        await update.message.reply_text('Пожалуйста, выберите группу через команду.')
        return CHOOSE_GROUP_HINT
    try:
        chat_id = int(text[7:])
    except Exception:
        await update.message.reply_text('Некорректная команда.')
        return CHOOSE_GROUP_HINT
    if chat_id not in known_chats:
        await update.message.reply_text('Группа не найдена.')
        return CHOOSE_GROUP_HINT
    try:
        member = await context.bot.get_chat_member(chat_id, update.effective_user.id)
        if member.status not in ('administrator', 'creator'):
            await update.message.reply_text('Вы не админ/владелец этой группы.')
            return MENU
    except Exception as e:
        await update.message.reply_text('Не удалось проверить ваши права в группе.')
        return MENU
    mode = context.user_data.get('hint_mode_to_set', 'private')
    template_hint_mode[chat_id] = mode
    await update.message.reply_text(f'Режим подсказки для группы {known_chats[chat_id]} установлен: {mode}')
    return MENU

#GROUP CHAT HANDLERS
async def settemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message
    thread_id = getattr(msg, 'message_thread_id', None)
    if not user or not chat or not thread_id:
        await update.message.reply_text('Эту команду можно использовать только в теме группы.')
        return
    member = await chat.get_member(user.id)
    if member.status not in ('administrator', 'creator'):
        await update.message.reply_text('Только админ может включить шаблон для темы.')
        return
    template_topics.add((chat.id, thread_id))
    await update.message.reply_text(f'В этой теме теперь разрешены только сообщения по шаблону: {TEMPLATE_EXAMPLE}')

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    thread_id = getattr(msg, 'message_thread_id', None)
    if not msg or not chat or not msg.text:
        return
    known_chats[chat.id] = chat.title or str(chat.id)
    if thread_id and (chat.id, thread_id) in template_topics:
        if not TEMPLATE_REGEX.match(msg.text.strip()):
            mode = template_hint_mode.get(chat.id, 'both')
            user_mention = msg.from_user.mention_html() if msg.from_user else 'Пользователь'
            hint_message = None
            sent = False
            hint_kwargs = dict()
            if thread_id:
                hint_kwargs['message_thread_id'] = thread_id
            if mode == 'both':
                try:
                    await context.bot.send_message(
                        msg.from_user.id,
                        f'Здравствуйте! Формат вашего сообщения в чате не соответствует правилам темы.\nПожалуйста, напишите его согласно примеру:\n {TEMPLATE_EXAMPLE}',
                    )
                    sent = True
                except Exception:
                    hint_message = await context.bot.send_message(
                        chat.id,
                        f'{user_mention}, формат вашего сообщения не соответствует правилам темы.\nПожалуйста, напишите его согласно примеру:\n {TEMPLATE_EXAMPLE}',
                        parse_mode='HTML',
                        **hint_kwargs
                    )
            elif mode == 'private':
                try:
                    await context.bot.send_message(
                        msg.from_user.id,
                        f'{user_mention}, формат вашего сообщения не соответствует правилам темы.\nПожалуйста, напишите его согласно примеру:\n {TEMPLATE_EXAMPLE}',
                    )
                except Exception:
                    pass
            elif mode == 'chat':
                hint_message = await context.bot.send_message(
                    chat.id,
                    f'{user_mention}, формат вашего сообщения не соответствует правилам темы.\nПожалуйста, напишите его согласно примеру:\n {TEMPLATE_EXAMPLE}',
                    parse_mode='HTML',
                    **hint_kwargs
                )
            try:
                await msg.delete()
            except Exception:
                pass
            if hint_message:
                context.job_queue.run_once(lambda ctx: ctx.bot.delete_message(chat.id, hint_message.message_id), HINT_DELETE_DELAY)
            return
    #проверка на спам
    mode = chat_modes.get(chat.id, 'auto')
    is_spam, prob = await check_spam(msg.text)
    if not is_spam:
        return
    if mode == 'auto':
        try:
            log_vote_result(msg.text, 'spam', getattr(msg.from_user, 'id', None))
            await msg.delete()
        except Exception as e:
            logging.warning(f'Не удалось удалить: {e}')
    else:
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('СПАМ', callback_data=f'spam|{msg.message_id}')],
            [InlineKeyboardButton('НЕ СПАМ', callback_data=f'ham|{msg.message_id}')]
        ])
        await context.bot.send_message(chat.id, f'Это сообщение — спам?', reply_markup=kbd, reply_to_message_id=msg.message_id)
        votes[(chat.id, msg.message_id)] = set()
        vote_message_texts[(chat.id, msg.message_id)] = (msg.text, getattr(msg.from_user, 'id', None))

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    data = query.data
    if not data or '|' not in data:
        return
    vote, msg_id = data.split('|', 1)
    msg_id = int(msg_id)
    key = (chat.id, msg_id)
    if vote == 'spam':
        votes.setdefault(key, set()).add(user.id)
        if len(votes[key]) >= VOTE_THRESHOLD:
            try:
                text, author_id = vote_message_texts.get(key, (None, None))
                try:
                    await context.bot.delete_message(chat.id, msg_id)
                except Exception:
                    pass
                try:
                    await query.message.delete()
                except Exception:
                    pass
                if text:
                    log_vote_result(text, 'spam', author_id)
                vote_message_texts.pop(key, None)
            except Exception as e:
                logging.warning(f'Ошибка удаления по голосованию: {e}')
            votes.pop(key, None)
        else:
            await query.answer(f'Голос учтён ({len(votes[key])}/{VOTE_THRESHOLD})')
    else:
        ham_key = ('ham', key)
        votes.setdefault(ham_key, set()).add(user.id)
        if len(votes[ham_key]) >= VOTE_THRESHOLD:
            try:
                text, author_id = vote_message_texts.get(key, (None, None))
                try:
                    await query.message.delete()
                except Exception:
                    pass
                if text:
                    log_vote_result(text, 'ham', author_id)
                vote_message_texts.pop(key, None)
            except Exception as e:
                logging.warning(f'Ошибка удаления сообщения с голосованием: {e}')
            votes.pop(ham_key, None)
        else:
            await query.answer(f'Голос учтён ({len(votes[ham_key])}/{VOTE_THRESHOLD})')

async def delete_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #команда /delete
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg.reply_to_message:
        return
    try:
        member = await chat.get_member(user.id)
        if member.status not in ('administrator', 'creator'):
            return
    except Exception:
        return
    target_msg = msg.reply_to_message
    try:
        await target_msg.delete()
        log_vote_result(target_msg.text, 'spam', getattr(target_msg.from_user, 'id', None))
        await msg.delete()
    except Exception as e:
        pass

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    #PRIVATE CHAT
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start_private)],
        states={
            MENU: [CommandHandler('guide', guide_private), CommandHandler('settings', settings_private), CommandHandler('spamsettings', spamsettings_private), CommandHandler('templatehintsettings', templatehintsettings_private), CommandHandler('templatehint', templatehint_private)],
            CHOOSE_GROUP: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_group)],
            CHOOSE_MODE: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_mode)],
            CHOOSE_GROUP_HINT: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_group_hint)],
        },
        fallbacks=[CommandHandler('start', start_private)],
    )
    app.add_handler(conv)
    #GROUP CHAT
    app.add_handler(CommandHandler('settemplate', settemplate))
    app.add_handler(CommandHandler('delete', delete_message_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.ChatType.PRIVATE), handle_group_message))
    app.add_handler(CallbackQueryHandler(vote_callback))
    print('Бот запущен!')
    app.run_polling()

