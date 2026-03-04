from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from settings import GAME_FONT
from menu.screen import GameMenu

class PauseMenu(FloatLayout):
    """
    หน้าเมนูพักเกม (Pause Menu)
    แก้ไขให้ใช้หลักการเดียวกันกับเมนูในหน้าแรก (GameMenu)
    เพื่อความพรีเมียมและความสม่ำเสมอของดีไซน์
    """
    def __init__(self, resume_cb, load_cb, menu_cb, exit_cb, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.callbacks = {
            "Resume Game": resume_cb,
            "Load Game": load_cb,
            "Return to Main Menu": menu_cb,
            "Exit Game": exit_cb
        }
        
        # 1. พื้นหลังดำจางๆ
        with self.canvas.before:
            Color(0, 0, 0, 0.4)
            self.overlay_rect = Rectangle(pos=self.pos, size=self.size)
            
        # 2. กล่องเมนูสีดำ
        self.menu_box = FloatLayout(
            size_hint=(None, None),
            size=(500, 430),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        with self.menu_box.canvas.before:
            Color(0, 0, 0, 1)
            self.box_rect = Rectangle(pos=self.menu_box.pos, size=self.menu_box.size)
            Color(1, 1, 1, 1)
            self.box_border = Line(rectangle=(self.menu_box.x, self.menu_box.y, self.menu_box.width, self.menu_box.height), width=2)
            
        self.add_widget(self.menu_box)
        
        # หัวข้อ PAUSE GAME 
        self.title = Label(
            text="PAUSE GAME",
            font_name=GAME_FONT,
            font_size='50sp', # ลดขนาดลงเพื่อให้สมดุลกับกล่องใหม่
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=100,
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        self.menu_box.add_widget(self.title)
        
        # รายการปุ่ม
        items = ["Resume Game", "Load Game", "Return to Main Menu", "Exit Game"]
        self.inner_menu = GameMenu(
            items=items,
            callback=self.on_menu_select
        )
        
        # ปรับจูนขนาดปุ่มและตัวอักษรเพื่อให้แสดงบรรทัดเดียวทั้งหมด
        for btn in self.inner_menu.buttons:
            btn.label.font_size = '28sp' # ปรับขนาดที่พอดีเพื่อให้ Return to Main Menu อยู่บรรทัดเดียว
            
        # บังคับขนาดของปุ่ม GameMenu ให้กว้างขึ้นตามกล่อง
        self.inner_menu.size = (450, 250)
        self.inner_menu.pos_hint = {'center_x': 0.5, 'center_y': 0.48}
        
        # เคลียร์กราฟิกซ้อนทับ (ขอบและพื้นหลัง) ของ GameMenu เดิม เพราะเราวาดเองใน menu_box แล้ว
        self.inner_menu.canvas.before.clear()
        self.menu_box.add_widget(self.inner_menu)
        
        # ผูกความสัมพันธ์การ Resize
        self.bind(pos=self._update_all, size=self._update_all)
        self.menu_box.bind(pos=self._update_all, size=self._update_all)
        
        # ขอ Keyboad เฉพาะสำหรับเมนูนี้
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

    def on_menu_select(self, choice):
        if choice in self.callbacks:
            self.callbacks[choice]()

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key == 'up':
            self.inner_menu.move_selection('up')
        elif key == 'down':
            self.inner_menu.move_selection('down')
        elif key in ('enter', 'space'):
            self.inner_menu.select_current()
        elif key == 'escape':
            # Resume เกมทันที
            if "Resume Game" in self.callbacks:
                self.callbacks["Resume Game"]()
        return True

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard = None

    def _update_all(self, *args):
        # คำนวณ Scale ตามความสูงหน้าจอ (อิงความสูงมาตรฐาน 540)
        scale = max(0.5, self.height / 540.0)
        
        # อัปเดตพื้นหลัง
        self.overlay_rect.pos = self.pos
        self.overlay_rect.size = self.size
        
        # อัปเดตขนาดกล่องเมนู
        self.menu_box.size = (500 * scale, 430 * scale)
        self.box_rect.pos = self.menu_box.pos
        self.box_rect.size = self.menu_box.size
        self.box_border.rectangle = (self.menu_box.x, self.menu_box.y, self.menu_box.width, self.menu_box.height)
        
        # อัปเดตขนาดตัวอักษรหัวข้อ
        self.title.font_size = f'{int(50 * scale)}sp'
        self.title.height = 100 * scale
        
        # อัปเดตขนาดปุ่มและตัวอักษรใน GameMenu
        self.inner_menu.size = (450 * scale, 250 * scale)
        for btn in self.inner_menu.buttons:
            btn.label.font_size = f'{int(28 * scale)}sp'

    def close(self):
        if self._keyboard:
            self._keyboard.release()
            self._keyboard = None
        if self.parent:
            self.parent.remove_widget(self)
