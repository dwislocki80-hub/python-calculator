"""The calculator window (Tkinter), styled after the Windows 11 calculator.

This file only deals with the look and with user input. Every button calls a method
of `Calculator` (engine.py), and after each click the screen is refreshed from the
engine's `display` and `expression`.
"""

import tkinter as tk
import tkinter.font as tkfont

from .engine import Calculator, HistoryItem
from .widgets import RoundedButton

THEMES = {
    "dark": {
        "window": "#202020", "text": "#ffffff", "muted": "#a0a0a0",
        "digit": {"bg": "#3b3b3b", "hover": "#323232", "pressed": "#2b2b2b", "fg": "#ffffff"},
        "function": {"bg": "#323232", "hover": "#3b3b3b", "pressed": "#2b2b2b", "fg": "#ffffff"},
        "equals": {"bg": "#4cc2ff", "hover": "#47b1e8", "pressed": "#42a1d2", "fg": "#000000"},
        "header": {"bg": "#202020", "hover": "#2d2d2d", "pressed": "#292929", "fg": "#ffffff"},
        "history_hover": "#2d2d2d",
    },
    "light": {
        "window": "#f3f3f3", "text": "#1b1b1b", "muted": "#616161",
        "digit": {"bg": "#ffffff", "hover": "#f6f6f6", "pressed": "#f0f0f0", "fg": "#1b1b1b"},
        "function": {"bg": "#f9f9f9", "hover": "#f0f0f0", "pressed": "#e8e8e8", "fg": "#1b1b1b"},
        "equals": {"bg": "#005fb8", "hover": "#1a6fc0", "pressed": "#3380c8", "fg": "#ffffff"},
        "header": {"bg": "#f3f3f3", "hover": "#e9e9e9", "pressed": "#e0e0e0", "fg": "#1b1b1b"},
        "history_hover": "#e9e9e9",
    },
}

# (text on the button, style, method name in Calculator, optional argument)
LAYOUT = [
    [("%", "function", "percent"), ("CE", "function", "clear_entry"),
     ("C", "function", "clear"), ("⌫", "function", "backspace")],
    [("1/x", "function", "reciprocal"), ("x²", "function", "square"),
     ("√x", "function", "square_root"), ("÷", "function", "press_operator", "/")],
    [("7", "digit", "press_digit", "7"), ("8", "digit", "press_digit", "8"),
     ("9", "digit", "press_digit", "9"), ("×", "function", "press_operator", "*")],
    [("4", "digit", "press_digit", "4"), ("5", "digit", "press_digit", "5"),
     ("6", "digit", "press_digit", "6"), ("−", "function", "press_operator", "-")],
    [("1", "digit", "press_digit", "1"), ("2", "digit", "press_digit", "2"),
     ("3", "digit", "press_digit", "3"), ("+", "function", "press_operator", "+")],
    [("+/−", "digit", "negate"), ("0", "digit", "press_digit", "0"),
     (".", "digit", "press_decimal_point"), ("=", "equals", "press_equals")],
]

# keyboard key -> button text (shortcuts are the same as in the Windows calculator)
KEYS = {
    **{str(d): str(d) for d in range(10)},
    "+": "+", "-": "−", "*": "×", "/": "÷", "=": "=", "Return": "=", "KP_Enter": "=",
    ".": ".", ",": ".", "%": "%", "BackSpace": "⌫", "Escape": "C", "Delete": "CE",
    "@": "√x", "q": "x²", "r": "1/x", "F9": "+/−",
    "KP_Add": "+", "KP_Subtract": "−", "KP_Multiply": "×", "KP_Divide": "÷", "KP_Decimal": ".",
}

FONT = "Segoe UI"  # the Windows font; other systems use their default if it is missing
DISPLAY_SIZES = (42, 34, 28, 22, 18, 15)  # the result font shrinks for long numbers


class CalculatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.calc = Calculator()
        self.theme_name = "dark"
        self.history_visible = False
        self.buttons: dict[str, RoundedButton] = {}

        root.title("Calculator")
        root.geometry("340x540")
        root.minsize(320, 500)

        self._build_header()
        self._build_display()
        self._build_keypad()
        self._build_history_panel()
        self._apply_theme()

        root.bind("<Key>", self._on_key)
        root.bind("<Control-h>", lambda e: self.toggle_history())
        self.refresh()

    # ---------- building the window ----------

    def _build_header(self):
        self.header = tk.Frame(self.root)
        self.header.pack(fill="x", padx=6, pady=(6, 0))
        self.title_label = tk.Label(self.header, text="Standard", font=(FONT, 15, "bold"))
        self.title_label.pack(side="left", padx=8)

        self.history_button = RoundedButton(self.header, "History", self.toggle_history,
                                            THEMES["dark"]["header"], (FONT, 10), width=70, height=32)
        self.history_button.pack(side="right", padx=2)
        self.theme_button = RoundedButton(self.header, "Light", self.toggle_theme,
                                          THEMES["dark"]["header"], (FONT, 10), width=60, height=32)
        self.theme_button.pack(side="right", padx=2)

    def _build_display(self):
        self.body = tk.Frame(self.root)
        self.body.pack(fill="both", expand=True)
        self.left = tk.Frame(self.body)
        self.left.pack(side="left", fill="both", expand=True)

        self.expression_label = tk.Label(self.left, anchor="e", font=(FONT, 12))
        self.expression_label.pack(fill="x", padx=16, pady=(18, 0))
        # fixed-height box, so the buttons do not jump when the font gets smaller
        self.display_box = tk.Frame(self.left, height=72)
        self.display_box.pack(fill="x", padx=14, pady=(0, 10))
        self.display_box.pack_propagate(False)
        self.display_label = tk.Label(self.display_box, anchor="e", font=(FONT, DISPLAY_SIZES[0], "bold"))
        self.display_label.pack(fill="both", expand=True)
        self.display_label.bind("<Configure>", lambda e: self._fit_display_font())

    def _build_keypad(self):
        self.keypad = tk.Frame(self.left)
        self.keypad.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        for row, buttons in enumerate(LAYOUT):
            self.keypad.rowconfigure(row, weight=1, uniform="row")
            for col, (text, style, method, *arg) in enumerate(buttons):
                self.keypad.columnconfigure(col, weight=1, uniform="col")
                size = 16 if text.isdigit() else 18 if text in "÷×−+=" else 13
                button = RoundedButton(self.keypad, text, self._command(method, *arg),
                                       THEMES["dark"][style], (FONT, size, "bold" if text.isdigit() else "normal"),
                                       width=70, height=50)
                button.style = style
                button.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                self.buttons[text] = button

    def _build_history_panel(self):
        self.history_frame = tk.Frame(self.body, width=260)
        self.history_frame.pack_propagate(False)
        self.history_title = tk.Label(self.history_frame, text="History", anchor="w", font=(FONT, 13, "bold"))
        self.history_title.pack(fill="x", padx=12, pady=(18, 6))
        self.history_list = tk.Frame(self.history_frame)
        self.history_list.pack(fill="both", expand=True, padx=4)
        self.clear_history_button = RoundedButton(self.history_frame, "Clear history", self.clear_history,
                                                  THEMES["dark"]["header"], (FONT, 10), width=110, height=32)
        self.clear_history_button.pack(side="bottom", anchor="e", padx=10, pady=10)

    def _command(self, method: str, *args):
        """Create the function a button runs: call the engine, then redraw the screen."""
        def run():
            getattr(self.calc, method)(*args)
            self.refresh()
        return run

    # ---------- updating the screen ----------

    def refresh(self):
        self.expression_label.configure(text=self.calc.expression)
        self.display_label.configure(text=self.calc.display)
        self._fit_display_font()
        if self.history_visible:
            self._render_history()

    def _fit_display_font(self):
        """Pick the biggest font size at which the number still fits the window."""
        available = max(self.display_label.winfo_width() - 8, 100)
        text = self.display_label.cget("text")
        for size in DISPLAY_SIZES:
            font = tkfont.Font(family=FONT, size=size, weight="bold")
            if font.measure(text) <= available:
                break
        self.display_label.configure(font=(FONT, size, "bold"))

    def _render_history(self):
        theme = THEMES[self.theme_name]
        for widget in self.history_list.winfo_children():
            widget.destroy()
        if not self.calc.history:
            tk.Label(self.history_list, text="There's no history yet", anchor="w",
                     bg=theme["window"], fg=theme["muted"], font=(FONT, 10)).pack(fill="x", padx=8)
            return
        for item in self.calc.history[:12]:
            self._history_entry(item, theme)

    def _history_entry(self, item: HistoryItem, theme: dict):
        box = tk.Frame(self.history_list, bg=theme["window"], cursor="hand2")
        box.pack(fill="x", pady=1)
        top = tk.Label(box, text=item.expression, anchor="e", bg=theme["window"], fg=theme["muted"], font=(FONT, 10))
        bottom = tk.Label(box, text=item.result, anchor="e", bg=theme["window"], fg=theme["text"], font=(FONT, 16, "bold"))
        top.pack(fill="x", padx=10, pady=(6, 0))
        bottom.pack(fill="x", padx=10, pady=(0, 6))

        def set_bg(color):
            for w in (box, top, bottom):
                w.configure(bg=color)

        def use(_event):
            self.calc.use_history_item(item)
            self.refresh()

        for w in (box, top, bottom):
            w.bind("<Enter>", lambda e: set_bg(theme["history_hover"]))
            w.bind("<Leave>", lambda e: set_bg(theme["window"]))
            w.bind("<Button-1>", use)

    # ---------- header buttons ----------

    def toggle_history(self):
        self.history_visible = not self.history_visible
        width = self.root.winfo_width()
        if self.history_visible:
            self.history_frame.pack(side="right", fill="y")
            self.root.geometry(f"{width + 260}x{self.root.winfo_height()}")
            self._render_history()
        else:
            self.history_frame.pack_forget()
            self.root.geometry(f"{max(width - 260, 340)}x{self.root.winfo_height()}")

    def clear_history(self):
        self.calc.history.clear()
        self._render_history()

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self._apply_theme()
        self.refresh()

    def _apply_theme(self):
        theme = THEMES[self.theme_name]
        bg = theme["window"]
        self.root.configure(bg=bg)
        for frame in (self.header, self.body, self.left, self.display_box, self.keypad,
                      self.history_frame, self.history_list):
            frame.configure(bg=bg)
        for label in (self.title_label, self.display_label, self.history_title):
            label.configure(bg=bg, fg=theme["text"])
        self.expression_label.configure(bg=bg, fg=theme["muted"])

        for button in self.buttons.values():
            button.set_colors({**theme[button.style], "parent": bg})
        for button in (self.history_button, self.theme_button, self.clear_history_button):
            button.set_colors({**theme["header"], "parent": bg})
        self.theme_button.text = "Light" if self.theme_name == "dark" else "Dark"
        self.theme_button.set_colors({**theme["header"], "parent": bg})

    # ---------- keyboard ----------

    def _on_key(self, event):
        text = KEYS.get(event.keysym) or KEYS.get(event.char)
        if text in self.buttons:
            button = self.buttons[text]
            button.flash()
            button.command()


def run() -> None:
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()
