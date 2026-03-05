from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math
import random

class Enemy:
    """
    Renders and manages Enemy characters.
    Enemies chase the player unless they enter a safe zone around the Reaper.
    """
    def __init__(self, canvas, x, y, enemy_id, enemy_type=1):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.id = enemy_id
        self.enemy_type = enemy_type

        # Stats and behavior
        self.speed = ENEMY_SPEED
        self.detection_radius = ENEMY_DETECTION_RADIUS
        self.safe_zone_radius = SAFE_ZONE_RADIUS
        
        # Fade & Stun system
        self.is_stunned = False
        self.stun_timer = 0
        self.is_fading = False
        self.fading_done = False
        self.alpha = 1.0
        
        # Position system (เหมือน player)
        self.logic_pos = [x, y]  # ตำแหน่ง 32x32 ทางตรรกะสำหรับการคำนวณเดินตาม Grid
        self.is_moving = False
        self.target_pos = [x, y]
        self.turn_delay = 0
        self.direction = 'down'
        
        # Animation properties
        self.state = 'idle'
        self.frame_index = 0
        self.animation_fps = 8
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0
        self.directions = ['down', 'left', 'right', 'up']
        
        # Load textures and configure spritesheets
        self._init_assets(enemy_type)
        
        # Initialize graphics on canvas
        self._init_graphics()
        
        # Schedule updates
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.animation_fps)
            
    def _init_assets(self, enemy_type):
        """Loads textures and sets up animation configuration based on enemy types in settings.py."""
        config = ENEMY_TYPES.get(enemy_type, ENEMY_TYPES[1])
        
        try:
            self.idle_texture = CoreImage(config['idle']['path']).texture
            self.walk_texture = CoreImage(config['walk']['path']).texture
            self.anim_config = {
                'idle': {'tex': self.idle_texture, 'cols': config['idle']['cols'], 'rows': config['idle']['rows']},
                'walk': {'tex': self.walk_texture, 'cols': config['walk']['cols'], 'rows': config['walk']['rows']}
            }
        except Exception as e:
            print(f"Error loading Enemy{enemy_type} textures: {e}")
            self.idle_texture = self.walk_texture = None
            self.anim_config = {
                'idle': {'tex': None, 'cols': 1, 'rows': 4},
                'walk': {'tex': None, 'cols': 1, 'rows': 4}
            }

        # Row mapping (แยกแถวระหว่าง idle และ walk)
        idle_rows = {'down': 1, 'left': 3, 'right': 2, 'up': 0}
        walk_rows = {'down': 1, 'left': 3, 'right': 2, 'up': 0}
        self.anim_row_map = {'idle': idle_rows, 'walk': walk_rows}

    def _init_graphics(self):
        """Create the Kivy canvas instructions for the enemy."""
        self.group = InstructionGroup()
        
        # Sprite appearance
        self.color_instr = Color(1, 1, 1, 1)
        if not self.idle_texture:
            self.color_instr.rgb = (1, 0, 0)
        self.group.add(self.color_instr)
        
        offset_x = (TILE_SIZE - ENEMY_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect = Rectangle(pos=(self.logic_pos[0] + offset_x, self.logic_pos[1] + offset_y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))
        self.group.add(self.rect)
        self.canvas.add(self.group)

    def destroy(self):
        """Cleans up canvas instructions and events when the enemy is removed."""
        self.canvas.remove(self.group)
        self.anim_event.cancel()
            
    def update_frame(self):
        """Updates the texture region (tex_coords) based on state, direction, and frame."""
        config = self.anim_config.get(self.state)
        if not config or not config['tex']:
            self.rect.texture = None
            return
            
        tex = config['tex']
        w = 1.0 / config['cols']
        h = 1.0 / config['rows']
        
        u = self.frame_index * w
        row_index = self.anim_row_map[self.state].get(self.direction, 0)
        
        # Standardize vertical coordinate (Kivy textures often need Y-flip correction)
        v = 1.0 - ((row_index + 1) * h)
        
        self.rect.texture = tex
        self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)
    
    def animate(self, dt):
        """Handles state transitions and frame updates."""
        new_state = 'walk' if self.is_moving else 'idle'
        if self.state != new_state:
            self.state = new_state
            self.frame_index = 0
        
        max_frames = self.anim_config[self.state]['cols']
        self.frame_index = (self.frame_index + 1) % max_frames
        self.update_frame()
            
    def update(self, dt, player_pos, reaper_pos=None):
        """Main update loop called by the game logic."""
        if self.is_fading:
            self.alpha -= dt * 1.5 # ปรับความเร็วในการจางหาย
            if self.alpha <= 0:
                self.alpha = 0
                self.fading_done = True
            self.color_instr.a = self.alpha
            return

        if self.is_moving:
            self.continue_move()
            
        if not self.is_moving:
            # Randomly change direction while idle
            self.direction_change_timer += dt
            if self.direction_change_timer >= self.direction_change_interval:
                self.direction_change_timer = 0
                available_dirs = [d for d in self.directions if d != self.direction]
                self.direction = random.choice(available_dirs)
                self.frame_index = 0

            # Stun check
            if self.is_stunned:
                self.stun_timer -= dt
                if self.stun_timer <= 0:
                    self.is_stunned = False
                    self.color_instr.rgb = (1, 1, 1) # Reset color
                return # Don't move or chase while stunned

            # Decide whether to chase the player
            dist = self.calculate_distance(player_pos)
            if dist <= self.detection_radius:
                self.chase_player_grid(player_pos, reaper_pos)
        
    def calculate_distance(self, target_pos):
        """Calculates distance between enemy and target (เหมือน player)."""
        return math.sqrt((target_pos[0] - self.logic_pos[0])**2 + (target_pos[1] - self.logic_pos[1])**2)
        
    def chase_player_grid(self, player_pos, reaper_pos=None):
        """Implements grid-based chasing logic with safe zone detection."""
        # เมื่อไล่ล่า เราจะยกเลิกการหน่วงเวลาเพื่อให้เข้าหาผู้เล่นได้ทันที
        self.turn_delay = 0

        dx = player_pos[0] - self.logic_pos[0]
        dy = player_pos[1] - self.logic_pos[1]
        move_x, move_y = 0, 0
        new_dir = self.direction
        
        # เลือกแกนที่จะเดิน โดยให้ความสำคัญกับแกนตั้ง (Vertical) เล็กน้อยเพื่อลดอาการลังเล (Zig-zag)
        if abs(dy) >= abs(dx) and abs(dy) > 0:
            move_y = TILE_SIZE if dy > 0 else -TILE_SIZE
            new_dir = 'up' if dy > 0 else 'down'
        elif abs(dx) > 0:
            move_x = TILE_SIZE if dx > 0 else -TILE_SIZE
            new_dir = 'right' if dx > 0 else 'left'
                
        if move_x != 0 or move_y != 0:
            # หันหน้าไปตามทิศทางทันที
            self.direction = new_dir
            self.frame_index = 0
            
            # Check safe zone
            new_x = self.logic_pos[0] + move_x
            new_y = self.logic_pos[1] + move_y
            
            if reaper_pos:
                r_center_x, r_center_y = reaper_pos[0] + TILE_SIZE/2, reaper_pos[1] + TILE_SIZE/2
                e_center_x, e_center_y = new_x + TILE_SIZE/2, new_y + TILE_SIZE/2
                dist_to_reaper = math.sqrt((e_center_x - r_center_x)**2 + (e_center_y - r_center_y)**2)
                
                if dist_to_reaper < self.safe_zone_radius:
                    self.start_fade()
                    return # Stop and fade if too close to the Reaper
            
            self.start_move(move_x, move_y)

    def start_move(self, dx, dy):
        """Sets the target position and begins movement (เหมือน player)."""
        self.target_pos = [self.logic_pos[0] + dx, self.logic_pos[1] + dy]
        self.is_moving = True

    def continue_move(self):
        """Smoothly interpolates movement towards the target grid position (เหมือน player)."""
        cur_x, cur_y = self.logic_pos
        tar_x, tar_y = self.target_pos

        if cur_x < tar_x: cur_x = min(cur_x + self.speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.speed, tar_y)

        self.logic_pos = [cur_x, cur_y]
        
        # อัปเดตกราฟิกสี่เหลี่ยมตามพิกัด x, y (เหมือน player)
        offset_x = (TILE_SIZE - ENEMY_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect.pos = (cur_x + offset_x, cur_y + offset_y)
        
        self.rect.pos = (cur_x + offset_x, cur_y + offset_y)
        
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False
            
    def check_player_collision_logic(self, player_pos, tile_size):
        """Check for collision with player using logic coordinates"""
        buffer = 4
        return (self.logic_pos[0] < player_pos[0] + tile_size + buffer and
                self.logic_pos[0] + TILE_SIZE + buffer > player_pos[0] and
                self.logic_pos[1] < player_pos[1] + tile_size + buffer and
                self.logic_pos[1] + TILE_SIZE + buffer > player_pos[1])
            
    def stun(self, duration=3.0):
        """Stuns the enemy for a specified duration."""
        if self.is_fading: return
        self.is_stunned = True
        self.stun_timer = duration
        self.is_moving = False
        self.color_instr.rgb = (0.4, 0.4, 0.4) # Dark greyish tint for stun effect
        self.update_frame()

    def start_fade(self):
        """เริ่มกระบวนการจางหาย"""
        self.is_fading = True
        self.is_moving = False
        self.is_stunned = False # ยกเลิกสถานะอื่น
