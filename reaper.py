from kivy.graphics import Rectangle, Color, Ellipse
from settings import *
import math

class Reaper:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.speed = REAPER_SPEED
        self.target_pos = [x, y]
        self.is_moving = False
        self.safe_zone_radius = SAFE_ZONE_RADIUS
        self.detection_radius = REAPER_DETECTION_RADIUS
        self.is_patrolling = True
        self.patrol_direction = 1  # 1 for right, -1 for left
        self.patrol_timer = 0
        self.patrol_interval = 120  # frames before changing direction
        self.is_protector = True  # Reaper เป็นผู้ปกป้อง
        
        # Visual elements
        with canvas:
            # Reaper body (friendly blue color)
            Color(0.2, 0.5, 1.0, 1)  # สีฟ้าอ่อน - ดูเป็นมิตร
            self.rect = Rectangle(pos=(x, y), size=(REAPER_WIDTH, REAPER_HEIGHT))
            
            # Safe zone visualization (protective green circle)
            Color(0, 1, 0, 0.2)  # เขียวเข้มขึ้น - ดูปลอดภัย
            self.safe_zone_circle = Ellipse(
                pos=(x - self.safe_zone_radius + REAPER_WIDTH//2, 
                     y - self.safe_zone_radius + REAPER_HEIGHT//2),
                size=(self.safe_zone_radius * 2, self.safe_zone_radius * 2)
            )
            
            # Protection aura (gentle blue glow)
            Color(0.3, 0.7, 1.0, 0.1)  # สีฟ้าพาสเทลอ่อนๆ
            self.protection_circle = Ellipse(
                pos=(x - self.detection_radius + REAPER_WIDTH//2, 
                     y - self.detection_radius + REAPER_HEIGHT//2),
                size=(self.detection_radius * 2, self.detection_radius * 2)
            )
    
    def update(self, dt, player_pos):
        # Update visual positions
        self.update_visual_positions()
        
        # Check if player is in safe zone
        distance_to_player = self.calculate_distance(player_pos)
        
        if distance_to_player <= self.safe_zone_radius:
            # Player is in safe zone - provide protection
            self.protect_player(player_pos)
        else:
            # Player outside safe zone - patrol behavior
            pass
        
        # Continue movement if needed
        if self.is_moving:
            self.continue_move()
    
    def update_visual_positions(self):
        # Update safe zone circle position
        self.safe_zone_circle.pos = (
            self.x - self.safe_zone_radius + REAPER_WIDTH//2,
            self.y - self.safe_zone_radius + REAPER_HEIGHT//2
        )
        
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
    
    def check_player_collision(self, player_rect):
        reaper_rect = [self.x, self.y, REAPER_WIDTH, REAPER_HEIGHT]
        player_rect_list = [player_rect.pos[0], player_rect.pos[1], 
                           player_rect.size[0], player_rect.size[1]]
        
        # Reaper ไม่ทำอันตรายผู้เล่น - แค่สัมผัสกันได้
        return (reaper_rect[0] < player_rect_list[0] + player_rect_list[2] and
                reaper_rect[0] + reaper_rect[2] > player_rect_list[0] and
                reaper_rect[1] < player_rect_list[1] + player_rect_list[3] and
                reaper_rect[1] + reaper_rect[3] > player_rect_list[1])

    def check_player_collision_logic(self, player_pos, tile_size):
        reaper_rect = [self.x, self.y, REAPER_WIDTH, REAPER_HEIGHT]
        player_rect_list = [player_pos[0], player_pos[1], tile_size, tile_size]
        
        return (reaper_rect[0] < player_rect_list[0] + player_rect_list[2] and
                reaper_rect[0] + reaper_rect[2] > player_rect_list[0] and
                reaper_rect[1] < player_rect_list[1] + player_rect_list[3] and
                reaper_rect[1] + reaper_rect[3] > player_rect_list[1])

