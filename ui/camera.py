from kivy.graphics import Translate, Scale, PushMatrix, PopMatrix
from data.settings import WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT, TILE_SIZE

class Camera:
    def __init__(self, canvas_before):
        with canvas_before:
            PushMatrix()
            self.trans_center = Translate(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            self.scale = Scale(1, 1, 1)
            self.trans_pos = Translate(0, 0)
        self.locked = False
            
    def end_camera(self, canvas_after):
        with canvas_after:
            PopMatrix()

    def update(self, width, height, player_pos, map_width, map_height, should_clamp=True):
        # 1. จัดการการซูมและจัดกึ่งกลางของหน้าต่าง Application จริงๆ
        # ต้องทำเสมอแม้กล้องจะถูกล็อก (locked) เพื่อให้สเกลภาพไม่เบี้ยวเวลาขยาย/ย่อจอ
        self.trans_center.xy = (width / 2, height / 2)

        scale_x = width / CAMERA_WIDTH
        scale_y = height / CAMERA_HEIGHT
        scale_factor = min(scale_x, scale_y)
        self.scale.xyz = (scale_factor, scale_factor, 1)

        if self.locked:
            return

        # ศูนย์กลางของตัวละคร (นี่คือจุดที่อยากให้เป็นจุดศูนย์กลางจอ)
        px, py = player_pos
        cam_x = px + TILE_SIZE / 2
        cam_y = py + TILE_SIZE / 2

        if should_clamp:
            # ป้องกันไม่ให้กล้องเห็นพื้นที่นอกแมพ (Clamp Camera) 
            map_w = map_width * TILE_SIZE
            map_h = map_height * TILE_SIZE
            
            visible_w = width / scale_factor
            visible_h = height / scale_factor
            
            # 1. การคำนวณตำแหน่ง X
            if map_w < visible_w:
                cam_x = map_w / 2
            else:
                half_w = visible_w / 2
                cam_x = max(half_w, min(cam_x, map_w - half_w))
                
            # 2. การคำนวณตำแหน่ง Y
            if map_h < visible_h:
                cam_y = map_h / 2
            else:
                half_h = visible_h / 2
                cam_y = max(half_h, min(cam_y, map_h - half_h))
        
        # เลื่อนหน้าจอ
        self.trans_pos.xy = (-cam_x, -cam_y)

    def world_to_screen(self, x, y):
        """แปลงพิกัดโลก (World) ในเกมให้เป็นพิกัดหน้าจอ (Screen)"""
        # 1. เลื่อนตามตำแหน่งกล้อง
        cx = x + self.trans_pos.x
        cy = y + self.trans_pos.y
        
        # 2. ปรับตามอัตราการซูม (Scale)
        sx = cx * self.scale.x
        sy = cy * self.scale.y
        
        # 3. เลื่อนเข้าหาจุดศูนย์กลางของหน้าต่าง
        wx = sx + self.trans_center.x
        wy = sy + self.trans_center.y
        
        return wx, wy
