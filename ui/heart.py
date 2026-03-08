from kivy.graphics import Rectangle, Color, RoundedRectangle
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from data.settings import WINDOW_HEIGHT

class HeartUI:
    def __init__(self, canvas, initial_health=3):
        self.canvas = canvas
        self.heart_size = 48
        self.pad = 5
        self.start_x = 10
        self.max_health = 3
        self.current_health = initial_health
        
        # โหลด Texture ของหัวใจ
        self.tex_heart_full = CoreImage('assets/Heart/หัวใจ-1.png').texture
        self.tex_heart_full.mag_filter = 'nearest'
        self.tex_heart_full.min_filter = 'nearest'

        self.tex_heart_break = CoreImage('assets/Heart/หัวใจ-2.png').texture
        self.tex_heart_break.mag_filter = 'nearest'
        self.tex_heart_break.min_filter = 'nearest'

        self.tex_heart_empty = CoreImage('assets/Heart/หัวใจ-3.png').texture
        self.tex_heart_empty.mag_filter = 'nearest'
        self.tex_heart_empty.min_filter = 'nearest'

        self.hearts = []
        self.stun_visible = False # คุมการโชว์แถบคูลดาวน์
        self.stun_label = None # จะถูกสร้างเมื่อเรียก update_position ครั้งแรก
        
        with self.canvas.after:
            Color(1, 1, 1, 1)
            for i in range(self.max_health):
                # กำหนดรูปหัวใจตามเลือดที่มี
                tex = self.tex_heart_full if i < self.current_health else self.tex_heart_empty
                rect = Rectangle(texture=tex, size=(self.heart_size, self.heart_size))
                self.hearts.append(rect)
                
            # Stamina Bar Border
            Color(0.2, 0.4, 0.6, 1)  # สีฟ้าเข้ม (สำหรับขอบ)
            self.stamina_border = RoundedRectangle(size=(0, 6), radius=[3])
            
            # Stamina Bar Background
            Color(0.2, 0.2, 0.2, 1)
            self.stamina_bg = RoundedRectangle(size=(0, 6), radius=[2])
            
            # Stamina Bar Foreground
            Color(0.3, 0.7, 1.0, 1)  # สีฟ้าอ่อนๆ (Stamina)
            self.stamina_bar = RoundedRectangle(size=(0, 6), radius=[2])

            # --- Stun Cooldown Bar (User Request) ---
            self.stun_opacity = 0 # เริ่มต้นซ่อนไว้
            self.stun_color_border = Color(0.8, 0, 0, self.stun_opacity)
            self.stun_border = RoundedRectangle(size=(0, 6), radius=[3])
            
            self.stun_color_bg = Color(0.2, 0.2, 0.2, self.stun_opacity)
            self.stun_bg = RoundedRectangle(size=(0, 6), radius=[2])
            
            self.stun_color_fg = Color(1.0, 0.2, 0.2, self.stun_opacity)
            self.stun_bar = RoundedRectangle(size=(0, 6), radius=[2])
            
        self.current_ui_scale = 1.0

    def take_damage(self):
        if self.current_health > 0:
            # หา index ของหัวใจดวงขวาสุดที่ยังมีเลือดอยู่ (เช่น เลือดเหลือ 3 จะเปลี่ยนดวงที่ 2 (ดวงที่ 3 เริ่มนับ 0))
            heart_index = self.current_health - 1
            
            # ลดเลือด 1 ขั้น
            self.current_health -= 1
            
            # เปลี่ยนภาพหัวใจเป็นสีดำขั้นแรก (หัวใจแตก) ทันที
            self.hearts[heart_index].texture = self.tex_heart_break
            
            # เก็บค่า health ปัจจุบันไว้ เพื่อเช็คใน callback ว่ามีการรีเซ็ตเลือด (เช่น ตายแล้วเกิดใหม่) หรือไม่
            expected_health = self.current_health

            # ตั้งเวลาเปลี่ยนเป็นหัวใจว่างเปล่า (หัวใจ-3.png) ในอีก 0.5 วินาที
            def change_to_empty(dt):
                # ถ้าเลือดมีการเปลี่ยนแปลงไปในทางเพิ่มขึ้น (เกิดใหม่) ไม่ต้องเปลี่ยนภาพเป็นหัวใจว่าง
                if self.current_health <= expected_health:
                    self.hearts[heart_index].texture = self.tex_heart_empty
                    
            Clock.schedule_once(change_to_empty, 0.5)

    def reset_health(self):
        """รีเซ็ตเลือดกลับมาเต็ม 3 ดวง และล้างสถานะกราฟิก"""
        self.current_health = self.max_health
        for rect in self.hearts:
            rect.texture = self.tex_heart_full

    def update_position(self, width, height):
        # Calculate UI scale based on window height
        ui_scale = height / WINDOW_HEIGHT
        self.current_ui_scale = ui_scale
        
        # UI sizing constants
        current_heart_size = self.heart_size * ui_scale
        current_pad = self.pad * ui_scale
        current_start_x = self.start_x * ui_scale
        top_margin = 10 * ui_scale
        self.stamina_height = 6 * ui_scale
        
        # Position hearts at the top left
        start_y = height - current_heart_size - top_margin
        for i, rect in enumerate(self.hearts):
            rect.size = (current_heart_size, current_heart_size)
            rect.pos = (current_start_x + i * (current_heart_size + current_pad), start_y)

        # Calculate stamina bar dimensions
        self.stamina_max_width = (self.max_health * current_heart_size) + ((self.max_health - 1) * current_pad)
        stamina_y = start_y - (10 * ui_scale)
        border_thickness = 2 * ui_scale
        
        # Update stamina UI components
        self.stamina_border.pos = (current_start_x - border_thickness, stamina_y - border_thickness)
        self.stamina_border.size = (self.stamina_max_width + (border_thickness * 2), self.stamina_height + (border_thickness * 2))
        self.stamina_border.radius = [3 * ui_scale]
        
        self.stamina_bg.pos = (current_start_x, stamina_y)
        self.stamina_bg.size = (self.stamina_max_width, self.stamina_height)
        self.stamina_bg.radius = [2 * ui_scale]
        
        self.stamina_bar.pos = (current_start_x, stamina_y)
        self.stamina_bar.size = (self.stamina_max_width, self.stamina_height)
        self.stamina_bar.radius = [2 * ui_scale]

        # --- Update Stun Bar Dimensions ---
        stun_y = stamina_y - (16 * ui_scale) 
        
        self.stun_border.pos = (current_start_x - border_thickness, stun_y - border_thickness)
        self.stun_border.size = (self.stamina_max_width + (border_thickness * 2), self.stamina_height + (border_thickness * 2))
        self.stun_border.radius = [3 * ui_scale]
        
        self.stun_bg.pos = (current_start_x, stun_y)
        self.stun_bg.size = (self.stamina_max_width, self.stamina_height)
        self.stun_bg.radius = [2 * ui_scale]
        
        self.stun_bar.pos = (current_start_x, stun_y)
        self.stun_bar.size = (0, self.stamina_height)
        self.stun_bar.radius = [2 * ui_scale]

        # จัดการ Label ตัวเลขบนแถบ
        if self.stun_label is None:
            from kivy.uix.label import Label
            from data.settings import GAME_FONT
            self.stun_label = Label(
                text="", font_name=GAME_FONT, font_size=12 * ui_scale,
                color=(1, 1, 1, 0), bold=True, size_hint=(None, None),
                halign='center', valign='middle'
            )
            # ผูก text_size กับ size เพื่อให้ halign ทำงาน
            self.stun_label.bind(size=lambda l, s: setattr(l, 'text_size', s))
        
        if self.stun_label:
            self.stun_label.font_size = 12 * ui_scale
            # วางตำแหน่งไว้ท้ายแถบหรือกลางแถบ
            self.stun_label.size = (self.stamina_max_width, self.stamina_height * 2)
            self.stun_label.pos = (current_start_x, stun_y - self.stamina_height * 0.5)

    def update_stamina(self, ratio):
        """Updates the stamina bar width based on the current ratio (0.0 - 1.0)."""
        if hasattr(self, 'stamina_max_width'):
            self.stamina_bar.size = (self.stamina_max_width * ratio, self.stamina_height)

    def set_stun_visibility(self, visible):
        """คุมการแสดงผลของแถบคูลดาวน์"""
        self.stun_visible = visible
        opacity = 1.0 if visible else 0.0
        self.stun_color_border.a = opacity
        self.stun_color_bg.a = opacity
        self.stun_color_fg.a = opacity
        if self.stun_label:
            self.stun_label.color = (1, 1, 1, opacity)

    def update_stun_cooldown(self, current_time, max_time=15.0):
        """อัปเดตความกว้างและตัวเลขคูลดาวน์"""
        if not self.stun_visible: return
        
        ratio = max(0, min(1, current_time / max_time))
        if hasattr(self, 'stamina_max_width'):
            self.stun_bar.size = (self.stamina_max_width * ratio, self.stamina_height)
            
        if self.stun_label:
                if current_time > 0:
                    self.stun_label.text = f"{current_time:.1f}s"
                else:
                    self.stun_label.text = "READY"
