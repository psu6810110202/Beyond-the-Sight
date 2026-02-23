from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import random

class NPC:
    def __init__(self, canvas, x, y, color=(1, 0, 0, 1)):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.color = color
        
        # เลือกรูป NPC แบบสุ่ม
        npc_images = ['assets/NPC/NPC1.png', 'assets/NPC/NPC2.png', 'assets/NPC/NPC3.png', 'assets/NPC/NPC4.png', 'assets/NPC/NPC5.png']
        self.image_path = random.choice(npc_images)
        
        # กำหนด spritesheet สำหรับแต่ละ NPC
        if 'NPC1' in self.image_path:
            self.cols = 1
            self.rows = 3
            self.anim_row_map = {
                'idle': {
                    'down': 2, 
                    'left': 0, 
                    'right': 1, 
                    'up': 0  # ใช้ซ้าแทนขึ้นเพราะมีแค่ 3 แถว
                }
            }
        elif 'NPC4' in self.image_path:
            self.cols = 1
            self.rows = 2
            self.anim_row_map = {
                'idle': {
                    'down': 1, 
                    'left': 0, 
                    'right': 0, 
                    'up': 0  # ใช้ซ้าแทนขึ้นเพราะมีแค่ 2 แถว
                }
            }
        elif 'NPC5' in self.image_path:
            self.cols = 1
            self.rows = 3
            self.anim_row_map = {
                'idle': {
                    'down': 2, 
                    'left': 0, 
                    'right': 1, 
                    'up': 0  # ใช้ซ้าแทนขึ้นเพราะมีแค่ 3 แถว
                }
            }
        else:
            # NPC2, NPC3 ใช้ spritesheet 1x4 เหมือนเดิม
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
        
        # โหลด Texture
        try:
            self.idle_texture = CoreImage(self.image_path).texture
            print(f"NPC loaded: {self.image_path}, size: {self.idle_texture.size}")
        except Exception as e:
            print(f"Failed to load NPC texture {self.image_path}: {e}")
            # ใช้สีแดงเป็น fallback ถ้าโหลดรูปไม่ได้
            self.idle_texture = None
        
        # ตั้งค่า animation config (ใช้ spritesheet แบบไดนามิก)
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': self.cols, 'rows': self.rows}
        }
        
        self.state = 'idle'
        self.direction = random.choice(['down', 'left', 'right', 'up'])
        self.frame_index = 0
        
        # Animation properties
        self.current_fps = 1  # ลด FPS เหลือ 1 เพื่อไม่ให้กระพริบ
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0  # เปลี่ยนทิศทางทุก 3 วินาที (ช้าขึ้น)
        self.directions = ['down', 'left', 'right', 'up']
        
        # Create visual elements
        with canvas:
            if self.idle_texture:
                # ใช้สีขาวปกติเพื่อให้เห็นภาพชัด
                Color(1, 1, 1, 1)
            else:
                # ใช้สีแดงถ้าโหลดรูปไม่ได้
                Color(1, 0, 0, 1)
            self.rect = Rectangle(pos=(x, y), size=(NPC_WIDTH, NPC_HEIGHT))
        
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)
    
    def update_frame(self):
        # ใช้ spritesheet แบบเดียวกับ player
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
    
    def update(self, dt):
        # อัปเดตการเปลี่ยนทิศทางอัตโนมัติ
        self.direction_change_timer += dt
        if self.direction_change_timer >= self.direction_change_interval:
            self.direction_change_timer = 0
            # เลือกทิศทางใหม่แบบสุ่ม (แต่ไม่ซ้ำทิศทางปัจจุบัน)
            current_direction = self.direction
            available_directions = [d for d in self.directions if d != current_direction]
            self.direction = random.choice(available_directions)
            self.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง
    
    def check_player_collision(self, player_rect):
        npc_rect = [self.x, self.y, NPC_WIDTH, NPC_HEIGHT]
        player_rect_list = [player_rect.pos[0], player_rect.pos[1], 
                           player_rect.size[0], player_rect.size[1]]
        
        return (npc_rect[0] < player_rect_list[0] + player_rect_list[2] and
                npc_rect[0] + npc_rect[2] > player_rect_list[0] and
                npc_rect[1] < player_rect_list[1] + player_rect_list[3] and
                npc_rect[1] + npc_rect[3] > player_rect_list[1])
