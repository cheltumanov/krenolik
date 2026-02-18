import socket
import threading
import json
from enum import Enum

class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

class GameServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []  # (socket, address, player_symbol)
        self.rooms = {}  # room_id -> [player1, player2]
        self.current_room = None
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_turn = 'X'
        self.game_state = GameState.WAITING
        
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")
        
        while True:
            client_socket, address = self.server_socket.accept()
            print(f"New connection from {address}")
            
            # Создаем комнату или добавляем во вторую
            if len(self.clients) % 2 == 0:
                # Первый игрок в комнате
                player_symbol = 'X'
                room_id = len(self.clients) // 2
                self.rooms[room_id] = [client_socket]
                print(f"Created room {room_id} for player X")
            else:
                # Второй игрок в комнате
                player_symbol = 'O'
                room_id = (len(self.clients) - 1) // 2
                self.rooms[room_id].append(client_socket)
                print(f"Added player O to room {room_id}")
                
                # Запускаем игру в комнате
                self.start_game(room_id)
            
            self.clients.append((client_socket, address, player_symbol))
            
            # Отправляем игроку его символ
            self.send_message(client_socket, {
                'type': 'assign_symbol',
                'symbol': player_symbol,
                'room_id': room_id
            })
            
            # Запускаем поток для обработки сообщений от клиента
            thread = threading.Thread(target=self.handle_client, 
                                     args=(client_socket, player_symbol, room_id))
            thread.daemon = True
            thread.start()
    
    def start_game(self, room_id):
        """Начинает игру в комнате"""
        player1, player2 = self.rooms[room_id]
        
        # Отправляем обоим игрокам сообщение о начале игры
        self.send_message(player1, {
            'type': 'game_start',
            'message': 'Game started! You are X',
            'turn': True
        })
        
        self.send_message(player2, {
            'type': 'game_start',
            'message': 'Game started! You are O',
            'turn': False
        })
    
    # Обработка сообщений от клиента
    def handle_client(self, client_socket, player_symbol, room_id):
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(message, client_socket, player_symbol, room_id)
                
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            self.remove_client(client_socket, room_id)
    
    def process_message(self, message, client_socket, player_symbol, room_id):
        msg_type = message.get('type')
        
        if msg_type == 'move':
            # Проверяем, что ход правильный
            if player_symbol != self.current_turn:
                self.send_message(client_socket, {
                    'type': 'error',
                    'message': 'Not your turn!'
                })
                return
            
            row, col = message['row'], message['col']
            
            # Проверяем, что клетка свободна
            if self.board[row][col] != ' ':
                self.send_message(client_socket, {
                    'type': 'error',
                    'message': 'Cell already taken!'
                })
                return
            
            # Делаем ход
            self.board[row][col] = player_symbol
            
            # Отправляем ход всем игрокам в комнате
            for player in self.rooms[room_id]:
                self.send_message(player, {
                    'type': 'move_made',
                    'row': row,
                    'col': col,
                    'symbol': player_symbol
                })
            
            # Проверяем победу
            winner = self.check_winner()
            if winner:
                for player in self.rooms[room_id]:
                    self.send_message(player, {
                        'type': 'game_over',
                        'winner': winner
                    })
                self.reset_board()
            elif self.check_draw():
                for player in self.rooms[room_id]:
                    self.send_message(player, {
                        'type': 'game_over',
                        'winner': 'draw'
                    })
                self.reset_board()
            else:
                # Меняем ход
                self.current_turn = 'O' if player_symbol == 'X' else 'X'
                
                # Сообщаем, чей ход
                for player in self.rooms[room_id]:
                    self.send_message(player, {
                        'type': 'turn_change',
                        'turn': self.current_turn
                    })
        
        elif msg_type == 'reset':
            self.reset_board()
            for player in self.rooms[room_id]:
                self.send_message(player, {
                    'type': 'game_reset'
                })
    
    def check_winner(self):
        # Проверка строк
        for row in range(3):
            if self.board[row][0] == self.board[row][1] == self.board[row][2] != ' ':
                return self.board[row][0]
        
        # Проверка колонок
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != ' ':
                return self.board[0][col]
        
        # Проверка диагоналей
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != ' ':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != ' ':
            return self.board[0][2]
        
        return None
    
    def check_draw(self):
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == ' ':
                    return False
        return True
    
    def reset_board(self):
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_turn = 'X'
    
    def send_message(self, client_socket, message):
        try:
            client_socket.send(json.dumps(message).encode('utf-8'))
        except:
            pass
    
    def remove_client(self, client_socket, room_id):
        for player in self.rooms.get(room_id, []):
            if player != client_socket:
                self.send_message(player, {
                    'type': 'opponent_disconnected'
                })
        
        # Удаляем клиента из списков
        self.clients = [c for c in self.clients if c[0] != client_socket]
        if room_id in self.rooms:
            self.rooms[room_id] = [p for p in self.rooms[room_id] if p != client_socket]
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        client_socket.close()

if __name__ == "__main__":
    server = GameServer()
    server.start()