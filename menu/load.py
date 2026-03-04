from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
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
        self.size = (900, 100)
        self.slot_id = slot_id
        self.data = data
        self.is_selected = False
        self.heart_icons = []
        
        with self.canvas.before:
            # พื้นหลังสีดำ
            self.bg_color = Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            # ไฮไลท์สีขาวจางๆ เมื่อเลือก
            self.sel_color = Color(1, 1, 1, 0)
            self.sel_rect = Rectangle(pos=self.pos, size=self.size)
            # เส้นขอบสีขาว
            self.highlight_color = Color(1, 1, 1, 0)
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)
            # ตกแต่งมุม
            self.corner_color = Color(1, 1, 1, 0.8)
            self.corner1 = Line(points=[self.x, self.y + self.height - 10, self.x, self.y + self.height, self.x + 10, self.y + self.height], width=1.5)
            self.corner2 = Line(points=[self.x + self.width - 10, self.y, self.x + self.width, self.y, self.x + self.width, self.y + 10], width=1.5)

        # 1. ข้อมูลวันที่
        day_text = f"Day {data['day']}" if data else "Empty Slot"
        self.day_label = Label(
            text=day_text,
            font_name='assets/Fonts/edit-undo.brk.ttf',
            size_hint=(0.3, 1),
            halign='left',
            valign='middle',
            color=(1, 1, 1, 1) if data else (0.4, 0.4, 0.4, 1)
        )
        self.day_label.bind(size=self._update_text_size)
        self.add_widget(self.day_label)
        
        if data:
            # 2. ข้อมูลหัวใจ
            health = data.get('heart', 3)
            for i in range(3):
                tex_path = 'assets/Heart/หัวใจ-1.png' if i < health else 'assets/Heart/หัวใจ-3.png'
                heart = Image(
                    source=tex_path, 
                    size_hint=(None, None),
                    fit_mode='contain'
                )
                # บังคับความคมชัด (Pixel Art) ทันที
                if heart.texture:
                    self._set_nearest_filter(heart, heart.texture)
                heart.bind(texture=self._set_nearest_filter)
                self.add_widget(heart)
                self.heart_icons.append(heart)
            
            # 3. รูปตัวละคร
            try:
                # โหลด texture หลัก
                full_texture = CoreImage(PLAYER_IDLE_IMG).texture
                # บังคับความคมชัดตั้งแต่ต้นฉบับ
                full_texture.min_filter = 'nearest'
                full_texture.mag_filter = 'nearest'
                
                # ท่าหันหน้าตรง (Down) - ปรับเป็นครึ่งตัว (Portrait)
                # ดึงแค่ส่วนบนของตัวละคร (128x64px) จากพิกัดเดิม
                idle_half_tex = full_texture.get_region(0, 395 + 40, 128, 88) 
                self.player_img = Image(
                    texture=idle_half_tex, 
                    size_hint=(None, None),
                    fit_mode='contain'
                )
                # บังคับความคมชัดซ้ำเพื่อให้มั่นใจ
                if self.player_img.texture:
                    self._set_nearest_filter(self.player_img, self.player_img.texture)
                self.player_img.bind(texture=self._set_nearest_filter)
                self.add_widget(self.player_img)
            except Exception as e:
                print(f"Error slicing player texture: {e}")

            # 4. ข้อมูลเวลาเล่น (Play Time)
            seconds = data.get('play_time', 0)
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            time_text = f"{h:02d}:{m:02d}:{s:02d}"
            
            self.time_label = Label(
                text=time_text,
                font_name='assets/Fonts/edit-undo.brk.ttf',
                size_hint=(None, None),
                color=(1, 1, 1, 1) # เปลี่ยนเป็นสีขาวตามคำขอ
            )
            self.add_widget(self.time_label)

        self.update_layout(1.0)
        self.bind(pos=self._update_graphics, size=self._update_graphics)

    def update_layout(self, scale=1.0):
        """จุดเดียวที่จัดการขนาดและตำแหน่งของทุกอย่างในสล็อต"""
        # วันที่
        self.day_label.font_size = f'{int(28 * scale)}sp'
        self.day_label.pos_hint = {'x': 0.04, 'center_y': 0.5}

        # หัวใจ
        for i, heart in enumerate(self.heart_icons):
            heart.size = (50 * scale, 50 * scale)
            # แก้ไข: เอา * scale ออกเพื่อให้ระยะห่างคงที่เสมอ (ไม่ยืดตามจอ)
            heart.pos_hint = {'x': 0.15 + (i * 0.055), 'center_y': 0.5}

        # ตัวละคร (ปรับตำแหน่งให้โผล่พ้นขอบล่างขึ้นมา)
        if hasattr(self, 'player_img'):
            self.player_img.size = (110 * scale, 110 * scale)
            self.player_img.pos_hint = {'center_x': 0.90, 'center_y': 0.75}
            
        # เวลาเล่น
        if hasattr(self, 'time_label'):
            self.time_label.font_size = f'{int(18 * scale)}sp'
            self.time_label.size = (150 * scale, 30 * scale)
            self.time_label.pos_hint = {'center_x': 0.90, 'center_y': 0.2}

    def _update_text_size(self, instance, value):
        instance.text_size = instance.size

    def _set_nearest_filter(self, instance, texture):
        if texture:
            texture.min_filter = 'nearest'
            texture.mag_filter = 'nearest'

    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.sel_rect.pos = self.pos
        self.sel_rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)
        self.corner1.points = [self.x, self.y + self.height - 10, self.x, self.y + self.height, self.x + 10, self.y + self.height]
        self.corner2.points = [self.x + self.width - 10, self.y, self.x + self.width, self.y, self.x + self.width, self.y + 10]

    def set_selected(self, selected):
        self.is_selected = selected
        self.highlight_color.a = 1.0 if selected else 0
        self.sel_color.a = 0.15 if selected else 0 # สีขาวจางๆ 15%
        if selected:
            self.day_label.color = (1, 1, 1, 1)
        elif not self.data:
            self.day_label.color = (0.4, 0.4, 0.4, 1)

class SaveLoadScreen(FloatLayout):
    """Screen for selecting a save/load slot."""
    def __init__(self, mode="LOAD", callback=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.callback = callback
        self.slots = []
        self.index = 0
        
        with self.canvas.before:
            Color(0, 0, 0, 1) # พื้นหลังดำสนิท
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

        # ScrollView
        self.scroll_view = ScrollView(
            size_hint=(0.9, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.45},
            do_scroll_x=False,
            bar_width=5
        )
        self.add_widget(self.scroll_view)

        # Container
        self.slot_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=20,
            padding=[20, 20, 20, 20]
        )
        self.slot_container.bind(minimum_height=self.slot_container.setter('height'))
        self.scroll_view.add_widget(self.slot_container)

        # โหลดข้อมูลเซฟ
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
        
        # สร้างสล็อตจากข้อมูล (เรียง 5 ช่อง)
        for i in range(5):
            slot = SaveSlot(slot_id=i+1, data=save_data[i])
            slot.pos_hint = {'center_x': 0.5}
            self.slot_container.add_widget(slot)
            self.slots.append(slot)

        self.bind(size=self.on_size)
        self.update_selection()
        
        # Keyboard handling
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

    def on_size(self, *args):
        """จัดการ Resize หน้าจอ"""
        scale = self.height / 540.0
        self.full_bg.size = self.size
        self.full_bg.pos = self.pos
        self.title.font_size = f'{int(40 * scale)}sp'
        self.scroll_view.size_hint = (0.9, 0.75)
        self.slot_container.spacing = 20 * scale
        self.slot_container.padding = [20 * scale, 20 * scale, 20 * scale, 20 * scale]
        
        slot_w = self.width * 0.85 
        slot_h = 100 * scale 
        for slot in self.slots:
            slot.size = (slot_w, slot_h)
            slot.update_layout(scale)

    def _update_bg(self, *args):
        self.full_bg.size = self.size
        self.full_bg.pos = self.pos

    def update_selection(self):
        for i, slot in enumerate(self.slots):
            slot.set_selected(i == self.index)
        if len(self.slots) > 0:
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
                self.callback(self.index + 1, self)
        elif key == 'escape':
            if self.mode == "LOAD":
                self.close()
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