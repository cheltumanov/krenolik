from enum import Enum
from random import choice
from tkinter import *
from tkinter import ttk
from tkinter import messagebox 

gameState = None

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
    
class Score:
    def __init__(self, root):
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
        self.playerLabel.config(text=f"You - {self.playerScore}")
        self.cpuLabel.config(text=f"Cpu - {self.cpuScore}")


    def playerWon(self):
        self.playerScore += 1
        self.updateScore()


    def cpuWon(self):
        self.cpuScore += 1
        self.updateScore()

class GameState:
    def __init__(self, root):
        self.canvas = self.setupCanvas(root)
        self.cells = [[Cell(self.canvas, i, j) for i in range(Const.ROWCOL.value)] for j in range(Const.ROWCOL.value)]        
        self.score = Score(root)
        self.turn = Const.TURN_PLAYER.value

    
    def setupCanvas(self, root):
        c = Canvas(root)
        c.place(x=0, y=0, height=Const.WINSIZE.value, width=Const.WINSIZE.value)
        c.create_line(250, 100, 250, 550, width=5, fill="#aaa")
        c.create_line(400, 100, 400, 550, width=5, fill="#aaa")
        c.create_line(100, 250, 550, 250, width=5, fill="#aaa")
        c.create_line(100, 400, 550, 400, width=5, fill="#aaa")
        c.bind("<Button-1>", mouseCb)
        return c


    def playerSelected(self, i, j):
        valid = lambda x : 0 <= x < Const.ROWCOL.value
        if not valid(i) or not valid(j):
            return False
        return self.cells[i][j].markPlayer()


    def clear(self, winner="none"):
        for i in range(Const.ROWCOL.value):
            for j in range(Const.ROWCOL.value):
                self.cells[i][j].unmark()

        match winner:
            case "player": self.score.playerWon()
            case "cpu": self.score.cpuWon()
            case "_": pass
        
        if self.turn == Const.TURN_PLAYER.value:
            self.turn = Const.TURN_CPU.value
            self.aiTurn()
        elif self.turn == Const.TURN_CPU.value:
            self.turn = Const.TURN_PLAYER.value


    def check(self, rowColPairs, marker):
        for (row, col) in rowColPairs:
            if (marker != self.cells[row][col].getMarker()):
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


    def aiTurn(self):
        slots = self.getEmptySlots()
        if len(slots) == 0:
            return
        (row, col) = choice(slots)
        self.cells[row][col].markPC()

def mouseCb(event):
    index = lambda x: (x - Const.OFFSET.value) // Const.SIDE.value
    j = index(event.x)
    i = index(event.y)

    if not gameState.playerSelected(i, j):
        return

    if gameState.checkPlayerWin():
        messagebox.showinfo("You won", "You won the round.")
        gameState.clear(winner="player")
        return

    gameState.aiTurn()

    if gameState.checkCpuWin():
        messagebox.showinfo("Cpu won", "Cpu won the round.")
        gameState.clear(winner="cpu")
        return

    if gameState.checkDrawn():
        messagebox.showinfo("Game drawn", "The round has been drawn.")
        gameState.clear()

def main():
    global gameState
    global pc
    root = Tk()
    root.title("Tic-tac-toe")
    root.geometry(f"{Const.WINSIZE.value}x{Const.WINSIZE.value}+500+500")
    root.resizable(False, False)
    gameState = GameState(root)
    root.mainloop()


if __name__ == "__main__":
    main()