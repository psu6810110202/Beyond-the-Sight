from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from data.settings import TILE_SIZE

class Candle:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.logic_pos = [x, y]
        self.is_lit = False
        self.current_color = None
        
        self.image_path = 'assets/Items/candle/candle.png'
        self.textures = {}
        self.load_textures()
            
        self.group = InstructionGroup()
        self.group.add(Color(1, 1, 1, 1))
        
        # Candle is 16x16
        self.rect = Rectangle(pos=(self.x, self.y), size=(TILE_SIZE, TILE_SIZE))
        if 'default' in self.textures:
            self.rect.texture = self.textures['default']
            
        self.group.add(self.rect)
        self.canvas.add(self.group)

    def load_textures(self):
        paths = {
            'default': 'assets/Items/candle/candle.png',
            'RED': 'assets/Items/candle/red.png',
            'BLUE': 'assets/Items/candle/blue.png',
            'YELLOW': 'assets/Items/candle/yellow.png'
        }
        for name, path in paths.items():
            try:
                tex = CoreImage(path).texture
                if tex:
                    tex.min_filter = 'nearest'
                    tex.mag_filter = 'nearest'
                    self.textures[name] = tex
            except Exception as e:
                print(f"Error loading Candle texture {name}: {e}")

    def set_color(self, color_name):
        """เปลี่ยนสีเทียนตามที่เลือก"""
        if color_name in self.textures:
            self.rect.texture = self.textures[color_name]
            self.is_lit = True
            self.current_color = color_name

    def update_visuals(self):
        """อัปเดตกราฟิกตามสถานะ (เปิด/ปิดไฟ)"""
        if not self.is_lit:
            if 'default' in self.textures:
                self.rect.texture = self.textures['default']
        elif self.current_color and self.current_color in self.textures:
            self.rect.texture = self.textures[self.current_color]

    def destroy(self):
        if self.group and self.group in self.canvas.children:
            self.canvas.remove(self.group)
