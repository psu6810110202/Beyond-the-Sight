from kivy.graphics import Rectangle, Color
from settings import *

class NPC:
    def __init__(self, canvas, x, y, walls, color=(1, 0, 0, 1)):
        self.canvas = canvas
        self.walls = walls
        self.x = x
        self.y = y
        self.color = color
        
        with canvas:
            Color(*color)
            self.rect = Rectangle(pos=(x, y), size=(NPC_WIDTH, NPC_HEIGHT))
    
    def update(self, dt):
        # NPC ยืนอยู่กับที่ ไม่ต้องทำอะไร
        pass
    
    def check_player_collision(self, player_rect):
        npc_rect = [self.x, self.y, NPC_WIDTH, NPC_HEIGHT]
        player_rect_list = [player_rect.pos[0], player_rect.pos[1], 
                           player_rect.size[0], player_rect.size[1]]
        
        return (npc_rect[0] < player_rect_list[0] + player_rect_list[2] and
                npc_rect[0] + npc_rect[2] > player_rect_list[0] and
                npc_rect[1] < player_rect_list[1] + player_rect_list[3] and
                npc_rect[1] + npc_rect[3] > player_rect_list[1])
