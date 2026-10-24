"""Графический терминал Tkinter с вводом команд и журналом диалога."""

import tkinter as tk
from tkinter import scrolledtext, ttk

from .scripts import run_script


class EmulatorWindow:
    """Связать виджеты с оболочкой и стартовым сценарием."""

    def __init__(self, root, shell, config, lines):
        """Создать журнал, приглашение и строку ввода."""
        self.root, self.shell = root, shell
        self.lines = lines
        self.history_index = len(shell.history)
        root.title(shell.title)
        root.geometry("980x600")
        root.minsize(650, 360)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.output = scrolledtext.ScrolledText(
            root, wrap="word", state="disabled", font=("Consolas", 11),
            background="#17212b", foreground="#e3e9ef", padx=12, pady=12,
        )
        self.output.pack(fill="both", expand=True, padx=10, pady=10)
        row = ttk.Frame(root, padding=(10, 0, 10, 10))
        row.pack(fill="x")
        self.prompt = tk.StringVar(value=shell.prompt)
        ttk.Label(row, textvariable=self.prompt).pack(side="left")
        self.entry = ttk.Entry(row, font=("Consolas", 11))
        self.entry.pack(side="left", fill="x", expand=True, padx=8)
        button = ttk.Button(row, text="Выполнить", command=self.submit)
        button.pack(side="right")
        self.entry.bind("<Return>", self.submit)
        self.entry.bind("<Up>", lambda event: self.recall(-1))
        self.entry.bind("<Down>", lambda event: self.recall(1))
        self.entry.bind("<Control-c>", self.cancel)
        for line in config.debug_lines():
            self.emit(line)
        root.after_idle(self.start)

    def emit(self, text):
        """Добавить текст в защищенный от редактирования журнал."""
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.configure(state="disabled")
        self.output.see("end")

    def start(self):
        """Выполнить сценарий после появления окна, затем ждать ввода."""
        run_script(self.shell, self.lines, self.emit)
        self.refresh()

    def submit(self, event=None):
        """Обработать Enter или кнопку и обновить приглашение."""
        line = self.entry.get()
        self.entry.delete(0, "end")
        self.emit(self.shell.prompt + line)
        _, output = self.shell.execute(line)
        if output:
            self.emit(output)
        self.history_index = len(self.shell.history)
        self.refresh()
        return "break"

    def refresh(self):
        """Обновить путь и фокус либо закрыть окно после exit."""
        if not self.shell.running:
            self.close()
            return
        self.prompt.set(self.shell.prompt)
        self.history_index = len(self.shell.history)
        self.entry.focus_set()

    def recall(self, direction):
        """Перебирать ранее введенные команды стрелками вверх/вниз."""
        self.history_index = min(len(self.shell.history),
                                 max(0, self.history_index + direction))
        self.entry.delete(0, "end")
        if self.history_index < len(self.shell.history):
            self.entry.insert(0, self.shell.history[self.history_index])
        return "break"

    def cancel(self, event=None):
        """Отменить текущую строку, не завершая приложение."""
        self.entry.delete(0, "end")
        self.emit("^C")
        return "break"

    def close(self):
        """Остановить оболочку и уничтожить окно."""
        self.shell.running = False
        self.root.destroy()
