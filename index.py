from enum import Enum
from random import choice
from tkinter import *
from tkinter import ttk
from tkinter import messagebox 
import functools
import time

# Декоратор для логирования вызовов методов
def log_method_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling: {func.__name__}")
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} completed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Декоратор для проверки валидности индексов
def validate_indices(func):
    @functools.wraps(func)
    def wrapper(self, i, j, *args, **kwargs):
        valid = lambda x: 0 <= x < Const.ROWCOL.value
        if not valid(i) or not valid(j):
            print(f"Invalid indices: ({i}, {j})")
            return False
        return func(self, i, j, *args, **kwargs)
    return wrapper

# Декоратор для проверки возможности хода
def check_turn(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'turn') and self.turn != Const.TURN_PLAYER.value:
            print("Not player's turn")
            return False
        return func(self, *args, **kwargs)
    return wrapper

# Декоратор для кэширования результатов проверки победы
def cache_winner_check(func):
    cache = {}
    @functools.wraps(func)
    def wrapper(self, char):
        # Создаем ключ на основе состояния клеток
        cells_state = tuple(self.cells[i][j].getMarker() 
                          for i in range(Const.ROWCOL.value) 
                          for j in range(Const.ROWCOL.value))
        key = (char, cells_state)
        
        if key not in cache:
            cache[key] = func(self, char)
        return cache[key]
    return wrapper

# Декоратор для синхронизации с GUI
def sync_with_gui(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if hasattr(self, 'canvas'):
            self.canvas.update()
        return result
    return wrapper

# Декоратор для обработки исключений
def handle_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None
    return wrapper

# Декоратор для замедления выполнения (для отладки)
def delay_execution(seconds=0.5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(seconds)
            return func(*args, **kwargs)
        return wrapper
    return decorator

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

    @log_method_call
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

    @log_method_call
    @sync_with_gui
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

    @log_method_call
    def markPlayer(self):
        return self.mark(Const.PLAYER_CHAR.value)

    @log_method_call
    def markPC(self):
        return self.mark(Const.PC_CHAR.value)

    @log_method_call
    @sync_with_gui
    def unmark(self):
        if not self.marked:
            return False

        self.canvas.delete(self.textId)
        self.marked = False
        self.marker = Const.EMPTY_CHAR.value
        return True

    @property
    def marker_value(self):
        return self.marker

    def getMarker(self):
        return self.marker

# ============= LOGIC LAYER =============
class GameLogic:
    def __init__(self):
        self.cells = [[Cell(None, i, j) for i in range(Const.ROWCOL.value)] 
                      for j in range(Const.ROWCOL.value)]
        self.turn = Const.TURN_PLAYER.value
        self.player_score = 0
        self.cpu_score = 0

    @log_method_call
    @validate_indices
    @check_turn
    def playerSelected(self, i, j):
        return self.cells[i][j].markPlayer()

    @log_method_call
    def aiTurn(self):
        slots = self.getEmptySlots()
        if len(slots) == 0:
            return
        (row, col) = choice(slots)
        self.cells[row][col].markPC()

    @log_method_call
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

    @staticmethod
    def check(rowColPairs, marker, cells):
        for (row, col) in rowColPairs:
            if marker != cells[row][col].getMarker():
                return False
        return True

    def getColPair(self, row):
        return [(row, i) for i in range(Const.ROWCOL.value)]

    def getRowPair(self, col):
        return [(i, col) for i in range(Const.ROWCOL.value)]

    @log_method_call
    @cache_winner_check
    def checkWinner(self, char):
        for row in range(Const.ROWCOL.value):
            if self.check(self.getColPair(row), char, self.cells):
                return True

        for col in range(Const.ROWCOL.value):
            if self.check(self.getRowPair(col), char, self.cells):
                return True

        if self.check([(0, 0), (1, 1), (2, 2)], char, self.cells):
            return True
        if self.check([(0, 2), (1, 1), (2, 0)], char, self.cells):
            return True
        
        return False

    def checkPlayerWin(self):
        return self.checkWinner(Const.PLAYER_CHAR.value)

    def checkCpuWin(self):
        return self.checkWinner(Const.PC_CHAR.value)

    @property
    def empty_slots(self):
        slots = []
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                if self.cells[i][j].getMarker() == Const.EMPTY_CHAR.value:
                    slots.append((i, j))
        return slots

    def getEmptySlots(self):
        return self.empty_slots

    def checkDrawn(self):
        return len(self.getEmptySlots()) == 0

    def getScores(self):
        return self.player_score, self.cpu_score

# ============= VIEW LAYER =============
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

    @log_method_call
    def setupCanvas(self, root):
        c = Canvas(root)
        c.place(x=0, y=0, height=Const.WINSIZE.value, width=Const.WINSIZE.value)
        
        c.create_line(250, 100, 250, 550, width=5, fill="#aaa")
        c.create_line(400, 100, 400, 550, width=5, fill="#aaa")
        c.create_line(100, 250, 550, 250, width=5, fill="#aaa")
        c.create_line(100, 400, 550, 400, width=5, fill="#aaa")
        
        c.bind("<Button-1>", self.mouseCb)
        return c

    def linkCellsToCanvas(self):
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                self.logic.cells[i][j].canvas = self.canvas

    @handle_exceptions
    @log_method_call
    def mouseCb(self, event):
        index = lambda x: (x - Const.OFFSET.value) // Const.SIDE.value
        j = index(event.x)
        i = index(event.y)

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

@handle_exceptions
def main():
    root = Tk()
    root.title("Tic-tac-toe")
    root.geometry(f"{Const.WINSIZE.value}x{Const.WINSIZE.value}+500+500")
    root.resizable(False, False)
    
    game = GameView(root)
    game.run()

if __name__ == "__main__":
    main()