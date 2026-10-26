"""A rounded, flat button drawn on a Canvas.

The normal tk.Button cannot have rounded corners, and on some systems it ignores
background colours. Drawing the button ourselves gives the same look everywhere.
"""

import tkinter as tk
from typing import Callable


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text: str, command: Callable[[], None], colors: dict,
                 font: tuple, radius: int = 8, **kwargs):
        super().__init__(parent, highlightthickness=0, borderwidth=0, cursor="hand2", **kwargs)
        self.text = text
        self.command = command
        self.font = font
        self.radius = radius
        self.colors = colors  # {"bg", "hover", "pressed", "fg", "parent"}
        self._state = "bg"
        self._hovering = False

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ---------- drawing ----------

    def set_colors(self, colors: dict) -> None:
        """Used when switching between dark and light theme."""
        self.colors = colors
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 4 or height < 4:
            return
        self.configure(bg=self.colors["parent"])
        self._rounded_rectangle(1, 1, width - 1, height - 1, self.radius, fill=self.colors[self._state])
        self.create_text(width / 2, height / 2, text=self.text, fill=self.colors["fg"], font=self.font)

    def _rounded_rectangle(self, x1, y1, x2, y2, r, **kwargs):
        """A rectangle with rounded corners, drawn as a smoothed polygon."""
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(points, smooth=True, outline="", **kwargs)

    # ---------- mouse ----------

    def _on_enter(self, _event):
        self._hovering = True
        self._set_state("hover")

    def _on_leave(self, _event):
        self._hovering = False
        self._set_state("bg")

    def _on_press(self, _event):
        self._set_state("pressed")

    def _on_release(self, _event):
        # run the command only if the mouse is still over the button (like a real button)
        if self._hovering:
            self._set_state("hover")
            self.command()
        else:
            self._set_state("bg")

    def _set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self._draw()

    def flash(self) -> None:
        """Briefly show the button as pressed – used when the key is pressed on the keyboard."""
        self._set_state("pressed")
        self.after(110, lambda: self._set_state("hover" if self._hovering else "bg"))
