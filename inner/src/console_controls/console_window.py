# console_controls/console_window.py
# module for rendering the pseudo-console.
###### IMPORT ######

import tkinter as tk

###### TK CONSOLE INITIALIZE ######

class ConsoleWindow(tk.Tk):
    def __init__(self, lines, source_path, font="Consolas 10"):
        super().__init__()
        icon = tk.PhotoImage(file=f"{source_path}/assets/terminal-icon.png")
        self.iconphoto(True, icon)
        self.title("Symphony: Console")
        self.geometry("800x400")
        self.resizable(False, False)
        self.configure(bg="black")
        self.lines = lines
        self.font = font

        self.text = tk.Text(self, bg="black", font=font, wrap="word", state="disabled")
        self.scroll = tk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)

        self.text.tag_config("gray", foreground="gray")
        self.text.tag_config("yellow", foreground="yellow")
        self.text.tag_config("red", foreground="red")
        self.text.tag_config("magenta", foreground="magenta")

        self.text.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self._last_len = 0

    def update_console(self):
        if len(self.lines) != self._last_len:
            self._last_len = len(self.lines)
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            for message, tag in self.lines:
                self.text.insert("end", message + "\n", tag)
            self.text.see("end")
            self.text.configure(state="disabled")