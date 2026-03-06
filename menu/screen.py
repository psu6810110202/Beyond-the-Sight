from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.animation import Animation
import os

from menu.load import SaveLoadScreen # นำเข้าหน้าจอเซฟ
from settings import GAME_FONT

class MenuButton(ButtonBehavior, FloatLayout):
    """Custom button used within GameMenu."""
    def __init__(self, text="", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (200, 50)
        self.is_selected = False
        
        with self.canvas.before:
            # พื้นหลังสีดำจางๆ หรือโปร่งใสตามสไตล์ในรูป
            self.bg_color = Color(0, 0, 0, 0) 
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            # เส้นขอบที่จะแสดงเมื่อเลือก (Highlight) - เปลี่ยนเป็นสีขาว
            self.highlight_color = Color(1, 1, 1, 0) # สีขาว โปร่งใสเริ่มต้น
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)
            
        self.label = Label(
            text=text,
            font_name=GAME_FONT,
            color=(0.7, 0.7, 0.7, 1), # สีเทาเริ่มต้น
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center', # เปลี่ยนเป็นอยู่ตรงกลาง
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)
        
        self.bind(pos=self._update_graphics, size=self._update_graphics)

    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        # ปรับขนาดเส้นขอบให้เล็กลงนิดนึงเพื่อให้ดูเหมือนกรอบล้อมรอบตัวอักษร
        self.border.rectangle = (self.x, self.y, self.width, self.height)

    def set_selected(self, selected, is_disabled=False):
        self.is_selected = selected
        if is_disabled:
            self.label.color = (0.3, 0.3, 0.3, 1) # สีเทาเข้มเมื่อปิดใช้งาน
            self.highlight_color.a = 0
            return

        if selected:
            self.highlight_color.a = 1.0 
            self.label.color = (1, 1, 1, 1) # สีขาว
        else:
            self.highlight_color.a = 0 
            self.label.color = (1, 1, 1, 1) # สีขาวปกติ
            
class GameMenu(FloatLayout):
    """Container for menu buttons with box styling and keyboard support."""
    def __init__(self, items, callback, disabled_indices=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.callback = callback
        self.disabled_indices = disabled_indices or []
        
        # จัดการการเลือก
        self.items = items
        self.buttons = []
        self.index = 0
        
        # โหลดเสียงคลิกสำหรับเมนู
        self.click_sound = SoundLoader.load('assets/sound/click.wav')
        if self.click_sound:
            self.click_sound.volume = 0.5
        
        with self.canvas.before:
            # กรอบเมนูสีดำขอบขาว
            Color(0, 0, 0, 0.9) # พื้นหลังดำเกือบสนิท
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 1) # ขอบสีขาว
            self.border = Line(rectangle=(self.x, self.y, self.width, self.height), width=2)
            
            # ตกแต่งมุม
            # มุมซ้ายบน
            Line(points=[self.x, self.y + self.height - 15, self.x, self.y + self.height, self.x + 15, self.y + self.height], width=2)
            # มุมขวาล่าง
            Line(points=[self.x + self.width - 15, self.y, self.x + self.width, self.y, self.x + self.width, self.y + 15], width=2)

        # สร้างปุ่ม
        for text in items:
            btn = MenuButton(text=text)
            self.add_widget(btn)
            self.buttons.append(btn)
        
        self.layout_buttons() # เรียกใช้ฟังก์ชันจัดเลย์เอาต์ครั้งแรก
        self.update_selection()
        self.bind(pos=self._update_all, size=self._update_all)

    def layout_buttons(self):
        """จัดการตำแหน่งและขนาดของปุ่มทั้งหมดให้สมดุลและกึ่งกลาง (จุดปรับแต่งจุดเดียว)"""
        btn_h = self.height * 0.25 # ปรับความสูงปุ่ม
        spacing = self.height * 0.28 # ระยะห่างระหว่างปุ่ม
        start_y = (self.height / 2) + spacing - (btn_h / 2)
        
        for i, btn in enumerate(self.buttons):
            btn.size = (self.width - 40, btn_h)
            btn.pos = (self.x + 20, self.y + start_y - (i * spacing))

    def _update_all(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rectangle = (self.x, self.y, self.width, self.height)
        self.layout_buttons() # อัปเดตตำแหน่งปุ่มทุกครั้งที่มีการ Resize

    def move_selection(self, direction):
        old_index = self.index
        count = len(self.items)
        
        # วนลูปหาปุ่มที่ไม่ได้ disabled
        for _ in range(count):
            if direction == 'up':
                self.index = (self.index - 1) % count
            else:
                self.index = (self.index + 1) % count
            
            if self.index not in self.disabled_indices:
                break
        else:
            self.index = old_index # ป้องกันค้างถ้าโดนปิดหมด
        
        # เล่นเสียงคลิกเมื่อเลื่อน
        if self.click_sound and old_index != self.index:
            self.click_sound.play()
            
        self.update_selection()

    def update_selection(self):
        for i, btn in enumerate(self.buttons):
            btn.set_selected(i == self.index, is_disabled=(i in self.disabled_indices))

    def select_current(self):
        if self.index in self.disabled_indices:
            return # กดไม่ได้
        
        # เล่นเสียงคลิกเมื่อกดตกลง
        if self.click_sound:
            self.click_sound.play()
            
        if self.callback:
            self.callback(self.items[self.index])

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
        
        # Keyboard binding - สำคัญมากสำหรับการเลื่อนเมนู
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

        # Title Group
        self.title_beyond = Label(
            text="Beyond",
            font_size='80sp',
            font_name=GAME_FONT,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.7, 'center_y': 0.8}
        )
        
        self.title_the = Label(
            text="the",
            font_size='30sp',
            font_name=GAME_FONT,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.85, 'center_y': 0.7}
        )


        self.title_sight = Label(
            text="Sight",
            font_size='90sp',
            font_name=GAME_FONT,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            pos_hint={'center_x': 0.75, 'center_y': 0.55}
        )

        self.add_widget(self.title_beyond)
        self.add_widget(self.title_the)
        self.add_widget(self.title_sight)
        
        # ตรวจสอบว่ามีไฟล์เซฟหรือไม่
        has_saves = False
        if os.path.exists('saves'):
            for i in range(1, 6):
                if os.path.exists(f'saves/slot_{i}.json'):
                    has_saves = True
                    break
        
        # รายการเมนูทั้งหมด
        menu_items = ["New Game", "Load Game", "Exit"]
        disabled_list = []
        if not has_saves:
            disabled_list.append(1) # Index 1 (Load Game) ปิดใช้งาน

        # เมนูแบบใหม่สไตล์ Visual Novel / RPG
        self.menu = GameMenu(
            items=menu_items,
            callback=self.on_menu_select,
            disabled_indices=disabled_list,
            # ขยับลงมาข้างล่างเพื่อให้ห่างจากชื่อเรื่อง
            pos_hint={'center_x': 0.75, 'center_y': 0.28}
        )
        self.add_widget(self.menu)

        # Pulsing animation for title
        self.start_animations()

    def on_menu_select(self, choice):
        if choice == "New Game":
            self.finish_splash()
        elif choice == "Load Game":
            # แสดงหน้าจอโหลดเซฟ 5 สล็อต
            load_screen = SaveLoadScreen(
                mode="LOAD", 
                callback=self.on_slot_selected
            )
            self.add_widget(load_screen)
        elif choice == "Exit":
            Window.close()

    def on_slot_selected(self, slot_id, load_screen=None):
        import json
        save_path = f'saves/slot_{slot_id}.json'
        data = None
        
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f:
                    data = json.load(f)
                print(f"Loaded Slot {slot_id}: {data}")
            except Exception as e:
                print(f"Error loading save: {e}")
        
        if load_screen:
            load_screen.close()
            
        self.finish_splash(initial_data=data)

    def finish_splash(self, initial_data=None):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard = None
        if self.callback:
            # ส่งข้อมูลที่โหลดมากลับไปที่ show_game ใน MyApp
            self.callback(initial_data=initial_data)
        if self.parent:
            self.parent.remove_widget(self)

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
        """ปรับขนาดตัวอักษรชื่อเกมตามความสูงของหน้าจอ"""
        scale = self.height / 540.0
        
        # ปรับความสูงของฟอนต์ชื่อเกม
        self.title_beyond.font_size = f'{int(80 * scale)}sp'
        self.title_the.font_size = f'{int(30 * scale)}sp'
        self.title_sight.font_size = f'{int(90 * scale)}sp'
        
        # ปรับขนาดกล่องเมนูให้ขยายตามหน้าจอ (สัดส่วน 240x130 สำหรับ 3 ปุ่ม)
        self.menu.size = (240 * scale, 130 * scale)
        for btn in self.menu.buttons:
            btn.label.font_size = f'{int(22 * scale)}sp'

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
    

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key == 'up':
            self.menu.move_selection('up')
        elif key == 'down':
            self.menu.move_selection('down')
        elif key in ('enter', 'space'):
            self.menu.select_current()
    
    def _on_keyboard_closed(self):
        pass
