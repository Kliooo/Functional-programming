import asyncio

clients = {}

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Новое подключение: {addr}")

    try:
        username = (await reader.readline()).decode().strip()
        room = (await reader.readline()).decode().strip()

        if room not in clients:
            clients[room] = []
        clients[room].append((username, writer))
        print(f"Клиент {username}{addr} подключился в комнату {room}")

        await send_active_users_to_room(room)

        await send_message_to_room(room, f"{username} присоединился к комнате.")

        while True:
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            print(f"{username} ({addr}) в комнате {room}: {message}")
            await send_message_to_room(room, message)

    finally:
        # Удаление клиента и обновление списка активных пользователей
        if room in clients:
            clients[room] = [client for client in clients[room] if client[1] != writer]
            await send_active_users_to_room(room)

        print(f"Клиент {username}{addr} отключился из комнаты {room}")
        await send_message_to_room(room, f"{username} покинул комнату.")

        writer.close()
        await writer.wait_closed()


async def send_active_users_to_room(room):
    # Отправка списка активных пользователей
    if room in clients:
        active_users = [username for username, _ in clients[room]]
        message = f"Активные пользователи в комнате {room}: " + ", ".join(active_users)
        await send_message_to_room(room, message)

async def send_message_to_room(room, message):
    # Отправка сообщения всем пользователям в комнате
    if room in clients:
        for _, writer in clients[room]:
            writer.write(f"{message}\n".encode())
            await writer.drain()


async def main():
    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888
    )
    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
