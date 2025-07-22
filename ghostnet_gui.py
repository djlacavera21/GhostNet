#!/usr/bin/env python3
"""Simple Tkinter GUI for GhostNet.

This GUI wraps the existing command line interface of ghostnet.py.
Users can start any of the available modes (voice server/client,
text server/client) with provided parameters.
"""

import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

SCRIPT = os.path.join(os.path.dirname(__file__), "ghostnet.py")

class GhostNetGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GhostNet GUI")
        self.process: subprocess.Popen[str] | None = None

        self.mode = tk.StringVar(value="voice_server")
        self.host = tk.StringVar(value="0.0.0.0")
        self.port = tk.IntVar(value=7777)
        self.password = tk.StringVar()

        self._build_widgets()

    def _build_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Mode:").grid(row=0, column=0, sticky="w")
        modes = (
            ("Voice Server", "voice_server"),
            ("Voice Client", "voice_client"),
            ("Text Server", "text_server"),
            ("Text Client", "text_client"),
        )
        row = 1
        for text, val in modes:
            ttk.Radiobutton(
                frame, text=text, variable=self.mode, value=val
            ).grid(row=row, column=0, sticky="w")
            row += 1

        ttk.Label(frame, text="Host:").grid(row=0, column=1, sticky="w")
        ttk.Entry(frame, textvariable=self.host, width=20).grid(
            row=0, column=2, sticky="ew")
        ttk.Label(frame, text="Port:").grid(row=1, column=1, sticky="w")
        ttk.Entry(frame, textvariable=self.port, width=10).grid(
            row=1, column=2, sticky="ew")
        ttk.Label(frame, text="Password (optional):").grid(row=2, column=1, sticky="w")
        ttk.Entry(frame, textvariable=self.password, show="*", width=20).grid(
            row=2, column=2, sticky="ew")

        frame.columnconfigure(2, weight=1)

        self.start_btn = ttk.Button(frame, text="Start", command=self.start)
        self.start_btn.grid(row=3, column=1, columnspan=2, pady=(10, 0))

        self.output = scrolledtext.ScrolledText(frame, width=80, height=20, state="disabled")
        self.output.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="nsew")
        frame.rowconfigure(4, weight=1)

    def append_output(self, text: str):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text)
        self.output.configure(state="disabled")
        self.output.yview(tk.END)

    def reader_thread(self, pipe):
        try:
            for line in iter(pipe.readline, ""):
                self.append_output(line)
        finally:
            pipe.close()

    def start(self):
        if self.process:
            self.stop()
            return

        cmd = [sys.executable, SCRIPT]
        mode = self.mode.get()
        host = self.host.get()
        port = str(self.port.get())
        pwd = self.password.get()

        if mode == "voice_server":
            cmd += ["server", "--host", host, "--port", port]
        elif mode == "voice_client":
            cmd += ["client", "--host", host, "--port", port]
        elif mode == "text_server":
            cmd += ["text-server", "--host", host, "--port", port]
        else:
            cmd += ["text-client", "--host", host, "--port", port]

        if pwd:
            cmd += ["--password", pwd]

        self.append_output(f"Starting: {' '.join(cmd)}\n")
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        threading.Thread(target=self.reader_thread, args=(self.process.stdout,), daemon=True).start()
        self.start_btn.config(text="Stop")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            self.append_output("Process terminated\n")
        self.process = None
        self.start_btn.config(text="Start")

if __name__ == "__main__":
    app = GhostNetGUI()
    app.mainloop()
