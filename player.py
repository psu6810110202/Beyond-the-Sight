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
        
        # โหลด Texture
        self.idle_texture = CoreImage('assets/players/Player_idle.png').texture
        self.walk_texture = CoreImage('assets/players/Player_walk.png').texture
        
        # ตั้งชื่อให้ตรงกันทั้งหมด (ใช้ anim_config และ key 'tex')
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': 3, 'rows': 4},
            'walk': {'tex': self.walk_texture, 'cols': 8, 'rows': 4}
        }
        
        # Mapping Direction to Row Index for each state
        # Adjust these numbers if the Idle animation is still wrong!
        self.anim_row_map = {
            'idle': {
                'up': 0, 
                'down': 1, 
                'left': 2, 
                'right': 3
            },
            'walk': {
                'up': 0, 
                'down': 1, 
                'left': 2, 
                'right': 3
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
            self.rect = Rectangle(pos=(96, 96), size=(TILE_SIZE * 2, TILE_SIZE * 2))
            
            # Stamina Bar
            Color(0, 1, 0, 1)
            self.stamina_bar = Rectangle(pos=(10, 10), size=(0, 5))
            
        self.update_frame()
        Clock.schedule_interval(self.animate, 0.12)

    def update_frame(self):
        # เรียกใช้ตัวแปรที่ชื่อตรงกัน
        config = self.anim_config[self.state]
        w = 1.0 / config['cols']
        h = 1.0 / config['rows']
        
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
        # เปลี่ยน state ตามการเคลื่อนที่
        self.state = 'walk' if self.is_moving else 'idle'
        
        max_frames = self.anim_config[self.state]['cols']
        self.frame_index = (self.frame_index + 1) % max_frames
        self.update_frame()
        
    def move(self, pressed_keys):
        # ระบบวิ่งและ Stamina
        is_running = 'shift' in pressed_keys and self.is_moving
        if is_running and self.stamina > 0:
            self.current_speed = RUN_SPEED
            self.stamina -= STAMINA_DRAIN
        else:
            self.current_speed = WALK_SPEED
            if self.stamina < self.max_stamina:
                self.stamina += STAMINA_REGEN

        if not self.is_moving:
            dx, dy = 0, 0
            if 'w' in pressed_keys or 'up' in pressed_keys: 
                dy = TILE_SIZE; self.direction = 'up' 
            elif 's' in pressed_keys or 'down' in pressed_keys: 
                dy = -TILE_SIZE; self.direction = 'down' 
            elif 'a' in pressed_keys or 'left' in pressed_keys: 
                dx = -TILE_SIZE; self.direction = 'left' 
            elif 'd' in pressed_keys or 'right' in pressed_keys: 
                dx = TILE_SIZE; self.direction = 'right'

            if dx != 0 or dy != 0:
                self.start_move(dx, dy)
        else:
            self.continue_move()

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