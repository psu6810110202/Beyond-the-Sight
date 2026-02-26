from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *

class Player:
    def __init__(self, canvas):
        self.canvas = canvas
        self.is_moving = False
        self.target_pos = [96, 96]
        self.logic_pos = [96, 96]  # ตำแหน่ง 32x32 ทางตรรกะสำหรับการคำนวณเดินตาม Grid
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
            # DEBUG: แถบสีเหลืองจำลองแสดงว่า Hitbox (จุดปะทะจริง) มีขนาดแค่ 32x32 ไม่เกิน 1 ช่อง
            Color(1, 1, 0, 0.3)
            self.debug_rect = Rectangle(pos=self.logic_pos, size=(TILE_SIZE, TILE_SIZE))
            
            Color(1, 1, 1, 1)
            # จุดเกิดตอนแรก จัดแกน X ให้ตัวละครกึ่งกลางบล็อก และดันแกน Y ขึ้นเล็กน้อยเพื่อให้เท้าแตะกลางแผ่น
            offset_x = (TILE_SIZE - PLAYER_WIDTH) / 2
            offset_y = TILE_SIZE / 2  # เผื่อพื้นที่ว่างด้านล่างของรูป เพื่อดันให้ตัวละครขึ้นมายืนตรงกลางช่องพอดี
            self.rect = Rectangle(pos=(self.logic_pos[0] + offset_x, self.logic_pos[1] + offset_y), size=(PLAYER_WIDTH, PLAYER_HEIGHT))
            
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
        
    def move(self, pressed_keys, npcs=None, reaper=None):  # เพิ่ม npcs parameter
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
                        self.start_move(dx, dy, npcs, reaper)  # ส่ง npcs และ reaper ไปด้วย

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

    def start_move(self, dx, dy, npcs=None, reaper=None):
        new_x = self.logic_pos[0] + dx
        new_y = self.logic_pos[1] + dy
        
        # ตรวจสอบขอบเขตหน้าต่าง
        if 0 <= new_x <= WINDOW_WIDTH - TILE_SIZE and 0 <= new_y <= WINDOW_HEIGHT - TILE_SIZE:
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
    
    def check_npc_collision(self, new_x, new_y, npcs):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับ NPC หรือไม่"""
        player_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        for npc in npcs:
            # ใช้พื้นที่บล็อคของ NPC เป็น 1x1 (32x32) เหมือน Player
            # คำนวณตำแหน่งศูนย์กลางของ NPC แล้วลดขนาดลงเป็น 1x1
            npc_center_x = npc.x + (NPC_WIDTH - TILE_SIZE) / 2
            npc_center_y = npc.y + (NPC_HEIGHT - TILE_SIZE) / 2
            npc_rect = [npc_center_x, npc_center_y, TILE_SIZE, TILE_SIZE]
            
            # ตรวจสอบการชนระหว่างสี่เหลี่ยม
            if (player_rect[0] < npc_rect[0] + npc_rect[2] and
                player_rect[0] + player_rect[2] > npc_rect[0] and
                player_rect[1] < npc_rect[1] + npc_rect[3] and
                player_rect[1] + player_rect[3] > npc_rect[1]):
                return True
        
        return False

    def check_reaper_collision(self, new_x, new_y, reaper):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับ Reaper หรือไม่"""
        player_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        # ใช้พื้นที่บล็อคของ Reaper เป็น 1x1 (32x32) เหมือน Player
        # คำนวณตำแหน่งศูนย์กลางของ Reaper แล้วลดขนาดลงเป็น 1x1
        reaper_center_x = reaper.x + (REAPER_WIDTH - TILE_SIZE) / 2
        reaper_center_y = reaper.y + (REAPER_HEIGHT - TILE_SIZE) / 2
        reaper_rect = [reaper_center_x, reaper_center_y, TILE_SIZE, TILE_SIZE]
        
        # ตรวจสอบการชนระหว่างสี่เหลี่ยม
        if (player_rect[0] < reaper_rect[0] + reaper_rect[2] and
            player_rect[0] + player_rect[2] > reaper_rect[0] and
            player_rect[1] < reaper_rect[1] + reaper_rect[3] and
            player_rect[1] + player_rect[3] > reaper_rect[1]):
            return True
        
        return False

    def continue_move(self):
        cur_x, cur_y = self.logic_pos
        tar_x, tar_y = self.target_pos

        # ใช้ current_speed แทน PLAYER_SPEED เพื่อให้วิ่งเร็วขึ้นจริง
        if cur_x < tar_x: cur_x = min(cur_x + self.current_speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.current_speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.current_speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.current_speed, tar_y)

        self.logic_pos = [cur_x, cur_y]
        
        # จัดตำแหน่งรูปสไปรท์ใหม่เวลาเดิน
        offset_x = (TILE_SIZE - PLAYER_WIDTH) / 2
        offset_y = TILE_SIZE / 2  # เผื่อพื้นที่ว่างด้านล่างของรูป เพื่อดันให้ตัวละครขึ้นมายืนตรงกลางช่องพอดี
        self.rect.pos = (cur_x + offset_x, cur_y + offset_y)
        
        # อัปเดตกรอบเช็คการชน (Hitbox) สีเหลืองตามการเดินให้เห็นชัดๆ ว่าแค่ 1 ช่อง
        self.debug_rect.pos = self.logic_pos
        
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False