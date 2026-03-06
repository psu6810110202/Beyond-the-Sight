from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
import os
from settings import GAME_FONT, WINDOW_HEIGHT

class IntroScreen(FloatLayout):
    """
    หน้าจอจอดำพร้อมตัวหนังสือ Day 1 
    จะแสดงหลังจากกด New Game ก่อนเริ่มเข้าเกม
    """
    def __init__(self, callback, day=1, duration=3.0, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.day = day
        self.duration = duration
        
        # วาดพื้นหลังสีดำ
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
        # สร้าง Label คำว่า Day X
        self.label = Label(
            text=f"Day {self.day}",
            font_name=GAME_FONT,
            font_size=self._get_scaled_font_size(),
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.label)
        
        # เสียงประตูเปิดตอนขึ้นวันใหม่
        door_sound_path = 'assets/sound/door/Door_squeeky_2.wav'
        if os.path.exists(door_sound_path):
            sound = SoundLoader.load(door_sound_path)
            if sound:
                sound.volume = 0.6
                sound.play()

        # สำคัญ: ต้องผูกเหตุการณ์ Resize เพื่อให้อัปเดต UI ตามขนาดจอ
        self.bind(pos=self._update_ui, size=self._update_ui)
        
        # ตั้งเวลาให้ข้ามหน้าจอนี้อัตโนมัติ
        Clock.schedule_once(self.finish, self.duration)
        
    def _get_scaled_font_size(self):
        """Scale font size (Single point of control)"""
        # ปรับพื้นฐานจาก 70 เป็น 120 ให้ตัวใหญ่ขึ้นแบบพรีเมียม
        return 120 * (self.height / WINDOW_HEIGHT if self.height > 0 else 1.0)

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
