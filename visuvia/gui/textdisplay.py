"""
Describe this module
"""


# Third party imports
import tkinter as tk


__all__ = ["TextDisplayGUI"]


class TextDisplayGUI():
    """
    Describe this class
    """
    def __init__(self, window):
        """
        Describe this method
        """
        self.frame = tk.Frame(window)

        self.scrollbar = tk.Scrollbar(self.frame)

        self.txt_display = tk.Text(self.frame, bg="black",
                                   fg="lightgreen", relief="sunken",
                                   bd=4, width=43, height=40,
                                   yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.txt_display.yview)

        self.frame.grid(row=3, column=0, padx=10, pady=10,
                        sticky="nsew")

    def place_widgets(self):
        """
        Describe this method
        """
        self.txt_display.pack(side=tk.LEFT)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_display.insert(tk.END, ">> Waiting for text messages")

    def append_text(self, text_channels):
        """
        Describe this method
        """
        if len(text_channels) < 0:
            return
        for ch_id, text_data in text_channels.items():
            if text_data:
                msg_str = f"\nCH_{ch_id}>> {text_data}"
                self.txt_display.insert(tk.END, msg_str)
                self.txt_display.see(tk.END)

    def reset(self):
        """
        Describe this method
        """
        self.txt_display.delete("1.0", tk.END)
        self.txt_display.insert(tk.END, ">> Waiting for text messages")
