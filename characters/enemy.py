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
        self.is_chasing = False
        
        # Animation properties
        self.state = 'idle'
        self.frame_index = 0
        self.current_fps = 8
        self.direction_change_timer = 0
        self.direction_change_interval = 3.0
        self.directions = ['down', 'left', 'right', 'up']
        
        # Load textures and configure spritesheets
        self._init_assets(enemy_type)
        
        # Initialize graphics on canvas
        self._init_graphics()
        
        # Schedule updates
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.current_fps)
            
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
            if new_state == 'idle':
                self.update_frame()
                return
        else:
            max_frames = self.anim_config[self.state]['cols']
            self.frame_index = (self.frame_index + 1) % max_frames
            
        self.update_frame()
        self.update_animation_speed()
            
    def update_animation_speed(self):
        """Sets animation FPS based on movement state and fatigue like Player."""
        if self.is_moving:
            target_fps = 8  # Walking speed (same as Player)
        else:
            target_fps = 2  # Idle speed (same as Player)
        
        if self.current_fps != target_fps:
            self.current_fps = target_fps
            self.anim_event.cancel()
            self.anim_event = Clock.schedule_interval(self.animate, 1.0 / target_fps)
            
    def update(self, dt, player_pos, reaper_pos=None, map_rects=None):
        """Main update loop called by the game logic."""
        if self.is_fading:
            self.is_chasing = False
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
                self.is_chasing = False
                self.stun_timer -= dt
                if self.stun_timer <= 0:
                    self.is_stunned = False
                    self.color_instr.rgb = (1, 1, 1) # Reset color
                return # Don't move or chase while stunned

            # Decide whether to chase the player
            dist = self.calculate_distance(player_pos)
            if dist <= self.detection_radius and self.has_line_of_sight(player_pos, map_rects):
                self.is_chasing = True
                self.chase_player_grid(player_pos, reaper_pos, map_rects)
            else:
                self.is_chasing = False
        else:
            # ขณะเดินไปเป้าหมาย (is_moving) ถ้ายังอยู่ในรัศมีและมองเห็น ก็ถือว่ายังไล่อยู่
            dist = self.calculate_distance(player_pos)
            self.is_chasing = dist <= self.detection_radius and self.has_line_of_sight(player_pos, map_rects)
        
    def calculate_distance(self, target_pos):
        """Calculates distance between enemy and target (เหมือน player)."""
        return math.sqrt((target_pos[0] - self.logic_pos[0])**2 + (target_pos[1] - self.logic_pos[1])**2)
        
    def chase_player_grid(self, player_pos, reaper_pos=None, map_rects=None):
        """Implements grid-based chasing logic with safe zone detection."""
        # เมื่อไล่ล่า เราจะยกเลิกการหน่วงเวลาเพื่อให้เข้าหาผู้เล่นได้ทันที
        self.turn_delay = 0

        dx = player_pos[0] - self.logic_pos[0]
        dy = player_pos[1] - self.logic_pos[1]
        # พยายามเดินในแกนที่ระยะห่างมากที่สุดก่อน
        primary_axis_blocked = False
        if abs(dy) >= abs(dx) and abs(dy) > 0:
            move_y = TILE_SIZE if dy > 0 else -TILE_SIZE
            new_dir = 'up' if dy > 0 else 'down'
            
            # เช็คว่าแกน Y เดินได้ไหม
            new_x = self.logic_pos[0]
            new_y = self.logic_pos[1] + move_y
            if self._is_pos_safe_and_clear(new_x, new_y, reaper_pos, map_rects):
                self.direction = new_dir
                self.frame_index = 0
                self.start_move(0, move_y)
                return
            primary_axis_blocked = True
            
        if abs(dx) > 0:
            move_x = TILE_SIZE if dx > 0 else -TILE_SIZE
            new_dir = 'right' if dx > 0 else 'left'
            
            # เช็คว่าแกน X เดินได้ไหม
            new_x = self.logic_pos[0] + move_x
            new_y = self.logic_pos[1]
            if self._is_pos_safe_and_clear(new_x, new_y, reaper_pos, map_rects):
                self.direction = new_dir
                self.frame_index = 0
                self.start_move(move_x, 0)
                return
            
        # ถ้าแกน X เป็นแกนหลักแต่โดนบล็อก ให้มาลองแกน Y ที่เมื่อกี้ข้ามไป
        if not primary_axis_blocked and abs(dy) > 0:
            move_y = TILE_SIZE if dy > 0 else -TILE_SIZE
            new_dir = 'up' if dy > 0 else 'down'
            new_x = self.logic_pos[0]
            new_y = self.logic_pos[1] + move_y
            if self._is_pos_safe_and_clear(new_x, new_y, reaper_pos, map_rects):
                self.direction = new_dir
                self.frame_index = 0
                self.start_move(0, move_y)
                return

    def _is_pos_safe_and_clear(self, new_x, new_y, reaper_pos, map_rects):
        """ตรวจสอบว่าตำแหน่งใหม่ปลอดภัยจาก Reaper และไม่มีกำแพงขวาง"""
        # 1. เช็คขอบเขตแผนที่
        if not (0 <= new_x <= MAP_WIDTH - TILE_SIZE and 0 <= new_y <= MAP_HEIGHT - TILE_SIZE):
            return False
            
        # 2. เช็ค Safe Zone (Reaper) - ลบออกเพื่อให้ศัตรูเดินเข้าไปชนวงและหายไปได้
        # (เราปล่อยให้ main.py จัดการลบศัตรูเมื่อเข้าใกล้วงแทน)
                
        # 3. เช็คกำแพง
        if map_rects and self.check_map_collision(new_x, new_y, map_rects):
            return False
            
        return True

    def start_move(self, dx, dy):
        """Sets the target position and begins movement (เหมือน player)."""
        self.target_pos = [self.logic_pos[0] + dx, self.logic_pos[1] + dy]
        self.is_moving = True

    def continue_move(self):
        """เลื่อนตำแหน่งศัตรูเข้าหาเป้าหมายอย่างลื่นไหล"""
        for i in range(2):
            if self.logic_pos[i] < self.target_pos[i]:
                self.logic_pos[i] = min(self.logic_pos[i] + self.speed, self.target_pos[i])
            elif self.logic_pos[i] > self.target_pos[i]:
                self.logic_pos[i] = max(self.logic_pos[i] - self.speed, self.target_pos[i])
        
        ox = (TILE_SIZE - ENEMY_WIDTH) / 2
        oy = TILE_SIZE / 2
        self.rect.pos = (self.logic_pos[0] + ox, self.logic_pos[1] + oy)
        
        if self.logic_pos == self.target_pos:
            self.is_moving = False
            
    def check_map_collision(self, new_x, new_y, map_rects):
        """ตรวจสอบว่าตำแหน่งใหม่จะชนกับกำแพง (Map tiles) หรือไม่"""
        enemy_rect = [new_x, new_y, TILE_SIZE, TILE_SIZE]
        
        for r in map_rects:
            # ใช้ Logic กล่องแบบห้ามซ้อนทับกันเต็มขนาด (ถ้ามากกว่าคือทับ)
            if (enemy_rect[0] < r[0] + r[2] and
                enemy_rect[0] + enemy_rect[2] > r[0] and
                enemy_rect[1] < r[1] + r[3] and
                enemy_rect[1] + enemy_rect[3] > r[1]):
                return True
        return False

    def check_player_collision_logic(self, player_pos, tile_size):
        """Check for collision with player using logic coordinates"""
        buffer = 4
        return (self.logic_pos[0] < player_pos[0] + tile_size + buffer and
                self.logic_pos[0] + TILE_SIZE + buffer > player_pos[0] and
                self.logic_pos[1] < player_pos[1] + tile_size + buffer and
                self.logic_pos[1] + TILE_SIZE + buffer > player_pos[1])
            
    def has_line_of_sight(self, target_pos, map_rects):
        """ตรวจสอบว่ามีกำแพงกั้นระหว่างศัตรูกับผู้เล่นหรือไม่ (เช็คหลายจุดเพื่อให้เห็นตามหัวมุมได้ดีขึ้น)"""
        if not map_rects:
            return True
            
        # จุดเช็คของศัตรู (กลาง + 4 มุมหดเข้ามา 2 พิกเซลเพื่อไม่ให้ติดขอบกำแพงตัวเอง)
        ex, ey = self.logic_pos
        e_pts = [
            (ex + TILE_SIZE / 2, ey + TILE_SIZE / 2),
            (ex + 2, ey + 2),
            (ex + TILE_SIZE - 2, ey + 2),
            (ex + 2, ey + TILE_SIZE - 2),
            (ex + TILE_SIZE - 2, ey + TILE_SIZE - 2)
        ]
        
        # จุดเช็คของผู้เล่น (กลาง + 4 มุมหดเข้ามา 2 พิกเซล)
        px, py = target_pos
        p_pts = [
            (px + TILE_SIZE / 2, py + TILE_SIZE / 2),
            (px + 2, py + 2),
            (px + TILE_SIZE - 2, py + 2),
            (px + 2, py + TILE_SIZE - 2),
            (px + TILE_SIZE - 2, py + TILE_SIZE - 2)
        ]
        
        # ตรวจสอบทุกลำแสงที่เป็นไปได้ (ถ้ามีสักเส้นที่ผ่านได้ ถือว่าเห็นกัน)
        for e_pt in e_pts:
            for p_pt in p_pts:
                x1, y1 = e_pt
                x2, y2 = p_pt
                
                blocked = False
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                
                for r in map_rects:
                    rx, ry, rw, rh = r
                    if rx + rw < min_x or rx > max_x or ry + rh < min_y or ry > max_y:
                        continue
                        
                    if self.line_intersects_rect(x1, y1, x2, y2, r):
                        blocked = True
                        break
                
                if not blocked:
                    return True # เห็นแล้วจากมุมนี้!
                    
        return False # บล็อกมิดทุกทิศทาง

    def line_intersects_rect(self, x1, y1, x2, y2, rect):
        """ตรวจสอบว่าเส้นตรงตัดกับสี่เหลี่ยมหรือไม่"""
        rx, ry, rw, rh = rect
        # ขอบทั้ง 4 ของสี่เหลี่ยม
        edges = [
            ((rx, ry), (rx + rw, ry)),           # ล่าง
            ((rx + rw, ry), (rx + rw, ry + rh)), # ขวา
            ((rx + rw, ry + rh), (rx, ry + rh)), # บน
            ((rx, ry + rh), (rx, ry))            # ซ้าย
        ]
        
        for p3, p4 in edges:
            if self.segments_intersect((x1, y1), (x2, y2), p3, p4):
                return True
        return False

    def segments_intersect(self, p1, p2, p3, p4):
        """อัลกอริทึม CCW เพื่อเช็คว่าเส้นตรง 2 เส้นตัดกันหรือไม่"""
        def ccw(A, B, C):
            val = (C[1] - A[1]) * (B[0] - A[0]) - (B[1] - A[1]) * (C[0] - A[0])
            if abs(val) < 1e-9: return 0 # ขนานหรือทับ
            return 1 if val > 0 else -1

        res1 = ccw(p1, p3, p4) != ccw(p2, p3, p4)
        res2 = ccw(p1, p2, p3) != ccw(p1, p2, p4)
        return res1 and res2

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
