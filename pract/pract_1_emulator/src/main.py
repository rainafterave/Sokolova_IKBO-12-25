import tkinter as tk
import getpass
import socket
import shlex

def on_enter(event):
    command = command_input.get().strip()
    if not command:
        return
    try:
        parts = shlex.split(command)
    except ValueError as error:
        response = f"Ошибка разбора команды: {error}"
    else:
        command_name = parts[0]
        arguments = parts[1:]
        if command_name in ("ls", "cd"):
            if command_name == "cd" and len(arguments) > 1:
                response = "Ошибка: команда cd принимает не больше одного аргумента."
            else:
                response = f"Команда: {command_name}\nАргументы: {arguments}"
        elif command_name == "exit":
            if arguments:
                response = "Ошибка: команда exit не принимает аргументы."
            else:
                window.destroy()
                return
        else:
            response = f"Ошибка: неизвестная команда «{command_name}»."
    output.config(state="normal")
    output.insert(tk.END, f"> {command}\n{response}\n")
    output.config(state="disabled")
    output.see(tk.END)
    command_input.delete(0, tk.END)

username = getpass.getuser()
hostname = socket.gethostname()
window = tk.Tk()
window.title(f"Эмулятор — [{username}@{hostname}]")
window.geometry("800x500")
output = tk.Text(window)
output.pack(fill="both", expand=True, padx=10, pady=10)
output.insert(tk.END, "Эмулятор запущен.\n")
output.config(state="disabled")
command_input = tk.Entry(window)
command_input.pack(fill="x", padx=10, pady=10)
command_input.focus_set()
command_input.bind("<Return>", on_enter)

window.mainloop()
