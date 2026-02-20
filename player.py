from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *

class Player:
    def __init__(self, canvas):
        self.canvas = canvas
        self.is_moving = False
        self.target_pos = [96, 96]
        self.current_speed = WALK_SPEED
        self.turn_delay = 0  # <--- เพิ่มตัวหน่วงเวลาตอนเปลี่ยนทิศทาง
        
        # โหลด Texture
        self.idle_texture = CoreImage('assets/players/player_idle.png').texture
        self.walk_texture = CoreImage('assets/players/player_walk.png').texture
        
        # ตั้งชื่อให้ตรงกันทั้งหมด (ใช้ anim_config และ key 'tex')
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': 3, 'rows': 4},
            'walk': {'tex': self.walk_texture, 'cols': 8, 'rows': 4}
        }
        
        # สลับตัวเลข 0, 1, 2, 3 เพื่อให้ตรงกับแถวในรูป Spritesheet ได้เลยครับ
        # 0 = แถวบนสุด (1), 1 = แถว 2, 2 = แถว 3, 3 = แถวล่างสุด (4)
        self.anim_row_map = {
            'idle': {
                'down': 3, 
                'left': 0, 
                'right': 1, 
                'up': 2
            },
            'walk': {
                'down': 3, 
                'left': 0, 
                'right': 1, 
                'up': 2
            }
        }
        
        self.state = 'idle'
        self.direction = 'down' 
        self.frame_index = 0
        
        # Stamina
        self.stamina = MAX_STAMINA
        self.max_stamina = MAX_STAMINA

        with canvas:
            # สร้างตัวละครแค่ครั้งเดียว (ขนาดแนะนำคือ TILE_SIZE * 2 หรือตามความเหมาะสม)
            Color(1, 1, 1, 1)
            self.rect = Rectangle(pos=(96, 96), size=(PLAYER_WIDTH, PLAYER_HEIGHT))
            
            # Stamina Bar
            Color(0, 1, 0, 1)
            self.stamina_bar = Rectangle(pos=(10, 10), size=(0, 5))
            
        self.update_frame()
        self.current_fps = 8
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)

    def update_frame(self):
        # เรียกใช้ตัวแปรที่ชื่อตรงกัน
        config = self.anim_config[self.state]
        tex = config['tex']
        w = 128.0 / tex.width
        h = 128.0 / tex.height
        
        u = self.frame_index * w
        
        # Get row index based on state and direction
        try:
            row_index = self.anim_row_map[self.state][self.direction]
        except KeyError:
            row_index = 0 # Fallback
            
        # คำนวณแถว
        v = 1.0 - ((row_index + 1) * h)
        
        self.rect.texture = config['tex']
        # Flip texture vertically by swapping v and v + h
        self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)
        
    def animate(self, dt):
        # ตรวจสอบ state ปัจจุบันว่าควรจะเป็นอะไร
        new_state = 'walk' if self.is_moving else 'idle'
        
        # ถ้ามีการสลับระหว่าง "ยืนนิ่ง" กับ "เดิน" ให้ทำการรีเซตเฟรมอนิเมชันกลับไปเริ่มที่ 0
        if self.state != new_state:
            self.state = new_state
            # ดึงเฉพาะภาพ Idle กรอบแรกแบบเฉียบพลัน เพื่อไม่ให้มีหน่วงเมื่อหยุดการเดิน/วิ่ง
            self.frame_index = 0
            if new_state == 'idle':
                # บังคับอัปลงจอก่อนเลยจะได้เห็นว่าหยุดนิ่งแล้ว
                self.update_frame()
                return
        else:
            # ถ้า state เดิม ให้เล่นเฟรมถัดไป
            max_frames = self.anim_config[self.state]['cols']
            self.frame_index = (self.frame_index + 1) % max_frames
            
        self.update_frame()
        
    def move(self, pressed_keys):
        # 1. อัปเดตตำแหน่งก่อน หากเดินอยู่ให้เดินจนจบช่อง
        if self.is_moving:
            self.continue_move()

        # 2. ถ้าตรวจสอบแล้วพบว่าหยุดนิ่ง (หรือเพิ่งเดินถึงเป้าหมายในเฟรมนี้พอดี) ให้รับคำสั่งเดินต่อทันที
        if not self.is_moving:
            if self.turn_delay > 0:
                self.turn_delay -= 1
            else:
                dx, dy = 0, 0
                new_dir = self.direction

                if 'w' in pressed_keys or 'up' in pressed_keys: 
                    dy = TILE_SIZE; new_dir = 'up' 
                elif 's' in pressed_keys or 'down' in pressed_keys: 
                    dy = -TILE_SIZE; new_dir = 'down' 
                elif 'a' in pressed_keys or 'left' in pressed_keys: 
                    dx = -TILE_SIZE; new_dir = 'left' 
                elif 'd' in pressed_keys or 'right' in pressed_keys: 
                    dx = TILE_SIZE; new_dir = 'right'

                if dx != 0 or dy != 0:
                    if self.direction != new_dir:
                        # ถ้าเปลี่ยนทิศ ให้หันหน้าก่อนแล้วหน่วงเวลาเล็กน้อย
                        self.direction = new_dir
                        self.turn_delay = 6  # จำนวนเฟรมที่รอก่อนเดิน (ประมาน 0.1 วินาที)
                        self.update_frame()
                    else:
                        self.start_move(dx, dy)

        # 3. คำนวณความเร็วและ FPS จากค่าความจริงของ self.is_moving ที่เพิ่งได้รับการอัปเดตอย่างต่อเนื่องแล้วเท่านั้น
        is_running = 'shift' in pressed_keys and self.is_moving
        
        if self.is_moving:
            if is_running and self.stamina > 0:
                self.current_speed = RUN_SPEED
                self.stamina -= STAMINA_DRAIN
                target_fps = 12
            else:
                self.current_speed = WALK_SPEED
                if self.stamina < self.max_stamina:
                    self.stamina += STAMINA_REGEN
                target_fps = 8
        else:
            # ไม่ได้เดินอยู่ (ยืนเฉยๆ) ให้ฟื้นฟู Stamina และคำนวณ FPS
            if self.stamina < self.max_stamina:
                self.stamina += STAMINA_REGEN
                # พักฟื้นหลังวิ่ง -> ใช้ 3 FPS
                target_fps = 3
            else:
                # ยืนปกติ พลังเต็ม -> ใช้ 2 FPS
                target_fps = 2
            
            self.current_speed = WALK_SPEED
            
        # ปรับความเร็วอนิเมชันให้เหมาะสมตามสถานะ
        if getattr(self, 'current_fps', 8) != target_fps:
            self.current_fps = target_fps
            self.anim_event.cancel()
            self.anim_event = Clock.schedule_interval(self.animate, 1.0 / target_fps)
            
        # 4. บังคับอัปเดตกลับไปยืน Idle ทันทีเมื่อผู้เล่นปล่อยปุ่มเดิน
        if not self.is_moving and self.state != 'idle':
            self.state = 'idle'
            self.frame_index = 0
            self.update_frame()

    def start_move(self, dx, dy):
        new_x = self.rect.pos[0] + dx
        new_y = self.rect.pos[1] + dy
        
        if 0 <= new_x <= WINDOW_WIDTH - self.rect.size[0] and 0 <= new_y <= WINDOW_HEIGHT - self.rect.size[1]:
            self.target_pos = [new_x, new_y]
            self.is_moving = True

    def continue_move(self):
        cur_x, cur_y = self.rect.pos
        tar_x, tar_y = self.target_pos

        # ใช้ current_speed แทน PLAYER_SPEED เพื่อให้วิ่งเร็วขึ้นจริง
        if cur_x < tar_x: cur_x = min(cur_x + self.current_speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.current_speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.current_speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.current_speed, tar_y)

        self.rect.pos = (cur_x, cur_y)
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False