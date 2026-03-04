from kivy.graphics import Rectangle, Color, Ellipse, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from settings import *
import math
import random

REAPER_START_POS = (1168, 80)

class Reaper:
    """
    Renders and manages the Reaper character.
    The Reaper provides a safe zone for the player and handles interactions.
    """
    def __init__(self, canvas, x=None, y=None):
        self.canvas = canvas
        self.x = x if x is not None else REAPER_START_POS[0]
        self.y = y if y is not None else REAPER_START_POS[1]
        
        # Appearance configuration
        self.image_path = REAPER_IMG
        self.cols = 1
        self.rows = 4
        
        # Spritesheet row mapping for idle state
        self.anim_row_map = {
            'idle': {
                'down': 3, 
                'left': 0, 
                'right': 1, 
                'up': 2
            }
        }
        
        # Load texture with fallback
        try:
            self.idle_texture = CoreImage(self.image_path).texture
        except Exception as e:
            print(f"Error loading Reaper texture: {e}")
            self.idle_texture = None
        
        # Animation data
        self.anim_config = {
            'idle': {'tex': self.idle_texture, 'cols': self.cols, 'rows': self.rows}
        }
        self.state = 'idle'
        self.direction = 'left'
        self.frame_index = 0
        self.animation_fps = 1
        
        # Behavior and Movement
        self.speed = REAPER_SPEED
        self.target_pos = [self.x, self.y]
        self.is_moving = False
        self.safe_zone_radius = SAFE_ZONE_RADIUS
        
        # Graphics initialization
        self._init_graphics()
        
        # Schedule animation and update initial frame
        self.update_frame()
        self.anim_event = Clock.schedule_interval(self.animate, 1.0 / self.animation_fps)
    
    def _init_graphics(self):
        """Create the Kivy canvas instructions for the Reaper."""
        self.group = InstructionGroup()
        
        # Protection aura (gentle blue glow) - Draw FIRST
        self.group.add(Color(0.3, 0.7, 1.0, 0.1))
        self.protection_circle = Ellipse(
            pos=(self.x - self.safe_zone_radius + TILE_SIZE // 2, 
                    self.y - self.safe_zone_radius + TILE_SIZE // 2),
            size=(self.safe_zone_radius * 2, self.safe_zone_radius * 2)
        )
        self.group.add(self.protection_circle)

        # DEBUG: Hitbox visualization
        self.group.add(Color(1, 1, 0, 0.2))
        self.debug_rect = Rectangle(pos=(self.x, self.y), size=(TILE_SIZE, TILE_SIZE))
        self.group.add(self.debug_rect)
        
        # Main sprite
        if self.idle_texture:
            self.group.add(Color(1, 1, 1, 1))
        else:
            self.group.add(Color(1, 0, 0, 1)) 
        
        offset_x = (TILE_SIZE - REAPER_VISUAL_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        self.rect = Rectangle(
            pos=(self.x + offset_x, self.y + offset_y), 
            size=(REAPER_VISUAL_WIDTH, REAPER_VISUAL_HEIGHT)
        )
        self.group.add(self.rect)
        self.canvas.add(self.group)

    def update_frame(self):
        """Maps the current state and direction to the texture region (tex_coords)."""
        config = self.anim_config.get(self.state)
        if not config or not config['tex']:
            self.rect.texture = None
            return
            
        tex = config['tex']
        w = 1.0 / config['cols']
        h = 1.0 / config['rows']
        
        # Calculate texture coordinates for the current direction and frame
        u = self.frame_index * w
        row_index = self.anim_row_map.get(self.state, {}).get(self.direction, 0)
        v = row_index * h
        
        self.rect.texture = tex
        # Map texture to rect corners (standard sprite mapping)
        self.rect.tex_coords = (u, v + h, u + w, v + h, u + w, v, u, v)
    
    def animate(self, dt):
        """Periodic animation update."""
        max_frames = self.anim_config[self.state]['cols']
        if max_frames > 1:
            self.frame_index = (self.frame_index + 1) % max_frames
        self.update_frame()
    
    def update(self, dt, player_pos):
        """Main logic update called by the game engine."""
        # Check protection
        dist = self.calculate_distance(player_pos)
        if dist <= self.safe_zone_radius:
            self.protect_player(player_pos)
            
        # Movement logic
        if self.is_moving:
            self.continue_move()
        
        # Sync visuals
        self.update_visual_positions()
    
    def continue_move(self):
        """Interpolates movement towards the target position."""
        tx, ty = self.target_pos
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist < self.speed:
            self.x, self.y = tx, ty
            self.is_moving = False
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
    
    def update_visual_positions(self):
        """Syncs the Kivy graphics positions with logic coordinates."""
        offset_x = (TILE_SIZE - REAPER_VISUAL_WIDTH) / 2
        offset_y = TILE_SIZE / 2
        
        self.rect.pos = (self.x + offset_x, self.y + offset_y)
        
        # อัปเดต Debug Hitbox สีเหลือง
        self.debug_rect.pos = (self.x, self.y)
        
        # Center protection circle on the reaper's logic position
        self.protection_circle.pos = (
            self.x - self.safe_zone_radius + TILE_SIZE // 2,
            self.y - self.safe_zone_radius + TILE_SIZE // 2
        )
    
    def calculate_distance(self, target_pos):
        """Calculate Euclidean distance between Reaper and target centers."""
        # Using TILE_SIZE // 2 to get center of tiles
        r_center_x = self.x + TILE_SIZE / 2
        r_center_y = self.y + TILE_SIZE / 2
        t_center_x = target_pos[0] + TILE_SIZE / 2
        t_center_y = target_pos[1] + TILE_SIZE / 2
        
        return math.sqrt((t_center_x - r_center_x)**2 + (t_center_y - r_center_y)**2)
    
    def protect_player(self, player_pos):
        """Logic for player protection behavior."""
        # Note: Visual/Dialogue feedback is primarily handled in GameWidget for now.
        pass
    
    def check_player_collision(self, player_pos):
        """Basic AABB collision check with the player."""
        return (self.x < player_pos[0] + TILE_SIZE and
                self.x + TILE_SIZE > player_pos[0] and
                self.y < player_pos[1] + TILE_SIZE and
                self.y + TILE_SIZE > player_pos[1])
