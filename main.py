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
from heart import HeartUI
from enemy import Enemy

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
            
        # สร้างคลาสหัวใจโดยส่ง canvas เข้าไป
        self.heart_ui = HeartUI(self.canvas)

        # Ensure UI updates position correctly on window resize
        self.bind(size=self.update_ui_positions)

        # Draw Map Background (Grid 32x32)
        with self.canvas:
            # วาดตารางหมากรุกขนาด TILE_SIZE x TILE_SIZE ทั่วทั้งหน้าจอ
            # เพื่อให้เห็นขอบเขตของแต่ละบล็อกการเดินอย่างชัดเจน
            for x in range(0, WINDOW_WIDTH, TILE_SIZE):
                for y in range(0, WINDOW_HEIGHT, TILE_SIZE):
                    if (x // TILE_SIZE + y // TILE_SIZE) % 2 == 0:
                        Color(0.2, 0.2, 0.2, 1)  # พื้นสีเทาเข้ม
                    else:
                        Color(0.25, 0.25, 0.25, 1) # พื้นสีเทาอ่อน
                    Rectangle(pos=(x, y), size=(TILE_SIZE, TILE_SIZE))

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        
        # 2. สร้าง NPCs
        self.npcs = []
        self.create_npcs()
        
        # 3. สร้าง Reaper
        self.reaper = Reaper(self.canvas, 400, 400)
        
        # 4. สร้าง Enemies
        self.enemies = []
        self.create_enemies()

        self.player = Player(self.canvas)

        Clock.schedule_interval(self.move_step, 1.0 / FPS) 

    def update_camera(self):
        # อัปเดตจุดศูนย์กลางกล้องให้เป็นกึ่งกลางของหน้าต่าง Application จริงๆ (เพื่อรองรับการขยายจอ)
        self.cam_trans_center.xy = (self.width / 2, self.height / 2)

        # คำนวณอัตราส่วนการซูม (Scale) 
        # เพื่อให้หน้าจอแคบๆ (CAMERA_SIZE) ถูกขยายให้เต็มหน้าต่างเกม (self.width / self.height)
        scale_x = self.width / CAMERA_WIDTH
        scale_y = self.height / CAMERA_HEIGHT
        
        # เลือกซูมตามด้านที่น้อยที่สุด เพื่อไม่ให้ภาพเสียสัดส่วน (รักษาสัดส่วนเดิม)
        scale_factor = min(scale_x, scale_y)
        self.cam_scale.xyz = (scale_factor, scale_factor, 1)

        # ศูนย์กลางของตัวละครให้แทร็กที่ logic_pos (กรอบ 32x32)
        px, py = self.player.logic_pos
        pw, ph = TILE_SIZE, TILE_SIZE
        
        cam_x = px + pw / 2
        cam_y = py + ph / 2
        
        # เลื่อนตำแหน่งตัวละครมาไว้ที่จุดศูนย์กลางของจอ
        self.cam_trans_pos.xy = (-cam_x, -cam_y)

    def update_ui_positions(self, *args):
        # เรียกปรับตำแหน่งของหัวใจเมื่อหน้าจอมีการเปลี่ยนแปลงขนาด
        self.heart_ui.update_position(self.width, self.height)

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
        self.player.move(self.pressed_keys, self.npcs)  # ส่ง npcs ไปด้วย
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
    
        # ใช้ logic_pos ของผู้เล่นสำหรับการคำนวณระยะห่าง
        player_pos = self.player.logic_pos
        
        # Update Enemies
        # ใช้ [:] เพื่อคัดลอกลิสต์ ป้องกันการ error ขณะลบไอเทมในลูป
        for enemy in self.enemies[:]:
            enemy.update(dt, player_pos)
            if enemy.check_player_collision_logic(self.player.logic_pos, TILE_SIZE):
                enemy.destroy()           # ลบรูปสี่เหลี่ยมออกจากจอ
                self.enemies.remove(enemy) # ลบตรรกะศัตรูออกจากระบบ
                self.heart_ui.take_damage() # ลดเลือดผู้เล่นและเปลี่ยนภาพ 1 -> 2 -> 3
                print("Enemy attacked the player and disappeared!")
    
    def create_npcs(self):
        # กำหนดตำแหน่ง NPC แบบตายตัว
        npc_positions = [
            (100, 100),   # NPC 1
            (300, 200),   # NPC 2
            (500, 150),   # NPC 3
            (200, 350),   # NPC 4
            (700, 250)    # NPC 5
        ]
        
        for i in range(NPC_COUNT):
            x, y = npc_positions[i]
            npc = NPC(self.canvas, x, y)
            self.npcs.append(npc)
            
    def create_enemies(self):
        # สร้างศัตรูชั่วคราว ดักจับตำแหน่งให้อยู่บน Grid ของช่อง 32x32 
        enemy_positions = [
            (608, 416), # 19*32, 13*32
            (192, 96)   # 6*32, 3*32
        ]
        for x, y in enemy_positions:
            enemy = Enemy(self.canvas, x, y)
            self.enemies.append(enemy)
    
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