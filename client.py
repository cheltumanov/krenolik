from enum import Enum
from random import choice
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import socket
import threading
import json

class Const(Enum):
    OFFSET = 100
    SIDE = 150
    MID = 75
    FONT = "Arial"
    CELL_FONT_SIZE = 56
    LABEL_FONT_SIZE = 16
    WINSIZE = 650
    ROWCOL = 3
    PLAYER_CHAR = "X"
    PC_CHAR = "O"
    EMPTY_CHAR = "0"
    TURN_PLAYER = 0
    TURN_CPU = 1

class Point:
    def __init__(self, x, y, offset=0):
        self.x = x + offset
        self.y = y + offset

    def add(self, offset):
        return Point(self.x + offset, self.y + offset)

class Cell:
    def __init__(self, canvas, i, j):
        self.canvas = canvas
        self.i = i
        self.j = j
        self.start = Point(i * Const.SIDE.value,
                           j * Const.SIDE.value,
                           offset=Const.OFFSET.value)
        self.mid = self.start.add(Const.MID.value)
        self.textId = 0
        self.marked = False
        self.marker = Const.EMPTY_CHAR.value

    def mark(self, char):
        if self.marked:
            return False

        self.marker = char
        self.textId = self.canvas.create_text(
                           self.mid.x,
                           self.mid.y,
                           text=self.marker,
                           font=(Const.FONT.value,
                                 Const.CELL_FONT_SIZE.value))
        self.marked = True
        return True

    def markPlayer(self):
        return self.mark(Const.PLAYER_CHAR.value)

    def markPC(self):
        return self.mark(Const.PC_CHAR.value)

    def unmark(self):
        if not self.marked:
            return False

        self.canvas.delete(self.textId)
        self.marked = False
        self.marker = Const.EMPTY_CHAR.value
        return True

    def getMarker(self):
        return self.marker

# LOGIC LAYER
class GameLogic:
    def __init__(self):
        self.cells = [[Cell(None, i, j) for i in range(Const.ROWCOL.value)] 
                      for j in range(Const.ROWCOL.value)]
        self.turn = Const.TURN_PLAYER.value
        self.player_score = 0
        self.cpu_score = 0
        self.player_symbol = 'X'  # По умолчанию X
        self.is_online = False
        self.my_turn = True

    def playerSelected(self, i, j):
        valid = lambda x: 0 <= x < Const.ROWCOL.value
        if not valid(i) or not valid(j):
            return False
        return self.cells[i][j].markPlayer()

    def aiTurn(self):
        slots = self.getEmptySlots()
        if len(slots) == 0:
            return
        (row, col) = choice(slots)
        self.cells[row][col].markPC()

    def clear(self, winner="none"):
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                self.cells[i][j].unmark()

        if winner == "player":
            self.player_score += 1
        elif winner == "cpu":
            self.cpu_score += 1
        
        if self.turn == Const.TURN_PLAYER.value:
            self.turn = Const.TURN_CPU.value
        elif self.turn == Const.TURN_CPU.value:
            self.turn = Const.TURN_PLAYER.value

    def check(self, rowColPairs, marker):
        for (row, col) in rowColPairs:
            if marker != self.cells[row][col].getMarker():
                return False
        return True

    def getColPair(self, row):
        return [(row, i) for i in range(Const.ROWCOL.value)]

    def getRowPair(self, col):
        return [(i, col) for i in range(Const.ROWCOL.value)]

    def checkWinner(self, char):
        for row in range(Const.ROWCOL.value):
            if self.check(self.getColPair(row), char):
                return True

        for col in range(Const.ROWCOL.value):
            if self.check(self.getRowPair(col), char):
                return True

        if self.check([(0, 0), (1, 1), (2, 2)], char):
            return True
        if self.check([(0, 2), (1, 1), (2, 0)], char):
            return True
        
        return False

    def checkPlayerWin(self):
        return self.checkWinner(Const.PLAYER_CHAR.value)

    def checkCpuWin(self):
        return self.checkWinner(Const.PC_CHAR.value)

    def getEmptySlots(self):
        slots = []
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                if self.cells[i][j].getMarker() == Const.EMPTY_CHAR.value:
                    slots.append((i, j))
        return slots

    def checkDrawn(self):
        return len(self.getEmptySlots()) == 0

    def getScores(self):
        return self.player_score, self.cpu_score

# ONLINE CLIENT
class OnlineClient:
    def __init__(self, game_view, host='127.0.0.1', port=5555):
        self.game_view = game_view
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.player_symbol = None
        self.room_id = None
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Запускаем поток для приема сообщений
            thread = threading.Thread(target=self.receive_messages)
            thread.daemon = True
            thread.start()
            
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            return False
    
    def receive_messages(self):
        while self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(message)
                
            except:
                break
        
        self.connected = False
        if self.game_view:
            self.game_view.root.after(0, lambda: messagebox.showinfo(
                "Disconnected", "Disconnected from server"))
    
    def process_message(self, message):
        msg_type = message.get('type')
        
        if msg_type == 'assign_symbol':
            self.player_symbol = message['symbol']
            self.room_id = message['room_id']
            self.game_view.root.after(0, lambda: self.game_view.update_status(
                f"You are {self.player_symbol}. Waiting for opponent..."))
            
        elif msg_type == 'game_start':
            self.game_view.logic.is_online = True
            self.game_view.logic.player_symbol = self.player_symbol
            self.game_view.logic.my_turn = message['turn']
            self.game_view.root.after(0, lambda: self.game_view.update_status(
                f"Game started! You are {self.player_symbol}. {'Your turn' if message['turn'] else 'Opponent turn'}"))
            
        elif msg_type == 'move_made':
            row, col, symbol = message['row'], message['col'], message['symbol']
            
            # Отмечаем клетку на доске
            cell = self.game_view.logic.cells[row][col]
            self.game_view.root.after(0, lambda: cell.mark(symbol))
            
        elif msg_type == 'turn_change':
            self.game_view.logic.my_turn = (message['turn'] == self.player_symbol)
            self.game_view.root.after(0, lambda: self.game_view.update_status(
                f"{'Your turn' if self.game_view.logic.my_turn else 'Opponent turn'}"))
            
        elif msg_type == 'game_over':
            winner = message['winner']
            if winner == self.player_symbol:
                self.game_view.root.after(0, lambda: messagebox.showinfo("Game Over", "You won!"))
                self.game_view.logic.player_score += 1
            elif winner == 'draw':
                self.game_view.root.after(0, lambda: messagebox.showinfo("Game Over", "It's a draw!"))
            else:
                self.game_view.root.after(0, lambda: messagebox.showinfo("Game Over", "You lost!"))
                self.game_view.logic.cpu_score += 1
            
            self.game_view.root.after(0, lambda: self.game_view.reset_board())
            
        elif msg_type == 'game_reset':
            self.game_view.root.after(0, lambda: self.game_view.reset_board())
            
        elif msg_type == 'opponent_disconnected':
            self.game_view.root.after(0, lambda: messagebox.showinfo(
                "Opponent left", "Opponent disconnected"))
            self.game_view.logic.is_online = False
            
        elif msg_type == 'error':
            self.game_view.root.after(0, lambda: messagebox.showerror("Error", message['message']))
    
    def send_move(self, row, col):
        if not self.connected:
            return False
        
        try:
            message = {
                'type': 'move',
                'row': row,
                'col': col
            }
            self.socket.send(json.dumps(message).encode('utf-8'))
            return True
        except:
            return False
    
    def disconnect(self):
        self.connected = False
        if self.socket:
            self.socket.close()

# VIEW LAYER
class Score:
    def __init__(self, root, logic):
        self.logic = logic
        self.playerScore = 0
        self.cpuScore = 0
        
        self.playerLabel = ttk.Label(root,
                                     font=(Const.FONT.value,
                                           Const.LABEL_FONT_SIZE.value))
        self.playerLabel.place(x=100, y=35, width=Const.SIDE.value)        
        self.cpuLabel = ttk.Label(root,
                                  font=(Const.FONT.value,
                                        Const.LABEL_FONT_SIZE.value),
                                  anchor='e')
        self.cpuLabel.place(x=400, y=35, width=Const.SIDE.value)
        self.updateScore()

    def updateScore(self):
        player, cpu = self.logic.getScores()
        self.playerLabel.config(text=f"You - {player}")
        self.cpuLabel.config(text=f"Cpu - {cpu}")

    def playerWon(self):
        self.playerScore += 1
        self.updateScore()

    def cpuWon(self):
        self.cpuScore += 1
        self.updateScore()

class GameView:
    def __init__(self, root):
        self.root = root
        self.logic = GameLogic()
        self.canvas = self.setupCanvas(root)
        self.score = Score(root, self.logic)
        self.linkCellsToCanvas()
        self.online_client = None
        self.status_label = self.setupStatusLabel(root)
        
        # Добавляем кнопки для сетевой игры
        self.setupNetworkButtons(root)

    def setupCanvas(self, root):
        c = Canvas(root)
        c.place(x=0, y=0, height=Const.WINSIZE.value, width=Const.WINSIZE.value)
        
        c.create_line(250, 100, 250, 550, width=5, fill="#aaa")
        c.create_line(400, 100, 400, 550, width=5, fill="#aaa")
        c.create_line(100, 250, 550, 250, width=5, fill="#aaa")
        c.create_line(100, 400, 550, 400, width=5, fill="#aaa")
        
        c.bind("<Button-1>", self.mouseCb)
        return c

    def setupStatusLabel(self, root):
        label = ttk.Label(root, text="Local game", 
                         font=(Const.FONT.value, 10))
        label.place(x=250, y=600)
        return label

    def setupNetworkButtons(self, root):
        # Кнопка подключения к серверу
        self.connect_btn = ttk.Button(root, text="Connect to Server", 
                                      command=self.show_connect_dialog)
        self.connect_btn.place(x=50, y=600)
        
        # Кнопка отключения
        self.disconnect_btn = ttk.Button(root, text="Disconnect", 
                                        command=self.disconnect_from_server,
                                        state='disabled')
        self.disconnect_btn.place(x=180, y=600)
        
        # Кнопка локальной игры
        self.local_btn = ttk.Button(root, text="Local Game", 
                                   command=self.switch_to_local)
        self.local_btn.place(x=450, y=600)

    def show_connect_dialog(self):
        dialog = Toplevel(self.root)
        dialog.title("Connect to Server")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Server IP:").pack(pady=5)
        ip_entry = ttk.Entry(dialog)
        ip_entry.insert(0, "127.0.0.1")
        ip_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Port:").pack(pady=5)
        port_entry = ttk.Entry(dialog)
        port_entry.insert(0, "5555")
        port_entry.pack(pady=5)
        
        def connect():
            ip = ip_entry.get()
            port = int(port_entry.get())
            dialog.destroy()
            self.connect_to_server(ip, port)
        
        ttk.Button(dialog, text="Connect", command=connect).pack(pady=10)

    def connect_to_server(self, host, port):
        self.online_client = OnlineClient(self, host, port)
        if self.online_client.connect():
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.local_btn.config(state='disabled')
            self.update_status("Connecting to server...")

    def disconnect_from_server(self):
        if self.online_client:
            self.online_client.disconnect()
            self.online_client = None
        
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.local_btn.config(state='normal')
        self.logic.is_online = False
        self.update_status("Local game")
        self.reset_board()

    def switch_to_local(self):
        self.logic.is_online = False
        self.update_status("Local game")
        self.reset_board()

    def update_status(self, text):
        self.status_label.config(text=text)

    def reset_board(self):
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                self.logic.cells[i][j].unmark()

    def linkCellsToCanvas(self):
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                self.logic.cells[i][j].canvas = self.canvas

    def mouseCb(self, event):
        index = lambda x: (x - Const.OFFSET.value) // Const.SIDE.value
        j = index(event.x)
        i = index(event.y)

        # Проверка границ
        if i < 0 or i >= Const.ROWCOL.value or j < 0 or j >= Const.ROWCOL.value:
            return

        # Онлайн режим (нахуй я его начал делать)
        if self.logic.is_online and self.online_client and self.online_client.connected:
            if not self.logic.my_turn:
                messagebox.showinfo("Not your turn", "Wait for opponent's move")
                return
            
            if self.logic.cells[i][j].getMarker() != Const.EMPTY_CHAR.value:
                return
            
            # Отправляем ход на сервер
            if self.online_client.send_move(i, j):
                # Временно отмечаем клетку (сервер подтвердит)
                self.logic.cells[i][j].mark(self.logic.player_symbol)
                self.logic.my_turn = False
                self.update_status("Waiting for opponent...")
            return

        # Локальный режим (против компьютера)
        if not self.logic.playerSelected(i, j):
            return

        if self.logic.checkPlayerWin():
            messagebox.showinfo("You won", "You won the round.")
            self.logic.clear(winner="player")
            self.score.updateScore()
            return

        self.logic.aiTurn()

        if self.logic.checkCpuWin():
            messagebox.showinfo("Cpu won", "Cpu won the round.")
            self.logic.clear(winner="cpu")
            self.score.updateScore()
            return

        if self.logic.checkDrawn():
            messagebox.showinfo("Game drawn", "The round has been drawn.")
            self.logic.clear()
            self.score.updateScore()

    def run(self):
        self.root.mainloop()

def main():
    root = Tk()
    root.title("Tic-tac-toe Online")
    root.geometry(f"{Const.WINSIZE.value}x{Const.WINSIZE.value + 50}+500+500")
    root.resizable(False, False)
    
    game = GameView(root)
    game.run()

if __name__ == "__main__":
    main()