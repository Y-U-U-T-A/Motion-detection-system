import cv2
import numpy as np
import pygame
import threading
import smtplib
import time
import os
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.recycleview import RecycleView
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, NumericProperty
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.spinner import Spinner

# Enable Kivy debug logging
from kivy.config import Config
Config.set('kivy', 'log_level', 'debug')

# ---------------------------
# Theme Dictionary
# ---------------------------
theme = {
    'background_color': (0.98, 0.98, 0.98, 1),
    'primary_color': (0.20, 0.60, 0.86, 1),
    'hover_color': (0.30, 0.75, 0.95, 1),
    'text_color': (0.25, 0.25, 0.25, 1),
    'shadow_color': (0, 0, 0, 0.15),
    'font_name': "DejaVuSans.ttf",
    'card_radius': dp(10),
    'card_padding': dp(30)
}

Window.clearcolor = theme['background_color']

# -----------------------------------------------------------------------------
# Utility to create a gradient texture – used for backgrounds
# -----------------------------------------------------------------------------
def create_gradient_texture(color_top, color_bottom, height=512):
    texture = Texture.create(size=(1, height), colorfmt='rgba')
    buf = []
    for y in range(height):
        t = y / (height - 1)
        r = color_top[0] * (1 - t) + color_bottom[0] * t
        g = color_top[1] * (1 - t) + color_bottom[1] * t
        b = color_top[2] * (1 - t) + color_bottom[2] * t
        a = color_top[3] * (1 - t) + color_bottom[3] * t
        buf.extend([int(r * 255), int(g * 255), int(b * 255), int(a * 255)])
    texture.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
    return texture

# -----------------------------------------------------------------------------
# Build a full-screen background using a generated texture
# -----------------------------------------------------------------------------
def build_background_widget():
    # For example, we create a gradient from a dark gray to a light gray based on the theme:
    tex = create_gradient_texture((0.2, 0.2, 0.2, 1), (0.9, 0.9, 0.9, 1))
    bg = Image()
    bg.texture = tex
    bg.allow_stretch = True
    bg.keep_ratio = False
    return bg

# -----------------------------------------------------------------------------
# Kivy Builder String for RecycleView Items with consistent styling
# -----------------------------------------------------------------------------
Builder.load_string('''
<MediaListItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(55)
    padding: dp(10)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
    Label:
        text: root.text
        markup: True
        color: (0.25, 0.25, 0.25, 1)
        size_hint_x: 0.5
        text_size: self.size
        halign: 'left'
        valign: 'middle'
    HoverButton:
        text: "[b]View[/b]"
        markup: True
        size_hint_x: 0.25
        font_size: dp(18)
        background_normal: ''
        background_down: ''
        on_release: root.view_media()
    HoverButton:
        text: "[b]Delete[/b]"
        markup: True
        size_hint_x: 0.25
        font_size: dp(18)
        background_normal: ''
        background_down: ''
        on_release: root.delete_media()

<EmailLogItem>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(65)
    padding: dp(10)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [%(card_radius)f]
    Label:
        text: root.text
        markup: True
        color: %(text_color)s
        text_size: self.width, None
        halign: 'left'
        valign: 'middle'

<UserListItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(55)
    padding: dp(10)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [%(card_radius)f]
    Label:
        text: root.text
        markup: True
        color: %(text_color)s
        size_hint_x: 1
        text_size: self.size
        halign: 'left'
        valign: 'middle'

<MediaRecycleView>:
    viewclass: "MediaListItem"
    RecycleBoxLayout:
        default_size: None, dp(55)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [%(card_radius)f]

<EmailLogRecycleView>:
    viewclass: "EmailLogItem"
    RecycleBoxLayout:
        default_size: None, dp(65)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [%(card_radius)f]

<UserRecycleView>:
    viewclass: "UserListItem"
    RecycleBoxLayout:
        default_size: None, dp(55)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: 1, 1, 1, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [%(card_radius)f]
''' % theme)

# -----------------------------------------------------------------------------
# Helper Functions for file directories
# -----------------------------------------------------------------------------
def get_user_target_folder():
    user_folder = os.path.join("users_data", current_user, "Target")
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

def get_user_email_log_file():
    user_folder = os.path.join("users_data", current_user)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return os.path.join(user_folder, "email_log.json")

# -----------------------------------------------------------------------------
# Custom HoverButton with theming and drop shadow
# -----------------------------------------------------------------------------
class HoverBehavior:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        Window.bind(mouse_pos=self.on_mouse_pos)
        self.hovered = False

    def on_mouse_pos(self, window, pos):
        if not self.get_root_window():
            return
        inside = self.collide_point(*self.to_widget(*pos))
        if inside == self.hovered:
            return
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self):
        pass

    def on_leave(self):
        pass

class HoverButton(HoverBehavior, ButtonBehavior, BoxLayout):
    text = StringProperty('')
    font_size = NumericProperty(14)
    def __init__(self, default_color=None, hover_color=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(8)
        self.default_color = default_color if default_color else theme['primary_color']
        self.hover_color = hover_color if hover_color else theme['hover_color']
        self.normal_texture = create_gradient_texture(self.default_color,
                                                      (self.default_color[0]*0.85,
                                                       self.default_color[1]*0.85,
                                                       self.default_color[2]*0.85, 1))
        self.hover_texture = create_gradient_texture(self.hover_color,
                                                     (self.hover_color[0]*0.85,
                                                      self.hover_color[1]*0.85,
                                                      self.hover_color[2]*0.85, 1))
        self.label = Label(markup=True, halign='center', valign='middle', size_hint=(1, 1))
        self.label.text = self.text
        self.label.font_size = self.font_size
        self.label.font_name = theme['font_name']
        self.label.color = (1, 1, 1, 1)
        self.add_widget(self.label)
        self.bind(text=self._on_text_change, font_size=self._on_fontsize_change)
        with self.canvas.before:
            Color(*theme['shadow_color'])
            self.shadow = RoundedRectangle(pos=(self.x+dp(2), self.y-dp(2)), size=self.size, radius=[theme['card_radius']])
            Color(1, 1, 1, 1)
            self.background_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[theme['card_radius']], texture=self.normal_texture)
        self.bind(pos=self._update_rect, size=self._update_rect)
    def _on_text_change(self, instance, value):
        self.label.text = value
    def _on_fontsize_change(self, instance, value):
        self.label.font_size = value
    def on_enter(self):
        Animation(font_size=self.font_size + dp(2), d=0.1).start(self.label)
        self.background_rect.texture = self.hover_texture
    def on_leave(self):
        Animation(font_size=self.font_size, d=0.1).start(self.label)
        self.background_rect.texture = self.normal_texture
    def _update_rect(self, *args):
        self.shadow.pos = (self.x+dp(2), self.y-dp(2))
        self.shadow.size = self.size
        self.background_rect.pos = self.pos
        self.background_rect.size = self.size

# -----------------------------------------------------------------------------
# Initialize Pygame Mixer
# -----------------------------------------------------------------------------
pygame.mixer.init()

# -----------------------------------------------------------------------------
# Global Variables & Configuration
# -----------------------------------------------------------------------------
sound_playing = False
motion_detected = False
last_email_sent_time = 0
recording = False
sensitivity = 500  
stop_detection = False
users = {}
current_user = None
default_subject = "Motion Detected"
default_body = "Motion has been detected by your security system."
droidcam_ip = "http://192.168.145.75:4747/video"

sender_email = "shrikukde@gmail.com"
receiver_email = "charlicriation@gmail.com"
password = "rxqz bofx xwic mejw"  # Replace with your actual app-specific password

USER_DATA_FILE = "users.json"
CONFIG_FILE = "config.json"

def initialize_users():
    global users
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as file:
                loaded_users = json.load(file)
                for username, data in loaded_users.items():
                    if isinstance(data, str):
                        users[username] = {'name': '', 'surname': '', 'email': receiver_email, 'password': data, 'role': 'user'}
                    elif isinstance(data, dict):
                        users[username] = data
                        if 'role' not in data:
                            users[username]['role'] = 'user'
            logging.info("Users loaded from %s", USER_DATA_FILE)
        except Exception as e:
            logging.error("Error loading users: %s", e)
            users = {}
    else:
        users = {
            "Yuta": {
                "name": "Yuta",
                "surname": "",
                "email": "yuta@example.com",
                "password": "rikka",
                "role": "admin"
            }
        }
        with open(USER_DATA_FILE, "w") as file:
            json.dump(users, file)
        logging.info("Initialized users.json with admin user 'Yuta'")
    if "Yuta" not in users or users["Yuta"]["role"] != "admin":
        users["Yuta"] = {
            "name": "Yuta",
            "surname": "",
            "email": "yuta@example.com",
            "password": "rikka",
            "role": "admin"
        }
        with open(USER_DATA_FILE, "w") as file:
            json.dump(users, file)
        logging.info("Added or updated admin user 'Yuta'")
initialize_users()

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as file:
        config = json.load(file)
        default_subject = config.get('email_subject', default_subject)
        default_body = config.get('email_body', default_body)
        receiver_email = config.get('receiver_email', receiver_email)
        droidcam_ip = config.get('droidcam_ip', droidcam_ip)
else:
    config = {
        'email_subject': default_subject,
        'email_body': default_body,
        'receiver_email': receiver_email,
        'droidcam_ip': droidcam_ip
    }
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

logging.basicConfig(filename='motion_detection.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# -----------------------------------------------------------------------------
# Custom OpenCV-based Video Player Class (CVVideoPlayer)
# -----------------------------------------------------------------------------
class CVVideoPlayer(BoxLayout):
    def __init__(self, video_path, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.video_path = video_path
        self.playing = False
        self.capture = cv2.VideoCapture(video_path)
        if not self.capture.isOpened():
            self.add_widget(Label(text="Error: Unable to open video file", color=(1,0,0,1)))
            return
        # Get total frames and fps for seeking
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.current_frame = 0
        self.image_widget = Image()
        self.add_widget(self.image_widget)
        self._update_event = None

    def start(self):
        if not self.playing:
            self.playing = True
            self._update_event = Clock.schedule_interval(self.update, 1.0 / self.fps)

    def pause(self):
        if self.playing:
            self.playing = False
            if self._update_event:
                Clock.unschedule(self._update_event)
                self._update_event = None

    def stop(self):
        self.pause()
        if self.capture and self.capture.isOpened():
            self.capture.release()

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            self.current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
            # Convert BGR to RGB and update texture
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            texture.flip_vertical()
            self.image_widget.texture = texture
        else:
            self.stop()

    def seek(self, frame_index):
        if self.capture and self.capture.isOpened():
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            self.current_frame = frame_index

# -----------------------------------------------------------------------------
# Core Functions
# -----------------------------------------------------------------------------
def play_alert_sound():
    global sound_playing
    if not sound_playing:
        sound_playing = True
        pygame.mixer.music.load("alert_sound.wav")
        pygame.mixer.music.play()
        threading.Timer(10.0, stop_alert_sound).start()

def stop_alert_sound():
    global sound_playing
    pygame.mixer.music.stop()
    sound_playing = False

def send_email_alert(video_path=None, image_path=None):
    global last_email_sent_time, receiver_email, default_subject, default_body, password
    current_time = time.time()
    if current_time - last_email_sent_time >= 20:
        msg = MIMEMultipart()
        msg["Subject"] = default_subject
        msg["From"] = sender_email
        msg["To"] = receiver_email
        body = MIMEText(default_body)
        msg.attach(body)
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as f:
                video_attachment = MIMEApplication(f.read(), _subtype="avi")
                video_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(video_path))
                msg.attach(video_attachment)
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                image_attachment = MIMEApplication(f.read(), _subtype="jpg")
                image_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                msg.attach(image_attachment)
        try:
            if not password:
                raise ValueError("Email password not set.")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Email sent successfully!")
            logging.info("Email sent successfully to %s", receiver_email)
            last_email_sent_time = current_time
            email_log_file = get_user_email_log_file()
            email_log = []
            if os.path.exists(email_log_file):
                with open(email_log_file, "r") as file:
                    email_log = json.load(file)
            email_log.append({
                'to': receiver_email,
                'subject': default_subject,
                'body': default_body,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'video': os.path.basename(video_path) if video_path else None,
                'image': os.path.basename(image_path) if image_path else None
            })
            with open(email_log_file, "w") as file:
                json.dump(email_log, file)
        except Exception as e:
            print(f"Error sending email: {e}")
            logging.error("Error sending email: %s", e)

def motion_detection():
    global sound_playing, motion_detected, recording, sensitivity, stop_detection, droidcam_ip
    cap = cv2.VideoCapture(droidcam_ip)
    if not cap.isOpened():
        logging.error(f"Failed to open video capture with IP: {droidcam_ip}")
        Clock.schedule_once(lambda dt: App.get_running_app().show_error("Camera Error", 
            f"Unable to access video stream at {droidcam_ip}"), 0)
        return
    ret, frame1 = cap.read()
    if not ret:
        logging.error("Failed to read initial frame from video stream.")
        cap.release()
        return
    ret, frame2 = cap.read()
    if not ret:
        logging.error("Failed to read second frame from video stream.")
        cap.release()
        return

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = None
    video_path = None
    image_path = None

    while cap.isOpened():
        if stop_detection:
            Clock.schedule_once(lambda dt: App.get_running_app().update_status_label("[b][color=757575]Detection Stopped[/color][/b]"), 0)
            break

        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 25, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion_in_zone = False
        for contour in contours:
            if cv2.contourArea(contour) < sensitivity:
                continue
            motion_in_zone = True
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)

        if motion_in_zone:
            if not motion_detected:
                threading.Thread(target=play_alert_sound).start()
                Clock.schedule_once(lambda dt: App.get_running_app().update_status_label("[b][color=E53935]Motion Detected[/color][/b]"), 0)
                motion_detected = True
                recording = True
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                target_folder = get_user_target_folder()
                video_path = os.path.join(target_folder, f'motion_{timestamp}.avi')
                out = cv2.VideoWriter(video_path, fourcc, 20.0, (frame1.shape[1], frame1.shape[0]))
                if not out.isOpened():
                    logging.error(f"Failed to initialize VideoWriter for {video_path}")
                image_path = os.path.join(target_folder, f'image_{timestamp}.jpg')
                cv2.imwrite(image_path, frame1)
                print(f"Started recording to {video_path}")
                logging.info(f"Started recording to {video_path}")
            if recording and out and out.isOpened():
                out.write(frame1)
        else:
            if motion_detected:
                motion_detected = False
                recording = False
                if out and out.isOpened():
                    out.release()
                    out = None
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                        send_email_alert(video_path=video_path, image_path=image_path)
                    else:
                        logging.error(f"Video file {video_path} is empty or not created.")
                    video_path = None
                    image_path = None
                Clock.schedule_once(lambda dt: App.get_running_app().update_status_label("[b][color=43A047]No Motion[/color][/b]"), 0)
                print("Stopped recording...")
                logging.info("Stopped recording")
        cv2.imshow("Motion Detector", frame1)
        frame1 = frame2
        ret, frame2 = cap.read()
        if not ret:
            logging.error("Failed to read frame during motion detection.")
            break

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    if out and out.isOpened():
        out.release()
    cv2.destroyAllWindows()

# -----------------------------------------------------------------------------
# Custom OpenCV-based Video Player Class (CVVideoPlayer)
# -----------------------------------------------------------------------------
class CVVideoPlayer(BoxLayout):
    def __init__(self, video_path, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.video_path = video_path
        self.playing = False
        self.capture = cv2.VideoCapture(video_path)
        if not self.capture.isOpened():
            self.add_widget(Label(text="Error: Unable to open video file", color=(1,0,0,1)))
            return
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.current_frame = 0
        self.image_widget = Image()
        self.add_widget(self.image_widget)
        self._update_event = None

    def start(self):
        if not self.playing:
            self.playing = True
            self._update_event = Clock.schedule_interval(self.update, 1.0 / self.fps)

    def pause(self):
        if self.playing:
            self.playing = False
            if self._update_event:
                Clock.unschedule(self._update_event)
                self._update_event = None

    def stop(self):
        self.pause()
        if self.capture and self.capture.isOpened():
            self.capture.release()

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            self.current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            texture.flip_vertical()
            self.image_widget.texture = texture
        else:
            self.stop()

    def seek(self, frame_index):
        if self.capture and self.capture.isOpened():
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            self.current_frame = frame_index

# -----------------------------------------------------------------------------
# Popup Classes with modern styling
# -----------------------------------------------------------------------------
class BasePopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*theme['background_color'])
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[theme['card_radius']])
        self.bind(size=self._update_bg_rect, pos=self._update_bg_rect)
    def _update_bg_rect(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

class SettingsPopup(BasePopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "[b]Update Settings[/b]"
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = False
        self.content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
        with self.content.canvas.before:
            Color(1, 1, 1, 1)
            self.content.bg_rect = RoundedRectangle(size=self.content.size, pos=self.content.pos, radius=[theme['card_radius']])
        self.content.bind(size=lambda inst, val: setattr(self.content.bg_rect, 'size', val))
        self.content.bind(pos=lambda inst, val: setattr(self.content.bg_rect, 'pos', val))
        user_email = users.get(current_user, {}).get('email', receiver_email) if current_user else receiver_email
        self.email_input = TextInput(hint_text="Receiver Email", text=user_email, multiline=False,
                                     font_size=dp(18), foreground_color=theme['text_color'])
        self.subject_input = TextInput(hint_text="Email Subject", text=default_subject, multiline=False,
                                       font_size=dp(18), foreground_color=theme['text_color'])
        self.body_input = TextInput(hint_text="Email Body", text=default_body, font_size=dp(18),
                                    foreground_color=theme['text_color'])
        self.ip_input = TextInput(hint_text="DroidCam IP (e.g., http://192.168.1.1:4747/video)", text=droidcam_ip,
                                  multiline=False, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(Label(text="Receiver Email:", font_size=dp(18), color=theme['text_color']))
        self.content.add_widget(self.email_input)
        self.content.add_widget(Label(text="Email Subject:", font_size=dp(18), color=theme['text_color']))
        self.content.add_widget(self.subject_input)
        self.content.add_widget(Label(text="Email Body:", font_size=dp(18), color=theme['text_color']))
        self.content.add_widget(self.body_input)
        self.content.add_widget(Label(text="DroidCam IP:", font_size=dp(18), color=theme['text_color']))
        self.content.add_widget(self.ip_input)
        btn_layout = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(12))
        self.save_button = HoverButton(text="[b]Save[/b]", font_size=dp(20))
        self.save_button.bind(on_release=self.save_settings)
        self.cancel_button = HoverButton(text="[b]Cancel[/b]", font_size=dp(20))
        self.cancel_button.bind(on_release=self.dismiss)
        btn_layout.add_widget(self.save_button)
        btn_layout.add_widget(self.cancel_button)
        self.content.add_widget(btn_layout)
    def save_settings(self, instance):
        global receiver_email, default_subject, default_body, droidcam_ip, config
        receiver_email = self.email_input.text
        default_subject = self.subject_input.text
        default_body = self.body_input.text
        droidcam_ip = self.ip_input.text.strip()
        config['receiver_email'] = receiver_email
        config['email_subject'] = default_subject
        config['email_body'] = default_body
        config['droidcam_ip'] = droidcam_ip
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file)
        logging.info(f"DroidCam IP updated to: {droidcam_ip}")
        self.dismiss()

class EmailLogItem(BoxLayout):
    text = StringProperty('')

class EmailLogRecycleView(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.load_emails()
    def load_emails(self):
        self.data = []
        email_log_file = get_user_email_log_file()
        if os.path.exists(email_log_file):
            with open(email_log_file, "r") as file:
                email_log = json.load(file)
            for email_entry in reversed(email_log):
                email_info = f"[b]To:[/b] {email_entry['to']}\n[b]Subject:[/b] {email_entry['subject']}\n[b]Time:[/b] {email_entry['time']}"
                self.data.append({'text': email_info})

class EmailLogPopup(BasePopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Sent Emails"
        self.size_hint = (0.8, 0.8)
        layout = BoxLayout(orientation='vertical', spacing=dp(12))
        with layout.canvas.before:
            Color(1, 1, 1, 1)
            layout.bg_rect = RoundedRectangle(size=layout.size, pos=layout.pos, radius=[theme['card_radius']])
        layout.bind(size=lambda inst, val: setattr(layout.bg_rect, 'size', val))
        layout.bind(pos=lambda inst, val: setattr(layout.bg_rect, 'pos', val))
        self.email_view = EmailLogRecycleView()
        layout.add_widget(self.email_view)
        close_button = HoverButton(text="[b]Close[/b]", font_size=dp(20), size_hint=(1, 0.15))
        close_button.bind(on_release=lambda inst: self.dismiss())
        layout.add_widget(close_button)
        self.content = layout
    def on_open(self):
        self.email_view.load_emails()

# -----------------------------------------------------------------------------
# VideoPlayerPopup Using CVVideoPlayer with Forward/Backward Slider Controls
# -----------------------------------------------------------------------------
class VideoPlayerPopup(BasePopup):
    def __init__(self, video_path, **kwargs):
        super().__init__(**kwargs)
        self.title = "Video Player"
        self.size_hint = (0.9, 0.9)
        self.video_path = video_path
        layout = BoxLayout(orientation='vertical', spacing=dp(12))
        logging.debug(f"Attempting to load video: {video_path}")
        print(f"Loading video: {video_path}")
        if not os.path.exists(video_path):
            logging.error(f"Video file not found: {video_path}")
            layout.add_widget(Label(text=f"Error: Video file not found at {video_path}", color=(1,0,0,1)))
        elif os.path.getsize(video_path) == 0:
            logging.error(f"Video file is empty: {video_path}")
            layout.add_widget(Label(text=f"Error: Video file is empty at {video_path}", color=(1,0,0,1)))
        else:
            self.cv_player = CVVideoPlayer(video_path)
            layout.add_widget(self.cv_player)
            # Slider to seek frames
            self.seek_slider = Slider(min=0, max=self.cv_player.total_frames - 1, value=0)
            self.seek_slider.bind(value=self.on_slider_value)
            layout.add_widget(self.seek_slider)
            # Add forward and backward buttons:
            nav_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.15), spacing=dp(12))
            self.backward_btn = HoverButton(text="[b]<<[/b]", font_size=dp(20))
            self.backward_btn.bind(on_release=self.step_backward)
            self.forward_btn = HoverButton(text="[b]>>[/b]", font_size=dp(20))
            self.forward_btn.bind(on_release=self.step_forward)
            nav_layout.add_widget(self.backward_btn)
            nav_layout.add_widget(self.forward_btn)
            layout.add_widget(nav_layout)
        # Control buttons for play/pause/stop/close
        control_layout = BoxLayout(size_hint=(1, 0.15), spacing=dp(12))
        play_btn = HoverButton(text="[b]Play[/b]", font_size=dp(20))
        play_btn.bind(on_release=lambda inst: self.cv_player.start() if hasattr(self, 'cv_player') else None)
        pause_btn = HoverButton(text="[b]Pause[/b]", font_size=dp(20))
        pause_btn.bind(on_release=lambda inst: self.cv_player.pause() if hasattr(self, 'cv_player') else None)
        stop_btn = HoverButton(text="[b]Stop[/b]", font_size=dp(20))
        stop_btn.bind(on_release=lambda inst: self.cv_player.stop() if hasattr(self, 'cv_player') else None)
        close_btn = HoverButton(text="[b]Close[/b]", font_size=dp(20))
        close_btn.bind(on_release=self.dismiss)
        control_layout.add_widget(play_btn)
        control_layout.add_widget(pause_btn)
        control_layout.add_widget(stop_btn)
        control_layout.add_widget(close_btn)
        layout.add_widget(control_layout)
        self.content = layout
        # Schedule periodic slider updates:
        Clock.schedule_interval(self.update_slider_position, 0.5)

    def on_slider_value(self, instance, value):
        # When slider is changed manually, seek the video.
        if hasattr(self, 'cv_player'):
            self.cv_player.seek(int(value))

    def update_slider_position(self, dt):
        if hasattr(self, 'cv_player') and self.cv_player.playing:
            # Update slider with current frame value
            self.seek_slider.value = self.cv_player.current_frame

    def step_backward(self, instance):
        if hasattr(self, 'cv_player'):
            new_frame = max(self.cv_player.current_frame - 10, 0)
            self.cv_player.seek(new_frame)
            self.seek_slider.value = new_frame

    def step_forward(self, instance):
        if hasattr(self, 'cv_player'):
            new_frame = min(self.cv_player.current_frame + 10, self.cv_player.total_frames - 1)
            self.cv_player.seek(new_frame)
            self.seek_slider.value = new_frame

    def on_open(self):
        if hasattr(self, 'cv_player'):
            self.cv_player.start()

    def on_dismiss(self):
        if hasattr(self, 'cv_player'):
            self.cv_player.stop()
            logging.debug(f"Video stopped and popup dismissed: {self.video_path}")

class ImageViewerPopup(BasePopup):
    def __init__(self, image_path, **kwargs):
        super().__init__(**kwargs)
        self.title = "Image Viewer"
        self.size_hint = (0.9, 0.9)
        layout = BoxLayout(orientation='vertical', spacing=dp(12))
        self.image = Image(source=image_path, allow_stretch=True, keep_ratio=True)
        layout.add_widget(self.image)
        close_btn = HoverButton(text="[b]Close[/b]", font_size=dp(20), size_hint=(1, 0.15))
        close_btn.bind(on_release=lambda inst: self.dismiss())
        layout.add_widget(close_btn)
        self.content = layout

# -----------------------------------------------------------------------------
# Media List and Sorting Features (unchanged)
# -----------------------------------------------------------------------------
class MediaListItem(BoxLayout):
    text = StringProperty('')
    media_path = StringProperty('')

    def view_media(self):
        if self.media_path.endswith('.avi'):
            player = VideoPlayerPopup(video_path=self.media_path)
            player.open()
        else:
            viewer = ImageViewerPopup(image_path=self.media_path)
            viewer.open()

    def delete_media(self):
        if os.path.exists(self.media_path):
            os.remove(self.media_path)
            App.get_running_app().show_popup("Deleted", f"{os.path.basename(self.media_path)} deleted.")
            App.get_running_app().media_list_popup.media_view.load_media()

class MediaRecycleView(RecycleView):
    def __init__(self, sort_order="newest", **kwargs):
        super().__init__(**kwargs)
        self.sort_order = sort_order
        self.data = []
        self.load_media()

    def load_media(self):
        self.data = []
        target_folder = get_user_target_folder()
        if os.path.exists(target_folder):
            media_files = [f for f in os.listdir(target_folder) if f.endswith('.avi') or f.endswith('.jpg')]
            if self.sort_order == "newest":
                media_files.sort(key=lambda f: os.path.getmtime(os.path.join(target_folder, f)), reverse=True)
            elif self.sort_order == "oldest":
                media_files.sort(key=lambda f: os.path.getmtime(os.path.join(target_folder, f)))
            elif self.sort_order == "name_az":
                media_files.sort()
            elif self.sort_order == "name_za":
                media_files.sort(reverse=True)
            for media_file in media_files:
                media_path = os.path.join(target_folder, media_file)
                self.data.append({'text': media_file, 'media_path': media_path})

class MediaListPopup(BasePopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Captured Media"
        self.size_hint = (0.8, 0.9)
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        self.sort_spinner = Spinner(
            text='Sort: Newest First',
            values=('Newest First', 'Oldest First', 'Name A-Z', 'Name Z-A'),
            size_hint=(1, None),
            height=dp(45)
        )
        self.sort_spinner.bind(text=self.on_sort_selected)
        self.media_view = MediaRecycleView()
        layout.add_widget(self.sort_spinner)
        layout.add_widget(self.media_view)
        close_btn = HoverButton(text="[b]Close[/b]", font_size=dp(20), size_hint=(1, 0.1))
        close_btn.bind(on_release=self.dismiss)
        layout.add_widget(close_btn)
        self.content = layout
    def on_open(self):
        self.media_view.load_media()
    def on_sort_selected(self, spinner, text):
        order_map = {
            "Newest First": "newest",
            "Oldest First": "oldest",
            "Name A-Z": "name_az",
            "Name Z-A": "name_za"
        }
        self.media_view.sort_order = order_map[text]
        self.media_view.load_media()

# -----------------------------------------------------------------------------
# Additional Popup Classes for User Management and About Section (unchanged)
# -----------------------------------------------------------------------------
class AddUserPopup(BasePopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Add New User"
        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = False
        self.content = GridLayout(cols=2, spacing=dp(12), padding=dp(20), row_default_height=dp(55))
        with self.content.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.form_rect = RoundedRectangle(size=self.content.size, pos=self.content.pos, radius=[theme['card_radius']])
        self.content.bind(size=lambda inst, val: setattr(self.form_rect, 'size', val))
        self.content.bind(pos=lambda inst, val: setattr(self.form_rect, 'pos', val))
        self.content.add_widget(Label(text="Name:", font_size=dp(18), color=theme['text_color']))
        self.name_input = TextInput(hint_text="Enter name", multiline=False, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(self.name_input)
        self.content.add_widget(Label(text="Surname:", font_size=dp(18), color=theme['text_color']))
        self.surname_input = TextInput(hint_text="Enter surname", multiline=False, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(self.surname_input)
        self.content.add_widget(Label(text="Email:", font_size=dp(18), color=theme['text_color']))
        self.email_input = TextInput(hint_text="Enter email", multiline=False, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(self.email_input)
        self.content.add_widget(Label(text="Username:", font_size=dp(18), color=theme['text_color']))
        self.username_input = TextInput(hint_text="Enter username", multiline=False, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(self.username_input)
        self.content.add_widget(Label(text="Password:", font_size=dp(18), color=theme['text_color']))
        self.password_input = TextInput(hint_text="Enter password", multiline=False, password=True, font_size=dp(18), foreground_color=theme['text_color'])
        self.content.add_widget(self.password_input)
        buttons_layout = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(12))
        self.save_button = HoverButton(text="[b]Add User[/b]", font_size=dp(20))
        self.save_button.bind(on_release=self.add_user)
        self.cancel_button = HoverButton(text="[b]Cancel[/b]", font_size=dp(20))
        self.cancel_button.bind(on_release=self.dismiss)
        buttons_layout.add_widget(self.save_button)
        buttons_layout.add_widget(self.cancel_button)
        self.content.add_widget(Label())
        self.content.add_widget(buttons_layout)
    def add_user(self, instance):
        name = self.name_input.text
        surname = self.surname_input.text
        email = self.email_input.text
        username = self.username_input.text
        password_input = self.password_input.text
        if all([name, surname, email, username, password_input]):
            if username in users:
                App.get_running_app().show_error("User Exists", "Username already exists!")
            else:
                users[username] = {
                    'name': name,
                    'surname': surname,
                    'email': email,
                    'password': password_input,
                    'role': 'user'
                }
                with open(USER_DATA_FILE, "w") as file:
                    json.dump(users, file)
                App.get_running_app().show_popup("User Created", "New user created successfully!")
                self.dismiss()
        else:
            App.get_running_app().show_error("Invalid Input", "Please fill in all fields.")

class AboutPopup(BasePopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "About"
        self.size_hint = (0.8, 0.5)
        self.content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
        self.content.add_widget(Label(text="[b]Motion Detector Security System[/b]", markup=True, font_size=dp(26)))
        self.content.add_widget(Label(text="Version 1.1", font_size=dp(20), color=theme['text_color']))
        self.content.add_widget(Label(text="Enhanced motion detection.", font_size=dp(20), color=theme['text_color']))
        close_btn = HoverButton(text="[b]Close[/b]", font_size=dp(20), size_hint=(1, None), height=dp(55))
        close_btn.bind(on_release=self.dismiss)
        self.content.add_widget(close_btn)

class UserListItem(BoxLayout):
    text = StringProperty('')

class UserRecycleView(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.load_users()
    def load_users(self):
        self.data = []
        for username, user_data in users.items():
            if isinstance(user_data, dict):
                name = user_data.get('name', '')
                surname = user_data.get('surname', '')
                email = user_data.get('email', '')
                role = user_data.get('role', 'user')
                user_info = (
                    f"[b]Username:[/b] {username} - "
                    f"[b]Name:[/b] {name} {surname} - "
                    f"[b]Email:[/b] {email} - "
                    f"[b]Role:[/b] {role}"
                )
                self.data.append({'text': user_info})

# -----------------------------------------------------------------------------
# Main Application Class
# -----------------------------------------------------------------------------
class MotionDetectionApp(App):
    def build(self):
        self.title = "Motion Detector Security System"
        self.root = FloatLayout()
        # Use our generated background texture instead of images
        bg = build_background_widget()
        self.root.add_widget(bg, index=0)
        self.login_layout = self.create_login_layout()
        self.root.add_widget(self.login_layout)
        Window.bind(on_resize=self.on_window_resize)
        return self.root

    def create_login_layout(self):
        root = FloatLayout()
        # Use generated texture for login background
        bg = build_background_widget()
        root.add_widget(bg)
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        card = BoxLayout(orientation='vertical', spacing=dp(20), padding=theme['card_padding'], size_hint=(None, None))
        card.width = min(Window.width * 0.4, 450)
        card.height = min(Window.height * 0.5, 400)
        with card.canvas.before:
            Color(0, 0, 0, 0.15)
            RoundedRectangle(pos=(card.x+dp(4), card.y-dp(4)), size=card.size, radius=[theme['card_radius']])
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(size=card.size, pos=card.pos, radius=[theme['card_radius']])
        card.bind(size=lambda inst, val: setattr(self.card_rect, 'size', val))
        card.bind(pos=lambda inst, val: setattr(self.card_rect, 'pos', val))
        heading = Label(text="[b]Motion Detector Security System[/b]", markup=True, font_size=dp(32),
                        color=theme['text_color'], size_hint=(1, None), height=dp(190), halign='center')
        heading.font_name = theme['font_name']
        heading.bind(size=lambda inst, val: setattr(heading, 'text_size', (val[0], None)))
        card.add_widget(heading)
        self.username_input = TextInput(hint_text="Username", multiline=False, font_size=dp(18),
                                        foreground_color=theme['text_color'], size_hint=(1, None), height=dp(45))
        self.password_input = TextInput(hint_text="Password", multiline=False, password=True, font_size=dp(18),
                                        foreground_color=theme['text_color'], size_hint=(1, None), height=dp(45))
        self.username_input.bind(on_text_validate=lambda inst: setattr(self.password_input, 'focus', True))
        card.add_widget(self.username_input)
        card.add_widget(self.password_input)
        login_btn = HoverButton(text="[b]Login 🚪[/b]", font_size=dp(20), size_hint=(1, None), height=dp(55))
        login_btn.bind(on_release=self.login)
        create_user_btn = HoverButton(text="[b]Create New User[/b]", font_size=dp(20), size_hint=(1, None), height=dp(55))
        create_user_btn.bind(on_release=self.create_new_user)
        card.add_widget(login_btn)
        card.add_widget(create_user_btn)
        anchor.add_widget(card)
        root.add_widget(anchor)
        return root

    def show_motion_layout(self):
        root = FloatLayout()
        bg = build_background_widget()
        root.add_widget(bg)
        layout = BoxLayout(orientation='vertical')
        with layout.canvas.before:
            Color(1, 1, 1, 1)
            self.layout_rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=lambda inst, val: setattr(self.layout_rect, 'size', val))
        layout.bind(pos=lambda inst, val: setattr(self.layout_rect, 'pos', val))
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), padding=dp(12), spacing=dp(12))
        with header.canvas.before:
            Color(1, 1, 1, 1)
            self.header_rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda inst, val: setattr(self.header_rect, 'size', val))
        header.bind(pos=lambda inst, val: setattr(self.header_rect, 'pos', val))
        self.menu_button = HoverButton(text="[b]☰[/b]", font_size=dp(24), size_hint=(None, 1), width=dp(60))
        self.menu_button.bind(on_release=self.toggle_menu)
        header_title = Label(text="Motion Detector Security System", font_size=dp(26),
                             halign='center', valign='middle', color=theme['text_color'])
        header_title.font_name = theme['font_name']
        header.add_widget(self.menu_button)
        header.add_widget(header_title)
        layout.add_widget(header)
        self.status_label = Label(text="[b][color=757575]Detection Stopped[/color][/b]",
                                  markup=True, font_size=dp(32), halign='center', valign='middle', color=theme['text_color'])
        self.status_label.font_name = theme['font_name']
        center_box = AnchorLayout(anchor_x='center', anchor_y='center')
        with center_box.canvas.before:
            Color(1, 1, 1, 1)
            self.center_rect = Rectangle(size=center_box.size, pos=center_box.pos)
        center_box.bind(size=lambda inst, val: setattr(self.center_rect, 'size', val))
        center_box.bind(pos=lambda inst, val: setattr(self.center_rect, 'pos', val))
        center_box.add_widget(self.status_label)
        layout.add_widget(center_box)
        bottom_bar = BoxLayout(orientation='horizontal', size_hint=(1, 0.15), padding=dp(12), spacing=dp(12))
        with bottom_bar.canvas.before:
            Color(1, 1, 1, 1)
            self.bottom_rect = Rectangle(size=bottom_bar.size, pos=bottom_bar.pos)
        bottom_bar.bind(size=lambda inst, val: setattr(self.bottom_rect, 'size', val))
        bottom_bar.bind(pos=lambda inst, val: setattr(self.bottom_rect, 'pos', val))
        start_btn = HoverButton(text="[b]▶ Start Detection[/b]", font_size=dp(20))
        start_btn.bind(on_release=self.start_motion_detection)
        stop_btn = HoverButton(text="[b]■ Stop Detection[/b]", font_size=dp(20))
        stop_btn.bind(on_release=self.stop_motion_detection)
        about_btn = HoverButton(text="[b]? About[/b]", font_size=dp(20))
        about_btn.bind(on_release=self.open_about)
        bottom_bar.add_widget(start_btn)
        bottom_bar.add_widget(stop_btn)
        bottom_bar.add_widget(about_btn)
        layout.add_widget(bottom_bar)
        root.add_widget(layout)
        return root

    def login(self, instance):
        global current_user
        username = self.username_input.text.strip()
        password_input = self.password_input.text.strip()
        logging.debug(f"Login attempt: Username='{username}', Password='{password_input}'")
        if username in users:
            user_data = users[username]
            stored_password = user_data.get('password', '') if isinstance(user_data, dict) else user_data
            logging.debug(f"Stored password for {username}: '{stored_password}'")
            if stored_password == password_input:
                current_user = username
                role = user_data.get('role', 'user') if isinstance(user_data, dict) else 'user'
                logging.info(f"Login successful for {username} with role {role}")
                fade_anim = Animation(opacity=0, duration=0.5)
                if role == 'admin':
                    fade_anim.bind(on_complete=lambda *args: self.switch_to_admin_screen())
                else:
                    fade_anim.bind(on_complete=lambda *args: self.switch_to_motion_screen())
                fade_anim.start(self.login_layout)
            else:
                logging.warning("Invalid password for %s", username)
                Clock.schedule_once(lambda dt: self.show_error("Login Failed", "Invalid password!"), 0)
        else:
            logging.warning("Invalid username: %s", username)
            Clock.schedule_once(lambda dt: self.show_error("Login Failed", "Invalid username!"), 0)

    def switch_to_motion_screen(self):
        self.root.clear_widgets()
        self.motion_layout = self.show_motion_layout()
        self.root.add_widget(self.motion_layout)
        self.menu_layout = self.create_menu_layout()
        self.root.add_widget(self.menu_layout)

    def switch_to_admin_screen(self):
        self.root.clear_widgets()
        self.admin_layout = self.create_admin_layout()
        self.root.add_widget(self.admin_layout)

    def create_new_user(self, instance):
        AddUserPopup().open()

    def start_motion_detection(self, instance):
        global stop_detection, recording
        stop_detection = False
        recording = False
        Clock.schedule_once(lambda dt: self.update_status_label("[b][color=43A047]No Motion[/color][/b]"), 0)
        threading.Thread(target=motion_detection).start()

    def stop_motion_detection(self, instance):
        global stop_detection
        stop_detection = True
        Clock.schedule_once(lambda dt: self.update_status_label("[b][color=757575]Detection Stopped[/color][/b]"), 0)

    def create_menu_layout(self):
        self.menu_open = False
        menu_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1))
        menu_layout.pos = (-Window.width * 0.6, 0)
        with menu_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.menu_rect = RoundedRectangle(size=menu_layout.size, pos=menu_layout.pos, radius=[theme['card_radius']])
        menu_layout.bind(size=lambda inst, val: setattr(self.menu_rect, 'size', val))
        menu_layout.bind(pos=lambda inst, val: setattr(self.menu_rect, 'pos', val))
        close_btn = HoverButton(text="[b]✕ Close Menu[/b]", font_size=dp(20),
                                default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        close_btn.bind(on_release=self.toggle_menu)
        settings_btn = HoverButton(text="[b]⚙ Settings[/b]", font_size=dp(20),
                                   default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        settings_btn.bind(on_release=self.open_settings)
        media_btn = HoverButton(text="[b]📷 View Media[/b]", font_size=dp(20),
                                default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        media_btn.bind(on_release=self.view_media)
        emails_btn = HoverButton(text="[b]✉ View Emails[/b]", font_size=dp(20),
                                 default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        emails_btn.bind(on_release=self.view_emails)
        add_user_btn = HoverButton(text="[b]➕ Add User[/b]", font_size=dp(20),
                                   default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        add_user_btn.bind(on_release=self.create_new_user)
        logout_btn = HoverButton(text="[b]🚪 Logout[/b]", font_size=dp(20),
                                 default_color=(0.3, 0.3, 0.3, 1), hover_color=(0.5, 0.5, 0.5, 1))
        logout_btn.bind(on_release=self.logout)
        menu_layout.add_widget(close_btn)
        menu_layout.add_widget(settings_btn)
        menu_layout.add_widget(media_btn)
        menu_layout.add_widget(emails_btn)
        menu_layout.add_widget(add_user_btn)
        menu_layout.add_widget(logout_btn)
        return menu_layout

    def toggle_menu(self, instance=None):
        if not hasattr(self, 'menu_layout'):
            return
        if not self.menu_open:
            Animation(x=0, d=0.3, t='out_quad').start(self.menu_layout)
            self.menu_open = True
        else:
            Animation(x=-self.menu_layout.width, d=0.3, t='out_quad').start(self.menu_layout)
            self.menu_open = False

    def open_settings(self, instance):
        if self.menu_open:
            self.toggle_menu()
        SettingsPopup().open()

    def view_media(self, instance):
        if self.menu_open:
            self.toggle_menu()
        popup = MediaListPopup()
        self.media_list_popup = popup
        popup.open()

    def view_emails(self, instance):
        if self.menu_open:
            self.toggle_menu()
        EmailLogPopup().open()

    def open_about(self, instance):
        if self.menu_open:
            self.toggle_menu()
        AboutPopup().open()

    def logout(self, instance):
        global current_user
        if self.menu_open:
            self.toggle_menu()
        self.stop_motion_detection(None)
        self.root.clear_widgets()
        self.root.add_widget(self.create_login_layout())
        current_user = None

    def update_status_label(self, text):
        if hasattr(self, 'status_label'):
            self.status_label.text = text

    def show_error(self, title, message):
        def _show_error(dt):
            popup = BasePopup(title=title, size_hint=(None, None), size=(400, 200))
            with popup.canvas.before:
                Color(*theme['background_color'])
                popup.error_rect = RoundedRectangle(size=popup.size, pos=popup.pos, radius=[theme['card_radius']])
            popup.bind(size=lambda inst, val: setattr(popup.error_rect, 'size', val))
            popup.bind(pos=lambda inst, val: setattr(popup.error_rect, 'pos', val))
            lbl = Label(text=f"[color=E53935]{message}[/color]", markup=True, font_size=dp(20), color=theme['text_color'])
            popup.content = lbl
            popup.open()
        Clock.schedule_once(_show_error, 0)

    def show_popup(self, title, message):
        def _show_popup(dt):
            popup = BasePopup(title=title, size_hint=(None, None), size=(400, 200))
            with popup.canvas.before:
                Color(*theme['background_color'])
                popup.popup_rect = RoundedRectangle(size=popup.size, pos=popup.pos, radius=[theme['card_radius']])
            popup.bind(size=lambda inst, val: setattr(popup.popup_rect, 'size', val))
            popup.bind(pos=lambda inst, val: setattr(popup.popup_rect, 'pos', val))
            lbl = Label(text=message, font_size=dp(20), color=theme['text_color'])
            popup.content = lbl
            popup.open()
        Clock.schedule_once(_show_popup, 0)

    def on_window_resize(self, instance, width, height):
        if hasattr(self, 'menu_layout') and not self.menu_open:
            self.menu_layout.pos = (-width * 0.6, 0)

    def on_stop(self):
        global stop_detection
        stop_detection = True

    def create_admin_layout(self):
        layout = BoxLayout(orientation='vertical')
        with layout.canvas.before:
            Color(1, 1, 1, 1)
            self.admin_rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=lambda inst, val: setattr(self.admin_rect, 'size', val)) 
        layout.bind(pos=lambda inst, val: setattr(self.admin_rect, 'pos', val))
        header = Label(
            text="[b]Admin Dashboard[/b]",
            markup=True,
            font_size=dp(32),
            color=theme['text_color'],
            size_hint=(1, 0.1)
        )
        layout.add_widget(header)
        self.user_view = UserRecycleView()
        layout.add_widget(self.user_view)
        logout_btn = HoverButton(text="[b]Logout[/b]", font_size=dp(20), size_hint=(1, 0.1))
        logout_btn.bind(on_release=self.logout)
        layout.add_widget(logout_btn)
        return layout

if __name__ == '__main__':
    MotionDetectionApp().run()
