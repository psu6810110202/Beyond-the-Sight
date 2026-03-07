from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from data.settings import *
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
            # แก้ไข: ขยับแกน x ออกไปทางขวาให้ห่างจากคำว่า Day (เปลี่ยน base x จาก 0.15 เป็น 0.25)
            heart.pos_hint = {'x': 0.2 + (i * 0.055), 'center_y': 0.5}

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
    def __init__(self, mode="LOAD", callback=None, on_close_cb=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.callback = callback
        self.on_close_cb = on_close_cb
        self.slots = []
        self.index = 0
        
        # โหลดเสียงคลิกสำหรับเมนูเซฟ
        self.click_sound = SoundLoader.load('assets/sound/click.wav')
        if self.click_sound:
            self.click_sound.volume = 0.5
        
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
        
        # ค้นหา Slot ที่มีข้อมูลเป็นค่าเริ่มต้น (สำหรับโหมด LOAD)
        valid_indices = [i for i, slot in enumerate(self.slots) if self.mode == "SAVE" or slot.data is not None]
        if valid_indices:
            self.index = valid_indices[0]
            
        self.update_selection()
        
        # Keyboard handling - ขอสิทธิ์ Keyboard ทันทีและทำให้เป็น Focus หลัก
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self.focus = True # บังคับ focus ให้แม่นยำขึ้น

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
        
        # ค้นหา Slot ที่มีข้อมูล (สำหรับโหมด LOAD)
        valid_indices = [i for i, slot in enumerate(self.slots) if self.mode == "SAVE" or slot.data is not None]
        
        if not valid_indices:
            if key == 'escape':
                self.close()
            return True

        # ปรับ index ให้เป็นตัวที่ใช้ได้ถ้าปัจจุบันหลุดขอบ (เช่น ลบเซฟทิ้ง)
        if self.index not in valid_indices:
            self.index = valid_indices[0]

        # หากมี Popup แจ้งยืนยันอยู่ บล็อกการเลื่อน Slot ข้างหลัง
        is_popup_open = hasattr(self, 'confirm_popup') and self.confirm_popup
        if is_popup_open:
            if key == 'up' or key == 'down':
                return True # กิน Event ทิ้ง ไม่ให้เลื่อน Slot

        if key == 'up':
            if is_popup_open:
                # ถ้ามีป๊อปอัพ ให้ UP/DOWN เลื่อน YES/NO ได้ด้วยเพื่อความสะดวก
                self.confirm_index = 1 - self.confirm_index
                self.update_popup_selection()
                if self.click_sound: self.click_sound.play()
                return True

            # หาค่าที่น้อยกว่าปัจจุบันในลิสต์ valid
            prev_indices = [i for i in valid_indices if i < self.index]
            if prev_indices:
                self.index = prev_indices[-1]
            else:
                self.index = valid_indices[-1] # วนไปท้ายสุด
            
            # เล่นเสียงคลิกเมื่อเลื่อน
            if self.click_sound:
                self.click_sound.play()
                
            self.update_selection()
        elif key == 'down':
            if is_popup_open:
                self.confirm_index = 1 - self.confirm_index
                self.update_popup_selection()
                if self.click_sound: self.click_sound.play()
                return True

            # หาค่าที่มากกว่าปัจจุบันในลิสต์ valid
            next_indices = [i for i in valid_indices if i > self.index]
            if next_indices:
                self.index = next_indices[0]
            else:
                self.index = valid_indices[0] # วนไปเริ่มใหม่
            
            # เล่นเสียงคลิกเมื่อเลื่อน
            if self.click_sound:
                self.click_sound.play()
                
            self.update_selection()
        elif key in ('enter', 'space'):
            if hasattr(self, 'confirm_popup') and self.confirm_popup:
                # ถ้ากำลังโชว์ popup อยู่
                if self.confirm_index == 0: # YES
                    if self.click_sound:
                        self.click_sound.play()
                    self.close_popup()
                    if self.callback:
                        self.callback(self.index + 1, self)
                else: # NO
                    if self.click_sound:
                        self.click_sound.play()
                    self.close_popup()
                return True
                
            if self.mode == "LOAD" and self.slots[self.index].data is None:
                return True # กดไม่ได้
            
            # เช็คว่าเป็นการเซฟทับหรือไม่
            if self.mode == "SAVE" and self.slots[self.index].data is not None:
                if self.click_sound:
                    self.click_sound.play()
                self.show_overwrite_confirmation()
            else:
                if self.click_sound:
                    self.click_sound.play()
                if self.callback:
                    self.callback(self.index + 1, self)
        elif key == 'escape':
            if hasattr(self, 'confirm_popup') and self.confirm_popup:
                self.close_popup()
                return True
            
            # บล็อกไม่ให้กด ESC ออกในโหมด SAVE (ต้องเซฟเท่านั้น)
            if self.mode == "SAVE":
                return True
                
            # กด ESC ออกจากหน้าจอโหลดได้ปกติ
            self.close()
            return True
        elif key == 'left' or key == 'right':
            if hasattr(self, 'confirm_popup') and self.confirm_popup:
                # สลับ YES / NO
                self.confirm_index = 1 - self.confirm_index
                if self.click_sound:
                    self.click_sound.play()
                self.update_popup_selection()
                return True
        return False

    def show_overwrite_confirmation(self):
        """แสดงป๊อปอัปยืนยันการเซฟทับกลางจอ"""
        self.confirm_index = 1 # เริ่มที่ NO เผื่อกดพลาด
        
        self.confirm_popup = FloatLayout(size_hint=(1, 1))
        # บล็อก Touch ไม่ให้ทะลุลงไปข้างล่าง
        self.confirm_popup.bind(on_touch_down=lambda inst, touch: True)
        self.confirm_popup.bind(on_touch_move=lambda inst, touch: True)
        self.confirm_popup.bind(on_touch_up=lambda inst, touch: True)
        
        # หยุดการทำงานของ ScrollView ทั่วไป
        self.scroll_view.do_scroll_y = False
        self.scroll_view.do_scroll_x = False

        # พื้นหลังดำจางๆ
        with self.confirm_popup.canvas.before:
            Color(0, 0, 0, 0.85)
            self.popup_bg = Rectangle(pos=self.pos, size=self.size)
            
            # กล่องป๊อปอัป
            Color(0.15, 0.15, 0.15, 1)
            self.popup_box = Rectangle()
            Color(1, 1, 1, 1) # ขอบขาว
            self.popup_line = Line(width=1.5)
            
        # สร้าง Widget ข้อความและปุ่มก่อน
        self.lbl_title = Label(text="[color=ff3333]OVERWRITE[/color] EXISTING SAVE DATA?",
            markup=True,
            font_name='assets/Fonts/edit-undo.brk.ttf',
            bold=True,
            halign='center',
            pos_hint={'center_x': 0.5, 'center_y': 0.55})
        
        self.lbl_yes = Label(text="YES", font_name='assets/Fonts/edit-undo.brk.ttf', 
                             color=(0.5, 0.5, 0.5, 1), pos_hint={'center_x': 0.35, 'center_y': 0.43})
        self.lbl_no = Label(text="NO", font_name='assets/Fonts/edit-undo.brk.ttf', 
                            color=(1, 1, 1, 1), pos_hint={'center_x': 0.65, 'center_y': 0.43})

        def update_popup_bg(instance, value):
            self.popup_bg.pos = instance.pos
            self.popup_bg.size = instance.size
            
            # คำนวณขนาดกล่องแบบ Responsive: กว้างยาวคลุมไปกับขนาดหลอด Save
            scale = self.height / 540.0
            box_w = min(800 * scale, self.width * 0.85)
            box_h = 160 * scale
            
            bx = self.center_x - box_w/2
            by = self.center_y - box_h/2
            
            self.popup_box.pos = (bx, by)
            self.popup_box.size = (box_w, box_h)
            self.popup_line.rectangle = (bx, by, box_w, box_h)
            
            # อัปเดตขนาดฟอนต์ให้ล้อตามกล่อง
            self.lbl_title.font_size = f'{int(26 * scale)}sp'
            self.lbl_yes.font_size = f'{int(22 * scale)}sp'
            self.lbl_no.font_size = f'{int(22 * scale)}sp'
                
        self.confirm_popup.bind(pos=update_popup_bg, size=update_popup_bg)
        update_popup_bg(self.confirm_popup, None)
        
        self.confirm_popup.add_widget(self.lbl_title)
        self.confirm_popup.add_widget(self.lbl_yes)
        self.confirm_popup.add_widget(self.lbl_no)
        self.add_widget(self.confirm_popup)
        self.update_popup_selection()
        
    def update_popup_selection(self):
        if self.confirm_index == 0:
            self.lbl_yes.color = (1, 1, 1, 1)
            self.lbl_no.color = (0.5, 0.5, 0.5, 1)
        else:
            self.lbl_yes.color = (0.5, 0.5, 0.5, 1)
            self.lbl_no.color = (1, 1, 1, 1)
            
    def close_popup(self):
        if self.confirm_popup and self.confirm_popup.parent:
            self.confirm_popup.parent.remove_widget(self.confirm_popup)
        self.confirm_popup = None
        # กลับมาเลื่อน Scroll ได้ปกติ
        self.scroll_view.do_scroll_y = True

    def close(self):
        if hasattr(self, 'confirm_popup') and self.confirm_popup:
            self.close_popup()
        if getattr(self, '_keyboard', None):
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard.release()
            self._keyboard = None
        
        parent = self.parent
        if parent:
            # คืนสถานะเดินได้ให้เกมถ้ามี
            if hasattr(parent, 'is_dialogue_active'):
                parent.is_dialogue_active = False
            elif hasattr(self.callback, '__self__') and hasattr(self.callback.__self__, 'game'):
                self.callback.__self__.game.is_dialogue_active = False
            
            # ลบตัวเองออก
            parent.remove_widget(self)
            
            if getattr(self, 'on_close_cb', None):
                self.on_close_cb()
            else:
                # คืน Focus ให้หน้าจอหลัก (Title หรือ Game)
                if hasattr(parent, 'request_keyboard_back'):
                    parent.request_keyboard_back()
                elif hasattr(self.callback, '__self__') and hasattr(self.callback.__self__, 'request_keyboard_back'):
                    self.callback.__self__.request_keyboard_back()

    def _on_keyboard_closed(self):
        pass