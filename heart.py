from kivy.graphics import Rectangle, Color, RoundedRectangle
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from settings import WINDOW_HEIGHT

class HeartUI:
    def __init__(self, canvas):
        self.canvas = canvas
        self.heart_size = 48
        self.pad = 5
        self.start_x = 10
        self.max_health = 3
        self.current_health = 3
        
        # โหลด Texture ของหัวใจและตั้งค่าให้เป็นแบบ 'nearest' เพื่อไม่ให้ภาพเบลอเวลาขยาย (Pixel Perfect)
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
        
        with self.canvas.after:
            Color(1, 1, 1, 1)
            for _ in range(self.max_health):
                rect = Rectangle(texture=self.tex_heart_full, size=(self.heart_size, self.heart_size))
                self.hearts.append(rect)
                
            # Stamina Bar Border
            Color(0, 0.2, 0, 1)  # สีเขียวเข้มขึ้นกว่าเดิมมาก
            self.stamina_border = RoundedRectangle(size=(0, 6), radius=[3])
            
            # Stamina Bar Background
            Color(0.2, 0.2, 0.2, 1)
            self.stamina_bg = RoundedRectangle(size=(0, 6), radius=[2])
            
            # Stamina Bar Foreground
            Color(0, 1, 0, 1)
            self.stamina_bar = RoundedRectangle(size=(0, 6), radius=[2])
            
        self.current_ui_scale = 1.0

    def take_damage(self):
        if self.current_health > 0:
            # หา index ของหัวใจดวงขวาสุดที่ยังมีเลือดอยู่ (เช่น เลือดเหลือ 3 จะเปลี่ยนดวงที่ 2 (ดวงที่ 3 เริ่มนับ 0))
            heart_index = self.current_health - 1
            
            # ลดเลือด 1 ขั้น
            self.current_health -= 1
            
            # เปลี่ยนภาพหัวใจเป็นสีดำขั้นแรก (หัวใจแตก) ทันที
            self.hearts[heart_index].texture = self.tex_heart_break
            
            # ตั้งเวลาเปลี่ยนเป็นหัวใจว่างเปล่า (หัวใจ-3.png) ในอีก 2 วินาที
            def change_to_empty(dt):
                self.hearts[heart_index].texture = self.tex_heart_empty
                    
            Clock.schedule_once(change_to_empty, 0.5)

    def update_position(self, width, height):
        # คำนวณอัตราส่วน (scale) UI เมื่อขยายจอ
        # โดยอิงจากความสูงของหน้าจอโปรแกรมในปัจจุบันเทียบกับค่า WINDOW_HEIGHT เริ่มต้น
        ui_scale = height / WINDOW_HEIGHT
        self.current_ui_scale = ui_scale
        
        current_heart_size = self.heart_size * ui_scale
        current_pad = self.pad * ui_scale
        current_start_x = self.start_x * ui_scale
        current_top_margin = 10 * ui_scale
        
        start_y = height - current_heart_size - current_top_margin
        
        for i, rect in enumerate(self.hearts):
            rect.size = (current_heart_size, current_heart_size)
            # ขยับแกน x ตามลำดับหัวใจ
            rect.pos = (current_start_x + i * (current_heart_size + current_pad), start_y)

        # คำนวณความกว้างรวมของหัวใจเพื่อเป็นความกว้างของแถบ Stamina
        total_width = (self.max_health * current_heart_size) + ((self.max_health - 1) * current_pad)
        
        stamina_y = start_y - (10 * ui_scale) # ลงมาใต้หัวใจ 10px (เผื่อพื้นที่ให้หลอดหนาขึ้น)
        
        # ขอบหลอด Stamina (ขยายความหนาเป็น 2px ทุกด้าน คูณด้วยสเกลหน้าจอ)
        border_thickness = 2 * ui_scale
        self.stamina_border.pos = (current_start_x - border_thickness, stamina_y - border_thickness)
        self.stamina_border.size = (total_width + (border_thickness * 2), (6 * ui_scale) + (border_thickness * 2))
        self.stamina_border.radius = [3 * ui_scale]
        
        self.stamina_bg.pos = (current_start_x, stamina_y)
        self.stamina_bg.size = (total_width, 6 * ui_scale)
        self.stamina_bg.radius = [2 * ui_scale]
        
        self.stamina_bar.pos = (current_start_x, stamina_y)
        self.stamina_bar.size = (total_width, 6 * ui_scale)
        self.stamina_bar.radius = [2 * ui_scale]

    def update_stamina(self, ratio):
        if hasattr(self, 'current_ui_scale'):
            ui_scale = self.current_ui_scale
            current_heart_size = self.heart_size * ui_scale
            current_pad = self.pad * ui_scale
            total_width = (self.max_health * current_heart_size) + ((self.max_health - 1) * current_pad)
            
            # ปรับความกว้างของแถบสีเขียวตาม Stamina ที่เหลือ (สูงสุด 100%)
            self.stamina_bar.size = (total_width * ratio, 6 * ui_scale)
