import asyncio
import os
from telethon import TelegramClient, events
from telethon.tl.functions.account import GetNotifySettingsRequest
from telethon.tl.types import InputNotifyPeer
from simple_term_menu import TerminalMenu
from colorama import init, Fore, Style
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

def get_sender_name(sender):
    """Определяет имя отправителя в зависимости от типа объекта."""
    if hasattr(sender, 'first_name'):  # Пользователь (User)
        return sender.first_name or sender.username or "Неизвестный"
    elif hasattr(sender, 'title'):  # Канал (Channel) или группа (Chat)
        return sender.title
    return "Неизвестный"

def determine_message_type(message):
    """Определяет тип сообщения."""
    if message.sticker:
        return "[Стикер]"
    elif message.photo:
        return "[Фото]"
    elif message.video:
        return "[Видео]"
    elif message.voice:
        return "[Голосовое сообщение]"
    elif message.document:
        return "[Файл]"
    elif message.text:
        return message.text
    return "[Неизвестный тип]"

async def load_unread_messages_from_dialogs():
    """Загружает все непрочитанные сообщения из диалогов с включенными уведомлениями."""
    global unread_messages
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        if dialog.unread_count > 0:
            chat = dialog.entity
            chat_name = chat.title if hasattr(chat, 'title') else get_sender_name(chat)
            try:
                peer = await client.get_input_entity(dialog.entity)
                notify_settings = await client(GetNotifySettingsRequest(peer=InputNotifyPeer(peer)))
                if not notify_settings.mute_until:
                    messages = await client.get_messages(dialog.entity, limit=dialog.unread_count)
                    for msg in messages:
                        sender = await msg.get_sender()
                        sender_name = get_sender_name(sender)
                        unread_messages.append({
                            'sender_name': sender_name,
                            'chat_id': chat.id,
                            'chat_name': chat_name,
                            'text': determine_message_type(msg)
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
        chat_info = current_chat_name or "не выбран пользователь"
        options = [
            "Список чатов",
            "Список каналов",
            "Выбрать чат",
            f"Отправить сообщение ({chat_info})",
            f"Просмотр медиа ({chat_info})",
            "Просмотреть непрочитанные сообщения",
            "Выход из аккаунта",
            "Выход"
        ]
        terminal_menu = TerminalMenu(options, title="Выберите действие")
        choice = options[terminal_menu.show()]
        if choice == "Список чатов":
            await view_chats()
        elif choice == "Список каналов":
            await view_channels()
        elif choice == "Выбрать чат":
            await select_chat()
        elif choice.startswith("Отправить сообщение"):
            await send_message()
        elif choice.startswith("Просмотр медиа"):
            await view_media()
        elif choice == "Просмотреть непрочитанные сообщения":
            await view_unread_messages()
        elif choice == "Выход из аккаунта":
            await logout_account()
        elif choice == "Выход":
            print("Выход из программы...")
            break

async def logout_account():
    """Выходит из текущего аккаунта и удаляет файл сессии."""
    clear_console()
    print("Выход из аккаунта...")
    try:
        await client.log_out()
        session_file = SESSION_NAME + ".session"
        if os.path.exists(session_file):
            os.remove(session_file)
            print("Файл сессии удален.")
        print("Вы успешно вышли из аккаунта.")
    except Exception as e:
        print(f"Ошибка при выходе из аккаунта: {e}")
    input("Нажмите Enter для завершения программы...")
    exit()

async def view_chats():
    clear_console()
    print("Загрузка чатов/групп...")
    try:
        dialogs = await client.get_dialogs()
        chats = [d for d in dialogs if not d.is_channel]
        if not chats:
            print("Нет доступных чатов/групп.")
            input("Нажмите Enter для возврата в главное меню...")
            return
        for i, chat in enumerate(chats):
            name = chat.name or "Без имени"
            chat_id = chat.entity.id
            print(f"{i + 1}. {name} ({chat_id})")
        input("\nНажмите Enter для возврата в главное меню...")
    except Exception as e:
        print(f"Ошибка при загрузке чатов/групп: {e}")
        input("Нажмите Enter для возврата в главное меню...")

async def view_channels():
    clear_console()
    print("Загрузка каналов...")
    try:
        dialogs = await client.get_dialogs()
        channels = [d for d in dialogs if d.is_channel]
        if not channels:
            print("Нет доступных каналов.")
            input("Нажмите Enter для возврата в главное меню...")
            return
        for i, channel in enumerate(channels):
            name = channel.name or "Без имени"
            channel_id = channel.entity.id
            print(f"{i + 1}. {name} ({channel_id})")
        input("\nНажмите Enter для возврата в главное меню...")
    except Exception as e:
        print(f"Ошибка при загрузке каналов: {e}")
        input("Нажмите Enter для возврата в главное меню...")

async def select_chat():
    global current_chat_id, current_chat_name
    clear_console()
    print("Загрузка чатов/групп...")
    try:
        dialogs = await client.get_dialogs()
        filtered_dialogs = [d for d in dialogs if not d.is_channel]
        if not filtered_dialogs:
            print("Нет доступных чатов/групп.")
            input("Нажмите Enter для возврата в главное меню...")
            return
        chat_options = [f"{d.name} ({d.entity.id})" for d in filtered_dialogs]
        terminal_menu = TerminalMenu(chat_options, title="Выбор чата")
        selected_index = terminal_menu.show()
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
    messages = await client.get_messages(current_chat_id, limit=100)
    messages.reverse()
    for msg in messages:
        sender = await msg.get_sender()
        sender_name = get_sender_name(sender)
        print(f"{sender_name}: {determine_message_type(msg)}")
    input("\nНажмите Enter для возврата в главное меню...")

async def send_message():
    if current_chat_id is None:
        print("Сначала выберите чат!")
        return
    clear_console()
    message = input("Введите сообщение: ")
    if message:
        await client.send_read_acknowledge(current_chat_id)
        await client.send_message(current_chat_id, message)
        print("Сообщение отправлено!")
        global unread_messages
        unread_messages = [msg for msg in unread_messages if msg['chat_id'] != current_chat_id]
    input("\nНажмите Enter для возврата в главное меню...")

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
        input("\nНажмите Enter для возврата в главное меню...")
        return
    media_options = []
    for i, msg in enumerate(media_messages):
        media_type = determine_message_type(msg)
        media_options.append(f"{i + 1}. {media_type} от {get_sender_name(await msg.get_sender())}")
    terminal_menu = TerminalMenu(media_options, title="Выбор медиафайла")
    selected_index = terminal_menu.show()
    if selected_index is not None:
        selected_msg = media_messages[selected_index]
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            media_path = await client.download_media(selected_msg.media, file=temp_file.name)
        if selected_msg.photo:
            print("Открытие изображения...")
            try:
                img = Image.open(media_path)
                img.show()
            except Exception as e:
                print(f"Ошибка при открытии изображения: {e}")
        elif selected_msg.video or selected_msg.document:
            print("Открытие файла...")
            try:
                if os.name == 'nt':
                    os.startfile(media_path)
                elif os.name == 'posix':
                    subprocess.run(['open', media_path] if os.uname().sysname == 'Darwin' else ['xdg-open', media_path])
            except Exception as e:
                print(f"Ошибка при открытии файла: {e}")
        choice = input("Хотите сохранить файл? (y/N): ").strip().lower()
        if choice == 'y':
            save_path = input("Введите путь для сохранения файла: ").strip()
            if save_path:
                try:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    os.rename(media_path, save_path)
                    print(f"Файл сохранен: {save_path}")
                except Exception as e:
                    print(f"Ошибка при сохранении файла: {e}")
            else:
                print("Путь не указан. Файл не сохранен.")
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
    input("\nНажмите Enter для возврата в главное меню...")

async def view_unread_messages():
    global unread_messages
    if not unread_messages:
        print("Нет непрочитанных сообщений.")
        input("\nНажмите Enter для возврата в главное меню...")
        return
    clear_console()
    print("Непрочитанные сообщения:")
    for i, msg in enumerate(unread_messages):
        sender_name = msg['sender_name']
        text = msg['text']
        print(f"{i + 1}. {sender_name}: {text}")
    options = ["Перейти в чат", "Пометить как прочитанное", "Вернуться в главное меню"]
    terminal_menu = TerminalMenu(options, title="Действия с непрочитанными сообщениями")
    choice = options[terminal_menu.show()]
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
        input("\nНажмите Enter для возврата в главное меню...")
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
            global current_chat_id, current_chat_name
            current_chat_id = selected_msg['chat_id']
            current_chat_name = selected_msg['chat_name']
            print(f"Переход в чат: {current_chat_name}")
            await view_chat_messages()
        else:
            print("Неверный номер сообщения.")
    except ValueError:
        print("Введите корректный номер.")
    input("\nНажмите Enter для возврата в главное меню...")

async def mark_as_read():
    global unread_messages
    if not unread_messages:
        print("Нет непрочитанных сообщений.")
        input("\nНажмите Enter для возврата в главное меню...")
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
            selected_msg = unread_messages.pop(index)
            chat_id = selected_msg['chat_id']
            await client.send_read_acknowledge(chat_id)
            print("Сообщение помечено как прочитанное.")
        else:
            print("Неверный номер сообщения.")
    except ValueError:
        print("Введите корректный номер.")
    input("\nНажмите Enter для возврата в главное меню...")

async def listen_for_new_messages():
    @client.on(events.NewMessage())
    async def handler(event):
        try:
            if event.is_private or event.mentioned:
                sender = await event.get_sender()
                sender_name = get_sender_name(sender)
                chat_id = event.chat_id
                try:
                    chat = await event.get_chat()
                    chat_name = chat.title if hasattr(chat, 'title') else sender_name
                except AttributeError:
                    chat_name = sender_name
                text = determine_message_type(event.message)
                global unread_messages
                unread_messages.append({
                    'sender_name': sender_name,
                    'chat_id': chat_id,
                    'chat_name': chat_name,
                    'text': text
                })
                print(f"\nНовое непрочитанное сообщение от {sender_name}: {text}")
        except Exception as e:
            print(f"Ошибка при обработке нового сообщения: {e}")

async def main():
    async with client:
        await load_unread_messages_from_dialogs()
        asyncio.create_task(listen_for_new_messages())
        await main_menu()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())