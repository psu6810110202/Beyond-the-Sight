from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from settings import *
import os

class SaveSlot(FloatLayout):
    """A single save/load slot showing game progress."""
    def __init__(self, slot_id, data=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (900, 100) # เพิ่มความยาวสล็อตตามที่ขอ
        self.slot_id = slot_id
        self.data = data # { 'day': 1, 'heart': 3, 'player_img': '...' }
        self.is_selected = False
        
        with self.canvas.before:
            # พื้นหลังสีดำ
            self.bg_color = Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            # เส้นขอบสีขาว
            self.highlight_color = Color(1, 1, 1, 0) # โปร่งใสเริ่มต้น
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)
            
            # ตกแต่งมุมเล็กๆ ให้เหมือนในรูป
            self.corner_color = Color(1, 1, 1, 0.8)
            self.corner1 = Line(points=[self.x, self.y + self.height - 10, self.x, self.y + self.height, self.x + 10, self.y + self.height], width=1.5)
            self.corner2 = Line(points=[self.x + self.width - 10, self.y, self.x + self.width, self.y, self.x + self.width, self.y + 10], width=1.5)

        # ข้อมูล Day และ Heart
        day_text = f"Day {data['day']}" if data else "Empty Slot"
        heart_text = f"Heart {data['heart']}" if data else ""
        
        self.day_label = Label(
            text=day_text,
            font_size='24sp',
            font_name='assets/Fonts/edit-undo.brk.ttf',
            size_hint=(None, None),
            # ปรับให้ระยะห่างจากขอบซ้ายเป็นเปอร์เซ็นต์ เพื่อไม่ให้ตัวอักษรล้นเมื่อขยายจอ
            pos_hint={'center_x': 0.15, 'center_y': 0.65}, 
            color=(1, 1, 1, 1) if data else (0.4, 0.4, 0.4, 1)
        )
        self.add_widget(self.day_label)
        
        if data:
            self.heart_label = Label(
                text=heart_text,
                font_size='20sp',
                font_name='assets/Fonts/edit-undo.brk.ttf',
                size_hint=(None, None),
                pos_hint={'center_x': 0.15, 'center_y': 0.35},
                color=(1, 1, 1, 1)
            )
            self.add_widget(self.heart_label)
            
            # รูปตัวละครหลัก
            self.player_img = Image(
                source='assets/players/player_idle.png',
                size_hint=(None, None),
                size=(80, 80),
                pos_hint={'right': 0.95, 'center_y': 0.5}, # ย้ายรูปไปทางขวาสุดของสล็อตรองรับความยาวใหม่
                allow_stretch=True,
                keep_ratio=True
            )
            # ปรับ Texture ให้คมชัด (Pixel Art)
            self.player_img.bind(texture=self._set_nearest_filter)
            self.add_widget(self.player_img)

        self.bind(pos=self._update_all, size=self._update_all)

    def _set_nearest_filter(self, instance, texture):
        if texture:
            texture.min_filter = 'nearest'
            texture.mag_filter = 'nearest'

    def _update_all(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)
        self.corner1.points = [self.x, self.y + self.height - 10, self.x, self.y + self.height, self.x + 10, self.y + self.height]
        self.corner2.points = [self.x + self.width - 10, self.y, self.x + self.width, self.y, self.x + self.width, self.y + 10]

    def set_selected(self, selected):
        self.is_selected = selected
        self.highlight_color.a = 1.0 if selected else 0
        if selected:
            self.day_label.color = (1, 1, 1, 1)
        elif not self.data:
            self.day_label.color = (0.4, 0.4, 0.4, 1)

class SaveLoadScreen(FloatLayout):
    """Screen for selecting a save/load slot."""
    def __init__(self, mode="LOAD", callback=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode # "SAVE" หรือ "LOAD"
        self.callback = callback
        self.slots = []
        self.index = 0
        
        # พื้นหลังสีดำสนิท
        with self.canvas.before:
            Color(0, 0, 0, 1) # ปรับเป็นสีดำเข้ม (Alpha = 1)
            self.full_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(size=self._update_bg)

        # หัวข้อ
        self.title = Label(
            text=f"{mode} GAME",
            font_size='40sp',
            font_name='assets/Fonts/edit-undo.brk.ttf',
            pos_hint={'center_x': 0.5, 'top': 0.95},
            size_hint=(None, None)
        )
        self.add_widget(self.title)

        # พื้นที่สำหรับเลื่อน (ScrollView)
        self.scroll_view = ScrollView(
            size_hint=(0.9, 0.7), # ขยายความกว้าง ScrollView
            pos_hint={'center_x': 0.5, 'center_y': 0.45},
            do_scroll_x=False,
            bar_width=5
        )
        self.add_widget(self.scroll_view)

        # คอนเทนเนอร์เก็บสล็อต
        self.slot_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=20, # เพิ่มระยะห่างระหว่างสล็อต
            padding=[20, 20, 20, 20]
        )
        self.slot_container.bind(minimum_height=self.slot_container.setter('height'))
        self.scroll_view.add_widget(self.slot_container)

        # ดึงข้อมูลจากไฟล์เซฟจริง (ถ้ามี)
        import json
        save_data = [None] * 5
        
        if os.path.exists('saves'):
            for i in range(5):
                slot_num = i + 1
                file_path = f'saves/slot_{slot_num}.json'
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            save_data[i] = json.load(f)
                    except Exception as e:
                        print(f"Error loading save slot {slot_num}: {e}")
        
        for i in range(5):
            slot = SaveSlot(
                slot_id=i+1, 
                data=save_data[i]
            )
            # ให้ Slot อยู่กลาง BoxLayout
            slot.pos_hint = {'center_x': 0.5}
            self.slot_container.add_widget(slot)
            self.slots.append(slot)

        self.bind(size=self.on_size)
        self.update_selection()
        
        # Keyboard handling
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

    def on_size(self, *args):
        """จัดการการขยายขนาดตามหน้าจอ (Responsive)"""
        scale = self.height / 540.0 # อ้างอิงจากความสูงมาตรฐาน
        
        # ปรับความหนาของพื้นหลังและหัวข้อ
        self.full_bg.size = self.size
        self.title.font_size = f'{int(40 * scale)}sp'
        
        # ปรับขนาดพื้นที่ ScrollView
        self.scroll_view.size_hint = (0.9, 0.75)
        
        # ปรับระยะห่างระหว่างสล็อต
        self.slot_container.spacing = 20 * scale
        self.slot_container.padding = [20 * scale, 20 * scale, 20 * scale, 20 * scale]
        
        # อัปเดตขนาดของแต่ละสล็อต (ใช้ความกว้างของหน้าจอ ณ ขณะนั้นเป็นเกณฑ์)
        slot_w = self.width * 0.85 
        slot_h = 100 * scale 
        
        for slot in self.slots:
            slot.size = (slot_w, slot_h)
            slot.day_label.font_size = f'{int(24 * scale)}sp'
            if hasattr(slot, 'heart_label'):
                slot.heart_label.font_size = f'{int(20 * scale)}sp'
            if hasattr(slot, 'player_img'):
                slot.player_img.size = (80 * scale, 80 * scale)

    def _update_bg(self, *args):
        self.full_bg.size = self.size
        self.full_bg.pos = self.pos

    def update_selection(self):
        for i, slot in enumerate(self.slots):
            slot.set_selected(i == self.index)
        
        # เลื่อน ScrollView ตามตำแหน่งที่เลือก
        if len(self.slots) > 0:
            # คำนวณตำแหน่งการเลื่อน (0 คือล่างสุด, 1 คือบนสุด)
            target_y = 1.0 - (self.index / (len(self.slots) - 1)) if len(self.slots) > 1 else 1.0
            self.scroll_view.scroll_y = target_y

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key == 'up':
            self.index = (self.index - 1) % 5
            self.update_selection()
        elif key == 'down':
            self.index = (self.index + 1) % 5
            self.update_selection()
        elif key in ('enter', 'space'):
            if self.callback:
                self.callback(self.index + 1)
        elif key == 'escape':
            self.close() # กด Esc เพื่อย้อนกลับ
            return True
        return False

    def close(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard = None
        if self.parent:
            self.parent.remove_widget(self)

    def _on_keyboard_closed(self):
        pass