from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import random

NPC_START_POSITIONS = {
    'NPC1': (896, 256),
    'NPC2': (544, 288),
    'NPC3': (704, 1472),
    'NPC4': (1392, 1072),
    'NPC5': (560, 256)
}

class NPC:
    def __init__(self, canvas, x=None, y=None, image_path=None, color=(1, 0, 0, 1)):
        self.canvas = canvas
        self.color = color
        
        # ถ้ามีการกำหนด image_path มาให้ใช้ค่านั้น ถ้าไม่ให้สุ่ม
        if image_path:
            self.image_path = image_path
        else:
            self.image_path = random.choice(NPC_IMAGE_LIST)
            
        # Set x, y from dictionary if not provided
        if x is None or y is None:
            for name, (px, py) in NPC_START_POSITIONS.items():
                if name in self.image_path:
                    self.x = (px // TILE_SIZE) * TILE_SIZE
                    self.y = (py // TILE_SIZE) * TILE_SIZE
                    break
        else:
            self.x = x
            self.y = y
        self.logic_pos = [self.x, self.y]
        self.target_pos = [self.x, self.y]
        self.is_moving = False
        self.is_fading = False
        self.fading_done = False
        self.speed = 1.0 # ความเร็วมาตรฐานของ NPC
        
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
            self.rows = 5
            self.anim_row_map = {
                'idle': {
                    'down': 4, 
                    'left': 3, 
                    'right': 2, 
                    'up': 1  # ใช้ซ้าแทนขึ้นเพราะมีแค่ 3 แถว
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
        self.direction = 'down'
        self.frame_index = 0
        
        # Animation properties
        # NPC5 มี animation ตลอดเวลา ส่วนอื่นๆ นิ่ง
        if 'NPC5' in self.image_path:
            self.current_fps = 8  # FPS สูงสำหรับ animation ตลอดเวลา
            self.is_animated = True
        else:
            self.current_fps = 1  # ลด FPS เหลือ 1 เพื่อไม่ให้กระพริบ
            self.is_animated = False
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0  # เปลี่ยนทิศทางทุก 3 วินาที (ช้าขึ้น)
        self.directions = ['down', 'left', 'right', 'up']
        
        # Create visual elements in an InstructionGroup for sorting
        self.group = InstructionGroup()
        self.alpha = 1.0
        
        if self.idle_texture:
            self.color_instr = Color(1, 1, 1, self.alpha)
        else:
            self.color_instr = Color(1, 0, 0, self.alpha)
            
        self.group.add(self.color_instr)
            
        # Offset position to center visual sprite
        offset_x = (TILE_SIZE - NPC_VISUAL_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect = Rectangle(pos=(self.x + offset_x, self.y + offset_y), size=(NPC_VISUAL_WIDTH, NPC_VISUAL_HEIGHT))
        self.group.add(self.rect)
            
        self.canvas.add(self.group)
        
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
        if self.is_animated:
            # NPC5 มี animation ตลอดเวลา
            max_frames = self.anim_config[self.state]['cols']  # 1 คอลัมน์
            self.frame_index = (self.frame_index + 1) % max_frames
            self.update_frame()
        else:
            # NPCs อื่นๆ นิ่ง
            max_frames = self.anim_config[self.state]['cols']  # 1 คอลัมน์
            # 1 คอลัมน์ ไม่ต้องเปลี่ยนเฟรม แต่ยังคงเรียก update_frame เพื่อเปลี่ยนทิศทาง
            if random.random() < 0.1:  # ลดความถี่ให้นิ่งขึ้น
                self.frame_index = (self.frame_index + 1) % max_frames
            self.update_frame()
    
    def sync_graphics_pos(self):
        """อัปเดตตำแหน่งกราฟิกให้ตรงกับ Logic Pos"""
        offset_x = (TILE_SIZE - NPC_VISUAL_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect.pos = (self.logic_pos[0] + offset_x, self.logic_pos[1] + offset_y)

    def start_move(self, dx, dy):
        """กำหนดเป้าหมายการเดินให้ NPC (ทิศทาง Grid-based)"""
        self.target_pos = [self.logic_pos[0] + dx, self.logic_pos[1] + dy]
        self.is_moving = True
        if dx > 0: self.direction = 'right'
        elif dx < 0: self.direction = 'left'
        elif dy > 0: self.direction = 'up'
        elif dy < 0: self.direction = 'down'
        self.state = 'walk' if hasattr(self, 'walk_texture') else 'idle'
        self.update_frame()

    def continue_move(self):
        """เลื่อนตำแหน่ง NPC เข้าหาเป้าหมายอย่างต่อเนื่อง"""
        cur_x, cur_y = self.logic_pos
        tar_x, tar_y = self.target_pos

        if cur_x < tar_x: cur_x = min(cur_x + self.speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.speed, tar_y)

        self.logic_pos = [cur_x, cur_y]
        self.sync_graphics_pos()

        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False
            self.state = 'idle'
            self.update_frame()

    def update(self, dt):
        if self.is_fading:
            self.alpha -= dt * 1.0 # ค่อยๆ จางลง
            if self.alpha <= 0:
                self.alpha = 0
                self.fading_done = True
            
            # อัปเดต Alpha ในส่วนประกอบ rgba
            if self.idle_texture:
                self.color_instr.rgba = (1, 1, 1, self.alpha)
            else:
                self.color_instr.rgba = (1, 0, 0, self.alpha)
            return

        if self.is_moving:
            self.continue_move()
            
        if self.is_animated:
            # NPC5 เปลี่ยนทิศทางอัตโนมัติเพื่อความหลากหลายใน animation
            self.direction_change_timer += dt
            if self.direction_change_timer >= self.direction_change_interval:
                self.direction_change_timer = 0
                # เลือกทิศทางใหม่แบบสุ่ม (แต่ไม่ซ้ำทิศทางปัจจุบัน)
                current_direction = self.direction
                available_directions = [d for d in self.directions if d != current_direction]
                self.direction = random.choice(available_directions)
                self.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง
        else:
            # NPCs อื่นๆ อยู่ในท่า down เสมอเมื่อไม่ได้เคลื่อนไหว
            pass
    
    def check_player_collision(self, player_logic_pos):
        # ใช้ 1 ช่อง TILE_SIZE x TILE_SIZE เป็นฐาน Hitbox
        npc_rect = [self.x, self.y, TILE_SIZE, TILE_SIZE]
        player_rect_list = [player_logic_pos[0], player_logic_pos[1], TILE_SIZE, TILE_SIZE]
        
        return (npc_rect[0] < player_rect_list[0] + player_rect_list[2] and
                npc_rect[0] + npc_rect[2] > player_rect_list[0] and
                npc_rect[1] < player_rect_list[1] + player_rect_list[3] and
                npc_rect[1] + npc_rect[3] > player_rect_list[1])
