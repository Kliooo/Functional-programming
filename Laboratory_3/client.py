import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
from datetime import datetime

asyncio_loop = None
reader = None
writer = None
username = None

# Функция для получения сообщений от сервера
async def get_messages(reader, text_widget, active_users_widget):
    while True:
        data = await reader.read(100)
        if not data:
            break
        message = data.decode()

        if message.startswith("Активные пользователи в комнате"):
            active_users_widget.config(state=tk.NORMAL)
            active_users_widget.delete(1.0, tk.END)
            active_users_widget.insert(tk.END, message + '\n')
            active_users_widget.config(state=tk.DISABLED)
        elif "присоединился к комнате" in message or "покинул комнату" in message:
            text_widget.insert(tk.END, f"{message}\n")
            text_widget.see(tk.END)
        else:
            text_widget.insert(tk.END, f"{message}\n")
            text_widget.see(tk.END)

# Функция для отправки сообщений на сервер
async def send_message(writer, message):
    timestamp = datetime.now().strftime("%H:%M")
    full_message = f"{username}({timestamp}): {message}"
    writer.write((full_message + '\n').encode())
    await writer.drain()

def on_send_button_click():
    message = entry_widget.get()
    entry_widget.delete(0, tk.END)
    asyncio.run_coroutine_threadsafe(send_message(writer, message), asyncio_loop)

async def register_client(ip, username, room):
    global reader, writer
    reader, writer = await asyncio.open_connection(ip, 8888)
    
    writer.write(f"{username}\n".encode())
    await writer.drain()
    writer.write(f"{room}\n".encode())
    await writer.drain()

    print(f"Клиент {username} зарегистрирован в комнате {room}")
    asyncio.create_task(get_messages(reader, text_widget, active_users_widget))

def start_chat(ip, username, room):
    asyncio.run_coroutine_threadsafe(register_client(ip, username, room), asyncio_loop)
    root.deiconify()

async def main():
    global reader, writer
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888)
    asyncio.create_task(get_messages(reader, text_widget, active_users_widget))

def start_client():
    global asyncio_loop
    asyncio_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(asyncio_loop)
    asyncio_loop.run_forever()

def prompt_user_info():
    dialog = tk.Toplevel(root)
    dialog.title("Введите данные для подключения")
    dialog.geometry("300x250")
    dialog.grab_set()

    center_window(dialog, 300, 250)

    tk.Label(dialog, text="IP сервера:").pack(pady=5)
    ip_entry = tk.Entry(dialog)
    ip_entry.insert(0, "127.0.0.1")
    ip_entry.pack()

    tk.Label(dialog, text="Имя пользователя:").pack(pady=5)
    username_entry = tk.Entry(dialog)
    username_entry.pack()

    tk.Label(dialog, text="Номер комнаты:").pack(pady=5)
    room_entry = tk.Entry(dialog)
    room_entry.pack()

    # Добавляем чекбокс для выбора личного чата
    private_chat_var = tk.BooleanVar()
    private_chat_checkbox = tk.Checkbutton(dialog, text="Личный чат", variable=private_chat_var)
    private_chat_checkbox.pack(pady=5)

    def on_confirm():
        global username
        ip = ip_entry.get()
        username = username_entry.get()
        room = room_entry.get()
        if ip and username and room:
            # Если выбран личный чат, создаем уникальную комнату
            if private_chat_var.get():
                room = f"private_{username}"
            start_chat(ip, username, room)
            dialog.destroy()

    tk.Button(dialog, text="Войти", command=on_confirm).pack(pady=5)
    dialog.protocol("WM_DELETE_WINDOW", root.destroy)

# Функция для отключения клиента
async def disconnect_client():
    global writer
    if writer:
        writer.close()
        await writer.wait_closed()
    root.destroy()

def on_disconnect_button_click():
    asyncio.run_coroutine_threadsafe(disconnect_client(), asyncio_loop)

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    position_top = int(screen_height / 2 - height / 2)
    position_left = int(screen_width / 2 - width / 2)
    window.geometry(f'{width}x{height}+{position_left}+{position_top}')

# Интерфейс tkinter для чата
root = tk.Tk()
root.geometry("800x400")
root.title("Чат клиент")
center_window(root, 800, 400)
root.withdraw()

# Контейнер для виджета активных пользователей и кнопки отключения
top_frame = tk.Frame(root)
top_frame.pack(padx=10, pady=5, fill="x")

# Виджет для отображения активных пользователей
active_users_widget = tk.Text(top_frame, height=1, wrap=tk.WORD, bg="#f0f0f0", fg="black", state=tk.DISABLED)
active_users_widget.pack(side="left", fill="x", expand=True)

# Кнопка для отключения от сервера и завершения программы
disconnect_button = tk.Button(top_frame, text="Отключиться", command=on_disconnect_button_click)
disconnect_button.pack(side="right", padx=(5, 0))

text_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
text_widget.pack(padx=10, pady=10, fill="both", expand=True)

input_frame = tk.Frame(root)
input_frame.pack(padx=10, pady=5, fill="x")

entry_widget = tk.Entry(input_frame)
entry_widget.pack(side="left", fill="x", expand=True)
entry_widget.insert(0, "Введите сообщение...")
entry_widget.config(fg="grey")

def on_entry_focus_in(event):
    if entry_widget.get() == "Введите сообщение...":
        entry_widget.delete(0, "end")
        entry_widget.config(fg="black")

def on_entry_focus_out(event):
    if entry_widget.get() == "":
        entry_widget.insert(0, "Введите сообщение...")
        entry_widget.config(fg="grey")

entry_widget.bind("<FocusIn>", on_entry_focus_in)
entry_widget.bind("<FocusOut>", on_entry_focus_out)
entry_widget.bind("<Return>", lambda event: on_send_button_click())

send_button = tk.Button(input_frame, text="Отправить", command=on_send_button_click)
send_button.pack(side="right", padx=(5,0))

client_thread = threading.Thread(target=start_client, daemon=True)
client_thread.start()

prompt_user_info()

root.protocol("WM_DELETE_WINDOW", lambda: asyncio.run_coroutine_threadsafe(disconnect_client(), asyncio_loop))

root.mainloop()
