from kivy.config import Config
from settings import *
from kivy.graphics import Color, Rectangle, Translate, Scale, PushMatrix, PopMatrix

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

class GameWidget(Widget): 
    def __init__(self, **kwargs): 
        super().__init__(**kwargs) 

        # Setup Camera
        with self.canvas.before:
            PushMatrix()
            self.cam_trans_center = Translate(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            self.cam_scale = Scale(1, 1, 1)
            self.cam_trans_pos = Translate(0, 0)
        
        with self.canvas.after:
            PopMatrix()

        # Draw Map Background
        with self.canvas:
            Color(0.2, 0.2, 0.2, 1) # Dark gray background
            Rectangle(pos=(0, 0), size=(WINDOW_WIDTH, WINDOW_HEIGHT))

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        
        # 2. สร้าง NPCs
        self.npcs = []
        self.create_npcs()
        
        # 3. สร้าง Reaper
        self.reaper = Reaper(self.canvas, 400, 400)

        self.player = Player(self.canvas)

        Clock.schedule_interval(self.move_step, 1.0 / FPS) 

    def update_camera(self):
        # คำนวณอัตราส่วนการซูม (Scale) 
        # เพื่อให้หน้าจอแคบๆ (CAMERA_SIZE) ถูกขยายให้เต็มหน้าต่างเกม (WINDOW_SIZE)
        scale_x = WINDOW_WIDTH / CAMERA_WIDTH
        scale_y = WINDOW_HEIGHT / CAMERA_HEIGHT
        
        # เลือกซูมตามด้านที่น้อยที่สุด เพื่อไม่ให้ภาพเสียสัดส่วน (รักษาสัดส่วนเดิม)
        scale_factor = min(scale_x, scale_y)
        self.cam_scale.xyz = (scale_factor, scale_factor, 1)

        # ศูนย์กลางของตัวละคร
        px, py = self.player.rect.pos
        pw, ph = self.player.rect.size
        
        cam_x = px + pw / 2
        cam_y = py + ph / 2
        
        # เลื่อนตำแหน่งตัวละครมาไว้ที่จุดศูนย์กลางของจอ
        self.cam_trans_pos.xy = (-cam_x, -cam_y)

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
        self.update_camera()
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
            npc = NPC(self.canvas, x, y, color)
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