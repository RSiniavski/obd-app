import socket
from emulator.mock_data import OBDMockEngine


def start_emulator_server(host: str, port: int):
    engine = OBDMockEngine()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"[Emulator] Сервер запущено на {host}:{port}...")

    while True:
        try:
            conn, addr = server_socket.accept()
            print(f"[Emulator] Підключено клієнта: {addr}")

            buffer = ""
            while True:
                data = conn.recv(1024)
                if not data:
                    print("[Emulator] Клієнт від'єднався.")
                    break

                buffer += data.decode("utf-8", errors="ignore")

                # Розбиваємо за символами \r або \n (будь-які закінчення команд)
                while "\r" in buffer or "\n" in buffer:
                    # Замінюємо \r\n на \r для уніфікації
                    buffer = buffer.replace("\r\n", "\r").replace("\n", "\r")
                    cmd, buffer = buffer.split("\r", 1)
                    cmd = cmd.strip()

                    if cmd:
                        print(f"[OBD Cmd Recv]: {cmd}")
                        response = engine.process_command(cmd)
                        conn.sendall(response.encode("utf-8"))

        except (ConnectionResetError, ConnectionAbortedError):
            print("[Emulator] З'єднання було скинуте клієнтом. Очікування нового підключення...")
        except Exception as e:
            print(f"[Emulator] Помилка: {e}")
        finally:
            try:
                conn.close()
            except NameError:
                pass