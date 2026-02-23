from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from settings import *
import math

class Enemy:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.speed = ENEMY_SPEED
        self.detection_radius = ENEMY_DETECTION_RADIUS
        
        self.is_moving = False
        self.target_pos = [x, y]
        self.turn_delay = 0
        self.direction = 'down'
        
        with canvas:
            # ใช้สี่เหลี่ยมสีแดงไปก่อนตามที่ต้องการ
            self.color = Color(1, 0, 0, 1)
            self.rect = Rectangle(pos=(self.x, self.y), size=(ENEMY_WIDTH, ENEMY_HEIGHT))
            
    def destroy(self):
        # ลบหน้าตาของศัตรูรูปสี่เหลี่ยมออกจากผืนผ้าใบแคนวาส
        self.canvas.remove(self.color)
        self.canvas.remove(self.rect)
            
    def update(self, dt, player_pos):
        # 1. ขยับตัวละครถ้าอยู่ในสถานะเดิน
        if self.is_moving:
            self.continue_move()

        # 2. ถ้าหยุดอยู่ ให้ตัดสินใจว่าจะเดินไปทางไหน
        if not self.is_moving:
            distance_to_player = self.calculate_distance(player_pos)
            if distance_to_player <= self.detection_radius:
                self.chase_player_grid(player_pos)
                    
        # อัปเดตกราฟิกสี่เหลี่ยมตามพิกัด x, y
        self.rect.pos = (self.x, self.y)
        
    def calculate_distance(self, target_pos):
        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        return math.sqrt(dx**2 + dy**2)
        
    def chase_player_grid(self, player_pos):
        if self.turn_delay > 0:
            self.turn_delay -= 1
            return

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        
        move_x, move_y = 0, 0
        new_dir = self.direction
        
        # เลือกเดินแกนที่ระยะห่างเยอะกว่าก่อน (หรือสุ่มก็ได้) แบบ Grid Movement
        if abs(dx) > abs(dy):
            if dx > 0:
                move_x = TILE_SIZE; new_dir = 'right'
            else:
                move_x = -TILE_SIZE; new_dir = 'left'
        elif abs(dy) > 0:
            if dy > 0:
                move_y = TILE_SIZE; new_dir = 'up'
            else:
                move_y = -TILE_SIZE; new_dir = 'down'
                
        if move_x != 0 or move_y != 0:
            if self.direction != new_dir:
                self.direction = new_dir
                self.turn_delay = 6
            else:
                self.start_move(move_x, move_y)

    def start_move(self, dx, dy):
        self.target_pos = [self.x + dx, self.y + dy]
        self.is_moving = True

    def continue_move(self):
        cur_x, cur_y = self.x, self.y
        tar_x, tar_y = self.target_pos

        if cur_x < tar_x: cur_x = min(cur_x + self.speed, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - self.speed, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + self.speed, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - self.speed, tar_y)

        self.x, self.y = cur_x, cur_y
        
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False
            
    def check_player_collision(self, player_rect):
        enemy_r = [self.x, self.y, ENEMY_WIDTH, ENEMY_HEIGHT]
        player_r = [player_rect.pos[0], player_rect.pos[1], 
                    player_rect.size[0], player_rect.size[1]]
        
        return (enemy_r[0] < player_r[0] + player_r[2] and
                enemy_r[0] + enemy_r[2] > player_r[0] and
                enemy_r[1] < player_r[1] + player_r[3] and
                enemy_r[1] + enemy_r[3] > player_r[1])

    def check_player_collision_logic(self, player_pos, tile_size):
        enemy_r = [self.x, self.y, ENEMY_WIDTH, ENEMY_HEIGHT]
        player_r = [player_pos[0], player_pos[1], tile_size, tile_size]
        
        return (enemy_r[0] < player_r[0] + player_r[2] and
                enemy_r[0] + enemy_r[2] > player_r[0] and
                enemy_r[1] < player_r[1] + player_r[3] and
                enemy_r[1] + enemy_r[3] > player_r[1])
