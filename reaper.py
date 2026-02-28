from kivy.graphics import Rectangle, Color, Ellipse
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math
import random

REAPER_START_POS = (864, 80)

class Reaper:
    def __init__(self, canvas, x=None, y=None, color=(1, 0, 0, 1)):
        self.canvas = canvas
        self.x = x if x is not None else REAPER_START_POS[0]
        self.y = y if y is not None else REAPER_START_POS[1]
        self.color = color
        
        # ใช้รูป Reaper เฉพาะ
        self.image_path = 'assets/Reaper/Reaper.png'
        
        # กำหนด spritesheet สำหรับ Reaper (เหมือน NPC)
        self.cols = 1
        self.rows = 4
        self.anim_row_map = {
            'idle': {
                'down': 3, 
                'left': 0, 
                'right': 1, 
                'up': 2
            }
        }
        
        # โหลด Texture (เหมือน NPC)
        try:
            self.idle_texture = CoreImage(self.image_path).texture
            print(f"Reaper loaded: {self.image_path}, size: {self.idle_texture.size}")
        except Exception as e:
            print(f"Failed to load Reaper texture {self.image_path}: {e}")
            # ใช้สีแดงเป็น fallback ถ้าโหลดรูปไม่ได้
            self.idle_texture = None
        
        # ตั้งค่า animation config (ใช้ spritesheet แบบไดนามิก)
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': self.cols, 'rows': self.rows}
        }
        
        self.state = 'idle'
        self.direction = 'down'  # Reaper เริ่มต้นหันลง
        self.frame_index = 0
        
        # Animation properties (เหมือน NPC)
        self.current_fps = 1  # ลด FPS เหลือ 1 เพื่อไม่ให้กระพริบ
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0  # เปลี่ยนทิศทางทุก 3 วินาที (ช้าขึ้น)
        self.directions = ['down', 'left', 'right', 'up']
        
        # Reaper-specific properties
        self.speed = REAPER_SPEED
        self.target_pos = [self.x, self.y]
        self.is_moving = False
        self.safe_zone_radius = SAFE_ZONE_RADIUS
        self.detection_radius = SAFE_ZONE_RADIUS
        self.is_patrolling = True
        self.patrol_direction = 1
        self.patrol_timer = 0
        self.patrol_interval = 120
        self.is_protector = True
        
        # Create visual elements
        with canvas:
            # DEBUG: แถบสีเหลืองจำลองแสดง Hitbox (1 ช่อง 16x16)
            Color(1, 1, 0, 0.3)
            self.debug_rect = Rectangle(pos=(self.x, self.y), size=(TILE_SIZE, TILE_SIZE))
            
            if self.idle_texture:
                # ใช้สีขาวปกติเพื่อให้เห็นภาพชัด
                Color(1, 1, 1, 1)
            else:
                # ใช้สีแดงถ้าโหลดรูปไม่ได้
                Color(1, 0, 0, 1)
            # ใช้ขนาดภาพตาม VISUAL_WIDTH/HEIGHT แต่ชดเชยเพื่อให้ยืนพื้นปกติ
            offset_x = (TILE_SIZE - REAPER_VISUAL_WIDTH) / 2
            offset_y = TILE_SIZE / 2
            self.rect = Rectangle(pos=(self.x + offset_x, self.y + offset_y), size=(REAPER_VISUAL_WIDTH, REAPER_VISUAL_HEIGHT))
            
            # Protection aura (gentle blue glow)
            Color(0.3, 0.7, 1.0, 0.1)  # สีฟ้าพาสเทลอ่อนๆ
            self.protection_circle = Ellipse(
                pos=(self.x - self.detection_radius + REAPER_WIDTH//2, 
                    self.y - self.detection_radius + REAPER_HEIGHT//2),
                size=(self.detection_radius * 2, self.detection_radius * 2)
            )
        
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)
    
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
        # NPC มีแค่ idle animation แต่ไม่เปลี่ยนทุกเฟรม
        max_frames = self.anim_config[self.state]['cols']  # 1 คอลัมน์
        # 1 คอลัมน์ ไม่ต้องเปลี่ยนเฟรม แต่ยังคงเรียก update_frame เพื่อเปลี่ยนทิศทาง
        if random.random() < 0.1:  # ลดความถี่ให้นิ่งขึ้น
            self.frame_index = (self.frame_index + 1) % max_frames
        self.update_frame()
    
    def update(self, dt, player_pos):
        # Reaper อยู่ในท่า down เสมอเมื่อไม่ได้เคลื่อนไหว
        
        # Check if player is in safe zone
        distance_to_player = self.calculate_distance(player_pos)
        
        if distance_to_player <= self.safe_zone_radius:
            # Player is in safe zone - provide protection
            self.protect_player(player_pos)
        else:
            # Player outside safe zone - patrol behavior
            pass
        
        # Update visual positions
        self.update_visual_positions()
        
        # Continue movement if needed
        if self.is_moving:
            self.continue_move()
        
        # Update animation state
        new_state = 'idle'  # Reaper ไม่มี walk animation ในตอนนี้
        if self.state != new_state:
            self.state = new_state
            self.frame_index = 0
    
    def continue_move(self):
        cur_x, cur_y = self.x, self.y
        tar_x, tar_y = self.target_pos

        if cur_x < tar_x: cur_x = min(cur_x + self.speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.speed, tar_y)

        self.x, self.y = cur_x, cur_y
        
        # อัปเดตตำแหน่งของ Rectangle ตาม offset
        offset_x = (TILE_SIZE - REAPER_VISUAL_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect.pos = (self.x + offset_x, self.y + offset_y)
        
        # อัปเดต Debug Hitbox สีเหลือง
        self.debug_rect.pos = (self.x, self.y)
        
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False
    
    def update_visual_positions(self):
        # Update protection circle position
        self.protection_circle.pos = (
            self.x - self.detection_radius + REAPER_WIDTH//2,
            self.y - self.detection_radius + REAPER_HEIGHT//2
        )
    
    def calculate_distance(self, target_pos):
        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        return math.sqrt(dx**2 + dy**2)
    
    def is_in_safe_zone(self, target_pos):
        distance = self.calculate_distance(target_pos)
        return distance <= self.safe_zone_radius
    
    def protect_player(self, player_pos):
        # Reaper ปกป้องผู้เล่น - ไม่ไล่ตามแต่คุ้มคุ้ม
        self.is_patrolling = False
        self.is_moving = False
        # สามารถเพิ่มเอฟเฟกต์การปกป้องได้ที่นี่
        print("Reaper is protecting you in the safe zone!")
    
    def check_player_collision(self, player_logic_pos):
        reaper_rect = [self.x, self.y, TILE_SIZE, TILE_SIZE]
        player_rect_list = [player_logic_pos[0], player_logic_pos[1], TILE_SIZE, TILE_SIZE]
        
        # Reaper ไม่ทำอันตรายผู้เล่น - แค่สัมผัสกันได้
        return (reaper_rect[0] < player_rect_list[0] + player_rect_list[2] and
                reaper_rect[0] + reaper_rect[2] > player_rect_list[0] and
                reaper_rect[1] < player_rect_list[1] + player_rect_list[3] and
                reaper_rect[1] + reaper_rect[3] > player_rect_list[1])

    def check_player_collision_logic(self, player_logic_pos, tile_size):
        reaper_rect = [self.x, self.y, tile_size, tile_size]
        player_rect_list = [player_logic_pos[0], player_logic_pos[1], tile_size, tile_size]
        
        return (reaper_rect[0] < player_rect_list[0] + player_rect_list[2] and
                reaper_rect[0] + reaper_rect[2] > player_rect_list[0] and
                reaper_rect[1] < player_rect_list[1] + player_rect_list[3] and
                reaper_rect[1] + reaper_rect[3] > player_rect_list[1])

