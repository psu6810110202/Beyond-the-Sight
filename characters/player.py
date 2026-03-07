from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
import random
import os
from settings import *

class Player:
    def __init__(self, canvas, x=None, y=None):
        self.canvas = canvas
        self.is_moving = False
        
        # กำหนดตำแหน่งเริ่มต้น (จากพิกัดที่ส่งมา หรือจากค่าเริ่มต้นใน settings)
        if x is not None and y is not None:
            start_x, start_y = x, y
        else:
            start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
            start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
            
        self.x, self.y = start_x, start_y
        self.target_pos = [start_x, start_y]
        self.logic_pos = [start_x, start_y]
        self.current_speed = WALK_SPEED
        self.turn_delay = 0  # <--- เพิ่มตัวหน่วงเวลาตอนเปลี่ยนทิศทาง
        self.is_in_home = False # เช็คว่าอยู่ในบ้านหรือไม่เพื่อเปลี่ยนเสียงเดิน
        
        # โหลด Texture
        self.idle_texture = CoreImage(PLAYER_IDLE_IMG).texture
        self.walk_texture = CoreImage(PLAYER_WALK_IMG).texture
        
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
        self.direction = 'up' 
        self.frame_index = 0
        
        # Stamina
        self.stamina = MAX_STAMINA
        self.max_stamina = MAX_STAMINA
        self.exhausted = False

        # สร้าง InstructionGroup เพื่อจัดการการวาดแบบแยกส่วน (สำหรับ Y-sorting)
        self.group = InstructionGroup()
        
        
        self.group.add(Color(1, 1, 1, 1))
        # จุดเกิดตอนแรก
        offset_x = (TILE_SIZE - PLAYER_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect = Rectangle(pos=(self.logic_pos[0] + offset_x, self.logic_pos[1] + offset_y), size=(PLAYER_WIDTH, PLAYER_HEIGHT))
        self.group.add(self.rect)
            
        self.canvas.add(self.group)
            
        self.update_frame()
        self.current_fps = 2
        
        # โหลดเสียงเดิน
        self.walk_sounds = []
        walk_sound_dir = 'assets/sound/walk'
        if os.path.exists(walk_sound_dir):
            for file in os.listdir(walk_sound_dir):
                if file.endswith('.wav'):
                    s = SoundLoader.load(os.path.join(walk_sound_dir, file))
                    if s:
                        s.volume = 0.5
                        self.walk_sounds.append(s)
        
        # โหลดเสียงวิ่ง
        self.run_sounds = self._load_sounds('assets/sound/run', 0.6)
        
        # โหลดเสียงเดินในบ้าน (ไม้)
        self.walk_w_sounds = self._load_sounds('assets/sound/walk_w', 0.5)
        
        # โหลดเสียงวิ่งในบ้าน (ไม้)
        self.run_w_sounds = self._load_sounds('assets/sound/run_w', 0.6)
        
        # โหลดเสียงหอบเมื่อเหนื่อย
        self.breath_sound = SoundLoader.load('assets/sound/breath.wav')
        if self.breath_sound:
            self.breath_sound.loop = True
            self.breath_sound.volume = 0.5
        
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)

    def _load_sounds(self, directory, volume):
        sounds = []
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith('.wav'):
                    s = SoundLoader.load(os.path.join(directory, file))
                    if s:
                        s.volume = volume
                        sounds.append(s)
        return sounds

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
        # ตรวจสอบ state ปัจจุบัน
        is_moving_now = self.is_moving or getattr(self, 'cutscene_mode', False)
        new_state = 'walk' if is_moving_now else 'idle'

        if self.state != new_state:
            self.state = new_state
            if not getattr(self, 'cutscene_mode', False):
                self.frame_index = 0
        
        # บวกเฟรมเสมอในทุกรอบที่ animate ถูกเรียก (ตราบใดที่ไม่ใช่ idle นิ่งๆ)
        if self.state != 'idle' or self.frame_index != 0:
            max_frames = self.anim_config[self.state]['cols']
            self.frame_index = (self.frame_index + 1) % max_frames
            
            # เล่นเสียงเดิน/วิ่ง (ในจังหวะลงเท้า: เฟรม 0 และ 4 ของอนิเมชั่น 8 เฟรม)
            if self.state == 'walk' and self.frame_index in [0, 4]:
                if self.current_speed == RUN_SPEED:
                    sounds = self.run_w_sounds if self.is_in_home else self.run_sounds
                    if sounds: random.choice(sounds).play()
                else:
                    sounds = self.walk_w_sounds if self.is_in_home else self.walk_sounds
                    if sounds: random.choice(sounds).play()
            
        self.update_frame()
        
    def move(self, pressed_keys, npcs=None, reaper=None, map_rects=None):  # เพิ่ม map_rects parameter
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
                        self.start_move(dx, dy, npcs, reaper, map_rects)  # ส่ง npcs, reaper, map_rects ไปด้วย

        # 3. Handling stamina and animation speed
        is_running = 'shift' in pressed_keys and self.is_moving
        self.update_stamina(is_running)
        self.update_animation_speed()
            
        # 4. Return to idle instantly if not moving
        if not self.is_moving and self.state != 'idle':
            # ถ้าอยู่ในคัทซีนและเป็นการเดินต่อเนื่อง ไม่ต้องรีเซตเฟรมเป็น 0 ทุกช่อง
            if not getattr(self, 'cutscene_mode', False):
                self.state = 'idle'
                self.frame_index = 0
                self.update_frame()
            else:
                # ในคัทซีน ให้ค้างท่าเดินไว้จนกว่าจะสั่งหยุดจริงๆ
                pass

    def update_stamina(self, is_running):
        """Manages stamina drain, regeneration, and exhausted state."""
        # Handle exhaustion recovery
        if self.exhausted and self.stamina >= self.max_stamina:
            self.exhausted = False
            if self.breath_sound and self.breath_sound.state == 'play':
                self.breath_sound.stop()

        if is_running and not self.exhausted:
            self.current_speed = RUN_SPEED
            self.stamina = max(0, self.stamina - STAMINA_DRAIN)
            if self.stamina <= 0:
                self.exhausted = True
                if self.breath_sound and self.breath_sound.state != 'play':
                    self.breath_sound.play()
        else:
            self.current_speed = WALK_SPEED
            if self.stamina < self.max_stamina:
                self.stamina = min(self.max_stamina, self.stamina + STAMINA_REGEN)

    def update_animation_speed(self):
        """Sets animation FPS based on movement state and fatigue."""
        if self.is_moving or getattr(self, 'cutscene_mode', False):
            is_running = self.current_speed == RUN_SPEED
            target_fps = 12 if is_running else 8
        else:
            target_fps = 3 if self.stamina < self.max_stamina else 2
        
        if self.current_fps != target_fps:
            self.current_fps = target_fps
            self.anim_event.cancel()
            self.anim_event = Clock.schedule_interval(self.animate, 1.0 / target_fps)

    def get_stamina_ratio(self):
        """Returns current stamina as a 0.0-1.0 ratio."""
        return max(0.0, self.stamina / self.max_stamina)

    def start_move(self, dx, dy, npcs=None, reaper=None, map_rects=None):
        new_x = self.logic_pos[0] + dx
        new_y = self.logic_pos[1] + dy
        
        # ตรวจสอบขอบเขตกำแพงล่องหนของแผนที่ (1600x1600)
        if 0 <= new_x <= MAP_WIDTH - TILE_SIZE and 0 <= new_y <= MAP_HEIGHT - TILE_SIZE:
            # ตรวจสอบกำแพงจากแผนที่
            if map_rects and self.check_map_collision(new_x, new_y, map_rects):
                # print("Cannot move - Wall blocking!") # ปิด log เพื่อไม่ให้รกจอ
                return
                
            # ตรวจสอบการชนกับ NPC
            if npcs and self.check_npc_collision(new_x, new_y, npcs):
                print("Cannot move - NPC blocking!")
                return
            
            # ตรวจสอบการชนกับ Reaper
            if reaper and self.check_reaper_collision(new_x, new_y, reaper):
                print("Cannot move - Reaper blocking!")
                return
            
            
            self.target_pos = [new_x, new_y]
            self.is_moving = True
            
            # บังคับแสดงท่าก้าวขาทันที (โดยเฉพาะเมื่อเดินแค่ 1 ช่อง สล็อตเวลาจะไม่พอให้อนิเมชั่นเล่นเอง)
            if self.state != 'walk':
                self.state = 'walk'
                self.frame_index = 1
                self.update_frame()
            
    def check_map_collision(self, new_x, new_y, map_rects):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับกำแพง (Map tiles) หรือไม่"""
        player_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        for r in map_rects:
            # ใช้ Logic กล่องแบบห้ามซ้อนทับกันเต็มขนาด (ถ้ามากกว่าคือทับ)
            if (player_rect[0] < r[0] + r[2] and
                player_rect[0] + player_rect[2] > r[0] and
                player_rect[1] < r[1] + r[3] and
                player_rect[1] + player_rect[3] > r[1]):
                return True
        return False
    
    def check_npc_collision(self, new_x, new_y, npcs):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับ NPC หรือไม่"""
        player_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        for npc in npcs:
            # ใช้พิกัด x, y ตัวแปรหลักของระบบ Hitbox ใหม่ 
            npc_rect = [npc.x, npc.y, TILE_SIZE, TILE_SIZE]
            
            # ตรวจสอบการชนระหว่างสี่เหลี่ยม
            if (player_rect[0] < npc_rect[0] + npc_rect[2] and
                player_rect[0] + player_rect[2] > npc_rect[0] and
                player_rect[1] < npc_rect[1] + npc_rect[3] and
                player_rect[1] + player_rect[3] > npc_rect[1]):
                print(f"DEBUG: Blocked by NPC physically located at {npc.x}, {npc.y}")
                return True
        
        return False

    def check_reaper_collision(self, new_x, new_y, reaper):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับ Reaper หรือไม่"""
        player_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        reapers = reaper if isinstance(reaper, list) else [reaper]
        for r in reapers:
            if not r: continue
            # ใช้พิกัด x, y ตัวแปรหลักของระบบ Hitbox ใหม่ 
            reaper_rect = [r.x, r.y, TILE_SIZE, TILE_SIZE]
            
            # ตรวจสอบการชนระหว่างสี่เหลี่ยม
            if (player_rect[0] < reaper_rect[0] + reaper_rect[2] and
                player_rect[0] + player_rect[2] > reaper_rect[0] and
                player_rect[1] < reaper_rect[1] + reaper_rect[3] and
                player_rect[1] + player_rect[3] > reaper_rect[1]):
                return True
        
        return False

    def continue_move(self):
        """เลื่อนตำแหน่งผู้เล่นเข้าหาเป้าหมาย (Grid-based)"""
        for i in range(2): # x, y
            if self.logic_pos[i] < self.target_pos[i]:
                self.logic_pos[i] = min(self.logic_pos[i] + self.current_speed, self.target_pos[i])
            elif self.logic_pos[i] > self.target_pos[i]:
                self.logic_pos[i] = max(self.logic_pos[i] - self.current_speed, self.target_pos[i])

        self.x, self.y = self.logic_pos
        self.sync_graphics_pos()
        if self.logic_pos == self.target_pos:
            self.is_moving = False

    def sync_graphics_pos(self):
        """อัปเดตตำแหน่งกราฟิกให้ตรงกับ Logic"""
        ox = (TILE_SIZE - PLAYER_WIDTH) / 2
        oy = TILE_SIZE / 2
        self.rect.pos = (self.logic_pos[0] + ox, self.logic_pos[1] + oy)

    def interact(self, npcs, reaper):
        """
        Check for interaction. (Now simplified as main.py handles the core logic)
        """
        # Note: เราใช้ _get_interaction_target ของ main.py เป็นหลักแล้ว
        # เมธอดนี้อาจเหลือไว้เพียงเพื่อให้รองรับโค้ดเก่าในบางจุด
        return None, None, None, 0, 0

    def cleanup(self):
        """หยุดเสียงทั้งหมดของ Player"""
        all_sound_groups = [
            self.walk_sounds, self.run_sounds, 
            self.walk_w_sounds, self.run_w_sounds
        ]
        
        for group in all_sound_groups:
            for s in group:
                if s and s.state == 'play':
                    s.stop()
                    
        if hasattr(self, 'breath_sound') and self.breath_sound:
            if self.breath_sound.state == 'play':
                self.breath_sound.stop()
