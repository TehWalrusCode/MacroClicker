import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
from cryptography.fernet import Fernet
import ctypes
import json
import os
import sys

# Recording and Playback Logic
from pynput import mouse, keyboard
import threading
import time

HOTKEY_FILE = "./hotkeys.json"

KEY = b'oq-k9iwYQoUFaya8AcsUiecMY_ZBW_cR9oSghw9dsII='

DEFAULT_HOTKEYS = {

    "play": keyboard.Key.f1.name,
    "record": keyboard.Key.f2.name,
    "autoclick": keyboard.Key.f3.name

}

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

IMAGE_FILES = {
            "record": ctk.CTkImage(dark_image=Image.open(resource_path("./images/record.png")), size=(144, 35)),
            "stop": ctk.CTkImage(dark_image=Image.open(resource_path("./images/stop.png")), size=(144, 32)),
            "play": ctk.CTkImage(dark_image=Image.open(resource_path("./images/play.png")), size=(75, 32)),
            "clear": ctk.CTkImage(dark_image=Image.open(resource_path("./images/clear.png")), size=(74, 30)),
            "loop": ctk.CTkImage(dark_image=Image.open(resource_path("./images/loop.png")), size=(63, 29)),
            "click_interval": ctk.CTkImage(dark_image=Image.open(resource_path("./images/click_interval.png")), size=(290, 68)),
            "mouse_button": ctk.CTkImage(dark_image=Image.open(resource_path("./images/mouse_button.png")), size=(145, 66)),
            "click_type": ctk.CTkImage(dark_image=Image.open(resource_path("./images/click_type.png")), size=(143, 63)),
            "repeat": ctk.CTkImage(dark_image=Image.open(resource_path("./images/repeat.png")), size=(290, 72)),
            "cursor_pos": ctk.CTkImage(dark_image=Image.open(resource_path("./images/cursor_pos.png")), size=(288, 92)),
            "start": ctk.CTkImage(dark_image=Image.open(resource_path("./images/start.png")), size=(284, 41))
            }

# TODO: Figure out interaction with pausing a macro and a move instruction shortening itself because of it
# TODO: Seems to happen when pausing during a movement instruction, but doesn't shorten the move instruction at the exact point of pausing
class MacroClickerUI(ctk.CTk):
    def __init__(self, root):
        super().__init__()
        self.root = root
        self.root.iconbitmap(resource_path("./images/icon.ico"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after_jobs = []
        self.root.title("MacroClicker")
        self.root.geometry("700x500")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        #self.root.resizable(False, False)

        # Encryption
        self.fernet = Fernet(KEY)

        # Listeners
        self.keyboard_listener = None
        self.start_kb_listener()

        # Create recorder/player
        self.recorder = ActionRecorder()
        self.player = MacroClickerPlayer()
        
        # Hotkeys
        hotkeys = self.load_hotkeys()
        self.play_hk = hotkeys["play"]
        self.record_hk = hotkeys["record"]
        self.autoclick_hk = hotkeys["autoclick"]

        # Variables
        self.playing = False
        self.autoclicking = False
        self.stop_event = threading.Event()
        self.action_blocks = []
        self.vcmd = self.root.register(self.validate_input)
        self.font = ctk.CTkFont("Comic Sans MS", 24, "bold", "italic", underline=True)
        self.macro_save_file = ""

        # Menu Bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        # File Menu
        self.file_menu.add_command(label="New", command=self.clear_actions)
        self.file_menu.add_command(label="Save", command=lambda: self.save_file(save_as=False))
        self.file_menu.add_command(label="Save As...", command=lambda: self.save_file(save_as=True))
        self.file_menu.add_command(label="Load", command=self.load_file)
        self.file_menu.add_command(label="Exit", command=self.on_close)

        # Edit Menu
        self.edit_menu.add_command(label="Hotkeys", command=lambda: HotkeyWindow(self, self.root))

        # Help Menu
        self.help_menu.add_command(label="How to use", command=lambda: How2UseWindow(self, self.root))

        # Macro Frame
        self.macro_frame = ctk.CTkFrame(self.root)
        self.macro_frame.grid(row=0, column=0, sticky="nsew", padx=(5,10), pady=5)
        self.macro_frame.grid_rowconfigure(0, weight=0)
        self.macro_frame.grid_rowconfigure(1, weight=0)
        self.macro_frame.grid_rowconfigure(2, weight=1)
        self.macro_frame.grid_columnconfigure(0, weight=1)

        # Macro Label
        self.macro_label_frame = ctk.CTkFrame(self.macro_frame)
        self.macro_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.macro_label_frame.grid_columnconfigure(0, weight=1)
        self.macro_label = ctk.CTkLabel(self.macro_label_frame, text="Macro Tool", font=self.font, text_color="#00FFFF", bg_color="#2B2B2B")
        self.macro_label.grid(row=0, column=0, sticky="nsew")

        # Macro Control Buttons Frame
        macro_controls = ctk.CTkFrame(self.macro_frame)
        macro_controls.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        macro_controls.grid_rowconfigure(0, weight=1)
        for i in range(4):
            macro_controls.grid_columnconfigure(i, weight=1)

        self.play_btn = ctk.CTkButton(macro_controls,
                                      text=f"Play ({str(self.play_hk).capitalize()})",
                                      width=80,
                                      command=self.toggle_play)
        self.play_btn.grid(row=0, column=0, padx=(0,5), sticky="nsew")

        self.record_btn = ctk.CTkButton(macro_controls,
                                        text=f"Record ({str(self.record_hk).capitalize()})",
                                        width=120,
                                        command=self.toggle_record)
        self.record_btn.grid(row=0, column=1, padx=(0,5), sticky="nsew")

        self.clear_btn = ctk.CTkButton(macro_controls,
                                       text="Clear",
                                       width=80,
                                       command=self.clear_actions)
        self.clear_btn.grid(row=0, column=2, padx=(0,5), sticky="nsew")

        self.loop_var = tk.BooleanVar(value=False)
        self.loop_check = ctk.CTkCheckBox(macro_controls, text="Loop", variable=self.loop_var, border_color="#1F6AA5", hover=False)
        self.loop_check.grid(row=0, column=3, padx=(0,5), sticky="nsew")

        # Scrollable Action Block Frame
        self.action_container = ctk.CTkFrame(self.macro_frame, bg_color="#363636")
        self.action_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.action_container.grid_rowconfigure(0, weight=1)
        self.action_container.grid_columnconfigure(0, weight=1)

        self.action_scroll_frame = ctk.CTkScrollableFrame(
            self.action_container,
            fg_color="#363636",
            scrollbar_fg_color="#555555",
            scrollbar_button_color="#777777",
            scrollbar_button_hover_color="#999999",
        )
        self.action_scroll_frame.grid(row=0, column=0, sticky="nsew")
        self.action_scroll_frame.grid_columnconfigure(0, weight=1)

        # Autoclicker Frame
        self.clicker_frame = ctk.CTkFrame(self.root)
        self.clicker_frame.grid(row=0, column=1, sticky="nsew", padx=(10,5), pady=5)
        self.clicker_frame.grid_columnconfigure(0, weight=1)

        # Autoclicker Label
        self.clicker_label_frame = ctk.CTkFrame(self.clicker_frame)
        self.clicker_label_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.clicker_label_frame.grid_columnconfigure(0, weight=1)

        self.clicker_label = ctk.CTkLabel(self.clicker_label_frame, text="Autoclicker", font=self.font, text_color="#FFFF00", bg_color="#2B2B2B")
        self.clicker_label.grid(row=0, column=0, sticky="nsew")

        # Click Interval
        self.click_interval_frame = ctk.CTkFrame(self.clicker_frame)
        self.click_interval_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.click_interval_frame.grid_rowconfigure(1, weight=1)
        for i in range(8):
            self.click_interval_frame.grid_columnconfigure(i, weight=1)

        self.click_interval_label = ctk.CTkLabel(self.click_interval_frame, text="Click Interval")
        self.click_interval_label.grid(row=0, column=0, columnspan=7, sticky="nsw", padx=5)

        self.hour_value = tk.StringVar(value="0")
        self.minute_value = tk.StringVar(value="0")
        self.second_value = tk.StringVar(value="0")
        self.millisecond_value = tk.StringVar(value="100")

        self.hour_entry = ctk.CTkEntry(self.click_interval_frame,
                                       width=20,
                                       textvariable=self.hour_value,
                                       validate="key",
                                       validatecommand=(self.vcmd, "%P"),
                                       justify="right",
                                       border_color="#1F6AA5")
        self.hour_entry.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=(0,5))
        self.hour_label = ctk.CTkLabel(self.click_interval_frame, text="h")
        self.hour_label.grid(row=1, column=1, sticky="nsw", padx=0, pady=(0,5))

        self.minute_entry = ctk.CTkEntry(self.click_interval_frame,
                                         width=20,
                                         textvariable=self.minute_value,
                                         validate="key",
                                         validatecommand=(self.vcmd, "%P"),
                                         justify="right",
                                         border_color="#1F6AA5")
        self.minute_entry.grid(row=1, column=2, sticky="nsew", pady=(0,5))
        self.minute_label = ctk.CTkLabel(self.click_interval_frame, text="m")
        self.minute_label.grid(row=1, column=3, sticky="nsw", padx=0, pady=(0,5))

        self.second_entry = ctk.CTkEntry(self.click_interval_frame,
                                         width=20,
                                         textvariable=self.second_value,
                                         validate="key",
                                         validatecommand=(self.vcmd, "%P"),
                                         justify="right",
                                         border_color="#1F6AA5")
        self.second_entry.grid(row=1, column=4, sticky="nsew", pady=(0,5))
        self.second_label = ctk.CTkLabel(self.click_interval_frame, text="s")
        self.second_label.grid(row=1, column=5, sticky="nsw", padx=0, pady=(0,5))

        self.millisecond_entry = ctk.CTkEntry(self.click_interval_frame,
                                              width=20,
                                              textvariable=self.millisecond_value,
                                              validate="key",
                                              validatecommand=(self.vcmd, "%P"),
                                              justify="right",
                                              border_color="#1F6AA5")
        self.millisecond_entry.grid(row=1, column=6, sticky="nsew", pady=(0,5))
        self.millisecond_label = ctk.CTkLabel(self.click_interval_frame, text="ms")
        self.millisecond_label.grid(row=1, column=7, sticky="nsw", padx=0, pady=(0,5))

        # Click Options
        self.click_options_frame = ctk.CTkFrame(self.clicker_frame)
        self.click_options_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.click_options_frame.grid_rowconfigure(0, weight=1)
        self.click_options_frame.grid_rowconfigure(1, weight=1)
        self.click_options_frame.grid_columnconfigure(0, weight=1)
        self.click_options_frame.grid_columnconfigure(1, weight=1)

        self.mouse_button_label = ctk.CTkLabel(self.click_options_frame, text="Mouse Button")
        self.mouse_button_label.grid(row=0, column=0, sticky="nsw", padx=5)
        self.mouse_button_box = ctk.CTkComboBox(self.click_options_frame,
                                                state="readonly",
                                                values=["Left", "Middle", "Right"],
                                                border_color="#1F6AA5",
                                                button_color="#1F6AA5",
                                                hover=False)
        self.mouse_button_box.set("Left")
        self.mouse_button_box.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))

        self.click_type_label = ctk.CTkLabel(self.click_options_frame, text="Click Type")
        self.click_type_label.grid(row=0, column=1, sticky="nsw", padx=(0,5))
        self.click_type_box = ctk.CTkComboBox(self.click_options_frame,
                                              state="readonly",
                                              values=["Single", "Double"],
                                              border_color="#1F6AA5",
                                              button_color="#1F6AA5",
                                              hover=False)
        self.click_type_box.set("Single")
        self.click_type_box.grid(row=1, column=1, sticky="nsew", padx=(0,5), pady=(0,5))

        # Click Repeat
        self.repeat_frame = ctk.CTkFrame(self.clicker_frame)
        self.repeat_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        self.repeat_frame.grid_columnconfigure(0, weight=0)
        self.repeat_frame.grid_columnconfigure(1, weight=1)
        self.repeat_frame.grid_columnconfigure(2, weight=1)

        self.repeat_radio_var = tk.IntVar(value=0)
        self.repeat_value = tk.StringVar(value="1")

        self.repeat_radio_button_2 = ctk.CTkRadioButton(self.repeat_frame, text="Repeat indefinitely", variable=self.repeat_radio_var, value=2)
        self.repeat_radio_button_2.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.repeat_radio_button_2.select()

        self.repeat_radio_button_1 = ctk.CTkRadioButton(self.repeat_frame, text="Repeat", variable=self.repeat_radio_var, value=1)
        self.repeat_radio_button_1.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))

        self.repeat_button_1_entry = ctk.CTkEntry(self.repeat_frame,
                                                  width=20,
                                                  textvariable=self.repeat_value,
                                                  validate="key",
                                                  validatecommand=(self.vcmd, "%P"),
                                                  justify="right",
                                                  border_color="#1F6AA5")
        self.repeat_button_1_entry.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0,5))

        self.repeat_label = ctk.CTkLabel(self.repeat_frame, text="times")
        self.repeat_label.grid(row=1, column=2, sticky="nsw", padx=5, pady=(0,5))

        # Cursor Position
        self.cursor_pos_frame = ctk.CTkFrame(self.clicker_frame)
        self.cursor_pos_frame.grid(row=4, column=0, sticky="nsew", padx=5, pady=5)
        self.cursor_pos_frame.grid_rowconfigure(0, weight=1)
        self.cursor_pos_frame.grid_rowconfigure(1, weight=1)
        self.cursor_pos_frame.grid_rowconfigure(2, weight=1)
        self.cursor_pos_frame.grid_columnconfigure(0, weight=1)
        self.cursor_pos_frame.grid_columnconfigure(1, weight=0, minsize=100)
        self.cursor_pos_frame.grid_columnconfigure(2, minsize=110, weight=1)

        self.cursor_radio_var = tk.IntVar(value=0)
        self.cursor_pos = (0,0)

        self.cursor_pos_label = ctk.CTkLabel(self.cursor_pos_frame, text="Cursor Position")
        self.cursor_pos_label.grid(row=0, column=0, columnspan=3, sticky="nsw", padx=5)

        self.cursor_radio_button_1 = ctk.CTkRadioButton(self.cursor_pos_frame, text="Current Position", variable=self.cursor_radio_var, value=1)
        self.cursor_radio_button_1.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=(0,5))
        self.cursor_radio_button_1.select()

        self.cursor_radio_button_2 = ctk.CTkRadioButton(self.cursor_pos_frame, text="", variable=self.cursor_radio_var, value=2)
        self.cursor_radio_button_2.grid(row=2, column=0, sticky="w", padx=5, pady=(0,5))
        self.cursor_button = ctk.CTkButton(self.cursor_pos_frame, text="Pick Location", width=20, command=self.location_picker)
        self.cursor_button.grid(row=2, column=1, sticky="nsew", padx=5, pady=(0,5))
        self.cursor_X_Y_pos = ctk.CTkLabel(self.cursor_pos_frame, text=f"X: {self.cursor_pos[0]} Y: {self.cursor_pos[1]}")
        self.cursor_X_Y_pos.grid(row=2, column=2, sticky="nsew", padx=5, pady=(0,5))

        # Play Frame
        self.autoclick_frame = ctk.CTkFrame(self.clicker_frame)
        self.autoclick_frame.grid(row=5, column=0, sticky="nsew", padx=5, pady=5)
        self.autoclick_frame.grid_columnconfigure(0, weight=1)

        self.autoclick_btn = ctk.CTkButton(self.autoclick_frame, text=f"Start ({str(self.autoclick_hk).capitalize()})", command=self.autoclicker)
        self.autoclick_btn.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def start_kb_listener(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.keyboard_listener.start()

    def autoclicker(self):
        self.autoclick_btn.configure(text=f"Stop ({str(self.autoclick_hk).capitalize()})")
        self.autoclicking = not self.autoclicking
        if not self.autoclicking:
            return
        
        time_delay = self.parse_interval()
        mouse_btn = self.mouse_button_box.get()
        click_type = self.click_type_box.get()
        self.repeat = True if self.repeat_radio_var.get() == 2 else (0 if self.repeat_value.get() == "" else self.repeat_value.get())
        curr_pos = self.cursor_pos if self.cursor_radio_var.get() == 2 else (-1,-1)

        def autoclick():
            mouse_controller = mouse.Controller()
            if self.repeat == True:
                while self.autoclicking and self.repeat:

                    if curr_pos == self.cursor_pos:
                        mouse_controller.position = curr_pos

                    if click_type == "Single":
                        x = 1
                    else:
                        x = 2
                    
                    if mouse_btn == "Left":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.left)
                            mouse.Controller().release(mouse.Button.left)
                    elif mouse_btn == "Middle":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.middle)
                            mouse.Controller().release(mouse.Button.middle)
                    elif mouse_btn == "Right":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.right)
                            mouse.Controller().release(mouse.Button.right)
                    
                    time.sleep(time_delay)
            else:
                count = int(self.repeat)
                while self.autoclicking and count > 0:
                    
                    count -= 1

                    if curr_pos == self.cursor_pos:
                        mouse_controller.position = curr_pos

                    if click_type == "Single":
                        x = 1
                    else:
                        x = 2
                    
                    if mouse_btn == "Left":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.left)
                            mouse.Controller().release(mouse.Button.left)
                    elif mouse_btn == "Middle":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.middle)
                            mouse.Controller().release(mouse.Button.middle)
                    elif mouse_btn == "Right":
                        for i in range(x):
                            mouse.Controller().press(mouse.Button.right)
                            mouse.Controller().release(mouse.Button.right)

                    time.sleep(time_delay)

            self.autoclicking = False
            self.autoclick_btn.configure(text=f"Start ({str(self.autoclick_hk).capitalize()})")

        threading.Thread(target=autoclick, daemon=True).start()

    def parse_interval(self):
        hours = 0 if self.hour_value.get() == "" else int(self.hour_value.get()) * 60 * 60
        minutes = 0 if self.minute_value.get() == "" else int(self.minute_value.get()) * 60
        seconds = 0 if self.second_value.get() == "" else int(self.second_value.get())
        milliseconds = 0 if self.millisecond_value.get() == "" else int(self.millisecond_value.get()) / 1000

        return hours + minutes + seconds + milliseconds

    def on_key_press(self, key):
        # Check hotkeys
        if self.key_type(key, self.play_hk) and not self.recorder.recording:
            job = self.root.after(0, self.toggle_play)
            self.after_jobs.append(job)
        if self.key_type(key, self.record_hk) and not self.playing:
            job = self.root.after(0, self.toggle_record)
            self.after_jobs.append(job)
        if self.key_type(key, self.autoclick_hk):
            job = self.root.after(0, self.autoclicker)

        if self.recorder.recording:
            self.recorder.on_key(key, "press")

    def on_key_release(self, key):
        if self.recorder.recording:
            self.recorder.on_key(key, "release")

    def toggle_play(self):
        self.playing = not self.playing

        if self.playing:
            self.stop_event.clear()
            self.play_btn.configure(text=f"Pause ({str(self.play_hk).capitalize()})")
            self.record_btn.configure(state="disabled")
            self._start_playback_thread()
        else:
            self.stop_event.set()
            self.play_btn.configure(text=f"Play ({str(self.play_hk).capitalize()})")
            self.record_btn.configure(state="enabled")

    def toggle_record(self):
        if not self.recorder.recording and not self.playing:
            self.record()
            self.record_btn.configure(text=f"Stop ({str(self.record_hk).capitalize()})")
        else:
            self.stop()
            self.record_btn.configure(text=f"Record ({str(self.record_hk).capitalize()})")

    def _start_playback_thread(self):

        def run_play():
            
            while self.playing and self.recorder.actions:

                if self.stop_event.is_set():
                    break

                if self.loop_var.get():
                        self.player.play(self.recorder.actions, self.stop_event, self.action_blocks)
                else:
                    self.player.play(self.recorder.actions, self.stop_event, self.action_blocks)
                    break

            time.sleep(0.1)
            self.playing = False
            self.record_btn.configure(state="enabled")
            job = self.root.after( 0, lambda: self.play_btn.configure(text=f"Play ({str(self.play_hk).capitalize()})"))
            self.after_jobs.append(job)
                
        threading.Thread(target=run_play, daemon=True).start()

    def stop(self):
        self.play_btn.configure(state="enabled")
        self.recorder.stop()
        self.update_action_blocks()

    def record(self):
        self.play_btn.configure(state="disabled")
        self.recorder.start(self.play_hk, self.record_hk)
        self.clear_actions()

    def clear_actions(self):
        self.clear_action_blocks()
        self.recorder.actions.clear()

    def clear_action_blocks(self):
        for block in self.action_blocks:
            block.destroy()
        self.action_blocks.clear()

    def update_action_blocks(self):
        self.clear_action_blocks()

        if len(self.recorder.actions) > 0:
            if self.recorder.actions[-1][1] == str(self.record_hk):
                self.recorder.actions.pop()
            if self.recorder.actions[0][1] == str(self.record_hk) or self.recorder.actions[0][0] == "mouse" and self.recorder.actions[0][1] == "release":
                self.recorder.actions.pop(0)

            for i, action in enumerate(self.recorder.actions):
                frame = ctk.CTkFrame(self.action_scroll_frame)
                frame.grid(row=i, column=0, sticky="nsew", padx=5, pady=5)
                frame.grid_columnconfigure(0, weight=1)

                label = ctk.CTkLabel(frame, text=self.parse_str(action), anchor="w")
                label.grid(row=0, column=0, sticky="w", padx=5)

                self.action_blocks.append(frame)
    
    def save_hotkeys(self, hotkeys: dict):
        with open(HOTKEY_FILE, "w", encoding="utf-8") as f:
            json.dump(hotkeys, f, indent=4)

    def load_hotkeys(self):
        if not os.path.exists(HOTKEY_FILE):
            self.create_path()
        
        try:
            with open(HOTKEY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except(json.JSONDecodeError, OSError):
            return DEFAULT_HOTKEYS.copy()
        
        result = {}
        
        for action, default in DEFAULT_HOTKEYS.items():
            value = data.get(action, default)

            try:
                result[action] = value
            except Exception:
                result[action] = default

        return result

    def save_file(self, save_as: bool):
        try:
            os.mkdir("./macros")
        except FileExistsError:
            pass

        if not os.path.exists(self.macro_save_file) or save_as:
            self.macro_save_file = filedialog.asksaveasfilename(title="Save As",
                                                                defaultextension=".mcro",
                                                                filetypes=[("Macro files", "*.mcro"), ("All files", "*.*")],
                                                                initialdir="./macros/"
                                                                )
        if self.recorder.actions:
            save_file: str = ""

            try:
                with open(self.macro_save_file, "wb") as f:
                    for action in self.recorder.actions:
                        if action[0] == "mouse":
                                save_file += action[0] + ", " + action[1] + ", " + str(action[2]) + ", " + str(action[3]) + ", " + str(action[4]) + ", " + action[5] + "\n"
                        elif action[0] == "mouse_move":
                            for moves in action[1]:
                                save_file += "mouse_move, " + str(moves[0]) + ", " + str(moves[1]) + ", " + str(moves[2]) + "\n"
                        elif action[0] == "key":
                                save_file += action[0] + ", " + action[1] + ", " + str(action[2]) + ", " + str(action[3]) + ", " + action[4] + "\n"

                    f.write(self.fernet.encrypt(save_file.encode()))
            except FileNotFoundError:
                return

    def load_file(self):
        self.macro_save_file = filedialog.askopenfilename(title="Load File",
                                                          defaultextension=".mcro",
                                                          filetypes=[("Macro files", "*.mcro"), ("All files", "*.*")],
                                                          initialdir="./macros/"
                                                          )

        try:
            with open(self.macro_save_file, "rb") as f:
                file = f.read()
        except FileNotFoundError:
            return

        #TODO: Add functionality to allow saving if actions not currently saved
        if self.recorder.actions:
            self.clear_actions()

        instructions = self.fernet.decrypt(file).decode().lower().split("\n")
        instructions.pop()

        for i in instructions:
            parsed_instruction = self.parse_instruction(i)

            if not parsed_instruction == None:
                self.recorder.actions.append(parsed_instruction)

        self.update_action_blocks()

    def parse_instruction(self, i: str):
        list = i.split(", ")

        match list[0]:
            case "mouse":
                self.recorder.flush_motion()
                return (list[0], list[1], float(list[2]), int(list[3]), int(list[4]), list[5])
            case "mouse_move":
                self.recorder.motion_buffer.append((float(list[1]), int(list[2]), int(list[3])))
                return None
            case "key":
                self.recorder.flush_motion()
                return (list[0], list[1], float(list[2]), list[3], list[4])
            case _:
                raise RuntimeError("File seems bad: " + list[0].capitalize())

    def key_type(self, key, hk):
        if isinstance (key, (keyboard.Key, keyboard.KeyCode)):
            try:
                if key == keyboard.Key[hk]: return True
            except KeyError:
                pass

            try:
                if key == keyboard.KeyCode.from_char(hk): return True
            except:
                pass

            return False
    
    def parse_str(self, text):
        match text[0]:
            case "mouse_move":
                output = text[0][6:].capitalize()
            case "mouse":
                output = str(text[5][7:]).capitalize() + " Mouse Btn" + ", X: " + str(text[3]) + ", Y: " + str(text[4]) + ", " + text[1].capitalize()
            case "key":
                output = text[0].capitalize() + ", " + text[1].capitalize() + ", " + text[4].capitalize()
            case _:
                output = "Something went wrong"
        return output
    
    def validate_input(self, P):
        if P.isdigit() or P == "":
            return True
        return False
    
    def create_path(self):
        with open(HOTKEY_FILE, "w", encoding="utf-8") as f:
            f.write("""{
                        "play": "f5",
                        "record": "f6",
                        "autoclick": "f7"
                    }""")
    
    def location_picker(self):
        self.cursor_button.configure(text="Waiting...")
        time.sleep(0.1)
        self.location_listener = mouse.Listener(on_click=self.cursor_location)
        self.location_listener.start()

    def cursor_location(self):
        self.cursor_pos = mouse.Controller().position
        self.cursor_X_Y_pos.configure(text=f"X: {self.cursor_pos[0]} Y: {self.cursor_pos[1]}")
        self.cursor_button.configure(text="Pick Location")
        if hasattr(self, "location_listener"):
            self.location_listener.stop()
    
    def on_close(self):
        # Protecc hotkeys
        self.save_hotkeys({
            "play": self.play_hk,
            "record": self.record_hk,
            "autoclick": self.autoclick_hk
        })

        # Ligma jobs
        for job in self.after_jobs:
            try:
                self.root.after_cancel(job)
            except:
                pass

        # Slay listeners
        if hasattr(self, "keyboard_listener"):
            self.keyboard_listener.stop()
        if hasattr(self.recorder, "mouse_listener"):
            try:
                self.recorder.mouse_listener.stop()
            except AttributeError:
                pass

        # Murder playback
        self.stop_event.set()

        # Massacre ctk
        try:
            self.root.quit()
        except:
            pass

        # Kill program
        self.root.destroy()
        
class ActionRecorder:
    def __init__(self):
        self.actions = []
        self.recording = False
        self.start_time = None
        self.motion_buffer = []
        self.mouse_listener = None
        self.keyboard_listener = None
        self.shift_pressed = False
        self.caps_lock = False

    def start(self, play_hk, record_hk):
        self.recording = True
        self.actions.clear()
        self.start_time = time.time()
        self.caps_lock = self.is_caps_lock()
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.mouse_listener.start()
        self.play_hk = play_hk
        self.record_hk = record_hk

    # TODO: Precheck if caps lock on/off
    def is_caps_lock(self):
        return bool(ctypes.WinDLL("user32").GetKeyState(0x14) & 1)

    def stop(self):
        if not self.recording:
            return
        
        if len(self.actions) > 0:
            last = self.actions[-1]

            if last[0] == "mouse" and last[1] == "press":
                x, y, button = last[3], last[4], last[5]
                t = time.time() - self.start_time
                self.actions.append(("mouse", "release", t, x, y, button))

        self.flush_motion()
        self.mouse_listener.stop()

        self.recording = False

    def on_click(self, x, y, button, pressed):
        if not self.recording:
            return
        self.flush_motion()

        t = time.time() - self.start_time
        action_type = "press" if pressed else "release"

        self.actions.append(("mouse", action_type, t, x, y, str(button)))

    def on_move(self, x, y):
        if not self.recording:
            return
        t = time.time() - self.start_time
        self.motion_buffer.append((t, x, y))

    def on_key(self, key, press):
        if not self.recording:
            return
        
        if key == self.play_hk or key == self.record_hk:
            return

        self.flush_motion()
        t = time.time() - self.start_time

        try:
            self.actions.append(("key", key.char, t, key, press))
        except:
            self.actions.append(("key", str(key)[4:], t, key, press))

    def flush_motion(self):
        if self.motion_buffer:
            cleaned_buffer = self.simplify_mbuffer()
            self.actions.append(("mouse_move", cleaned_buffer.copy()))
            self.motion_buffer.clear()

    def simplify_mbuffer(self):
        clean_buffer = [self.motion_buffer[0]]

        for t, x, y in self.motion_buffer[1:]:
            _, px, py = clean_buffer[-1]
            if (x, y) != (px, py):
                clean_buffer.append((t, x, y))
                
        return clean_buffer

class MacroClickerPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()

    def play(self, actions, stop_event, action_blocks):
        start = time.time()

        for i, action in enumerate(actions):
            if stop_event.is_set():
                for block in action_blocks:
                    block.configure(fg_color="#2B2B2B")
                return
            
            if action[0] == "mouse_move":
                moves = action[1]
                for t, x, y in moves:
                    if stop_event.is_set():
                        for block in action_blocks:
                            block.configure(fg_color="#2B2B2B")
                        return
                    while time.time() - start < t:
                        time.sleep(0.0005)
                    self.mouse_controller.position = (x, y)

            elif action[0] == "mouse":
                if stop_event.is_set():
                    for block in action_blocks:
                        block.configure(fg_color="#2B2B2B")
                    return
                _, action_type, t, x, y, button = action
                while time.time() - start < t:
                    time.sleep(0.0005)

                btn = mouse.Button.left if "left" in str(button) else mouse.Button.right

                self.mouse_controller.position = (x, y)
                if action_type == "press":
                    self.mouse_controller.press(btn)
                elif action_type == "release":
                    self.mouse_controller.release(btn)

            elif action[0] == "key":
                if stop_event.is_set():
                    for block in action_blocks:
                        block.configure(fg_color="#2B2B2B")
                    return
                _, _, t, char, action_type = action
                while time.time() - start < t:
                    time.sleep(0.0005)

                if action_type == "press":
                    try:
                        self.keyboard_controller.press(char)
                    except:
                        pass
                elif action_type == "release":
                    try:
                        self.keyboard_controller.release(char)
                    except:
                        pass
            
            action_blocks[i].configure(fg_color="#4B4B4B")
            try:
                action_blocks[i-1].configure(fg_color="#2B2B2B")
            except IndexError:
                pass

        time.sleep(0.1)
        action_blocks[-1].configure(fg_color="#2B2B2B")

class HotkeyWindow:
    def __init__(self, parent, root):
        self.parent = parent
        master = root
        
        self.parent.keyboard_listener.stop()

        master.update_idletasks()

        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        cw, ch = 500, 300

        x_off = px + (pw // 2) - (cw // 2)
        y_off = py + (ph // 2) - (ch // 2)

        self.hotkey_window = ctk.CTkToplevel(master)
        self.hotkey_window.title("Edit Hotkeys")
        self.hotkey_window.geometry(f"{cw}x{ch}+{x_off}+{y_off}")
        self.hotkey_window.resizable(False, False)
        self.hotkey_window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.hotkey_window.transient(master)
        self.hotkey_window.grab_set()
        self.hotkey_window.focus_force()
        self.hotkey_window.lift()

        self.hotkey_window.grid_columnconfigure(0, weight=1)
        self.hotkey_window.grid_rowconfigure(0, weight=1)

        self.hotkey_frame = ctk.CTkFrame(self.hotkey_window)
        self.hotkey_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.hotkey_frame.grid_rowconfigure(0, weight=1)
        self.hotkey_frame.grid_columnconfigure(0, weight=1)

        self.play_value = [ctk.StringVar(value=self.parent.play_hk), False]
        self.record_value = [ctk.StringVar(value=self.parent.record_hk), False]
        self.autoclick_value = [ctk.StringVar(value=self.parent.autoclick_hk), False]

        self.entry_frame = ctk.CTkFrame(self.hotkey_frame)
        self.entry_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        for i in range(3):
            self.entry_frame.grid_rowconfigure(i, weight=1)
            self.entry_frame.grid_columnconfigure(i, weight=1)

        self.play_hk_label = ctk.CTkLabel(self.entry_frame, text="Play Hotkey:")
        self.play_hk_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.play_value_entry = ctk.CTkEntry(self.entry_frame, textvariable=self.play_value[0], state="readonly", justify="center")
        self.play_value_entry.grid(row=0, column=1, sticky="ew", pady=5)
        self.play_hk_btn = ctk.CTkButton(self.entry_frame, text="Click to bind hotkey", command= lambda: self.change_hotkey(self.play_hk_btn, self.play_value))
        self.play_hk_btn.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        self.record_hk_label = ctk.CTkLabel(self.entry_frame, text="Record Hotkey:")
        self.record_hk_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.record_value_entry = ctk.CTkEntry(self.entry_frame, textvariable=self.record_value[0], state="readonly", justify="center")
        self.record_value_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.record_hk_btn = ctk.CTkButton(self.entry_frame, text="Click to bind hotkey", command= lambda: self.change_hotkey(self.record_hk_btn, self.record_value))
        self.record_hk_btn.grid(row=1, column=2, sticky="w", padx=5, pady=5)

        self.autoclick_hk_label = ctk.CTkLabel(self.entry_frame, text="Autoclick Hotkey:")
        self.autoclick_hk_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.autoclick_value_entry = ctk.CTkEntry(self.entry_frame, textvariable=self.autoclick_value[0], state="readonly", justify="center")
        self.autoclick_value_entry.grid(row=2, column=1, sticky="ew", pady=5)
        self.autoclick_hk_btn = ctk.CTkButton(self.entry_frame, text="Click to bind hotkey", command= lambda: self.change_hotkey(self.autoclick_hk_btn, self.autoclick_value))
        self.autoclick_hk_btn.grid(row=2, column=2, sticky="w", padx=5, pady=5)

        self.button_frame = ctk.CTkFrame(self.hotkey_frame, fg_color="#2B2B2B")
        self.button_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.button_frame.grid_rowconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)

        self.confirm_btn = ctk.CTkButton(self.button_frame, text="Confirm", command=self.confirm_changes)
        self.confirm_btn.grid(row=0, column=0, padx=5, pady=5)

        self.cancel_btn = ctk.CTkButton(self.button_frame, text="Cancel", command=self.on_close)
        self.cancel_btn.grid(row=0, column=1, padx=5, pady=5)

    def change_hotkey(self, hk_btn, value):
        self.hk_listener = keyboard.Listener(on_press=self.on_press)
        hk_btn.configure(text="Waiting...")
        value[1] = True
        self.play_hk_btn.configure(state="disabled")
        self.record_hk_btn.configure(state="disabled")
        self.autoclick_hk_btn.configure(state="disabled")

        self.hk_listener.start()

    def key_type(self, key):
        if isinstance(key, keyboard.Key):
            return key.name
        
        if isinstance(key, keyboard.KeyCode):
            return key

    def on_press(self, key):
        if self.play_value[1] == True:
            self.play_value[0] = ctk.StringVar(value=self.key_type(key))
            self.play_value[1] = False
            self.play_value_entry.configure(textvariable=self.play_value[0])
            self.play_hk_btn.configure(text="Click to bind hotkey")

        elif self.record_value[1] == True:
            self.record_value[0] = ctk.StringVar(value=self.key_type(key))
            self.record_value[1] = False
            self.record_value_entry.configure(textvariable=self.record_value[0])
            self.record_hk_btn.configure(text="Click to bind hotkey")

        elif self.autoclick_value[1] == True:
            self.autoclick_value[0] = ctk.StringVar(value=self.key_type(key))
            self.autoclick_value[1] = False
            self.autoclick_value_entry.configure(textvariable=self.autoclick_value[0])
            self.autoclick_hk_btn.configure(text="Click to bind hotkey")

        self.play_hk_btn.configure(state="enabled")
        self.record_hk_btn.configure(state="enabled")
        self.autoclick_hk_btn.configure(state="enabled")
        self.hk_listener.stop()

    def confirm_changes(self):
        self.parent.play_hk = self.play_value[0].get().strip("'")
        self.parent.record_hk = self.record_value[0].get().strip("'")
        self.parent.autoclick_hk = self.autoclick_value[0].get().strip("'")

        self.parent.save_hotkeys({
            "play": self.parent.play_hk,
            "record": self.parent.record_hk,
            "autoclick": self.parent.autoclick_hk
        })
        self.on_close()

    def on_close(self):
        self.parent.play_btn.configure(text=f"Play ({str(self.parent.play_hk).capitalize()})")
        self.parent.record_btn.configure(text=f"Record ({self.parent.record_hk})")
        self.parent.autoclick_btn.configure(text=f"Start ({self.parent.autoclick_hk})")
        self.parent.start_kb_listener()
        self.hotkey_window.grab_release()
        self.hotkey_window.destroy()

class How2UseWindow:
    def __init__(self, parent, root):
        self.parent = parent
        master = root
        
        self.parent.keyboard_listener.stop()

        master.update_idletasks()

        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        cw, ch = 350, 500

        x_off = px + (pw // 2) - (cw // 2)
        y_off = py + (ph // 2) - (ch // 2)

        self.help_window = ctk.CTkToplevel(master)
        self.help_window.title("How to Use")
        self.help_window.geometry(f"{cw}x{ch}+{x_off}+{y_off}")
        self.help_window.resizable(False, False)
        self.help_window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.help_window.transient(master)
        self.help_window.grab_set()
        self.help_window.focus_force()
        self.help_window.lift()

        self.header_font = ctk.CTkFont("Calibri", 36, "bold")
        self.subheader_font = ctk.CTkFont("Calibri", 20, "bold")
        self.body_font = ctk.CTkFont("Calibri", 16)

        self.help_window.grid_columnconfigure(0, weight=1)
        self.help_window.grid_rowconfigure(0, weight=0)
        self.help_window.grid_rowconfigure(1, weight=1)

        self.help_header = ctk.CTkLabel(self.help_window, text="How To Use", font=self.header_font)
        self.help_header.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.body_frame = ctk.CTkScrollableFrame(self.help_window)
        self.body_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.credits_subheader = ctk.CTkLabel(self.body_frame,
                                       text="""
Software created by TehWalrusCode
                                            """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.credits_subheader.grid(row=0, column=0, sticky="nsew")

        self.text_1 = ctk.CTkLabel(self.body_frame,
                                            text="""

This software is separated into two different functions. A Macro tool, and an Autoclicker.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_1.grid(row=1, column=0, sticky="nsew")

        self.macro_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""
Using the Macro tool
                                            """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.macro_subheader.grid(row=2, column=0, sticky="nsew")

        self.text_2 = ctk.CTkLabel(self.body_frame,
                                         text="""
To use the macro tool, first press Record or use the specified hotkey.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_2.grid(row=3, column=0, sticky="nsew")

        self.record_img = IMAGE_FILES["record"]
        self.record_label = ctk.CTkLabel(self.body_frame, image=self.record_img, text="")
        self.record_label.grid(row=4, column=0, sticky="nsew")

        self.text_3 = ctk.CTkLabel(self.body_frame,
                                       text="""
Then record the actions you want to repeat, such as mouse clicks, movement, or keyboard presses.
Once you are done, simply press stop or use the same hotkey as record and the actions will appear on screen.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_3.grid(row=5, column=0, sticky="nsew")

        self.stop_img = IMAGE_FILES["stop"]
        self.stop_label = ctk.CTkLabel(self.body_frame, image=self.stop_img, text="")
        self.stop_label.grid(row=6, column=0, sticky="nsew")

        self.text_4 = ctk.CTkLabel(self.body_frame,
                                       text="""
Then all you need to do is hit Play and watch the program replicate those actions exactly
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_4.grid(row=7, column=0, sticky="nsew")

        self.play_img = IMAGE_FILES["play"]
        self.play_label = ctk.CTkLabel(self.body_frame, image=self.play_img, text="")
        self.play_label.grid(row=8, column=0, sticky="nsew")

        self.text_5 = ctk.CTkLabel(self.body_frame,
                                       text="""
If you want to clear the actions, press the clear button or navigate to File->New
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_5.grid(row=9, column=0, sticky="nsew")

        self.clear_img = IMAGE_FILES["clear"]
        self.clear_label = ctk.CTkLabel(self.body_frame, image=self.clear_img, text="")
        self.clear_label.grid(row=10, column=0, sticky="nsew")

        self.text_6 = ctk.CTkLabel(self.body_frame,
                                       text="""
To loop the actions continuously, simply toggle loop and the actions will repeat until stopped by you.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_6.grid(row=11, column=0, sticky="nsew")

        self.loop_img = IMAGE_FILES["loop"]
        self.loop_label = ctk.CTkLabel(self.body_frame, image=self.loop_img, text="")
        self.loop_label.grid(row=12, column=0, sticky="nsew")

        self.text_7 = ctk.CTkLabel(self.body_frame,
                                       text="""
If you wish to save a macro for later use, navigate to File->Save and give your macro a name.
Loading a macro is much the same, simply navigate to File->Load and choose your specific file.
The default directory for macro saves is /macros/
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_7.grid(row=13, column=0, sticky="nsew")

        self.autoclicker_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""
Using the Autoclicker
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.autoclicker_subheader.grid(row=14, column=0, sticky="nsew")

        self.text_8 = ctk.CTkLabel(self.body_frame,
                                         text="""
To use the autoclicker, first specify your options as follows:
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_8.grid(row=15, column=0, sticky="nsew")

        self.click_interval_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""

Click Interval
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.click_interval_subheader.grid(row=16, column=0, sticky="nsew")

        self.click_interval_img = IMAGE_FILES["click_interval"]
        self.click_interval_label = ctk.CTkLabel(self.body_frame, image=self.click_interval_img, text="")
        self.click_interval_label.grid(row=17, column=0, sticky="nsew")

        self.text_9 = ctk.CTkLabel(self.body_frame,
                                       text="""
This is how long the program will wait before clicking the mouse, translated into seconds
1 hour: 3600 seconds
1 minute: 60 seconds
1 second: 1 seconds
1 millisecond: 0.001 seconds
(e.g 1h, 1m, 1s, 100ms translates to one click every 3661.1 seconds)
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_9.grid(row=18, column=0, sticky="nsew")

        self.mouse_button_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""

Mouse Button
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.mouse_button_subheader.grid(row=19, column=0, sticky="nsew")

        self.mouse_button_img = IMAGE_FILES["mouse_button"]
        self.mouse_button_label = ctk.CTkLabel(self.body_frame, image=self.mouse_button_img, text="")
        self.mouse_button_label.grid(row=20, column=0, sticky="nsew")

        self.text_10 = ctk.CTkLabel(self.body_frame,
                                       text="""
Which button should be pressed: Left, Middle, or Right click
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_10.grid(row=21, column=0, sticky="nsew")

        self.click_type_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""

Click Type
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.click_type_subheader.grid(row=22, column=0, sticky="nsew")

        self.click_type_img = IMAGE_FILES["click_type"]
        self.click_type_label = ctk.CTkLabel(self.body_frame, image=self.click_type_img, text="")
        self.click_type_label.grid(row=23, column=0, sticky="nsew")

        self.text_11 = ctk.CTkLabel(self.body_frame,
                                       text="""
Should it be a single, or double click
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_11.grid(row=24, column=0, sticky="nsew")

        self.repeat_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""

Repeat
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.repeat_subheader.grid(row=25, column=0, sticky="nsew")

        self.repeat_img = IMAGE_FILES["repeat"]
        self.repeat_label = ctk.CTkLabel(self.body_frame, image=self.repeat_img, text="")
        self.repeat_label.grid(row=26, column=0, sticky="nsew")

        self.text_12 = ctk.CTkLabel(self.body_frame,
                                       text="""
Repeat indefinitely, or by number of times
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_12.grid(row=27, column=0, sticky="nsew")

        self.cursor_pos_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""

Cursor Position
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.cursor_pos_subheader.grid(row=28, column=0, sticky="nsew")

        self.cursor_pos_img = IMAGE_FILES["cursor_pos"]
        self.cursor_pos_label = ctk.CTkLabel(self.body_frame, image=self.cursor_pos_img, text="")
        self.cursor_pos_label.grid(row=29, column=0, sticky="nsew")

        self.text_13 = ctk.CTkLabel(self.body_frame,
                                       text="""
Current Location of the mouse, or specific X, Y coordinates

Finally, once you're satisfied, simply press Start or use the hotkey and your mouse will begin clicking immediately.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_13.grid(row=30, column=0, sticky="nsew")

        self.start_img = IMAGE_FILES["start"]
        self.start_label = ctk.CTkLabel(self.body_frame, image=self.start_img, text="")
        self.start_label.grid(row=31, column=0, sticky="nsew")

        self.edit_hotkeys_subheader = ctk.CTkLabel(self.body_frame,
                                             text="""
Editing Hotkeys
                                                """,
                                       wraplength=260,
                                       font=self.subheader_font,
                                       justify="left")
        self.edit_hotkeys_subheader.grid(row=32, column=0, sticky="nsew")

        self.text_14 = ctk.CTkLabel(self.body_frame,
                                       text="""
To edit the hotkeys, simply navigate to Edit->Hotkeys and a new window will pop up, allowing you to change any hotkey into a different key if you wish.
It should go without saying that if you use a specific hotkey that you may want to use in a macro, it's probably not going to work like you want it to.
(Warning: You can set the same key for two or more different hotkeys, which will mess up the program.)
You can also change the hotkeys by opening the hotkeys.json file and manually editing them there.
                                            """,
                                       wraplength=260,
                                       font=self.body_font,
                                       justify="left")
        self.text_14.grid(row=33, column=0, sticky="nsew")

    def on_close(self):
        self.help_window.grab_release()
        self.help_window.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = MacroClickerUI(root)
    root.attributes('-topmost', True)
    root.mainloop()