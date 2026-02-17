from kivy.graphics import Rectangle
from settings import *

class Player:
    def __init__(self, canvas):
        self.is_moving = False
        self.target_pos = [96, 96]
        with canvas:
            self.rect = Rectangle(pos=(96, 96), size=(PLAYER_WIDTH * 2, PLAYER_HEIGHT * 2))

    def move(self, pressed_keys):
        if not self.is_moving:
            dx, dy = 0, 0
            if 'w' in pressed_keys or 'up' in pressed_keys: dy = TILE_SIZE
            elif 's' in pressed_keys or 'down' in pressed_keys: dy = -TILE_SIZE
            elif 'a' in pressed_keys or 'left' in pressed_keys: dx = -TILE_SIZE
            elif 'd' in pressed_keys or 'right' in pressed_keys: dx = TILE_SIZE

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

        if cur_x < tar_x: cur_x = min(cur_x + PLAYER_SPEED, tar_x)
        elif cur_x > tar_x: cur_x = max(cur_x - PLAYER_SPEED, tar_x)
        if cur_y < tar_y: cur_y = min(cur_y + PLAYER_SPEED, tar_y)
        elif cur_y > tar_y: cur_y = max(cur_y - PLAYER_SPEED, tar_y)

        self.rect.pos = (cur_x, cur_y)
        if cur_x == tar_x and cur_y == tar_y:
            self.is_moving = False