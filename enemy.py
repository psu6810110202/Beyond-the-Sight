from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math

class Enemy:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.speed = ENEMY_SPEED
        self.detection_radius = ENEMY_DETECTION_RADIUS
        self.safe_zone_radius = ENEMY_SAFE_ZONE_RADIUS
        
        self.is_moving = False
        self.target_pos = [x, y]
        self.turn_delay = 0
        self.direction = 'down'  # Enemy เริ่มต้นหันลง
        
        # Animation properties (เหมือน NPC)
        self.current_fps = 1  # ลด FPS เหลือ 1 เพื่อไม่ให้กระพริบ
        self.is_animated = False  # Enemy ไม่มี animation ตลอดเวลา
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0  # เปลี่ยนทิศทางทุก 3 วินาที (ช้าขึ้น)
        self.directions = ['down', 'left', 'right', 'up']
        
        # โหลด Texture (เหมือน NPC)
        try:
            self.idle_texture = CoreImage('assets/Enemy/Enemy1.png').texture
            print(f"Enemy loaded: assets/Enemy/Enemy1.png, size: {self.idle_texture.size}")
        except Exception as e:
            print(f"Failed to load Enemy texture: {e}")
            self.idle_texture = None
        
        # กำหนด spritesheet สำหรับ Enemy (เหมือน NPC)
        self.cols = 1
        self.rows = 4  # สมมตว่าว่าเป็น spritesheet 4 แถวเหมือน NPC
        self.anim_row_map = {
            'idle': {
                'down': 3, 
                'left': 0, 
                'right': 1, 
                'up': 2
            }
        }
        
        # ตั้งค่า animation config (ใช้ spritesheet แบบไดนามิก)
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': self.cols, 'rows': self.rows}
        }
        
        self.state = 'idle'
        self.frame_index = 0
        
        with canvas:
            # DEBUG: แถบสีเหลืองจำลองแสดงว่า Hitbox (จุดปะทะจริง) มีขนาดแค่ 32x32
            Color(1, 1, 0, 0.3)
            self.debug_rect = Rectangle(pos=(self.x, self.y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))
            
            if self.idle_texture:
                # ใช้สีขาวปกติเพื่อให้เห็นภาพชัด
                Color(1, 1, 1, 1)
            else:
                # ใช้สีแดงถ้าโหลดรูปไม่ได้
                Color(1, 0, 0, 1)
            self.rect = Rectangle(pos=(self.x, self.y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))
            
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)
            
    def destroy(self):
        # ลบหน้าตาของศัตรูรูปสี่เหลี่ยมออกจากผืนผ้าใบแคนวาส
        self.canvas.remove(self.debug_rect)
        self.canvas.remove(self.rect)
        self.anim_event.cancel()
            
    def update_frame(self):
        # ใช้ spritesheet แบบเดียวกับ NPC
        config = self.anim_config[self.state]
        tex = config['tex']
        
        if tex:
            # คำนวณขนาดของแต่ละเฟรมใน spritesheet
            w = 1.0 / config['cols']  # ความกว้างของแต่ละเฟรม
            h = 1.0 / config['rows']  # ความสูงของแต่ละเฟรม
            
            u = 0  # 1 คอลัมน์ ดังนั้น u จะเป็น 0 เสมอ
            
            # Get row index based on state and direction
            try:
                row_index = self.anim_row_map[self.state][self.direction]
            except KeyError:
                row_index = 0 # Fallback
                
            # คำนวณแถว - ปรับพิกัดให้ภาพไม่แหว่ง
            v = (row_index * h)
            
            self.rect.texture = tex
            # ปรับ tex_coords ให้ภาพอยู่ในกรอบ
            self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)
        else:
            # ไม่มี texture ให้แสดงสี่เหลี่ยมสีแดง
            self.rect.texture = None
    
    def animate(self, dt):
        if self.is_animated:
            # Enemy มี animation แบบ NPC
            max_frames = self.anim_config[self.state]['cols']  # 1 คอลัมน์
            # 1 คอลัมน์ ไม่ต้องเปลี่ยนเฟรม แต่ยังคงเรียก update_frame เพื่อเปลี่ยนทิศทาง
            if random.random() < 0.1:  # ลดความถี่ให้นิ่งขึ้น
                self.frame_index = (self.frame_index + 1) % max_frames
            self.update_frame()
        else:
            # Enemy ไม่มี animation ใช้ภาพเดียว
            # แต่ยังคงเรียก update_frame เพื่อความสมานธรร
            self.update_frame()
            
    def update(self, dt, player_pos, reaper_pos=None):
        # 1. ขยับตัวละครถ้าอยู่ในสถานะเดิน
        if self.is_moving:
            self.continue_move()
        else:
            # Enemy อยู่ในท่า down เสมอเมื่อไม่ได้เคลื่อนไหว (เหมือน NPC)
            self.direction_change_timer += dt
            if self.direction_change_timer >= self.direction_change_interval:
                self.direction_change_timer = 0
                # เลือกทิศทางใหม่แบบสุ่ม (แต่ไม่ซ้ำทิศทางปัจจุบัน)
                current_direction = self.direction
                available_directions = [d for d in self.directions if d != current_direction]
                self.direction = random.choice(available_directions)
                self.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง

        # 2. ถ้าหยุดอยู่ให้ตัดสินใจว่าจะเดินไปทางไหน
        if not self.is_moving:
            distance_to_player = self.calculate_distance(player_pos)
            if distance_to_player <= self.detection_radius:
                self.chase_player_grid(player_pos, reaper_pos)
                    
        # อัปเดตกรอบเช็คการชน (Hitbox) สีเหลืองตามตำแหน่งปัจจุบัน
        self.debug_rect.pos = (self.x, self.y)
        
        # อัปเดตกราฟิกสี่เหลี่ยมตามพิกัด x, y
        self.rect.pos = (self.x, self.y)
        
    def calculate_distance(self, target_pos):
        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        return math.sqrt(dx**2 + dy**2)
        
    def chase_player_grid(self, player_pos, reaper_pos=None):
        if self.turn_delay > 0:
            self.turn_delay -= 1
            return

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        
        move_x, move_y = 0, 0
        new_dir = self.direction
        
        # เลือกเดินแกนที่ระยะห่างเยอะกว่าก่อน (หรือสุ่มก็ได้) แบบ Grid Movement
        if abs(dx) > abs(dy):
            if dx > 0:
                move_x = TILE_SIZE; new_dir = 'right'
            else:
                move_x = -TILE_SIZE; new_dir = 'left'
        elif abs(dy) > 0:
            if dy > 0:
                move_y = TILE_SIZE; new_dir = 'up'
            else:
                move_y = -TILE_SIZE; new_dir = 'down'
                
        if move_x != 0 or move_y != 0:
            if self.direction != new_dir:
                self.direction = new_dir
                self.turn_delay = 6
            else:
                # ตรวจสอบว่าตำแหน่งใหม่อยู่ใน safe zone หรือไม่
                new_x = self.x + move_x
                new_y = self.y + move_y
                
                # คำนวณระยะห่างจาก Reaper (ถ้ามี Reaper position)
                if reaper_pos:
                    distance_from_reaper = math.sqrt((new_x - reaper_pos[0])**2 + (new_y - reaper_pos[1])**2)
                    
                    # ถ้าตำแหน่งใหม่อยู่ใน safe zone ให้หยุดเดิน
                    if distance_from_reaper < self.safe_zone_radius:
                        return  # ไม่เดินเข้าไปใน safe zone
                
                self.start_move(move_x, move_y)

    def start_move(self, dx, dy):
        self.target_pos = [self.x + dx, self.y + dy]
        self.is_moving = True

    def continue_move(self):
        cur_x, cur_y = self.x, self.y
        tar_x, tar_y = self.target_pos

        if cur_x < tar_x: cur_x = min(cur_x + self.speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.speed, tar_y)

        self.x, self.y = cur_x, cur_y
        
        # อัปเดตกราฟิกสี่เหลี่ยมตามพิกัด x, y
        self.rect.pos = (self.x, self.y)
        
        # อัปเดตกรอบเช็คการชน (Hitbox) สีเหลืองตามการเคลื่อนไหว
        self.debug_rect.pos = (self.x, self.y)
        
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False
            
    def check_player_collision(self, player_rect):
        enemy_r = [self.x, self.y, ENEMY_WIDTH, ENEMY_HEIGHT]
        player_r = [player_rect.pos[0], player_rect.pos[1], 
                    player_rect.size[0], player_rect.size[1]]
        
        return (enemy_r[0] < player_r[0] + player_r[2] and
                enemy_r[0] + enemy_r[2] > player_r[0] and
                enemy_r[1] < player_r[1] + player_r[3] and
                enemy_r[1] + enemy_r[3] > player_r[1])

    def check_player_collision_logic(self, player_pos, tile_size):
        enemy_r = [self.x, self.y, ENEMY_WIDTH, ENEMY_HEIGHT]
        player_r = [player_pos[0], player_pos[1], tile_size, tile_size]
        
        return (enemy_r[0] < player_r[0] + player_r[2] and
                enemy_r[0] + enemy_r[2] > player_r[0] and
                enemy_r[1] < player_r[1] + player_r[3] and
                enemy_r[1] + enemy_r[3] > player_r[1])
