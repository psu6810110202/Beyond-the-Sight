from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
import os
from data.settings import GAME_FONT, WINDOW_HEIGHT

class IntroScreen(FloatLayout):
    """
    หน้าจอจอดำพร้อมตัวหนังสือ Day 1 
    จะแสดงหลังจากกด New Game ก่อนเริ่มเข้าเกม
    """
    def __init__(self, callback, day=1, duration=3.0, custom_text=None, play_sound=True, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.day = day
        self.duration = duration
        self.custom_text = custom_text
        self.play_sound = play_sound
        
        # วาดพื้นหลังสีดำ
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
        # สร้าง Label คำว่า Day X หรือ custom_text
        display_text = self.custom_text if self.custom_text else f"Day {self.day}"
        self.label = Label(
            text=display_text,
            font_name=GAME_FONT,
            font_size=self._get_scaled_font_size(),
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            halign='center',
            valign='middle',
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)
        
        # เสียงประตูเปิดตอนขึ้นวันใหม่
        door_path = 'assets/sound/door/Door_squeeky_2.wav'
        close_path = 'assets/sound/door/Door_close.wav'
        
        if self.play_sound and os.path.exists(door_path):
            s_open = SoundLoader.load(door_path)
            if s_open:
                s_open.volume = 0.6
                s_open.play()
                
                # เสียงปิดประตูตามมา (ถ้ามีไฟล์)
                if os.path.exists(close_path):
                    s_close = SoundLoader.load(close_path)
                    if s_close:
                        s_close.volume = 0.6
                        Clock.schedule_once(lambda dt: s_close.play(), 1.2)

        # สำคัญ: ต้องผูกเหตุการณ์ Resize เพื่อให้อัปเดต UI ตามขนาดจอ
        self.bind(pos=self._update_ui, size=self._update_ui)
        
        # ตั้งเวลาให้ข้ามหน้าจอนี้อัตโนมัติ
        Clock.schedule_once(self.finish, self.duration)
        
    def _get_scaled_font_size(self):
        """Scale font size (Single point of control)"""
        # ปรับลงเหลือ 50 เพื่อให้ไม่เบียดจอและดูมินิมอลขึ้น (Further downsized to 50)
        return 50 * (self.height / WINDOW_HEIGHT if self.height > 0 else 1.0)

    def _update_ui(self, *args):
        # อัปเดตพื้นหลัง
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        # อัปเดตขนาดตัวอักษรเมื่อจอขยาย
        self.label.font_size = self._get_scaled_font_size()
        
    def finish(self, dt=None):
        if self.callback:
            self.callback()
        if self.parent:
            self.parent.remove_widget(self)
