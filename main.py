from kivy.config import Config
from settings import *
from kivy.graphics import Color, Rectangle # เพิ่ม Color
from settings import * # อย่าลืม import settings

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'position', 'auto')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App 
from kivy.uix.widget import Widget 
from kivy.core.window import Window 
from kivy.clock import Clock 
from player import Player
from npc import NPC
from reaper import Reaper

# เพิ่มคลาส Wall ง่ายๆ
class Wall:
    def __init__(self, canvas, pos, size):
        self.pos = pos
        self.size = size
        with canvas:
            Color(0.5, 0.5, 0.5, 1) # กำแพงสีเทา
            Rectangle(pos=pos, size=size)
class GameWidget(Widget): 
    def __init__(self, **kwargs): 
        super().__init__(**kwargs) 

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        # 1. สร้าง Map / กำแพง
        self.walls = []
        self.create_map()
        
        self.player = Player(self.canvas)
        
        # 2. สร้าง NPCs
        self.npcs = []
        self.create_npcs()
        
        # 3. สร้าง Reaper
        self.reaper = Reaper(self.canvas, 400, 400, self.walls)

        Clock.schedule_interval(self.move_step, 1.0 / FPS) 

    def _on_keyboard_closed(self): 
        self._keyboard.unbind(on_key_down=self._on_key_down)  
        self._keyboard.unbind(on_key_up=self._on_key_up) 
        self._keyboard = None 

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1]
        if key_name == 'f11':
            Window.fullscreen = 'auto' if not Window.fullscreen else False

        self.pressed_keys.add(key_name)
        
    def _on_key_up(self, keyboard, keycode): 
        key_name = keycode[1] 
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)

    def move_step(self, dt):
        self.player.move(self.pressed_keys)
        # Update NPCs
        for npc in self.npcs:
            npc.update(dt)
            # Check collision with player
            if npc.check_player_collision(self.player.rect):
                # Handle collision - you can add custom behavior here
                # For now, just print a message
                print("NPC collided with player!")
        
        # Update Reaper
        player_pos = self.player.rect.pos
        self.reaper.update(dt, player_pos)
        
        # Check Reaper collision with player (friendly interaction)
        if self.reaper.check_player_collision(self.player.rect):
            print("You touched the friendly Reaper!")
        
        # Check if player is in Reaper's safe zone
        if self.reaper.is_in_safe_zone(player_pos):
            print("You are safe in the Reaper's protection zone!")
    
    def create_map(self):
        # สร้างกำแพงขอบจอ
        wall_thickness = TILE_SIZE
        
        # กำแพงบน
        self.walls.append(Wall(self.canvas, (0, WINDOW_HEIGHT - wall_thickness), 
                              (WINDOW_WIDTH, wall_thickness)))
        # กำแพงล่าง
        self.walls.append(Wall(self.canvas, (0, 0), 
                              (WINDOW_WIDTH, wall_thickness)))
        # กำแพงซ้าย
        self.walls.append(Wall(self.canvas, (0, 0), 
                              (wall_thickness, WINDOW_HEIGHT)))
        # กำแพงขวา
        self.walls.append(Wall(self.canvas, (WINDOW_WIDTH - wall_thickness, 0), 
                              (wall_thickness, WINDOW_HEIGHT)))
        
        # สร้างกำแพงกลาง
        self.walls.append(Wall(self.canvas, (200, 200), 
                              (TILE_SIZE * 4, TILE_SIZE)))
        self.walls.append(Wall(self.canvas, (400, 100), 
                              (TILE_SIZE, TILE_SIZE * 6)))
        self.walls.append(Wall(self.canvas, (600, 300), 
                              (TILE_SIZE * 3, TILE_SIZE * 2)))
    
    def create_npcs(self):
        # กำหนดตำแหน่ง NPC แบบตายตัว
        npc_positions = [
            (100, 100),   # NPC 1
            (300, 200),   # NPC 2
            (500, 150),   # NPC 3
            (200, 350),   # NPC 4
            (700, 250)    # NPC 5
        ]
        
        colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 1), (1, 0, 1, 1)]
        
        for i in range(NPC_COUNT):
            x, y = npc_positions[i]
            color = colors[i % len(colors)]
            npc = NPC(self.canvas, x, y, self.walls, color)
            self.npcs.append(npc)
    
    def check_npc_wall_collision(self, rect, wall_obj):
        # rect = [x, y, w, h]
        # wall_obj.pos/size
        r1x, r1y, r1w, r1h = rect
        r2x, r2y = wall_obj.pos
        r2w, r2h = wall_obj.size
        
        return (r1x < r2x + r2w and r1x + r1w > r2x and
                r1y < r2y + r2h and r1y + r1h > r2y)

class MyApp(App): 
    def build(self): 
        self.title = TITLE
        return GameWidget() 

if __name__ == '__main__': 
    MyApp().run()