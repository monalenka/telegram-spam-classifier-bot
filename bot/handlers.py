import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, InputFile
)
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, CommandHandler, ConversationHandler
from config import *
from storage import *
from utils import *
from scheduler import content_scheduler

logger = logging.getLogger(__name__)

async def spam_exceptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('|')
    if len(parts) < 3:
        await query.edit_message_text("❌ Ошибка: неверный формат команды.")
        return SPAM_EXCEPTIONS_MENU
    
    action = parts[1]
    chat_id = int(parts[2]) if len(parts) > 2 else None
    
    if action == 'show':
        exceptions_text = get_spam_exceptions_text(chat_id)
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data=f"exceptions|add|{chat_id}")],
            [InlineKeyboardButton("➖ Удалить", callback_data=f"exceptions|remove|{chat_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"settings|pick_group|{chat_id}")]
        ]
        await query.edit_message_text(
            f"{exceptions_text}\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SPAM_EXCEPTIONS_MENU
    
    elif action == 'add':
        await query.edit_message_text(
            "Введите @никнеймы пользователей через запятую (например, @user1, @user2):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"exceptions|show|{chat_id}")]])
        )
        context.user_data['exceptions_chat_id'] = chat_id
        context.user_data['exceptions_action'] = 'add'
        return ADD_EXCEPTIONS
    
    elif action == 'remove':
        await query.edit_message_text(
            "Введите @никнеймы пользователей через запятую для удаления (например, @user1, @user2):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"exceptions|show|{chat_id}")]])
        )
        context.user_data['exceptions_chat_id'] = chat_id
        context.user_data['exceptions_action'] = 'remove'
        return REMOVE_EXCEPTIONS
    
    return SPAM_EXCEPTIONS_MENU

async def add_exceptions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    chat_id = context.user_data.get('exceptions_chat_id')
    if not chat_id:
        await update.message.reply_text('❌ Ошибка: чат не найден.')
        return SPAM_EXCEPTIONS_MENU
    
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text('❌ Введите никнеймы пользователей.')
        return ADD_EXCEPTIONS
    
    usernames = [username.strip() for username in text.split(',') if username.strip()]
    added_count = add_spam_exceptions(chat_id, usernames)
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    exceptions_text = get_spam_exceptions_text(chat_id)
    keyboard = [
        [InlineKeyboardButton("➕ Добавить", callback_data=f"exceptions|add|{chat_id}")],
        [InlineKeyboardButton("➖ Удалить", callback_data=f"exceptions|remove|{chat_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"settings|pick_group|{chat_id}")]
    ]
    
    result_message = f"✅ Список исключений обновлен. Добавлено {added_count} пользователей.\n\n{exceptions_text}"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=result_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.pop('exceptions_chat_id', None)
    context.user_data.pop('exceptions_action', None)
    return SPAM_EXCEPTIONS_MENU

async def remove_exceptions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    chat_id = context.user_data.get('exceptions_chat_id')
    if not chat_id:
        await update.message.reply_text('❌ Ошибка: чат не найден.')
        return SPAM_EXCEPTIONS_MENU
    
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text('❌ Введите никнеймы пользователей.')
        return REMOVE_EXCEPTIONS
    
    usernames = [username.strip() for username in text.split(',') if username.strip()]
    removed_count = remove_spam_exceptions(chat_id, usernames)
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    exceptions_text = get_spam_exceptions_text(chat_id)
    keyboard = [
        [InlineKeyboardButton("➕ Добавить", callback_data=f"exceptions|add|{chat_id}")],
        [InlineKeyboardButton("➖ Удалить", callback_data=f"exceptions|remove|{chat_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"settings|pick_group|{chat_id}")]
    ]
    
    result_message = f"✅ Список исключений обновлен. Удалено {removed_count} пользователей.\n\n{exceptions_text}"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=result_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.pop('exceptions_chat_id', None)
    context.user_data.pop('exceptions_action', None)
    return SPAM_EXCEPTIONS_MENU

def _start_menu_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('Перейти в главное меню', callback_data='start|root')]])

def _escape_html(text: str) -> str:
    return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _build_daily_time_picker(hour: int, minute: int) -> InlineKeyboardMarkup:
    h = max(0, min(23, hour))
    m = max(0, min(59, minute))
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('−1ч', callback_data='tp|dh|-1h'),
            InlineKeyboardButton(f'{h:02d}:{m:02d}', callback_data='tp|noop'),
            InlineKeyboardButton('+1ч', callback_data='tp|dh|+1h'),
        ],
        [
            InlineKeyboardButton('−1м', callback_data='tp|dm|-1m'),
            InlineKeyboardButton('Подтвердить', callback_data='tp|daily_confirm'),
            InlineKeyboardButton('+1м', callback_data='tp|dm|+1m'),
        ],
        [
            InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|schedule'),
            InlineKeyboardButton('Отмена', callback_data='cmenu|back')
        ]
    ])

def _build_date_picker(day_offset: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('◀', callback_data='tp|day|-1'),
            InlineKeyboardButton(f'+{max(0, day_offset)} дн.', callback_data='tp|noop'),
            InlineKeyboardButton('▶', callback_data='tp|day|+1'),
        ],
        [InlineKeyboardButton('Далее: время ▶', callback_data='tp|to_time')],
        [
            InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|schedule'),
            InlineKeyboardButton('Отмена', callback_data='cmenu|back')
        ]
    ])

def _build_once_time_picker(hour: int, minute: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('−1ч', callback_data='tp|oh|-1h'),
            InlineKeyboardButton(f'{hour:02d}:{minute:02d}', callback_data='tp|noop'),
            InlineKeyboardButton('+1ч', callback_data='tp|oh|+1h'),
        ],
        [
            InlineKeyboardButton('−1м', callback_data='tp|om|-1m'),
            InlineKeyboardButton('Подтвердить', callback_data='tp|once_confirm'),
            InlineKeyboardButton('+1м', callback_data='tp|om|+1m'),
        ],
        [
            InlineKeyboardButton('⬅️ Назад', callback_data='tp|back_to_date'),
            InlineKeyboardButton('Отмена', callback_data='cmenu|back')
        ]
    ])

def get_next_send_datetime_str(content_id: str) -> str:
    schedules = content_scheduler.get_all_schedules()
    candidates = []
    now = get_novosibirsk_time().replace(second=0, microsecond=0)
    for sid, sch in schedules.items():
        if sch.get('content_id') != content_id:
            continue
        if 'send_datetime' in sch:
            try:
                dt = datetime.fromisoformat(sch['send_datetime']).replace(second=0, microsecond=0)
                if dt >= now:
                    candidates.append(dt)
            except Exception:
                continue
        elif sch.get('send_time'):
            try:
                t = datetime.strptime(sch['send_time'], '%H:%M').time()
                # Если weekly — ищем ближайший следующий день недели
                if sch.get('repeat_weekly') and sch.get('send_weekday') is not None:
                    target_wd = int(sch.get('send_weekday', 0))
                    # вычисляем ближайшую дату той недели
                    days_ahead = (target_wd - now.weekday()) % 7
                    dt = now.replace(hour=t.hour, minute=t.minute)
                    dt = dt + pd.Timedelta(days=days_ahead)
                    if dt < now:
                        dt = dt + pd.Timedelta(days=7)
                else:
                    dt = now.replace(hour=t.hour, minute=t.minute)
                    if dt < now:
                        dt = dt + pd.Timedelta(days=1)
                candidates.append(dt)
            except Exception:
                continue
    if not candidates:
        return '-'
    nxt = min(candidates)
    return nxt.strftime('%Y-%m-%d %H:%M')

def _recipients_for_content(content_id: str) -> str:
    try:
        schedules = content_scheduler.get_all_schedules()
        targets = []
        usernames_all = []
        for sid, sch in schedules.items():
            if sch.get('content_id') != content_id:
                continue
            t = sch.get('target', 'users')
            if t == 'specific':
                unames = sch.get('usernames', []) or []
                usernames_all.extend(unames)
            targets.append(t)
        if not targets:
            return '—'
        targets_set = set(targets)
        # Приоритет all
        if 'all' in targets_set:
            return 'все'
        parts = []
        if 'groups' in targets_set:
            parts.append('группы')
        if 'users' in targets_set:
            parts.append('пользователи')
        if 'specific' in targets_set:
            if usernames_all:
                show = ', '.join(['@'+u.lstrip('@') for u in usernames_all])
                parts.append(f'конкретные: {show}')
            else:
                parts.append('конкретные')
        return ', '.join(parts) if parts else '—'
    except Exception:
        return '—'




async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if content_scheduler.add_subscriber(user.id, user.username, user.first_name):
        await update.message.reply_text(
            '✅ Вы успешно подписались на рассылку!\n'
            'Теперь я буду присылать вам контент в установленное время.'
        )
    else:
        await update.message.reply_text('❌ Произошла ошибка при подписке. Попробуйте позже.')

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if content_scheduler.remove_subscriber(user.id):
        await update.message.reply_text('✅ Вы отписались от рассылки.')
    else:
        await update.message.reply_text('❌ Вы не были подписаны на рассылку.')

async def content_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU

    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
        [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
        [InlineKeyboardButton('⏰ Запланировать рассылку', callback_data='cmenu|schedule')],
        [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
        [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
    ])
    await update.message.reply_text('📋 Меню управления контентом', reply_markup=kbd)
    return CONTENT_MENU

async def content_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопок меню контента"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    data = query.data or ''
    parts = data.split('|')
    action = parts[1] if len(parts) > 1 else ''
    
    # Helper: delete previously listed content messages
    async def _cleanup_listed_messages():
        ids = context.user_data.pop('listed_msg_ids', [])
        for mid in ids:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=mid)
            except Exception:
                pass
    if parts[0] == 'start':
        # обработка стартового меню
        sub = action
        if sub == 'root':
            if is_admin(user.id):
                text = (
                    'Приветствую! Я многофункциональный бот для Telegram-групп.\n\n'
                    'Выберите действие:'
                )
                buttons = [
                    [InlineKeyboardButton('📖 Руководство', callback_data='start|guide'), InlineKeyboardButton('⚙️ Настройки', callback_data='start|settings')],
                    [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')],
                    [InlineKeyboardButton('🧰 Меню контента', callback_data='cmenu|root')]
                ]
            else:
                text = 'Приветствую! Я бот Русской Общины г. Томск. Подписаться на рассылку?'
                buttons = [
                    [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')]
                ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            return MENU
        if sub == 'guide':
            guide_text = (
                'Справочник\n\n'
                'Мои возможности\n\n'
                '1. автоматически удаляю спам или запускаю голосование (раздел Настройки)\n' 
                '2. удаляю сообщения в темах, где включен шаблон\n'
                f'(админ может отправить команду /settemplate в тему чата, чтобы включить, или /unsettemplate, чтобы убрать эту функцию)\n\n   {TEMPLATE_EXAMPLE}\n\n'
                'Можно выбрать, куда я отправлю подсказку неправильно написавшему текст человеку.\n'
                '3. удаляю и запоминаю спам-сообщение, если вы напишите /delete в ответ на него\n'
                '4. рассылаю контент подписчикам по расписанию (раздел Меню контента)\n'
            )
            buttons = [
                [InlineKeyboardButton('🧰 Меню контента', callback_data='cmenu|root')],
                [InlineKeyboardButton('⬅️ В начало', callback_data='start|root')],
            ]
            await query.edit_message_text(guide_text, reply_markup=InlineKeyboardMarkup(buttons))
            return MENU
        if sub == 'settings':
            if not is_admin(user.id):
                # Не-админам не показываем настройки
                await query.answer('Недоступно', show_alert=False)
                return MENU
            # Показать список групп для настройки
            if not known_chats:
                await query.edit_message_text('Нет известных групп. Напишите что-нибудь в группе, где есть бот.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ В начало', callback_data='start|root')]]))
                return MENU
            buttons = []
            for chat_id, title in known_chats.items():
                buttons.append([InlineKeyboardButton(title, callback_data=f'settings|pick_group|{chat_id}')])
            buttons.append([InlineKeyboardButton('⬅️ В начало', callback_data='start|root')])
            await query.edit_message_text('Выберите группу для настройки:', reply_markup=InlineKeyboardMarkup(buttons))
            return MENU
        if sub == 'subscribe':
            if content_scheduler.is_subscriber(user.id):
                await query.edit_message_text('ℹ️ Вы уже подписаны на рассылку.', reply_markup=_start_menu_btn())
            else:
                added = content_scheduler.add_subscriber(user.id, user.username, user.first_name)
                if added:
                    await query.edit_message_text('✅ Вы успешно подписались на рассылку!', reply_markup=_start_menu_btn())
                else:
                    await query.edit_message_text('❌ Не удалось подписаться. Попробуйте позже.', reply_markup=_start_menu_btn())
            return MENU
        if sub == 'unsubscribe':
            if not content_scheduler.is_subscriber(user.id):
                await query.edit_message_text('ℹ️ Вы уже отписаны от рассылки.', reply_markup=_start_menu_btn())
            else:
                removed = content_scheduler.remove_subscriber(user.id)
                if removed:
                    await query.edit_message_text('✅ Вы отписались от рассылки.', reply_markup=_start_menu_btn())
                else:
                    await query.edit_message_text('❌ Не удалось отписаться.', reply_markup=_start_menu_btn())
            return MENU

    # Settings callbacks
    if parts[0] == 'settings':
        sub = action
        # Выбор группы из настроек
        if sub == 'pick_group' and len(parts) > 2:
            if not is_admin(user.id):
                await query.answer('Недоступно', show_alert=False)
                return MENU
            try:
                chat_id = int(parts[2])
            except Exception:
                await query.answer('Некорректная группа', show_alert=False)
                return MENU
            title = known_chats.get(chat_id, str(chat_id))
            cur_spam = chat_modes.get(chat_id, 'auto')
            cur_hint = template_hint_mode.get(chat_id, 'both')
            # Для отображения both показываем как private
            display_hint = 'private' if cur_hint == 'both' else cur_hint
            # ЗАМЕНИТЬ существующую клавиатуру в разделе настроек группы:
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton(f'🧹 Режим спама: авто {"✅" if cur_spam=="auto" else ""}', callback_data=f'settings|spam|{chat_id}|auto'), InlineKeyboardButton(f'голосование {"✅" if cur_spam=="vote" else ""}', callback_data=f'settings|spam|{chat_id}|vote')],
                [InlineKeyboardButton(f'📋 Подсказка: chat {"✅" if cur_hint=="chat" else ""}', callback_data=f'settings|hint|{chat_id}|chat'), InlineKeyboardButton(f'private {"✅" if cur_hint=="both" else ""}', callback_data=f'settings|hint|{chat_id}|both')],
                [InlineKeyboardButton('🛡️ Исключения на спам', callback_data=f'settings|exceptions|{chat_id}')],  # НОВАЯ КНОПКА
                [InlineKeyboardButton('⬅️ Выбрать другую группу', callback_data='start|settings')]
            ])
            await query.edit_message_text(f'Настройки для группы: {title}', reply_markup=kbd)
            return MENU
        # Установка режима спама для выбранной группы
        if sub == 'spam' and len(parts) > 3:
            if not is_admin(user.id):
                await query.answer('Недоступно', show_alert=False)
                return MENU
            try:
                chat_id = int(parts[2])
            except Exception:
                await query.answer('Некорректная группа', show_alert=False)
                return MENU
            mode = parts[3]
            chat_modes[chat_id] = 'auto' if mode == 'auto' else 'vote'
            title = known_chats.get(chat_id, str(chat_id))
            await query.edit_message_text(
                f'✅ Для группы "{title}" установлен режим: {"автоудаление" if chat_modes[chat_id]=="auto" else "голосование"}',
                reply_markup=_start_menu_btn()
            )
            return MENU
        # Установка режима подсказки для выбранной группы
        if sub == 'hint' and len(parts) > 3:
            if not is_admin(user.id):
                await query.answer('Недоступно', show_alert=False)
                return MENU
            try:
                chat_id = int(parts[2])
            except Exception:
                await query.answer('Некорректная группа', show_alert=False)
                return MENU
            mode = parts[3]
            if mode not in ('chat','both'):
                await query.answer('Некорректный режим', show_alert=False)
                return MENU
            template_hint_mode[chat_id] = mode
            title = known_chats.get(chat_id, str(chat_id))
            display_mode = 'private' if mode == 'both' else mode
            await query.edit_message_text(
                f'✅ Для группы "{title}" установлен режим подсказки: {display_mode}',
                reply_markup=_start_menu_btn()
            )
            return MENU
        # Обработка исключений для группы
        if sub == 'exceptions' and len(parts) > 2:
            if not is_admin(user.id):
                await query.answer('Недоступно', show_alert=False)
                return MENU
            try:
                chat_id = int(parts[2])
            except Exception:
                await query.answer('Некорректная группа', show_alert=False)
                return MENU
        
            # Показываем меню исключений
            exceptions_text = get_spam_exceptions_text(chat_id)
            keyboard = [
                [InlineKeyboardButton("➕ Добавить", callback_data=f"exceptions|add|{chat_id}")],
                [InlineKeyboardButton("➖ Удалить", callback_data=f"exceptions|remove|{chat_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"settings|pick_group|{chat_id}")]
            ]
            await query.edit_message_text(
                f"{exceptions_text}\n\nВыберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return SPAM_EXCEPTIONS_MENU

    # Audience selection callbacks
    if parts[0] == 'aud':
        choice = action  # all|users|groups|specific
        cid = context.user_data.get('last_scheduled_content_id')
        if not cid:
            await query.answer('Нет запланированного контента.', show_alert=False)
            return CONTENT_MENU
        if choice == 'specific':
            await query.edit_message_text('Укажите @ники пользователей через запятую (например, @user1,@user2):')
            context.user_data['await_usernames'] = True
            return SCHEDULE_CONTENT
        # Для остальных — применяем сразу
        content_scheduler.update_latest_schedule_target(cid, choice)
        await query.edit_message_text('✅ Аудитория сохранена.', reply_markup=_start_menu_btn())
        context.user_data.pop('last_scheduled_content_id', None)
        return CONTENT_MENU

    if action == 'root':
        # показать корневое меню контента
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
            [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
            [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
        ])
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
            [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
            [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
        ])
        await query.edit_message_text('📋 Меню управления контентом', reply_markup=kbd)
        return CONTENT_MENU

    if action == 'back':
        # Возврат в главное меню (/start) и максимально чистый чат
        await _cleanup_listed_messages()
        try:
            header_id = context.user_data.pop('listed_header_id', None)
            if header_id:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=header_id)
        except Exception:
            pass
        try:
            await query.message.delete()
        except Exception:
            pass
        if is_admin(user.id):
            start_text = (
                'Приветствую! Я многофункциональный бот для Telegram-групп.\n\n'
                'Выберите действие:'
            )
            start_buttons = [
                [InlineKeyboardButton('📖 Руководство', callback_data='start|guide'), InlineKeyboardButton('⚙️ Настройки', callback_data='start|settings')],
                [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')],
                [InlineKeyboardButton('🧰 Меню контента', callback_data='cmenu|root')],
            ]
        else:
            start_text = 'Приветствую! Я бот Русской Общины г. Томск. Подписаться на рассылку?'
            start_buttons = [
                [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')],
            ]
        await context.bot.send_message(chat_id=query.message.chat_id, text=start_text, reply_markup=InlineKeyboardMarkup(start_buttons))
        return MENU

    if action == 'add':
        # Удалим сообщение с кнопками
        logging.info("Установка состояния ADD_CONTENT")
        try:
            await query.message.delete()
        except Exception:
            pass
        m = await context.bot.send_message(chat_id=query.message.chat_id, text='📝 Отправьте текст/фото/видео/аудио для добавления как контент.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')]]))
        # Сохраним id подсказки, чтобы удалить после загрузки
        context.user_data['add_prompt_message_id'] = m.message_id
        return ADD_CONTENT

    if action == 'list':
        if not content_scheduler.scheduled_content:
            await query.edit_message_text('📝 Контент не добавлен.', reply_markup=_start_menu_btn())
            return CONTENT_MENU
        await query.edit_message_text('🗂 Доступный контент:')
        context.user_data['listed_header_id'] = query.message.message_id
        # Отправляем каждый элемент отдельным сообщением в порядке добавления
        # Сортировка по created_at
        items = sorted(content_scheduler.scheduled_content.items(), key=lambda kv: kv[1].get('created_at', ''))
        listed_ids = []
        for content_id, content in items:
            name = content.get('custom_name', content_id)
            caption = content.get('caption') or ''
            next_dt = get_next_send_datetime_str(content_id)
            recipients = _recipients_for_content(content_id)
            header_html = (
                f'<i>Название:</i> {_escape_html(name)}\n'
                f'<i>ID:</i> {_escape_html(content_id)}\n'
                f'<i>Следующая отправка:</i> {_escape_html(next_dt)}\n'
                f'<i>Получатели:</i> {_escape_html(recipients)}'
            )
            try:
                if content['type'] == 'text':
                    m = await context.bot.send_message(chat_id=query.message.chat_id, text=f'{header_html}\n\n{_escape_html(content["path"]) }', parse_mode='HTML')
                elif content['type'] == 'photo':
                    with open(content['path'], 'rb') as f:
                        m = await context.bot.send_photo(chat_id=query.message.chat_id, photo=InputFile(f), caption=f'{header_html}\n{_escape_html(caption)}'.strip(), parse_mode='HTML')
                elif content['type'] == 'video':
                    with open(content['path'], 'rb') as f:
                        m = await context.bot.send_video(chat_id=query.message.chat_id, video=InputFile(f), caption=f'{header_html}\n{_escape_html(caption)}'.strip(), parse_mode='HTML')
                elif content['type'] == 'audio':
                    with open(content['path'], 'rb') as f:
                        m = await context.bot.send_audio(chat_id=query.message.chat_id, audio=InputFile(f), caption=f'{header_html}\n{_escape_html(caption)}'.strip(), parse_mode='HTML')
                else:
                    m = await context.bot.send_message(chat_id=query.message.chat_id, text=f'{header_html}\n(неизвестный тип)', parse_mode='HTML')
                listed_ids.append(m.message_id)
            except Exception as e:
                m = await context.bot.send_message(chat_id=query.message.chat_id, text=f'{header_html}\n❌ Не удалось отправить файл', parse_mode='HTML')
                listed_ids.append(m.message_id)
        # Кнопки управления после списка
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('🗑 Удалить контент', callback_data='cmenu|delete')],
            [InlineKeyboardButton('⬅️ В меню', callback_data='cmenu|back')],
        ])
        m_ctrl = await context.bot.send_message(chat_id=query.message.chat_id, text='Выберите действие:', reply_markup=kbd)
        listed_ids.append(m_ctrl.message_id)
        context.user_data['listed_msg_ids'] = listed_ids
        return CONTENT_MENU

    if action == 'stats':
        if not is_admin(user.id):
            await query.answer('Недоступно', show_alert=False)
            return MENU
        stats = content_scheduler.get_stats()
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton('📜 Список пользователей', callback_data='cmenu|list_users')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|root')],
        ])
        await query.edit_message_text(
            '📊 Статистика рассылки:\n\n'
            f'• Подписчиков: {stats["subscribers_count"]}\n'
            f'• Контента: {stats["content_count"]}',
            reply_markup=btn
        )
        return CONTENT_MENU

    if action == 'list_users':
        if not is_admin(user.id):
            await query.answer('Недоступно', show_alert=False)
            return MENU
        subs = content_scheduler.subscribers or {}
        lines = []
        for uid, meta in subs.items():
            uname = meta.get('username') or ''
            if uname:
                if not uname.startswith('@'):
                    uname = '@' + uname
            else:
                uname = f'id:{uid}'
            lines.append(uname)
        text = '👤 Подписчики:\n' + ('\n'.join(lines) if lines else '—')
        btn = InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|stats')]])
        await query.edit_message_text(text, reply_markup=btn)
        return CONTENT_MENU

    if action == 'schedule':
        if not content_scheduler.scheduled_content:
            await query.edit_message_text('❌ Нет доступного контента для планирования.')
            return CONTENT_MENU
        # Кнопки выбора контента
        buttons = []
        for content_id, content in content_scheduler.scheduled_content.items():
            name = content.get('custom_name', content_id)
            buttons.append([InlineKeyboardButton(name, callback_data=f'cmenu|pick|{content_id}')])
        buttons.append([InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')])
        await query.edit_message_text('Выберите контент для планирования:', reply_markup=InlineKeyboardMarkup(buttons))
        return CONTENT_MENU

    if action == 'pick' and len(parts) > 2:
        content_id = parts[2]
        if content_id not in content_scheduler.scheduled_content:
            await query.edit_message_text('❌ Контент не найден.')
            return CONTENT_MENU
        context.user_data['schedule_content_id'] = content_id
        # Выбор режима: ежедневно/одноразово
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('🕒 Ежедневно по времени', callback_data='cmenu|time_daily|init')],
            [InlineKeyboardButton('📆 Еженедельно', callback_data='cmenu|time_weekly|init')],
            [InlineKeyboardButton('📅 Одноразово (дата+время)', callback_data='cmenu|time_once|init')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|schedule')],
        ])
        await query.edit_message_text('Выберите тип расписания:', reply_markup=kbd)
        return CONTENT_MENU

    # Time picker callbacks
    if parts[0] == 'tp':
        sub = parts[1] if len(parts) > 1 else ''
        if sub == 'daily_confirm':
            content_id = context.user_data.get('schedule_content_id')
            if not content_id:
                await query.edit_message_text('❌ Контент не выбран.')
                return CONTENT_MENU
            # сюда больше не попадём, так как daily/weekly теперь вводят время текстом
            time_str = "00:00"
            schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
            target = context.user_data.get('schedule_target', 'users')
            usernames = context.user_data.get('schedule_usernames', [])
            if context.user_data.get('weekly_mode'):
                weekday = int(context.user_data.get('weekly_weekday', 0))
                ok = content_scheduler.schedule_content(schedule_id, content_id, send_time=time_str, repeat_weekly=True, send_weekday=weekday, target=target, usernames=usernames)
            else:
                ok = content_scheduler.schedule_content(schedule_id, content_id, send_time=time_str, repeat_daily=True, target=target, usernames=usernames)
            if ok:
                if context.user_data.get('weekly_mode'):
                    await query.edit_message_text(f'✅ Еженедельная рассылка запланирована на {time_str}')
                else:
                    await query.edit_message_text(f'✅ Ежедневная рассылка запланирована на {time_str}')
            else:
                await query.edit_message_text('❌ Ошибка при планировании.')
            context.user_data.pop('schedule_content_id', None)
            context.user_data.pop('weekly_mode', None)
            return CONTENT_MENU
        # Once: date select and time select
        if sub == 'day':
            delta = parts[2]
            off = int(context.user_data.get('tp_day_offset', 0))
            off = max(0, min(6, off + (1 if delta == '+1' else -1)))
            context.user_data['tp_day_offset'] = off
            await query.edit_message_reply_markup(reply_markup=_build_date_picker(off))
            return CONTENT_MENU
        if sub == 'to_time':
            context.user_data['tp_hour'] = 12
            context.user_data['tp_min'] = 0
            await query.edit_message_text('Выберите время:', reply_markup=_build_once_time_picker(12, 0))
            return CONTENT_MENU
        if sub == 'back_to_date':
            off = int(context.user_data.get('tp_day_offset', 0))
            await query.edit_message_text('Выберите дату:', reply_markup=_build_date_picker(off))
            return CONTENT_MENU
        if sub == 'oh':
            delta = parts[2]
            hour = int(context.user_data.get('tp_hour', 12))
            hour = (hour + (1 if delta == '+1h' else -1)) % 24
            context.user_data['tp_hour'] = hour
            minute = int(context.user_data.get('tp_min', 0))
            await query.edit_message_reply_markup(reply_markup=_build_once_time_picker(hour, minute))
            return CONTENT_MENU
        if sub == 'om':
            delta = parts[2]
            minute = int(context.user_data.get('tp_min', 0))
            minute = (minute + (1 if delta == '+1m' else -1)) % 60
            context.user_data['tp_min'] = minute
            hour = int(context.user_data.get('tp_hour', 12))
            await query.edit_message_reply_markup(reply_markup=_build_once_time_picker(hour, minute))
            return CONTENT_MENU
        if sub == 'once_confirm':
            content_id = context.user_data.get('schedule_content_id')
            if not content_id:
                await query.edit_message_text('❌ Контент не выбран.')
                return CONTENT_MENU
            off = int(context.user_data.get('tp_day_offset', 0))
            hour = int(context.user_data.get('tp_hour', 12))
            minute = int(context.user_data.get('tp_min', 0))
            dt = get_novosibirsk_time().replace(second=0, microsecond=0) + pd.Timedelta(days=off)
            dt = dt.replace(hour=hour, minute=minute)
            schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
            ok = content_scheduler.schedule_content(schedule_id, content_id, send_datetime_iso=dt.isoformat())
            if ok:
                await query.edit_message_text(f'✅ Разовая рассылка запланирована на {dt.strftime("%Y-%m-%d %H:%M")}')
            else:
                await query.edit_message_text('❌ Ошибка при планировании.')
            context.user_data.pop('schedule_content_id', None)
            return CONTENT_MENU

    if action == 'delete':
        # Показать список контента кнопками для удаления
        await _cleanup_listed_messages()
        try:
            header_id = context.user_data.pop('listed_header_id', None)
            if header_id:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=header_id)
        except Exception:
            pass
        try:
            await query.message.delete()
        except Exception:
            pass
        if not content_scheduler.scheduled_content:
            await context.bot.send_message(chat_id=query.message.chat_id, text='Контент отсутствует.')
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
                [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
                [InlineKeyboardButton('⏰ Запланировать рассылку', callback_data='cmenu|schedule')],
                [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
                [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
            ])
            await context.bot.send_message(chat_id=query.message.chat_id, text='📋 Меню управления контентом', reply_markup=kbd)
            return CONTENT_MENU
        buttons = []
        items = sorted(content_scheduler.scheduled_content.items(), key=lambda kv: kv[1].get('created_at',''))
        for cid, meta in items:
            name = meta.get('custom_name', cid)
            buttons.append([InlineKeyboardButton(name, callback_data=f'cmenu|del_pick|{cid}')])
        buttons.append([InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|root')])
        await context.bot.send_message(chat_id=query.message.chat_id, text='Выберите контент для удаления:', reply_markup=InlineKeyboardMarkup(buttons))
        return CONTENT_MENU

    if action == 'del_pick' and len(parts) > 2:
        cid = parts[2]
        ok = False
        if cid in content_scheduler.scheduled_content:
            ok = content_scheduler.delete_content(cid)
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
            [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
            [InlineKeyboardButton('⏰ Запланировать рассылку', callback_data='cmenu|schedule')],
            [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
        ])
        await query.edit_message_text('✅ Контент и связанные расписания удалены.' if ok else '❌ Не удалось удалить контент.', reply_markup=kbd)
        return CONTENT_MENU

    if action == 'time_daily':
        # Запрос времени текстом ЧЧ.ММ
        try:
            pmid = context.user_data.pop('plan_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=pmid)
        except Exception:
            pass
        m = await context.bot.send_message(chat_id=query.message.chat_id, text='Введите время (ежедневно) в формате ЧЧ.ММ (например, 14.30)')
        context.user_data['await_time_daily'] = True
        context.user_data['schedule_prompt_message_id'] = m.message_id
        return SCHEDULE_CONTENT

    if action == 'time_weekly':
        # Выбор дня недели
        if len(parts) > 2 and parts[2] == 'init':
            context.user_data['weekly_weekday'] = 0
            context.user_data['weekly_mode'] = True
            context.user_data['tp_hour'] = 12
            context.user_data['tp_min'] = 0
        wd = int(context.user_data.get('weekly_weekday', 0))
        days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
        # Раскладываем дни по двум строкам для кликабельности
        row1 = [InlineKeyboardButton(days[i] + (' ✅' if i==wd else ''), callback_data=f'cmenu|week_pick|{i}') for i in range(0,4)]
        row2 = [InlineKeyboardButton(days[i] + (' ✅' if i==wd else ''), callback_data=f'cmenu|week_pick|{i}') for i in range(4,7)]
        buttons = [row1, row2,
            [InlineKeyboardButton('Далее: время ▶', callback_data='cmenu|week_time')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|pick_back')]
        ]
        try:
            pmid = context.user_data.pop('plan_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=pmid)
        except Exception:
            pass
        await query.edit_message_text('Выберите день недели:', reply_markup=InlineKeyboardMarkup(buttons))
        return CONTENT_MENU

    if action == 'week_pick' and len(parts) > 2:
        try:
            context.user_data['weekly_weekday'] = int(parts[2])
        except Exception:
            context.user_data['weekly_weekday'] = 0
        # Перерисуем выбор дней, чтобы показать отметку
        wd = int(context.user_data.get('weekly_weekday', 0))
        days = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
        row1 = [InlineKeyboardButton(days[i] + (' ✅' if i==wd else ''), callback_data=f'cmenu|week_pick|{i}') for i in range(0,4)]
        row2 = [InlineKeyboardButton(days[i] + (' ✅' if i==wd else ''), callback_data=f'cmenu|week_pick|{i}') for i in range(4,7)]
        buttons = [row1, row2,
            [InlineKeyboardButton('Далее: время ▶', callback_data='cmenu|week_time')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|pick_back')]
        ]
        await query.edit_message_text('Выберите день недели:', reply_markup=InlineKeyboardMarkup(buttons))
        return CONTENT_MENU

    if action == 'pick_back':
        # Назад к выбору типа расписания для выбранного контента
        if not context.user_data.get('schedule_content_id'):
            return CONTENT_MENU
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('🕒 Ежедневно по времени', callback_data='cmenu|time_daily|init')],
            [InlineKeyboardButton('📆 Еженедельно', callback_data='cmenu|time_weekly|init')],
            [InlineKeyboardButton('📅 Одноразово (дата+время)', callback_data='cmenu|time_once|init')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|schedule')],
        ])
        await query.edit_message_text('Выберите тип расписания:', reply_markup=kbd)
        return CONTENT_MENU

    if action == 'week_time':
        # удалим экран выбора дней
        try:
            await query.message.delete()
        except Exception:
            pass
        m = await context.bot.send_message(chat_id=query.message.chat_id, text='Введите время (еженедельно) в формате ЧЧ.ММ (например, 09.15)')
        context.user_data['weekly_mode'] = True
        context.user_data['await_time_weekly'] = True
        context.user_data['schedule_prompt_message_id'] = m.message_id
        return SCHEDULE_CONTENT
    if action == 'time_once':
        # Просим дату в формате дд.мм.гг
        try:
            pmid = context.user_data.pop('plan_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=pmid)
        except Exception:
            pass
        m = await context.bot.send_message(chat_id=query.message.chat_id, text='Введите дату в формате ДД.ММ.ГГ (например, 25.12.25)')
        context.user_data['await_date'] = True
        context.user_data['schedule_prompt_message_id'] = m.message_id
        return SCHEDULE_CONTENT

    return CONTENT_MENU

async def add_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления контента"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    prompt = await update.message.reply_text(
        '📝 Добавление контента:\n\n'
        'Отправьте мне:\n'
        '• Текстовое сообщение — для текстового контента\n'
        '• Фото — для изображений\n'
        '• Видео — для видео\n'
        '• Аудио — для аудио\n\n'
        'После отправки контента я попрошу вас ввести название для него.'
    )
    # Сохраним id подсказки, чтобы удалить позже
    context.user_data['add_prompt_message_id'] = prompt.message_id
    return ADD_CONTENT

async def handle_content_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загруженного контента"""
    logging.info("handle_content_upload: функция вызвана")
    
    user = update.effective_user
    message = update.message
    
    if not message:
        logging.error("handle_content_upload: сообщение не найдено")
        return ADD_CONTENT
        
    content_type = "unknown"
    if message.text:
        content_type = "text"
        logging.info("handle_content_upload: получен текст")
    elif message.photo:
        content_type = "photo"
        logging.info("handle_content_upload: получено фото")
    elif message.video:
        content_type = "video"
        logging.info("handle_content_upload: получено видео")
    elif message.audio:
        content_type = "audio"
        logging.info("handle_content_upload: получено аудио")
    elif message.document:
        content_type = "document"
        logging.info("handle_content_upload: получен документ")
    else:
        logging.warning("handle_content_upload: неподдерживаемый тип контента")
        await update.message.reply_text('❌ Неподдерживаемый тип контента.')
        return ADD_CONTENT
    
    logging.info(f"handle_content_upload: определен тип контента - {content_type}")
    logging.info(f"handle_content_upload: текст сообщения - {message.text}")
    logging.info(f"handle_content_upload: подпись - {message.caption}")
    
    content_id = f"content_{get_novosibirsk_time().replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}"
    content_data = None
    caption = message.caption
    
    # Определяем тип контента и обрабатываем
    if message.text:
        content_type = "text"
        content_data = message.text
        logging.info("handle_content_upload: обрабатывается текст")
    elif message.photo:
        content_type = "photo"
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            await file.download_to_drive(tmp_file.name)
            content_data = tmp_file.name
        logging.info("handle_content_upload: обрабатывается фото")
    elif message.video:
        content_type = "video"
        video = message.video
        file = await context.bot.get_file(video.file_id)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            await file.download_to_drive(tmp_file.name)
            content_data = tmp_file.name
        logging.info("handle_content_upload: обрабатывается видео")
    elif message.audio:
        content_type = "audio"
        audio = message.audio
        file = await context.bot.get_file(audio.file_id)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            await file.download_to_drive(tmp_file.name)
            content_data = tmp_file.name
        logging.info("handle_content_upload: обрабатывается аудио")
    elif message.document:
        content_type = "document"
        document = message.document
        file = await context.bot.get_file(document.file_id)
        import tempfile
        # Получаем расширение файла из имени или используем .bin по умолчанию
        file_extension = os.path.splitext(document.file_name or 'file.bin')[1] or '.bin'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            await file.download_to_drive(tmp_file.name)
            content_data = tmp_file.name
        logging.info("handle_content_upload: обрабатывается документ")
    else:
        logging.warning(f"handle_content_upload: неподдерживаемый тип контента")
        await update.message.reply_text('❌ Неподдерживаемый тип контента.')
        return ADD_CONTENT
    
    # Удаляем подсказку и сообщение пользователя
    try:
        prompt_id = context.user_data.get('add_prompt_message_id')
        if prompt_id:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=prompt_id)
            context.user_data.pop('add_prompt_message_id', None)
            logging.info("handle_content_upload: подсказка удалена")
    except Exception as e:
        logging.warning(f"handle_content_upload: не удалось удалить подсказку: {e}")
    
    # Удаляем сообщение пользователя с контентом
    try:
        await message.delete()
        logging.info("handle_content_upload: сообщение пользователя удалено")
    except Exception as e:
        logging.warning(f"handle_content_upload: не удалось удалить сообщение пользователя: {e}")
    
    # Сохраняем данные контента
    context.user_data['pending_content'] = {
        'content_id': content_id,
        'content_type': content_type,
        'content_data': content_data,
        'caption': caption
    }
    logging.info("handle_content_upload: данные контента сохранены")
    
    # Запрашиваем название
    name_prompt = await context.bot.send_message(
        chat_id=message.chat_id,
        text=f'📝 Контент получен!\nТип: {content_type}\n\nВведите название для контента (или отправьте /skip для автоматического названия):'
    )
    context.user_data['name_prompt_message_id'] = name_prompt.message_id
    logging.info("handle_content_upload: запрос названия отправлен")
    
    return ADD_CONTENT_NAME

async def handle_content_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия контента"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    pending_content = context.user_data.get('pending_content')
    if not pending_content:
        await update.message.reply_text('❌ Ошибка: данные контента не найдены.')
        return CONTENT_MENU
    
    message = update.message
    # Сохраняем введённый текст названия, затем удалим сообщение пользователя и подсказку
    entered_text = message.text or ''
    custom_name = None
    if entered_text and entered_text != '/skip':
        custom_name = entered_text.strip()
    # Удаляем подсказку названия и сообщение пользователя, чтобы не засорять чат
    try:
        name_prompt_id = context.user_data.pop('name_prompt_message_id', None)
        if name_prompt_id:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=name_prompt_id)
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    
    # Сохраняем контент
    if content_scheduler.add_content(
        pending_content['content_id'], 
        pending_content['content_type'], 
        pending_content['content_data'], 
        pending_content['caption'],
        custom_name
    ):
        # сразу предложим запланировать рассылку для этого контента
        content_id = pending_content['content_id']
        context.user_data['schedule_content_id'] = content_id
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('🕒 Ежедневно по времени', callback_data='cmenu|time_daily|init')],
            [InlineKeyboardButton('📆 Еженедельно', callback_data='cmenu|time_weekly|init')],
            [InlineKeyboardButton('📅 Одноразово (дата+время)', callback_data='cmenu|time_once|init')],
            [InlineKeyboardButton('⬅️ В меню', callback_data='cmenu|back')],
        ])
        plan_msg = await update.message.reply_text('✅ Контент добавлен. Как запланировать рассылку?', reply_markup=kbd)
        context.user_data['plan_prompt_message_id'] = plan_msg.message_id
        # Предложим сразу выбор аудитории после планирования времени
        context.user_data['schedule_target'] = 'users'
    else:
        await update.message.reply_text('❌ Ошибка при сохранении контента.')
    
    # Очищаем временные данные
    context.user_data.pop('pending_content', None)
    
    return CONTENT_MENU



async def handle_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода расписания"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    text = update.message.text.strip()
    parts = text.split()
    
    # Обработка ввода ников для аудитории (specific)
    if context.user_data.get('await_usernames'):
        raw = (update.message.text or '').strip()
        users = [u.strip() for u in raw.split(',') if u.strip()]
        cid = context.user_data.get('last_scheduled_content_id')
        if cid and users:
            content_scheduler.update_latest_schedule_target(cid, 'specific', users)
            await update.message.reply_text('✅ Аудитория сохранена.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ В меню контента', callback_data='cmenu|root')]]))
        else:
            await update.message.reply_text('❌ Не удалось сохранить пользователей.', reply_markup=_start_menu_btn())
        context.user_data.pop('await_usernames', None)
        context.user_data.pop('last_scheduled_content_id', None)
        return CONTENT_MENU
    
    # одноразовая дата/время
    if context.user_data.get('await_date') and context.user_data.get('schedule_content_id'):
        try:
            day, month, year2 = text.split('.')
            day = int(day); month = int(month); year2 = int(year2)
            year = 2000 + year2
            context.user_data['once_date'] = (year, month, day)
            context.user_data.pop('await_date', None)
            try:
                pmid = context.user_data.pop('schedule_prompt_message_id', None)
                if pmid:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=pmid)
            except Exception:
                pass
            try:
                await update.message.delete()
            except Exception:
                pass
            m = await context.bot.send_message(chat_id=update.effective_chat.id, text='Введите время в формате ЧЧ.ММ (например, 14.30)')
            context.user_data['schedule_prompt_message_id'] = m.message_id
            context.user_data['await_time'] = True
            return SCHEDULE_CONTENT
        except Exception:
            await update.message.reply_text('❌ Неверный формат. Используйте ДД.ММ.ГГ')
            return SCHEDULE_CONTENT
    if context.user_data.get('await_time') and context.user_data.get('schedule_content_id') and context.user_data.get('once_date'):
        try:
            hour_str, minute_str = text.split('.')
            hour = int(hour_str); minute = int(minute_str)
            y, m, d = context.user_data['once_date']
            dt = datetime(y, m, d, hour, minute)
        except Exception:
            await update.message.reply_text('❌ Неверный формат. Используйте ЧЧ.ММ')
            return SCHEDULE_CONTENT
        content_id = context.user_data.get('schedule_content_id')
        schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
        target = context.user_data.get('schedule_target', 'users')
        usernames = context.user_data.get('schedule_usernames', [])
        ok = content_scheduler.schedule_content(schedule_id, content_id, send_datetime_iso=dt.isoformat(), target=target, usernames=usernames)
        try:
            pmid = context.user_data.pop('schedule_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=pmid)
        except Exception:
            pass
        try:
            await update.message.delete()
        except Exception:
            pass
        context.user_data.pop('await_time', None)
        context.user_data.pop('once_date', None)
        context.user_data.pop('schedule_content_id', None)
        if ok:
            context.user_data['last_scheduled_content_id'] = content_id
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton('Всем', callback_data='aud|all'), InlineKeyboardButton('Пользователям', callback_data='aud|users')],
                [InlineKeyboardButton('Группам', callback_data='aud|groups'), InlineKeyboardButton('Отдельным пользователям', callback_data='aud|specific')],
            ])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'✅ Разовая рассылка на {dt.strftime("%Y-%m-%d %H:%M")} создана. Кому отправлять?', reply_markup=kbd)
        else:
            await update.message.reply_text('❌ Ошибка при планировании.', reply_markup=_start_menu_btn())
        return CONTENT_MENU
    # ежедневный режим
    if context.user_data.get('await_time_daily') and context.user_data.get('schedule_content_id'):
        try:
            h, m = text.split('.')
            hour = int(h); minute = int(m)
            time_str = f"{hour:02d}:{minute:02d}"
        except Exception:
            await update.message.reply_text('❌ Неверный формат. Используйте ЧЧ.ММ')
            return SCHEDULE_CONTENT
        content_id = context.user_data.get('schedule_content_id')
        schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
        target = context.user_data.get('schedule_target', 'users')
        usernames = context.user_data.get('schedule_usernames', [])
        ok = content_scheduler.schedule_content(schedule_id, content_id, send_time=time_str, repeat_daily=True, target=target, usernames=usernames)
        try:
            pmid = context.user_data.pop('schedule_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=pmid)
        except Exception:
            pass
        try:
            await update.message.delete()
        except Exception:
            pass
        context.user_data.pop('await_time_daily', None)
        context.user_data.pop('schedule_content_id', None)
        if ok:
            context.user_data['last_scheduled_content_id'] = content_id
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton('Всем', callback_data='aud|all'), InlineKeyboardButton('Пользователям', callback_data='aud|users')],
                [InlineKeyboardButton('Группам', callback_data='aud|groups'), InlineKeyboardButton('Отдельным пользователям', callback_data='aud|specific')],
            ])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'✅ Ежедневная рассылка на {time_str} создана. Кому отправлять?', reply_markup=kbd)
        else:
            await update.message.reply_text('❌ Ошибка при планировании.', reply_markup=_start_menu_btn())
        return CONTENT_MENU
    # ввод времени для еженедельного режима
    if context.user_data.get('await_time_weekly') and context.user_data.get('schedule_content_id'):
        try:
            h, m = text.split('.')
            hour = int(h); minute = int(m)
            time_str = f"{hour:02d}:{minute:02d}"
        except Exception:
            await update.message.reply_text('❌ Неверный формат. Используйте ЧЧ.ММ')
            return SCHEDULE_CONTENT
        content_id = context.user_data.get('schedule_content_id')
        weekday = int(context.user_data.get('weekly_weekday', 0))
        schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
        target = context.user_data.get('schedule_target', 'users')
        usernames = context.user_data.get('schedule_usernames', [])
        ok = content_scheduler.schedule_content(schedule_id, content_id, send_time=time_str, repeat_weekly=True, send_weekday=weekday, target=target, usernames=usernames)
        try:
            pmid = context.user_data.pop('schedule_prompt_message_id', None)
            if pmid:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=pmid)
        except Exception:
            pass
        try:
            await update.message.delete()
        except Exception:
            pass
        context.user_data.pop('await_time_weekly', None)
        context.user_data.pop('weekly_mode', None)
        context.user_data.pop('schedule_content_id', None)
        if ok:
            context.user_data['last_scheduled_content_id'] = content_id
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton('Всем', callback_data='aud|all'), InlineKeyboardButton('Пользователям', callback_data='aud|users')],
                [InlineKeyboardButton('Группам', callback_data='aud|groups'), InlineKeyboardButton('Отдельным пользователям', callback_data='aud|specific')],
            ])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'✅ Еженедельная рассылка на {time_str} создана. Кому отправлять?', reply_markup=kbd)
        else:
            await update.message.reply_text('❌ Ошибка при планировании.', reply_markup=_start_menu_btn())
        return CONTENT_MENU
    if len(parts) < 2 and not context.user_data.get('schedule_content_id'):
        await update.message.reply_text('❌ Неверный формат. Используйте: <content_id> <время> [ежедневно]')
        return SCHEDULE_CONTENT
    
    # выбор контента через кнопку
    content_id = context.user_data.get('schedule_content_id') or parts[0]
    time_str = parts[1] if len(parts) > 1 else (parts[0] if context.user_data.get('schedule_content_id') else None)
    repeat_daily = False
    if len(parts) > 2:
        repeat_daily = parts[2].lower() == 'ежедневно'
    elif len(parts) > 1 and context.user_data.get('schedule_content_id'):
        repeat_daily = parts[1].lower() == 'ежедневно'
    
    if content_id not in content_scheduler.scheduled_content:
        await update.message.reply_text(f'❌ Контент с ID "{content_id}" не найден.')
        return SCHEDULE_CONTENT
    
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await update.message.reply_text('❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)')
        return SCHEDULE_CONTENT
    
    schedule_id = f"schedule_{get_novosibirsk_time().strftime('%Y%m%d_%H%M%S')}"
    
    if content_scheduler.schedule_content(schedule_id, content_id, time_str, repeat_daily):
        repeat_text = " (ежедневно)" if repeat_daily else ""
        await update.message.reply_text(
            f'✅ Рассылка запланирована!\n'
            f'ID расписания: {schedule_id}\n'
            f'Контент: {content_id}\n'
            f'Время: {time_str}{repeat_text}'
        )
    else:
        await update.message.reply_text('❌ Ошибка при планировании рассылки.')
    
    context.user_data.pop('schedule_content_id', None)
    
    return CONTENT_MENU

async def list_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра списка контента"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    if not content_scheduler.scheduled_content:
        await update.message.reply_text('📝 Контент не добавлен.', reply_markup=_start_menu_btn())
        return CONTENT_MENU
    
    items = sorted(content_scheduler.scheduled_content.items(), key=lambda kv: kv[1].get('created_at', ''))
    await update.message.reply_text('🗂 Доступный контент:')
    for content_id, content in items:
        name = content.get('custom_name', content_id)
        next_dt = get_next_send_datetime_str(content_id)
        recipients = _recipients_for_content(content_id)
        header = f'Название: {name}\nID: {content_id}\nСледующая отправка: {next_dt}\nПолучатели: {recipients}'
        caption = content.get('caption') or ''
        try:
            if content['type'] == 'text':
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{header}\n\n{content["path"]}')
            elif content['type'] == 'photo':
                with open(content['path'], 'rb') as f:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(f), caption=f'{header}\n{caption}'.strip())
            elif content['type'] == 'video':
                with open(content['path'], 'rb') as f:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=InputFile(f), caption=f'{header}\n{caption}'.strip())
            elif content['type'] == 'audio':
                with open(content['path'], 'rb') as f:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=InputFile(f), caption=f'{header}\n{caption}'.strip())
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{header}\n(неизвестный тип)')
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{header}\n❌ Не удалось отправить файл: {e}')
    kbd = InlineKeyboardMarkup([
        [InlineKeyboardButton('⬅️ В меню', callback_data='cmenu|back')],
        [InlineKeyboardButton('✏️ Изменить контент', callback_data='cmenu|edit')],
        [InlineKeyboardButton('🗑 Удалить контент', callback_data='cmenu|delete')],
    ])
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите действие:', reply_markup=kbd)
    return CONTENT_MENU

async def list_schedules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра списка расписаний"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    schedules = content_scheduler.get_all_schedules()
    if not schedules:
        await update.message.reply_text('📅 Активных расписаний нет.')
        return CONTENT_MENU
    
    schedule_list = []
    for schedule_id, schedule in schedules.items():
        repeat_text = " (ежедневно)" if schedule.get('repeat_daily', False) else ""
        schedule_list.append(f"• {schedule_id}: {schedule['content_id']} в {schedule['send_time']}{repeat_text}")
    
    await update.message.reply_text(
        f'📅 Активные расписания:\n\n' + '\n'.join(schedule_list)
    )
    return CONTENT_MENU

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра статистики"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    
    stats = content_scheduler.get_stats()
    await update.message.reply_text(
        f'📊 Статистика рассылки:\n\n'
        f'• Подписчиков: {stats["subscribers_count"]}\n'
        f'• Контента: {stats["content_count"]}\n'
        f'• Активных расписаний: {stats["active_schedules"]}'
    )
    return CONTENT_MENU

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    kb = [
        [KeyboardButton('/guide'), KeyboardButton('/settings')],
    ]
    await update.message.reply_text(
        'Главное меню',
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return MENU

async def handle_edit_content_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ID (и опционально нового названия) для изменения контента"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    text = (update.message.text or '').strip()
    if not text:
        await update.message.reply_text('Введите ID контента.')
        return EDIT_CONTENT_ID
    parts = text.split('\n', 1)
    content_id = parts[0].strip()
    if content_id not in content_scheduler.scheduled_content:
        await update.message.reply_text('❌ Контент с таким ID не найден. Попробуйте снова.')
        return EDIT_CONTENT_ID
    if len(parts) == 2 and parts[1].strip():
        new_name = parts[1].strip()
        ok = content_scheduler.update_content_name(content_id, new_name)
        if ok:
            await update.message.reply_text('✅ Название обновлено.')
        else:
            await update.message.reply_text('❌ Не удалось обновить название.')
        return CONTENT_MENU
    context.user_data['edit_content_id'] = content_id
    await update.message.reply_text('Введите новое название для контента:')
    return EDIT_CONTENT_NAME

async def handle_edit_content_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода нового названия после того, как ID сохранён"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    content_id = context.user_data.get('edit_content_id')
    if not content_id:
        await update.message.reply_text('❌ Сессия редактирования утеряна. Начните заново.')
        return CONTENT_MENU
    new_name = (update.message.text or '').strip()
    if not new_name:
        await update.message.reply_text('Введите непустое название.')
        return EDIT_CONTENT_NAME
    ok = content_scheduler.update_content_name(content_id, new_name)
    context.user_data.pop('edit_content_id', None)
    if ok:
        await update.message.reply_text('✅ Название обновлено.')
    else:
        await update.message.reply_text('❌ Не удалось обновить название.')
    return CONTENT_MENU

async def handle_delete_content_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление контента по ID (также удаляет связанные расписания)"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ У вас нет прав для доступа к этой функции.')
        return MENU
    content_id = (update.message.text or '').strip()
    if not content_id:
        await update.message.reply_text('Введите ID контента для удаления:')
        return DELETE_CONTENT_ID
    if content_id not in content_scheduler.scheduled_content:
        await update.message.reply_text('❌ Контент с таким ID не найден. Попробуйте снова.')
        return DELETE_CONTENT_ID
    ok = content_scheduler.delete_content(content_id)
    if ok:
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить контент', callback_data='cmenu|add')],
            [InlineKeyboardButton('🗂 Список контента', callback_data='cmenu|list')],
            [InlineKeyboardButton('⏰ Запланировать рассылку', callback_data='cmenu|schedule')],
            [InlineKeyboardButton('📊 Статистика', callback_data='cmenu|stats')],
            [InlineKeyboardButton('⬅️ Назад', callback_data='cmenu|back')],
        ])
        await update.message.reply_text('✅ Контент и связанные расписания удалены.', reply_markup=kbd)
    else:
        await update.message.reply_text('❌ Не удалось удалить контент.')
    return CONTENT_MENU


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

async def unsettemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключает проверку шаблона в текущей теме группы"""
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message
    thread_id = getattr(msg, 'message_thread_id', None)
    if not user or not chat or not thread_id:
        await update.message.reply_text('Эту команду можно использовать только в теме группы.')
        return
    member = await chat.get_member(user.id)
    if member.status not in ('administrator', 'creator'):
        await update.message.reply_text('Только админ может отключить шаблон для темы.')
        return
    try:
        template_topics.discard((chat.id, thread_id))
        await update.message.reply_text('В этой теме больше не требуется шаблон. Проверка отключена.')
    except Exception:
        await update.message.reply_text('Не удалось отключить шаблон. Попробуйте позже.')

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    thread_id = getattr(msg, 'message_thread_id', None)
    msg_text = (getattr(msg, 'text', None) or getattr(msg, 'caption', None))
    if not msg or not chat or not msg_text:
        logging.debug('Пропущено сообщение без текста/подписи')
        return
    if is_user_exempted(msg.from_user, chat.id):
        logging.debug(f"Пользователь {msg.from_user.username} в исключениях, пропускаем проверку спама")
        return
    known_chats[chat.id] = chat.title or str(chat.id)
    if thread_id and (chat.id, thread_id) in template_topics:
        if not TEMPLATE_REGEX.match(msg_text.strip()):
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
    is_spam, prob = await check_spam(msg_text)
    logging.debug(f"Группа {chat.id}: режим={mode}, spam_prob={prob:.3f}")
    if not is_spam:
        return
    if mode == 'auto':
        try:
            log_vote_result(msg_text, 'spam', getattr(msg.from_user, 'id', None))
            await msg.delete()
            # Уведомим админов о автo-удалении
            try:
                author_username = ''
                if getattr(msg.from_user, 'username', None):
                    author_username = '@' + msg.from_user.username
                else:
                    author_username = (msg.from_user.full_name if getattr(msg, 'from_user', None) else 'Неизвестный пользователь')
                notify_text = (
                    f'ℹ️ Я автоматически удалил сообщение пользователя "{author_username}" следующего содержания:\n"{msg_text}"'
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(admin_id, notify_text)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            logging.warning(f'Не удалось удалить: {e}. Перехожу к голосованию.')
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton('СПАМ', callback_data=f'spam|{msg.message_id}')],
                [InlineKeyboardButton('НЕ СПАМ', callback_data=f'ham|{msg.message_id}')]
            ])
            await context.bot.send_message(chat.id, 'Это сообщение — спам?', reply_markup=kbd, reply_to_message_id=msg.message_id)
            votes[(chat.id, msg.message_id)] = set()
            vote_message_texts[(chat.id, msg.message_id)] = (msg_text, getattr(msg.from_user, 'id', None))
    else:
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton('СПАМ', callback_data=f'spam|{msg.message_id}')],
            [InlineKeyboardButton('НЕ СПАМ', callback_data=f'ham|{msg.message_id}')]
        ])
        await context.bot.send_message(chat.id, f'Это сообщение — спам?', reply_markup=kbd, reply_to_message_id=msg.message_id)
        votes[(chat.id, msg.message_id)] = set()
        vote_message_texts[(chat.id, msg.message_id)] = (msg_text, getattr(msg.from_user, 'id', None))

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




#PRIVATE CHAT HANDLERS
async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        text = (
            'Приветствую! Я многофункциональный бот для Telegram-групп.\n\n'
            'Выберите действие:'
        )
        buttons = [
            [InlineKeyboardButton('📖 Руководство', callback_data='start|guide'), InlineKeyboardButton('⚙️ Настройки', callback_data='start|settings')],
            [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')],
            [InlineKeyboardButton('🧰 Меню контента', callback_data='cmenu|root')]
        ]
    else:
        text = 'Приветствую! Я бот Русской Общины г. Томск. Подписаться на рассылку?'
        buttons = [
            [InlineKeyboardButton('✅ Подписаться', callback_data='start|subscribe'), InlineKeyboardButton('🚫 Отписаться', callback_data='start|unsubscribe')]
        ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    return MENU

async def guide_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guide_text = (
        'Мои возможности\n\n'
        '1. автоматически удаляю спам или запускаю голосование\n'
        '2. удаляю сообщения в темах, где включен шаблон\n'
        '(админ может отправить команду /settemplate в тему чата, чтобы включить)\n\n'
        f'   {TEMPLATE_EXAMPLE}\n\n'
        'Можно выбрать, куда я отправлю подсказку неправильно написавшему текст человеку.\n'
        '3. проверяю текст на спам\n'
        '4. рассылаю контент подписчикам по расписанию\n'
    )
    
    if is_admin(update.effective_user.id):
        guide_text += (
            '\nАдминские команды:\n'
            '• /content_menu — управление контентом и рассылкой\n'
            '• /add_content — добавить контент для рассылки\n'
            '• /list_content — список контента\n'
            '• /list_schedules — список расписаний\n'
            '• /stats — статистика рассылки\n'
        )
    
    buttons = [
        [InlineKeyboardButton('🧰 Меню контента', callback_data='cmenu|root')],
        [InlineKeyboardButton('⬅️ В начало', callback_data='start|root')],
    ]
    await update.message.reply_text(guide_text, reply_markup=InlineKeyboardMarkup(buttons))
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
        'где <режим> — chat (подсказка отправляется в общий чат), both (если я не могу написать пользователю лично, я напишу подсказку в общий чат).\n'
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
    if not context.args or context.args[0] not in ('chat', 'both'):
        await update.message.reply_text('Используйте: /templatehint chat|both')
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
    mode = context.user_data.get('hint_mode_to_set', 'both')
    template_hint_mode[chat_id] = mode
    display_mode = 'private' if mode == 'both' else mode
    await update.message.reply_text(f'Режим подсказки для группы {known_chats[chat_id]} установлен: {display_mode}')
    return MENU




conv = ConversationHandler(
        entry_points=[CommandHandler('start', start_private)],
        states={
            MENU: [
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^aud\|')
            ],
            CHOOSE_GROUP: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_group)],
            CHOOSE_MODE: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_mode)],
            CHOOSE_GROUP_HINT: [MessageHandler(filters.COMMAND & filters.ChatType.PRIVATE, choose_group_hint)],
            CONTENT_MENU: [
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^aud\|')
            ],
            ADD_CONTENT: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL) & 
                    filters.ChatType.PRIVATE, 
                    handle_content_upload
                ),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
            ],
            ADD_CONTENT_NAME: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_content_name_input),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|')
            ],
            SCHEDULE_CONTENT: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_schedule_input),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|')
            ],
            EDIT_CONTENT_ID: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_edit_content_id),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|')
            ],
            EDIT_CONTENT_NAME: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_edit_content_name),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|')
            ],
            DELETE_CONTENT_ID: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_delete_content_id),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|')
            ],
            SPAM_EXCEPTIONS_MENU: [
                CallbackQueryHandler(spam_exceptions_callback, pattern=r'^exceptions\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
            ],
            ADD_EXCEPTIONS: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, add_exceptions_handler),
                CallbackQueryHandler(spam_exceptions_callback, pattern=r'^exceptions\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
            ],
            REMOVE_EXCEPTIONS: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, remove_exceptions_handler),
                CallbackQueryHandler(spam_exceptions_callback, pattern=r'^exceptions\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'),
                CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'),
            ],
        },
        fallbacks=[CommandHandler('start', start_private)],
    )