from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import TILE_SIZE, STAR_IMG

class Star:
    def __init__(self, canvas, x, y, is_true=True):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.logic_pos = [x, y]
        self.is_true = is_true # ของที่ใช่หรือเปล่า (มีผลต่อ Ending)
        
        self.image_path = STAR_IMG
        try:
            self.texture = CoreImage(self.image_path).texture
            if self.texture:
                self.texture.min_filter = 'nearest'
                self.texture.mag_filter = 'nearest'
        except Exception as e:
            print(f"Error loading Star texture: {e}")
            self.texture = None
            
        self.group = InstructionGroup()
        self.group.add(Color(1, 1, 1, 1))
        
        # Star.png (4 frames horizontal)
        self.cols = 4
        self.rows = 1
        self.frame_index = 0
        
        self.rect = Rectangle(pos=(self.x, self.y), size=(TILE_SIZE, TILE_SIZE))
        self.group.add(self.rect)
        self.canvas.add(self.group)
        
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / 3) # 3 FPS for stars

    def update_frame(self):
        if not self.texture: return
        w = 1.0 / self.cols
        h = 1.0 / self.rows
        u = self.frame_index * w
        v = 0
        self.rect.texture = self.texture
        self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)

    def animate(self, dt):
        self.frame_index = (self.frame_index + 1) % self.cols
        self.update_frame()

    def destroy(self):
        if self.group in self.canvas.children:
            self.canvas.remove(self.group)
        self.anim_event.cancel()
