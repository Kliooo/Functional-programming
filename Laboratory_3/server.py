import asyncio

clients = {}

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Новое подключение: {addr}")

    try:
        username = (await reader.readline()).decode().strip()
        room = (await reader.readline()).decode().strip()

        # Если это личный чат, убедимся, что в комнате только два человека
        if room.startswith("private_"):
            if room in clients and len(clients[room]) > 1:
                writer.write("Комната уже занята.\n".encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
        
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
    if room in clients:
        active_users = [client[0] for client in clients[room]]
        message = f"Активные пользователи в комнате {room}: {', '.join(active_users)}\n"
        for _, writer in clients[room]:
            writer.write(message.encode())
            await writer.drain()


async def send_message_to_room(room, message):
    if room in clients:
        for username, writer in clients[room]:
            writer.write(f"{message}\n".encode())
            await writer.drain()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")
    async with server:
        await server.serve_forever()

asyncio.run(main())
