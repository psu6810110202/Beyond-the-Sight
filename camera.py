from kivy.graphics import Translate, Scale, PushMatrix, PopMatrix
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT, TILE_SIZE

class Camera:
    def __init__(self, canvas_before):
        with canvas_before:
            PushMatrix()
            self.trans_center = Translate(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            self.scale = Scale(1, 1, 1)
            self.trans_pos = Translate(0, 0)
            
    def end_camera(self, canvas_after):
        with canvas_after:
            PopMatrix()

    def update(self, width, height, player_pos, map_width, map_height):
        # อัปเดตจุดศูนย์กลางกล้องให้เป็นกึ่งกลางของหน้าต่าง Application จริงๆ
        self.trans_center.xy = (width / 2, height / 2)

        # คำนวณอัตราส่วนการซูม (Scale) 
        scale_x = width / CAMERA_WIDTH
        scale_y = height / CAMERA_HEIGHT
        
        scale_factor = min(scale_x, scale_y)
        self.scale.xyz = (scale_factor, scale_factor, 1)

        # ศูนย์กลางของตัวละคร
        px, py = player_pos
        cam_x = px + TILE_SIZE / 2
        cam_y = py + TILE_SIZE / 2

        # ป้องกันไม่ให้กล้องเห็นพื้นที่นอกแมพ (Clamp Camera)
        map_w = map_width * TILE_SIZE
        map_h = map_height * TILE_SIZE
        
        visible_w = width / scale_factor
        visible_h = height / scale_factor
        
        half_w = visible_w / 2
        if map_w < visible_w:
            cam_x = map_w / 2
        else:
            cam_x = max(half_w, min(cam_x, map_w - half_w))
            
        half_h = visible_h / 2
        if map_h < visible_h:
            cam_y = map_h / 2
        else:
            cam_y = max(half_h, min(cam_y, map_h - half_h))
        
        # เลื่อนตำแหน่งตัวละครมาไว้ที่จุดศูนย์กลางของจอ
        self.trans_pos.xy = (-cam_x, -cam_y)
