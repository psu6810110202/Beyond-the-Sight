from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from settings import GAME_FONT

class IntroScreen(FloatLayout):
    """
    หน้าจอจอดำพร้อมตัวหนังสือ Day 1 
    จะแสดงหลังจากกด New Game ก่อนเริ่มเข้าเกม
    """
    def __init__(self, callback, duration=3.0, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.duration = duration
        
        # วาดพื้นหลังสีดำ
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
        # สร้าง Label คำว่า Day 1
        self.label = Label(
            text="Day 1",
            font_name=GAME_FONT,
            font_size='70sp',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.label)
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # ตั้งเวลาให้ข้ามหน้าจอนี้อัตโนมัติ
        Clock.schedule_once(self.finish, self.duration)
        
    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
    def finish(self, dt=None):
        if self.callback:
            self.callback()
        if self.parent:
            self.parent.remove_widget(self)
