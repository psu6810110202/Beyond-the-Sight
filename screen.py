from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation
import os

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

class MenuButton(ButtonBehavior, FloatLayout):
    """Custom button that stays perfectly in proportion to its image source."""
    def __init__(self, text="", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (320, 80) # Initial size for stability
        
        # Determine aspect ratio from the image
        try:
            tex = CoreImage('assets/button/button0.png').texture
            self.image_ratio = tex.width / tex.height
        except:
            self.image_ratio = 4.0  # Safe fallback
            
        # Background Image - perfectly fitted
        self.bg_image = Image(
            source='assets/button/button0.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        # ตั้งค่าให้รูปภาพคมชัด (Pixel Art) โดยใช้ Nearest Filter
        self.bg_image.bind(texture=self._set_nearest_filter)
        self.add_widget(self.bg_image)
        
        # ตรวจสอบและตั้งค่า Filter ทันที (แก้ปัญหาเบลอตอนไม่กด)
        if self.bg_image.texture:
            self._set_nearest_filter(None, self.bg_image.texture)
        
        # Label - precisely centered
        self.label = Label(
            text=text,
            font_name='assets/Fonts/edit-undo.brk.ttf',
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.52}, # Slightly up for visual balance
            halign='center',
            valign='middle'
        )
        self.add_widget(self.label)
        
        # ผูกเหตุการณ์เมาส์ชี้เพื่อให้ปุ่มมืดลง (แยกทำงานทีละปุ่ม)
        self._mouse_callback = self.on_mouse_move
        Window.bind(mouse_pos=self._mouse_callback)

    def _set_nearest_filter(self, instance, texture):
        if texture:
            texture.min_filter = 'nearest'
            texture.mag_filter = 'nearest'

    def on_state(self, instance, value):
        # เปลี่ยนรูปภาพตามสถานะการกด
        if value == 'down':
            self.bg_image.source = 'assets/button/button1.png'
            # ตัวอักษรยุบลงตามปุ่ม
            self.label.pos_hint = {'center_x': 0.5, 'center_y': 0.48}
        else:
            self.bg_image.source = 'assets/button/button0.png'
            # ตัวอักษรกลับมาตำแหน่งปกติ
            self.label.pos_hint = {'center_x': 0.5, 'center_y': 0.52}
            
        # บังคับให้ตรวจสอบ Filter อีกครั้งเมื่อเปลี่ยนรูปเพื่อให้คมชัดเสมอ
        if self.bg_image.texture:
            self._set_nearest_filter(None, self.bg_image.texture)

    def on_mouse_move(self, window, pos):
        # ใช้ collide_point(*pos) ตรงๆ เพราะ pos จาก Window มาเป็นพิกัดหน้าต่างอยู่แล้ว
        # วิธีนี้จะทำให้เช็คโดนเฉพาะปุ่มที่เมาส์ชี้จริงๆ (แยกกันทำงาน)
        if self.collide_point(*pos):
            self.bg_image.color = (0.7, 0.7, 0.7, 1) # มืดลงเฉพาะปุ่มที่โดนชี้
        else:
            self.bg_image.color = (1, 1, 1, 1) # กลับมาสีปกติ

    def unbind_mouse(self):
        """ยกเลิกการตรวจเมาส์เมื่อจบหน้า Splash"""
        Window.unbind(mouse_pos=self._mouse_callback)

    @property
    def font_size(self): return self.label.font_size
    @font_size.setter
    def font_size(self, value): self.label.font_size = value

class SplashScreen(FloatLayout):
    """title screen that displays before gameplay"""
    
    def __init__(self, cover_path, callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.cover_path = cover_path
        self.callback = callback  
        self.allow_skip = True  
        self.image_texture = None
        
        # Draw background cover
        Clock.schedule_once(self.load_cover_image, 0)
        
        # Keyboard binding for backup
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

        # Title Group
        self.title_beyond = Label(
            text="Beyond",
            font_size='80sp',
            font_name='assets/Fonts/edit-undo.brk.ttf',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.7, 'center_y': 0.8}
        )
        
        self.title_the = Label(
            text="the",
            font_size='30sp',
            font_name='assets/Fonts/edit-undo.brk.ttf',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.85, 'center_y': 0.7}
        )

        self.title_sight = Label(
            text="Sight",
            font_size='90sp',
            font_name='assets/Fonts/edit-undo.brk.ttf',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.75, 'center_y': 0.55}
        )

        self.add_widget(self.title_beyond)
        self.add_widget(self.title_the)
        self.add_widget(self.title_sight)

        # Buttons on the right - ปรับตำแหน่งให้เหมาะสมกับขนาดที่เล็กลง
        self.btn_start = MenuButton(
            text="START GAME",
            pos_hint={'center_x': 0.75, 'center_y': 0.34}
        )
        self.btn_start.bind(on_release=lambda x: self.finish_splash())
        
        self.btn_exit = MenuButton(
            text="EXIT GAME",
            pos_hint={'center_x': 0.75, 'center_y': 0.22}
        )
        self.btn_exit.bind(on_release=lambda x: Window.close())

        self.add_widget(self.btn_start)
        self.add_widget(self.btn_exit)

        # Pulsing animation for title
        self.start_animations()

    def start_animations(self):
        anim = Animation(opacity=0.7, duration=1.5) + Animation(opacity=1, duration=1.5)
        anim.repeat = True
        anim.start(self.title_sight)

    def load_cover_image(self, dt=None):
        try:
            if not os.path.exists(self.cover_path):
                self.finish_splash()
                return
            self.image_texture = CoreImage(self.cover_path).texture
            self.update_image_position()
        except:
            self.finish_splash()
    
    def on_size(self, *args):
        """Called when widget size changes"""
        self.update_image_position()
        self._update_font_sizes()

    def _update_font_sizes(self):
        """ปรับขนาดตัวอักษรและขนาดปุ่มตามความสูงของหน้าจอ"""
        scale = self.height / 540.0
        
        # ปรับขนาดตัวอักษรชื่อเกม
        self.title_beyond.font_size = f'{int(80 * scale)}sp'
        self.title_the.font_size = f'{int(30 * scale)}sp'
        self.title_sight.font_size = f'{int(90 * scale)}sp'
        
        # ปรับขนาดปุ่มทั้งสองให้เล็กลงอีกเพื่อความสวยงาม (Base Width 220)
        btn_width = 220 * scale
        btn_font = f'{int(14 * scale)}sp'
        
        for btn in [self.btn_start, self.btn_exit]:
            # คำนวณความสูงจากสัดส่วนจริงของรูปภาพ
            btn_height = btn_width / btn.image_ratio
            btn.size = (btn_width, btn_height)
            btn.font_size = btn_font

    def update_image_position(self, *args):
        if not self.image_texture:
            return
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 1)
            Rectangle(pos=self.pos, size=self.size)
            
            w, h = self.size
            iw, ih = self.image_texture.width, self.image_texture.height
            window_ratio = w / h
            image_ratio = iw / ih
            
            if image_ratio > window_ratio:
                dw, dh = h * image_ratio, h
            else:
                dw, dh = w, w / image_ratio
            
            px, py = self.x + (w - dw) / 2, self.y + (h - dh) / 2
            Color(1, 1, 1, 1)
            Rectangle(texture=self.image_texture, pos=(px, py), size=(dw, dh))
            
            # Darken the right side slightly for text readability
            Color(0, 0, 0, 0.3)
            Rectangle(pos=(self.x + w*0.5, self.y), size=(w*0.5, h))
    
    def finish_splash(self):
        # ยกเลิกการตรวจเมาส์ของปุ่มก่อนเปลี่ยนหน้า
        self.btn_start.unbind_mouse()
        self.btn_exit.unbind_mouse()
        
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard = None
        if self.callback:
            self.callback()
        if self.parent:
            self.parent.remove_widget(self)

    # Keep keyboard as backup
    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'enter':
            self.finish_splash()
    
    def _on_keyboard_closed(self):
        pass
