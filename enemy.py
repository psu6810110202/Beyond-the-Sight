from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math
import random

ENEMY_START_POSITIONS = [
    (800, 800), 
    (850, 850)  # เพิ่มตำแหน่งสำหรับ Enemy2
]

class Enemy:
    def __init__(self, canvas, x, y, enemy_type=1):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.enemy_type = enemy_type  # 1 หรือ 2
        self.speed = ENEMY_SPEED
        self.detection_radius = ENEMY_DETECTION_RADIUS
        self.safe_zone_radius = ENEMY_SAFE_ZONE_RADIUS
        
        self.is_moving = False
        self.target_pos = [x, y]
        self.turn_delay = 0
        self.direction = 'down'  # Enemy เริ่มต้นหันลง
        
        # Animation properties (เหมือน player)
        self.current_fps = 8  # FPS สำหรับ animation
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0  # เปลี่ยนทิศทางทุก 3 วินาที
        self.directions = ['down', 'left', 'right', 'up']
        
        # โหลด Texture ตามประเภทของ enemy
        if enemy_type == 1:
            try:
                self.idle_texture = CoreImage('assets/Enemy/Enemy1_idle.png').texture
                self.walk_texture = CoreImage('assets/Enemy/Enemy1_walk.png').texture
                print(f"Enemy1 loaded idle: assets/Enemy/Enemy1_idle.png")
                print(f"Enemy1 loaded walk: assets/Enemy/Enemy1_walk.png")
            except Exception as e:
                print(f"Failed to load Enemy1 texture: {e}")
                self.idle_texture = None
                self.walk_texture = None
        elif enemy_type == 2:
            try:
                self.idle_texture = CoreImage('assets/Enemy/Enemy2_idle.png').texture
                self.walk_texture = CoreImage('assets/Enemy/Enemy2_idle.png').texture  # ใช้ไฟล์เดียวกัน
                print(f"Enemy2 loaded: assets/Enemy/Enemy2_idle.png")
            except Exception as e:
                print(f"Failed to load Enemy2 texture: {e}")
                self.idle_texture = None
                self.walk_texture = None
        
        # กำหนด spritesheet สำหรับ Enemy
        if enemy_type == 1:
            self.anim_config = {
                'idle': {'tex': self.idle_texture, 'cols': 1, 'rows': 4},
                'walk': {'tex': self.walk_texture, 'cols': 3, 'rows': 4}
            }
        elif enemy_type == 2:
            # Enemy2 ใช้ spritesheet แบบเดียว (1x4 frames)
            self.anim_config = {
                'idle': {'tex': self.idle_texture, 'cols': 1, 'rows': 4},
                'walk': {'tex': self.walk_texture, 'cols': 1, 'rows': 4}
            }
        
        # สลับตัวเลข 0, 1, 2, 3 เพื่อให้ตรงกับแถวในรูป Spritesheet (ตาม spritesheet จริง)
        self.anim_row_map = {
            'idle': {
                'down': 2, 
                'left': 0, 
                'right': 1, 
                'up': 3
            },
            'walk': {
                'down': 2, 
                'left': 0, 
                'right': 1, 
                'up': 3
            }
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
        # ใช้ spritesheet แบบเดียวกับ player
        config = self.anim_config[self.state]
        tex = config['tex']
        
        if tex:
            # คำนวณขนาดของแต่ละเฟรมใน spritesheet (เหมือน player)
            w = 1.0 / config['cols']
            h = 1.0 / config['rows']
            
            u = self.frame_index * w
            
            # Get row index based on state and direction
            try:
                row_index = self.anim_row_map[self.state][self.direction]
            except KeyError:
                row_index = 0 # Fallback
                
            # Debug: แสดงข้อมูล animation
            print(f"Enemy{self.enemy_type} animation: state={self.state}, dir={self.direction}, row={row_index}, frame={self.frame_index}")
                
            # คำนวณแถว (เหมือน player)
            v = 1.0 - ((row_index + 1) * h)
            
            self.rect.texture = tex
            # Flip texture vertically by swapping v and v + h (เหมือน player)
            self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)
        else:
            # ไม่มี texture ให้แสดงสี่เหลี่ยมสีแดง
            self.rect.texture = None
    
    def animate(self, dt):
        # ตรวจสอบ state ปัจจุบันว่าควรจะเป็นอะไร (เหมือน player)
        new_state = 'walk' if self.is_moving else 'idle'
        
        # ถ้ามีการสลับระหว่าง "ยืนนิ่ง" กับ "เดิน" ให้ทำการรีเซ็ตเฟรมอนิเมชันกลับไปเริ่มที่ 0
        if self.state != new_state:
            self.state = new_state
            self.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยน state
        
        # คำนวณจำนวนเฟรมสูงสุดตาม state ปัจจุบัน
        max_frames = self.anim_config[self.state]['cols']
        
        # เปลี่ยนเฟรม animation
        self.frame_index = (self.frame_index + 1) % max_frames
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
        
        # Debug: แสดงทิศทางที่จะเดิน
        print(f"Enemy{self.enemy_type} chasing: dx={dx}, dy={dy}, current_dir={self.direction}")
        
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
                
        print(f"Enemy{self.enemy_type} will move: ({move_x}, {move_y}), new_dir={new_dir}")
                
        if move_x != 0 or move_y != 0:
            if self.direction != new_dir:
                self.direction = new_dir
                self.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง
                self.turn_delay = 6
                print(f"Enemy{self.enemy_type} changed direction to {new_dir}")
            else:
                # ตรวจสอบว่าตำแหน่งใหม่อยู่ใน safe zone หรือไม่
                new_x = self.x + move_x
                new_y = self.y + move_y
                
                # คำนวณระยะห่างจาก Reaper (ถ้ามี Reaper position)
                if reaper_pos:
                    distance_from_reaper = math.sqrt((new_x - reaper_pos[0])**2 + (new_y - reaper_pos[1])**2)
                    
                    # ถ้าตำแหน่งใหม่อยู่ใน safe zone ให้หยุดเดิน
                    if distance_from_reaper < self.safe_zone_radius:
                        print(f"Enemy{self.enemy_type} stopped - safe zone")
                        return  # ไม่เดินเข้าไปใน safe zone
                
                self.start_move(move_x, move_y)
                print(f"Enemy{self.enemy_type} started moving to ({new_x}, {new_y})")

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
