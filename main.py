import asyncio
import os
from telethon import TelegramClient, events
from telethon.tl.functions.account import GetNotifySettingsRequest
from telethon.tl.types import InputNotifyPeer, PeerUser, PeerChat, PeerChannel
from simple_term_menu import TerminalMenu
from colorama import init
from colorama import Fore, Back, Style
from art import tprint
import tempfile
from PIL import Image  # Для отображения изображений
import subprocess  # Для открытия файлов в системе
import config

# Конфигурация клиента Telegram
API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = 'session_telegram'

# Инициализация клиента
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Глобальные переменные
current_chat_id = None
current_chat_name = None
unread_messages = []

def clear_console():
    """Очищает консоль в зависимости от операционной системы."""
    os.system('cls' if os.name == 'nt' else 'clear')

async def load_unread_messages_from_dialogs():
    """Загружает все непрочитанные сообщения из диалогов с включенными уведомлениями."""
    global unread_messages
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        # Проверяем, есть ли непрочитанные сообщения
        if dialog.unread_count > 0:
            chat = dialog.entity  # Используем атрибут entity
            chat_name = chat.title if hasattr(chat, 'title') else get_sender_name(chat)
            
            # Получаем настройки уведомлений для диалога
            try:
                peer = await client.get_input_entity(dialog.entity)
                notify_settings = await client(GetNotifySettingsRequest(
                    peer=InputNotifyPeer(peer)
                ))
                # Если уведомления не приглушены (mute_until == None), добавляем сообщения
                if not notify_settings.mute_until:
                    messages = await client.get_messages(dialog.entity, limit=dialog.unread_count)
                    for msg in messages:
                        sender = await msg.get_sender()
                        sender_name = get_sender_name(sender)
                        
                        # Определяем тип сообщения
                        if msg.sticker:
                            message_text = "[Стикер]"
                        elif msg.photo:
                            message_text = "[Фото]"
                        elif msg.video:
                            message_text = "[Видео]"
                        elif msg.voice:
                            message_text = "[Голосовое сообщение]"
                        elif msg.document:
                            message_text = "[Файл]"
                        else:
                            message_text = msg.text or "Без текста"
                        
                        unread_messages.append({
                            'sender_name': sender_name,
                            'chat_id': dialog.entity.id,
                            'chat_name': chat_name,
                            'text': message_text
                        })
            except Exception as e:
                print(f"Ошибка при получении настроек уведомлений: {e}")
    print(f"Загружено {len(unread_messages)} непрочитанных сообщений с уведомлениями.")

async def main_menu():
    while True:
        clear_console()
        init()
        print(Fore.BLUE)
        tprint("TelegConsole")
        print(Style.RESET_ALL)
        print("Главное меню:")
        print(f"Непрочитанные сообщения: {len(unread_messages)}")
        # Добавляем динамическую информацию о выбранном чате
        if current_chat_name == None or current_chat_name == "":
            chat_info = "не выбран пользователь"
        else:
            chat_info = current_chat_name
        # chat_info = f" ({current_chat_name})" if current_chat_name else " (не выбран)"
        
        options = [
            "Список сообщений и груп",
            "Список каналов",
            "Выбрать получателя(посмотреть чат)",
            f"Отправить сообщение ({chat_info})",
            f"Просмотр медиа ({chat_info})",
            "Просмотреть непрочитанные сообщения",
            "Выход"
        ]
        terminal_menu = TerminalMenu(options, title="Выберите действие")
        menu_entry_index = terminal_menu.show()
        choice = options[menu_entry_index]
        
        if choice == "Список сообщений и груп":
            await view_chats()
        elif choice == "Список каналов":
            await view_channels()
        elif choice == "Выбрать получателя(посмотреть чат)":
            await select_chat()
        elif choice == f"Отправить сообщение ({chat_info})":
            await send_message()
        elif choice == f"Просмотр медиа ({chat_info})":
            await view_media()
        elif choice == "Просмотреть непрочитанные сообщения":
            await view_unread_messages()
        elif choice == "Выход":
            print("Выход из программы...")
            break

async def view_chats():
    clear_console()
    print("Загрузка чатов/групп...")
    
    try:
        # Получаем список диалогов
        dialogs = await client.get_dialogs()
        
        # Фильтруем только чаты/группы (исключаем каналы)
        chats = [dialog for dialog in dialogs if not dialog.is_channel]
        # Инвертируем порядок чатов: последние добавленные вверху
        chats.reverse()
        
        # Проверяем, что есть доступные чаты/группы
        if not chats:
            print("Нет доступных чатов/групп.")
            input("Нажмите Enter для возврата в главное меню...")
            return

        total_channels = len(chats)  # Общее количество каналов
        for i, chats in enumerate(chats):
            name = chats.name or "Без имени"
            channel_id = chats.entity.id if chats.entity else "ID неизвестен"
            # Рассчитываем номер, начиная с наибольшего значения
            number = total_channels - i
            print(f"{number}. {name} ({channel_id})")
        
        input("\nНажмите Enter для возврата в главное меню...")
    
    except Exception as e:
        print(f"Ошибка при загрузке чатов/групп: {e}")
        input("Нажмите Enter для возврата в главное меню...")

async def view_channels():
    clear_console()
    print("Загрузка каналов...")
    
    try:
        # Получаем список диалогов
        dialogs = await client.get_dialogs()
        
        # Фильтруем только каналы
        channels = [dialog for dialog in dialogs if dialog.is_channel]
        # Инвертируем порядок чатов: последние добавленные вверху
        channels.reverse()
        
        # Проверяем, что есть доступные каналы
        if not channels:
            print("Нет доступных каналов.")
            input("Нажмите Enter для возврата в главное меню...")
            return
        
        # Выводим список каналов
        print("Доступные каналы:")
        total_channels = len(channels)  # Общее количество каналов
        for i, channel in enumerate(channels):
            name = channel.name or "Без имени"
            channel_id = channel.entity.id if channel.entity else "ID неизвестен"
            # Рассчитываем номер, начиная с наибольшего значения
            number = total_channels - i
            print(f"{number}. {name} ({channel_id})")
        
        input("\nНажмите Enter для возврата в главное меню...")
    
    except Exception as e:
        print(f"Ошибка при загрузке каналов: {e}")
        input("Нажмите Enter для возврата в главное меню...")
        
async def view_dialogs():
    clear_console()
    print("Загрузка диалогов...")
    dialogs = await client.get_dialogs()
    for i, dialog in enumerate(dialogs):
        print(f"{i + 1}. {dialog.name} ({dialog.entity.id})")
    input("Нажмите Enter для возврата в главное меню...")

async def select_chat():
    global current_chat_id, current_chat_name
    clear_console()
    print("Загрузка чатов/групп...")
    
    try:
        # Получаем список всех диалогов
        dialogs = await client.get_dialogs()
        
        # Фильтруем только личные сообщения и группы (исключаем каналы)
        filtered_dialogs = [
            dialog for dialog in dialogs
            if not dialog.is_channel  # Исключаем каналы
        ]
        
        # Проверяем, что есть доступные чаты/группы
        if not filtered_dialogs:
            print("Нет доступных чатов или групп.")
            input("Нажмите Enter для возврата в главное меню...")
            return
        
        # Создаем список названий чатов/групп для меню
        chat_options = [
            f"{d.name} ({d.entity.id})" for d in filtered_dialogs
        ]
        
        # Создаем меню выбора чата
        terminal_menu = TerminalMenu(chat_options, title="Выбор чата")
        selected_index = terminal_menu.show()
        
        # Проверяем, что пользователь выбрал чат
        if selected_index is not None:
            selected_dialog = filtered_dialogs[selected_index]
            current_chat_id = selected_dialog.entity.id
            current_chat_name = selected_dialog.name or "Без имени"
            print(f"Выбран чат: {current_chat_name}")
            await view_chat_messages()
        else:
            print("Чат не выбран.")
            input("Нажмите Enter для возврата в главное меню...")
    
    except Exception as e:
        print(f"Ошибка при выборе чата: {e}")
        input("Нажмите Enter для возврата в главное меню...")

async def view_chat_messages():
    if current_chat_id is None:
        print("Сначала выберите чат!")
        return
    clear_console()
    print(f"Последние сообщения из чата '{current_chat_name}':")
    
    # Загружаем последние 100 сообщений
    messages = await client.get_messages(current_chat_id, limit=100)
    messages.reverse()  # Инвертируем порядок: старые сверху, новые снизу
    
    # Выводим сообщения
    for msg in messages:
        sender = await msg.get_sender()
        sender_name = get_sender_name(sender)
        # Проверяем тип сообщения
        if msg.sticker:
            print(f"{sender_name}: [Стикер]")
        elif msg.photo:
            print(f"{sender_name}: [Фото]")
        elif msg.video:
            print(f"{sender_name}: [Видео]")
        elif msg.voice:
            print(f"{sender_name}: [Голосовое сообщение]")
        elif msg.document:
            print(f"{sender_name}: [Файл]")
        elif msg.text:
            print(f"{sender_name}: {msg.text}")
        else:
            print(f"{sender_name}: [Неизвестный тип сообщения]")
    
    input("Нажмите Enter для возврата в главное меню...")

async def send_message():
    try:
        if current_chat_id is None:
            print("Сначала выберите чат!")
            return
        clear_console()
        message = input("Введите сообщение: ")
        if message == "":
            return
        
        # Помечаем все непрочитанные сообщения в текущем чате как прочитанные
        await client.send_read_acknowledge(current_chat_id)
        
        # Отправляем новое сообщение
        await client.send_message(current_chat_id, message)
        print("Сообщение отправлено!")
        
        # Очищаем непрочитанные сообщения для текущего чата
        global unread_messages
        unread_messages = [msg for msg in unread_messages if msg['chat_id'] != current_chat_id]
        
        input("Нажмите Enter для возврата в главное меню...")
    except Exception as e:
        print(f"Что-то пошло не так. Ошибка при отправке сообщения: {e}")
        input("Нажмите Enter для возврата в главное меню...")

def open_file(file_path):
    """
    Открывает файл через системную программу.
    """
    if os.name == 'nt':  # Windows
        os.startfile(file_path)
    elif os.name == 'posix':  # macOS/Linux
        subprocess.run(['open', file_path] if os.uname().sysname == 'Darwin' else ['xdg-open', file_path])

async def view_media():
    if current_chat_id is None:
        print("Сначала выберите чат!")
        return
    
    clear_console()
    print("Загрузка медиа...")
    messages = await client.get_messages(current_chat_id, limit=50)
    media_messages = [msg for msg in messages if msg.media]
    
    if not media_messages:
        print("В этом чате нет медиафайлов.")
        input("Нажмите Enter для возврата в главное меню...")
        return
    
    media_options = []
    for i, msg in enumerate(media_messages):
        if msg.sticker:
            media_type = "[Стикер]"
        elif msg.photo:
            media_type = "[Фото]"
        elif msg.video:
            media_type = "[Видео]"
        elif msg.voice:
            media_type = "[Голосовое сообщение]"
        elif msg.document:
            media_type = "[Файл]"
        else:
            media_type = "[Неизвестный тип]"
        
        media_options.append(f"{i + 1}. {media_type} от {msg.sender_id}")
    
    terminal_menu = TerminalMenu(media_options, title="Выбор медиафайла")
    selected_index = terminal_menu.show()
    
    if selected_index is not None:
        selected_msg = media_messages[selected_index]
        media = selected_msg.media
        
        # Создаем временный файл для медиа
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            media_path = await client.download_media(media, file=temp_path)
        
        # Определяем тип медиафайла и обрабатываем его
        if selected_msg.sticker:
            print("Открытие стикера...")
            try:
                # Открываем документ через системную программу
                open_file(media_path)
            except Exception as e:
                print(f"Ошибка при открытии файла: {e}")
        
        elif selected_msg.photo:
            print("Открытие изображения...")
            try:
                # Открываем изображение с помощью Pillow
                img = Image.open(media_path)
                img.show()  # Отображаем изображение
            except Exception as e:
                print(f"Ошибка при открытии изображения: {e}")
        
        elif selected_msg.video:
            print("Открытие видео...")
            try:
                # Открываем видео через системную программу
                open_file(media_path)
            except Exception as e:
                print(f"Ошибка при открытии видео: {e}")
        
        elif selected_msg.voice:
            print("Голосовое сообщение. Открытие файла...")
            try:
                # Открываем голосовое сообщение через системную программу
                open_file(media_path)
            except Exception as e:
                print(f"Ошибка при открытии голосового сообщения: {e}")
        
        elif selected_msg.document:
            print("Открытие файла...")
            try:
                # Открываем документ через системную программу
                open_file(media_path)
            except Exception as e:
                print(f"Ошибка при открытии файла: {e}")
        
        # Предлагаем скачать файл
        choice = input("Хотите сохранить файл? (y/N): ").strip().lower()
        if choice == 'y':
            save_path = input("Введите путь для сохранения файла: ").strip()
            if save_path:
                try:
                    # Копируем файл в указанное место
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    os.rename(media_path, save_path)
                    print(f"Файл сохранен: {save_path}")
                except Exception as e:
                    print(f"Ошибка при сохранении файла: {e}")
            else:
                print("Путь не указан. Файл не сохранен.")
        
        # Удаляем временный файл, если он не был сохранен
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    input("Нажмите Enter для возврата в главное меню...")

async def view_unread_messages():
    global unread_messages
    if not unread_messages:
        print("Нет непрочитанных сообщений.")
        input("Нажмите Enter для возврата в главное меню...")
        return
    clear_console()
    print("Непрочитанные сообщения:")
    for i, msg in enumerate(unread_messages):
        sender_name = msg['sender_name']
        text = msg['text']
        print(f"{i + 1}. {sender_name}: {text}")
    
    options = ["Перейти в чат", "Пометить как прочитанное", "Вернуться в главное меню"]
    terminal_menu = TerminalMenu(options, title="Действия с непрочитанными сообщениями")
    menu_entry_index = terminal_menu.show()
    choice = options[menu_entry_index]
    if choice == "Перейти в чат":
        await go_to_chat_from_message()
    elif choice == "Пометить как прочитанное":
        await mark_as_read()
    elif choice == "Вернуться в главное меню":
        pass

async def go_to_chat_from_message():
    global unread_messages
    if not unread_messages:
        print("Нет непрочитанных сообщений.")
        input("Нажмите Enter для возврата в главное меню...")
        return
    
    clear_console()
    print("Непрочитанные сообщения:")
    for i, msg in enumerate(unread_messages):
        sender_name = msg['sender_name']
        text = msg['text']
        print(f"{i + 1}. {sender_name}: {text}")
    
    try:
        index = int(input("Введите номер сообщения для перехода в чат: ")) - 1
        if 0 <= index < len(unread_messages):
            selected_msg = unread_messages[index]
            chat_id = selected_msg['chat_id']
            
            # Переходим в чат
            global current_chat_id, current_chat_name
            current_chat_id = chat_id
            current_chat_name = selected_msg['chat_name']
            print(f"Переход в чат: {current_chat_name}")
            await view_chat_messages()
        else:
            print("Неверный номер сообщения.")
    except ValueError:
        print("Введите корректный номер.")
    
    input("Нажмите Enter для возврата в главное меню...")

async def mark_as_read():
    global unread_messages
    if not unread_messages:
        print("Нет непрочитанных сообщений.")
        input("Нажмите Enter для возврата в главное меню...")
        return
    clear_console()
    print("Непрочитанные сообщения:")
    for i, msg in enumerate(unread_messages):
        sender_name = msg['sender_name']
        text = msg['text']
        print(f"{i + 1}. {sender_name}: {text}")
    try:
        index = int(input("Введите номер сообщения для пометки как прочитанное: ")) - 1
        if 0 <= index < len(unread_messages):
            selected_msg = unread_messages.pop(index)  # Удаляем сообщение из списка
            chat_id = selected_msg['chat_id']
            # Помечаем сообщение как прочитанное
            await client.send_read_acknowledge(chat_id)
            print("Сообщение помечено как прочитанное.")
        else:
            print("Неверный номер сообщения.")
    except ValueError:
        print("Введите корректный номер.")
    input("Нажмите Enter для возврата в главное меню...")

async def listen_for_new_messages():
    @client.on(events.NewMessage())
    async def handler(event):
        try:
            # Проверяем, является ли сообщение новым (приватное или упомянутое)
            if event.is_private or event.mentioned:
                sender = await event.get_sender()
                sender_name = get_sender_name(sender)
                chat_id = event.chat_id
                
                # Определяем название чата
                try:
                    chat = await event.get_chat()
                    chat_name = chat.title if hasattr(chat, 'title') else sender_name
                except AttributeError:
                    chat_name = sender_name
                
                # Определяем тип сообщения
                if event.message.sticker:
                    message_text = "[Стикер]"
                elif event.message.photo:
                    message_text = "[Фото]"
                elif event.message.video:
                    message_text = "[Видео]"
                elif event.message.voice:
                    message_text = "[Голосовое сообщение]"
                elif event.message.document:
                    message_text = "[Файл]"
                else:
                    message_text = event.message.text or "Без текста"
                
                # Сохраняем новое непрочитанное сообщение
                global unread_messages
                unread_messages.append({
                    'sender_name': sender_name,
                    'chat_id': chat_id,
                    'chat_name': chat_name,
                    'text': message_text
                })
                print(f"\nНовое непрочитанное сообщение от {sender_name}: {message_text}")
        except Exception as e:
            print(f"Ошибка при обработке нового сообщения: {e}")

def get_sender_name(sender):
    """Определяет имя отправителя в зависимости от типа объекта."""
    if hasattr(sender, 'first_name'):  # Пользователь (User)
        return sender.first_name or sender.username or "Неизвестный"
    elif hasattr(sender, 'title'):  # Канал (Channel) или группа (Chat)
        return sender.title
    else:
        return "Неизвестный"

async def main():
    async with client:
        # Загружаем непрочитанные сообщения из диалогов с включенными уведомлениями
        await load_unread_messages_from_dialogs()
        
        # Запускаем фоновую задачу для отслеживания новых сообщений
        asyncio.create_task(listen_for_new_messages())
        
        # Основной цикл программы
        await main_menu()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())