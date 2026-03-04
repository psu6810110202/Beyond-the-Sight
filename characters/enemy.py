from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math
import random

ENEMY_START_POSITIONS = [
    (1280, 240), 
    (800, 800)
]

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
        """Loads textures and sets up animation configuration based on enemy type."""
        try:
            if enemy_type == 1:
                self.idle_texture = CoreImage('assets/characters/Enemy/Enemy1_idle.png').texture
                self.walk_texture = CoreImage('assets/characters/Enemy/Enemy1_walk.png').texture
                self.anim_config = {
                    'idle': {'tex': self.idle_texture, 'cols': 1, 'rows': 4},
                    'walk': {'tex': self.walk_texture, 'cols': 3, 'rows': 4}
                }
            else: # enemy_type 2
                self.idle_texture = CoreImage('assets/characters/Enemy/Enemy2_idle.png').texture
                self.walk_texture = self.idle_texture # Re-use for type 2
                self.anim_config = {
                    'idle': {'tex': self.idle_texture, 'cols': 1, 'rows': 4},
                    'walk': {'tex': self.walk_texture, 'cols': 1, 'rows': 4}
                }
        except Exception as e:
            print(f"Error loading Enemy{enemy_type} textures: {e}")
            self.idle_texture = self.walk_texture = None
            self.anim_config = {
                'idle': {'tex': None, 'cols': 1, 'rows': 4},
                'walk': {'tex': None, 'cols': 1, 'rows': 4}
            }

        # Row mapping (matches standard spritesheet order)
        rows = {'down': 2, 'left': 0, 'right': 1, 'up': 3}
        self.anim_row_map = {'idle': rows, 'walk': rows}

    def _init_graphics(self):
        """Create the Kivy canvas instructions for the enemy."""
        with self.canvas:
            # DEBUG: Hitbox visualization
            Color(1, 1, 0, 0.2)
            self.debug_rect = Rectangle(pos=(self.x, self.y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))
            
            # Sprite appearance
            if self.idle_texture:
                Color(1, 1, 1, 1)
            else:
                Color(1, 0, 0, 1) # Fallback to red
            
            self.rect = Rectangle(pos=(self.x, self.y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))

    def destroy(self):
        """Cleans up canvas instructions and events when the enemy is removed."""
        self.canvas.remove(self.debug_rect)
        self.canvas.remove(self.rect)
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
        if self.is_moving:
            self.continue_move()
        else:
            # Randomly change direction while idle
            self.direction_change_timer += dt
            if self.direction_change_timer >= self.direction_change_interval:
                self.direction_change_timer = 0
                available_dirs = [d for d in self.directions if d != self.direction]
                self.direction = random.choice(available_dirs)
                self.frame_index = 0

            # Decide whether to chase the player
            dist = self.calculate_distance(player_pos)
            if dist <= self.detection_radius:
                self.chase_player_grid(player_pos, reaper_pos)
                    
        # Sync visuals
        self.rect.pos = (self.x, self.y)
        self.debug_rect.pos = (self.x, self.y)
        
    def calculate_distance(self, target_pos):
        """Calculates distance between enemy and target."""
        return math.sqrt((target_pos[0] - self.x)**2 + (target_pos[1] - self.y)**2)
        
    def chase_player_grid(self, player_pos, reaper_pos=None):
        """Implements grid-based chasing logic with safe zone detection."""
        if self.turn_delay > 0:
            self.turn_delay -= 1
            return

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        move_x, move_y = 0, 0
        new_dir = self.direction
        
        # Determine movement direction based on largest axis distance
        if abs(dx) > abs(dy):
            move_x = TILE_SIZE if dx > 0 else -TILE_SIZE
            new_dir = 'right' if dx > 0 else 'left'
        elif abs(dy) > 0:
            move_y = TILE_SIZE if dy > 0 else -TILE_SIZE
            new_dir = 'up' if dy > 0 else 'down'
                
        if move_x != 0 or move_y != 0:
            if self.direction != new_dir:
                # Require a brief pause when changing directions
                self.direction = new_dir
                self.frame_index = 0
                self.turn_delay = 6 
            else:
                # Check for safe zone entry
                new_x, new_y = self.x + move_x, self.y + move_y
                if reaper_pos:
                    r_center_x, r_center_y = reaper_pos[0] + TILE_SIZE/2, reaper_pos[1] + TILE_SIZE/2
                    e_center_x, e_center_y = new_x + ENEMY_WIDTH/2, new_y + ENEMY_HEIGHT/2
                    dist_to_reaper = math.sqrt((e_center_x - r_center_x)**2 + (e_center_y - r_center_y)**2)
                    
                    if dist_to_reaper < self.safe_zone_radius:
                        return # Stop if too close to the Reaper
                
                self.start_move(move_x, move_y)

    def start_move(self, dx, dy):
        """Sets the target position and begins movement."""
        self.target_pos = [self.x + dx, self.y + dy]
        self.is_moving = True

    def continue_move(self):
        """Smoothly interpolates movement towards the target grid position."""
        tx, ty = self.target_pos
        
        if self.x < tx: self.x = min(self.x + self.speed, tx)
        elif self.x > tx: self.x = max(self.x - self.speed, tx)
        
        if self.y < ty: self.y = min(self.y + self.speed, ty)
        elif self.y > ty: self.y = max(self.y - self.speed, ty)
        
        if self.x == tx and self.y == ty:
            self.is_moving = False
            
    def check_player_collision_logic(self, player_pos, tile_size):
        """Check for collision with player using logic coordinates."""
        return (self.x < player_pos[0] + tile_size and
                self.x + ENEMY_WIDTH > player_pos[0] and
                self.y < player_pos[1] + tile_size and
                self.y + ENEMY_HEIGHT > player_pos[1])
