import os
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Union
from config import NOVOSIBIRSK_TZ

from telegram import Bot, InputFile
from telegram.error import TelegramError

from utils import get_novosibirsk_time
from storage import known_chats

logger = logging.getLogger(__name__)

class ContentScheduler:
    """Класс для управления рассылкой контента подписчикам"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.subscribers_file = os.path.join(data_dir, "subscribers.json")
        self.content_file = os.path.join(data_dir, "scheduled_content.json")
        self.schedule_file = os.path.join(data_dir, "schedule.json")
        
        os.makedirs(data_dir, exist_ok=True)
        
        self.subscribers = self._load_subscribers()
        self.scheduled_content = self._load_scheduled_content()
        self.schedule = self._load_schedule()
    
    def _load_subscribers(self) -> Dict[int, Dict]:
        """Загружает список подписчиков из файла"""
        if os.path.exists(self.subscribers_file):
            try:
                with open(self.subscribers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки подписчиков: {e}")
        return {}
    
    def _save_subscribers(self):
        """Сохраняет список подписчиков в файл"""
        try:
            with open(self.subscribers_file, 'w', encoding='utf-8') as f:
                json.dump(self.subscribers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения подписчиков: {e}")
    
    def _load_scheduled_content(self) -> Dict[str, Dict]:
        """Загружает запланированный контент"""
        if os.path.exists(self.content_file):
            try:
                with open(self.content_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки контента: {e}")
        return {}
    
    def _save_scheduled_content(self):
        """Сохраняет запланированный контент"""
        try:
            with open(self.content_file, 'w', encoding='utf-8') as f:
                json.dump(self.scheduled_content, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения контента: {e}")
    
    def _load_schedule(self) -> Dict[str, Dict]:
        """Загружает расписание рассылок"""
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки расписания: {e}")
        return {}
    
    def _save_schedule(self):
        """Сохраняет расписание рассылок"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.schedule, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения расписания: {e}")
    
    def add_subscriber(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Добавляет пользователя в список подписчиков"""
        try:
            self.subscribers[str(user_id)] = {
                "username": username,
                "first_name": first_name,
                "subscribed_at": get_novosibirsk_time().isoformat(),
                "active": True
            }
            self._save_subscribers()
            logger.info(f"Пользователь {user_id} добавлен в подписчики")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления подписчика {user_id}: {e}")
            return False
    
    def remove_subscriber(self, user_id: int) -> bool:
        """Удаляет пользователя из списка подписчиков"""
        try:
            if str(user_id) in self.subscribers:
                del self.subscribers[str(user_id)]
                self._save_subscribers()
                logger.info(f"Пользователь {user_id} удален из подписчиков")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления подписчика {user_id}: {e}")
            return False
    
    def is_subscriber(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь подписчиком"""
        return str(user_id) in self.subscribers and self.subscribers[str(user_id)].get("active", True)
    
    def get_subscribers(self) -> List[int]:
        """Возвращает список активных подписчиков"""
        return [int(user_id) for user_id, data in self.subscribers.items() 
                if data.get("active", True)]
    

#       ВНИМАНИЕ
    def add_content(self, content_id: str, content_type: str, content_data: Union[str, bytes], 
                   caption: str = None, custom_name: str = None) -> bool:
        """Добавляет контент для рассылки"""
        try:
            content_dir = os.path.join(self.data_dir, "content")
            os.makedirs(content_dir, exist_ok=True)
            
            if content_type in ["video", "audio", "photo"]:
                # сохраняем файл с корректным расширением
                ext_map = {"photo": "jpg", "video": "mp4", "audio": "mp3"}
                ext = ext_map.get(content_type, "bin")
                file_path = os.path.join(content_dir, f"{content_id}.{ext}")
                if isinstance(content_data, bytes):
                    with open(file_path, 'wb') as f:
                        f.write(content_data)
                else:
                    import shutil
                    shutil.copy2(content_data, file_path)
                content_path = file_path
            else:
                # текстовый контент
                content_path = content_data
            
            self.scheduled_content[content_id] = {
                "type": content_type,
                "path": content_path,
                "caption": caption,
                "custom_name": custom_name or content_id,
                "created_at": get_novosibirsk_time().isoformat()
            }
            self._save_scheduled_content()
            logger.info(f"Контент {content_id} добавлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления контента {content_id}: {e}")
            return False
    
    def schedule_content(self, schedule_id: str, content_id: str, send_time: str = None,
                        repeat_daily: bool = False, send_datetime_iso: str = None,
                        repeat_weekly: bool = False, send_weekday: int | None = None,
                        target: str | None = None, usernames: list[str] | None = None) -> bool:
        """Планирует отправку контента"""
        try:
            if content_id not in self.scheduled_content:
                logger.error(f"Контент {content_id} не найден")
                return False
            
            if send_datetime_iso:
                self.schedule[schedule_id] = {
                    "content_id": content_id,
                    "send_datetime": send_datetime_iso,
                    "repeat_daily": False,
                    "repeat_weekly": False,
                    "target": target or 'users',
                    "usernames": usernames or [],
                    "created_at": get_novosibirsk_time().isoformat(),
                    "active": True
                }
            elif repeat_weekly and send_weekday is not None and send_time:
                self.schedule[schedule_id] = {
                    "content_id": content_id,
                    "send_time": send_time,
                    "repeat_daily": False,
                    "repeat_weekly": True,
                    "send_weekday": int(send_weekday),
                    "target": target or 'users',
                    "usernames": usernames or [],
                    "created_at": get_novosibirsk_time().isoformat(),
                    "active": True
                }
            else:
                self.schedule[schedule_id] = {
                    "content_id": content_id,
                    "send_time": send_time,
                    "repeat_daily": repeat_daily,
                    "repeat_weekly": False,
                    "target": target or 'users',
                    "usernames": usernames or [],
                    "created_at": get_novosibirsk_time().isoformat(),
                    "active": True
                }
            self._save_schedule()
            logger.info(f"Рассылка {schedule_id} запланирована")
            return True
        except Exception as e:
            logger.error(f"Ошибка планирования рассылки {schedule_id}: {e}")
            return False
    
    def get_scheduled_content(self, content_id: str) -> Optional[Dict]:
        """Получает информацию о запланированном контенте"""
        return self.scheduled_content.get(content_id)
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        """Получает информацию о расписании"""
        return self.schedule.get(schedule_id)
    
    def get_all_schedules(self) -> Dict[str, Dict]:
        """Получает все активные расписания"""
        return {k: v for k, v in self.schedule.items() if v.get("active", True)}
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Удаляет расписание"""
        try:
            if schedule_id in self.schedule:
                del self.schedule[schedule_id]
                self._save_schedule()
                logger.info(f"Расписание {schedule_id} удалено")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления расписания {schedule_id}: {e}")
            return False

    def update_latest_schedule_target(self, content_id: str, target: str, usernames: list[str] | None = None) -> bool:
        """Обновляет цель аудитории у самого свежего активного расписания для контента."""
        try:
            candidates = [(sid, sch) for sid, sch in self.schedule.items() if sch.get('content_id') == content_id and sch.get('active', True)]
            if not candidates:
                return False
            def _key(item):
                from datetime import datetime as _dt
                sid, sch = item
                try:
                    return _dt.fromisoformat(sch.get('created_at', ''))
                except Exception:
                    return _dt.min
            sid, sch = sorted(candidates, key=_key, reverse=True)[0]
            sch['target'] = target
            sch['usernames'] = usernames or []
            self.schedule[sid] = sch
            self._save_schedule()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления аудитории для контента {content_id}: {e}")
            return False

    def update_content_name(self, content_id: str, new_name: str) -> bool:
        """Обновляет пользовательское имя контента"""
        try:
            if content_id in self.scheduled_content:
                self.scheduled_content[content_id]['custom_name'] = new_name
                self._save_scheduled_content()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка обновления названия контента {content_id}: {e}")
            return False

    def delete_content(self, content_id: str) -> bool:
        """Удаляет контент и связанные расписания. Пытается удалить файл с диска, если есть."""
        try:
            if content_id in self.scheduled_content:
                try:
                    content = self.scheduled_content[content_id]
                    path = content.get('path')
                    if path and isinstance(path, str) and os.path.isfile(path):
                        os.remove(path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл контента {content_id}: {e}")
                del self.scheduled_content[content_id]
                self._save_scheduled_content()
                to_delete = [sid for sid, sch in self.schedule.items() if sch.get('content_id') == content_id]
                for sid in to_delete:
                    del self.schedule[sid]
                if to_delete:
                    self._save_schedule()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления контента {content_id}: {e}")
            return False
    
    async def send_content_to_subscribers(self, bot: Bot, content_id: str) -> Dict[str, int]:
        """Отправляет контент всем подписчикам"""
        content = self.get_scheduled_content(content_id)
        if not content:
            logger.error(f"Контент {content_id} не найден")
            return {"sent": 0, "failed": 0}
        
        subscribers = self.get_subscribers()
        sent = 0
        failed = 0
        
        for user_id in subscribers:
            try:
                await self._send_content_to_user(bot, user_id, content)
                sent += 1
                logger.info(f"Контент {content_id} отправлен пользователю {user_id}")
            except TelegramError as e:
                failed += 1
                logger.warning(f"Не удалось отправить контент {content_id} пользователю {user_id}: {e}")
                # Если пользователь заблокировал бота, удаляем его из подписчиков
                if "bot was blocked" in str(e).lower():
                    self.remove_subscriber(user_id)
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка отправки контента {content_id} пользователю {user_id}: {e}")
        
        return {"sent": sent, "failed": failed}

    async def send_content_by_schedule(self, bot: Bot, schedule: Dict, known_chats: Dict[int, str]) -> Dict[str,int]:
        """Отправляет контент согласно настройкам аудитории в расписании."""
        content_id = schedule.get('content_id')
        content = self.get_scheduled_content(content_id)
        if not content:
            return {"sent": 0, "failed": 0}

        target = schedule.get('target', 'users')  # users|all|groups|specific
        usernames = schedule.get('usernames', []) or []
        sent = 0
        failed = 0

        async def _send_user(user_id: int):
            nonlocal sent, failed
            try:
                await self._send_content_to_user(bot, user_id, content)
                sent += 1
            except TelegramError as e:
                failed += 1
                if "bot was blocked" in str(e).lower():
                    self.remove_subscriber(user_id)
            except Exception:
                failed += 1

        # Resolve recipients
        recipients_users: list[int] = []
        if target in ('users','all','specific'):
            # start from subscribers
            recipients_users = [int(uid) for uid in self.subscribers.keys()]
            if target == 'specific' and usernames:
                # map usernames to ids among subscribers only
                uname_norm = {u.lstrip('@').lower() for u in usernames}
                recipients_users = [int(uid) for uid, meta in self.subscribers.items()
                                    if (meta.get('username') or '').lower() in uname_norm]

        # Send to users
        for uid in recipients_users:
            await _send_user(uid)

        # Send to groups (chats) if requested
        if target in ('groups','all') and known_chats:
            for chat_id in list(known_chats.keys()):
                try:
                    await self._send_to_chat(bot, chat_id, content)
                    sent += 1
                except Exception:
                    failed += 1

        return {"sent": sent, "failed": failed}

    async def _send_to_chat(self, bot: Bot, chat_id: int, content: Dict):
        content_type = content["type"]
        content_path = content["path"]
        caption = content.get("caption", "")
        if content_type == "text":
            await bot.send_message(chat_id, content_path)
        elif content_type == "photo":
            with open(content_path, 'rb') as f:
                await bot.send_photo(chat_id, InputFile(f), caption=caption)
        elif content_type == "video":
            with open(content_path, 'rb') as f:
                await bot.send_video(chat_id, InputFile(f), caption=caption)
        elif content_type == "audio":
            with open(content_path, 'rb') as f:
                await bot.send_audio(chat_id, InputFile(f), caption=caption)
        else:
            await bot.send_message(chat_id, '(неизвестный тип контента)')
    
    async def _send_content_to_user(self, bot: Bot, user_id: int, content: Dict):
        """Отправляет контент конкретному пользователю"""
        content_type = content["type"]
        content_path = content["path"]
        caption = content.get("caption", "")
        
        if content_type == "text":
            await bot.send_message(user_id, content_path)
        elif content_type == "photo":
            with open(content_path, 'rb') as f:
                await bot.send_photo(user_id, InputFile(f), caption=caption)
        elif content_type == "video":
            with open(content_path, 'rb') as f:
                await bot.send_video(user_id, InputFile(f), caption=caption)
        elif content_type == "audio":
            with open(content_path, 'rb') as f:
                await bot.send_audio(user_id, InputFile(f), caption=caption)
        else:
            raise ValueError(f"Неподдерживаемый тип контента: {content_type}")
    
    def should_send_now(self, schedule_id: str) -> bool:
        schedule = self.get_schedule(schedule_id)
        if not schedule or not schedule.get("active", True):
            return False
    
        try:
            now = get_novosibirsk_time().replace(second=0, microsecond=0)
        
            if "send_datetime" in schedule:
                dt = datetime.fromisoformat(schedule["send_datetime"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=NOVOSIBIRSK_TZ)
                if now >= dt and (now - dt).total_seconds() < 60:
                    return True
                return False
        
        # еженедельное время
            if schedule.get("repeat_weekly") and "send_time" in schedule and "send_weekday" in schedule:
                try:
                    t = datetime.strptime(schedule["send_time"], "%H:%M").time()
                    target_weekday = int(schedule.get("send_weekday", 0))  # 0..6
                    current_weekday = now.weekday()
                    current_time = now.time()
                
                    if (current_weekday == target_weekday and 
                        current_time.hour == t.hour and 
                        current_time.minute == t.minute):
                        return True
                except Exception as e:
                    logger.error(f"Ошибка weekly времени: {e}")
                return False

        # ежедневное время
            send_time = datetime.strptime(schedule["send_time"], "%H:%M").time()
            current_time = now.time()
            if (current_time.hour == send_time.hour and 
                current_time.minute == send_time.minute):
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки времени для расписания {schedule_id}: {e}")
            return False


    def get_stats(self) -> Dict:
        """Возвращает статистику рассылки"""
        return {
            "subscribers_count": len(self.get_subscribers()),
            "content_count": len(self.scheduled_content),
            "active_schedules": len(self.get_all_schedules())
        }


content_scheduler = ContentScheduler()



async def check_and_send_scheduled_content(context):
    """Проверяет расписание и отправляет контент если наступило время"""
    try:
        schedules = content_scheduler.get_all_schedules()
        for schedule_id, schedule in schedules.items():
            if content_scheduler.should_send_now(schedule_id):
                content_id = schedule['content_id']
                result = await content_scheduler.send_content_by_schedule(context.bot, schedule, known_chats)
                
                logging.info(f"Рассылка {schedule_id}: отправлено {result['sent']}, ошибок {result['failed']}")
                
                # если это не повторяющаяся рассылка, удаляем расписание
                if not schedule.get('repeat_daily', False) and not schedule.get('repeat_weekly', False):
                    content_scheduler.delete_schedule(schedule_id)
                    logging.info(f"Расписание {schedule_id} удалено (одноразовая рассылка)")
                    
    except Exception as e:
        logging.error(f"Ошибка в планировщике рассылки: {e}")