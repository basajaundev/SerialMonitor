#!/usr/bin/python3
import datetime
import sys
import threading
import time

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

import serial.tools.list_ports
from ttkbootstrap import Style


class SerialmonitorApp:
    def __init__(self, master=None):
        self.thread = None
        self.ser = serial.Serial()
        self.baudrates = ['9600', '19200', '38400', '115200']
        self.isConnected = False
        self.cmd_history = []
        self.current_cmd_index = -1

        self.root = tk.Tk(master)
        self.root.minsize(640, 450)
        self.root.resizable(True, True)
        self.root.title("SerialMonitor")
        self.root.protocol('WM_DELETE_WINDOW', self.close_app)

        self.style = Style(theme='darkly')

        frame1 = ttk.Frame(self.root)
        self.cbPort = ttk.Combobox(frame1, name="cbport", values=self.get_serialports())
        self.cbPort.configure(state="readonly")
        self.cbPort.current(0)
        self.cbPort.pack(padx=5, side="left")
        self.cbBaudrate = ttk.Combobox(frame1, name="cbbaudrate", values=self.baudrates)
        self.cbBaudrate.configure(width=10, state="readonly")
        self.cbBaudrate.current(0)
        self.cbBaudrate.pack(padx=5, side="left")
        self.btnConnect = ttk.Button(frame1, name="btnconnect", command=self.btnConnect_click)
        self.btnConnect.configure(text='Connect')
        self.btnConnect.pack(padx=5, side="left")
        self.btnDisconect = ttk.Button(frame1, name="btndisconect", command=self.btnDisconnect_click)
        self.btnDisconect.configure(text='Disconnect', state="disabled")
        self.btnDisconect.pack(padx=5, side="left")
        self.btnClear = ttk.Button(frame1, name="btnclear", command=self.btnClear_click)
        self.btnClear.configure(text='Clear Output', state="normal")
        self.btnClear.pack(padx=5, side="left")
        frame1.pack(fill="x", pady=5, side="top")

        frame3 = ttk.Frame(self.root)
        self.scrollbar = ttk.Scrollbar(frame3, name="scrollbar")
        self.scrollbar.configure(orient="vertical")
        self.scrollbar.pack(fill="y", side="right")
        self.txtReceived = tk.Text(
            frame3,
            name="txtreceived",
            highlightcolor=self.style.colors.primary,
            highlightbackground=self.style.colors.border,
            highlightthickness=1
        )
        self.txtReceived.configure(relief="flat", yscrollcommand=self.scrollbar.set)
        self.txtReceived.bind('<Key>', lambda _: 'break')  # Read-Only Trick
        self.scrollbar.config(command=self.txtReceived.yview)
        self.txtReceived.pack(expand=True, fill="both", side="left")
        frame3.pack(expand=True, fill="both", padx=5, side="top")

        frame4 = ttk.Frame(self.root)
        self.eEntry = ttk.Entry(frame4, name="eentry")
        self.eEntry.configure(state="readonly")
        self.eEntry.bind('<Return>', self.btnSend_click)
        self.eEntry.bind('<Up>', self.key_up_pressed)
        self.eEntry.bind('<Down>', self.key_down_pressed)
        self.eEntry.pack(fill="x", pady=5, side="top")
        frame4.pack(fill="both", padx=5, side="bottom")

        self.root.after(100, self.update_interface)

        self.mainwindow = self.root

    def run_app(self):
        self.mainwindow.mainloop()

    def update_interface(self):
        self.root.after(100, self.update_interface)

    def close_app(self):
        if self.isConnected:
            self.close_serial()
        self.root.destroy()
        sys.exit()

    def thread_it(self, func, *args):
        self.thread = threading.Thread(target=func, args=args, daemon=True)
        self.thread.start()

    @staticmethod
    def get_serialports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def read_data(self):
        buf = ''
        while self.isConnected:
            if self.ser.is_open:
                try:
                    data = self.ser.readline().decode('utf-8', "ignore").strip()
                    if data:
                        buf += data
                        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                        self.txtReceived.insert(tk.END, f"[{timestamp}] Recv <- {buf}\n")
                        self.txtReceived.see(tk.END)
                        buf = ''
                except Exception as e:
                    messagebox.showerror("Read Data Error", str(e))

            time.sleep(0.2)

        self.close_serial()

    def close_serial(self):
        if self.ser and self.ser.is_open:
            try:
                self.isConnected = False
                if hasattr(self.ser, 'cancel_read'):
                    self.ser.cancel_read()
                self.ser.close()
                self.thread.join()
            except serial.SerialException as e:
                messagebox.showerror("Close Serial Error", str(e))
                return

    def enable_components(self):
        self.cbPort["state"] = "disabled"
        self.cbBaudrate["state"] = "disabled"
        self.btnConnect["state"] = "disabled"
        self.btnDisconect["state"] = "normal"
        self.eEntry["state"] = "normal"

    def disable_components(self):
        self.cbPort["state"] = "readonly"
        self.cbBaudrate["state"] = "readonly"
        self.btnConnect["state"] = "normal"
        self.btnDisconect["state"] = "disabled"
        self.eEntry["state"] = "disabled"

    def btnConnect_click(self):
        port = self.cbPort.get()
        if not port:
            messagebox.showerror("Connect Error", "No Serial Port selected from the list")
            return

        baudrate = self.cbBaudrate.get()
        if not baudrate:
            messagebox.showerror("Connect Error", "No Baudrate selected from the list")
            return

        try:
            self.ser = serial.Serial(port, baudrate=int(baudrate), timeout=1)
            self.ser.close()
            self.ser.open()
            self.isConnected = True
            self.thread_it(self.read_data)
            self.root.title("SerialMonitor" + f" {port} - {baudrate}")
            self.enable_components()
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            self.txtReceived.insert(tk.END, f"[{timestamp}] Open <> {port}\n")
            self.txtReceived.see(tk.END)
        except serial.SerialException as e:
            messagebox.showerror("Connect Error", str(e))

    def btnDisconnect_click(self):
        self.close_serial()
        port = self.cbPort.get()
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.txtReceived.insert(tk.END, f"[{timestamp}] Close >< {port}\n")
        self.txtReceived.see(tk.END)
        self.root.title("SerialMonitor")
        self.disable_components()

    def btnSend_click(self, event):
        data = self.eEntry.get()
        try:
            self.ser.write(data.encode('utf-8'))
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            self.txtReceived.insert(tk.END, f"[{timestamp}] Send -> {data}\n")
            self.txtReceived.see(tk.END)
        except serial.SerialException as e:
            messagebox.showerror("Send Error", str(e))

        cmd = self.eEntry.get().strip()
        if cmd:
            self.cmd_history.append(data)
            self.current_cmd_index = -1
            self.eEntry.delete(0, tk.END)

    def key_up_pressed(self, event):
        if self.cmd_history:
            if self.current_cmd_index != 0:
                if self.current_cmd_index == -1:
                    self.current_cmd_index = len(self.cmd_history) - 1
                    self.eEntry.delete(0, tk.END)
                    self.eEntry.insert(0, self.cmd_history[self.current_cmd_index])
                else:
                    self.current_cmd_index = (self.current_cmd_index - 1) % len(self.cmd_history)
                    self.eEntry.delete(0, tk.END)
                    self.eEntry.insert(0, self.cmd_history[self.current_cmd_index])

    def key_down_pressed(self, event):
        if self.cmd_history:
            if self.current_cmd_index != len(self.cmd_history) - 1:
                if self.current_cmd_index == -1:
                    self.eEntry.delete(0, tk.END)
                else:
                    self.current_cmd_index = (self.current_cmd_index + 1) % len(self.cmd_history)
                    self.eEntry.delete(0, tk.END)
                    if self.current_cmd_index < len(self.cmd_history):
                        self.eEntry.insert(0, self.cmd_history[self.current_cmd_index])
            else:
                self.eEntry.delete(0, tk.END)
                self.current_cmd_index = -1

    def btnClear_click(self):
        self.txtReceived.delete(1.0, tk.END)


if __name__ == "__main__":
    app = SerialmonitorApp()
    try:
        app.run_app()
    except KeyboardInterrupt:
        app.close_app()
