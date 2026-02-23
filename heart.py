from kivy.graphics import Rectangle, Color
from settings import WINDOW_HEIGHT

class HeartUI:
    def __init__(self, canvas):
        self.canvas = canvas
        self.heart_size = 48
        self.pad = 5
        self.start_x = 10
        self.max_health = 3
        
        self.hearts = []
        
        with self.canvas.after:
            Color(1, 1, 1, 1)
            for _ in range(self.max_health):
                rect = Rectangle(source='assets/Heart/หัวใจ-1.png', size=(self.heart_size, self.heart_size))
                self.hearts.append(rect)

    def update_position(self, width, height):
        # คำนวณอัตราส่วน (scale) UI เมื่อขยายจอ
        # โดยอิงจากความสูงของหน้าจอโปรแกรมในปัจจุบันเทียบกับค่า WINDOW_HEIGHT เริ่มต้น
        ui_scale = height / WINDOW_HEIGHT
        
        current_heart_size = self.heart_size * ui_scale
        current_pad = self.pad * ui_scale
        current_start_x = self.start_x * ui_scale
        current_top_margin = 10 * ui_scale
        
        start_y = height - current_heart_size - current_top_margin
        
        for i, rect in enumerate(self.hearts):
            rect.size = (current_heart_size, current_heart_size)
            # ขยับแกน x ตามลำดับหัวใจ
            rect.pos = (current_start_x + i * (current_heart_size + current_pad), start_y)
