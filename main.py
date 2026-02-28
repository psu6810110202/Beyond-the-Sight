from kivy.config import Config
from settings import *
from kivy.graphics import Color, Rectangle, Translate, Scale, PushMatrix, PopMatrix, Ellipse
from kivy.uix.label import Label

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
from map_loader import KivyTiledMap

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
            pass 

        self.debug_label = Label(
            text="", 
            size_hint=(None, None),
            size=(200, 120),              # ตั้งขนาดกรอบ
            halign='right',                # ชิดซ้าย
            valign='top',                 # ชิดบน
            color=(0, 1, 0, 1),           # สีเขียว
            font_size='18sp'
        )
        self.debug_label.bind(size=self.debug_label.setter('text_size'))

        # สร้าง UI สำหรับแสดงข้อความคุย
        self.dialogue_text = None
        self.dialogue_bg = None
        self.dialogue_timer = 0
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC

        # Draw Map Background (Floor, Walls, etc) - in the background layer
        with self.canvas.before:
            self.game_map = KivyTiledMap('assets/Tiles/beyond.tmj')
            self.game_map.draw_background(self.canvas.before)

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
        
        # Draw Map Foreground (Roofs, hanging objects, etc) - in the foreground layer
        with self.canvas.after:
            self.game_map.draw_foreground(self.canvas.after)
            PopMatrix()
            
        # สร้างคลาสหัวใจโดยส่ง canvas เข้าไป (เพื่อให้วาดหน้าจอ Screen Space ทับ PopMatrix)
        self.heart_ui = HeartUI(self.canvas)
            
        # Initial chunk update setup
        self.game_map.update_chunks(self.player.logic_pos[0], self.player.logic_pos[1])
            
        # Ensure UI updates position correctly on window resize AFTER everything is created
        self.bind(size=self.update_ui_positions)
        
        # Manually force the first UI positioning update
        self.update_ui_positions()
            
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

        # ศูนย์กลางของตัวละครให้แทร็กที่ logic_pos
        px, py = self.player.logic_pos
        pw, ph = TILE_SIZE, TILE_SIZE
        
        cam_x = px + pw / 2
        cam_y = py + ph / 2
        
        # เลื่อนตำแหน่งตัวละครมาไว้ที่จุดศูนย์กลางของจอ
        self.cam_trans_pos.xy = (-cam_x, -cam_y)

    def update_ui_positions(self, *args):
        # เรียกปรับตำแหน่งของหัวใจเมื่อหน้าจอมีการเปลี่ยนแปลงขนาด
        if getattr(self, 'heart_ui', None):
            self.heart_ui.update_position(self.width, self.height)

    def _on_keyboard_closed(self): 
        self._keyboard.unbind(on_key_down=self._on_key_down)  
        self._keyboard.unbind(on_key_up=self._on_key_up) 
        self._keyboard = None 

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1]
        print(f"Key pressed: {key_name}")  # Debug: แสดงปุ่มที่กด
        
        if key_name == 'f11':
            Window.fullscreen = 'auto' if not Window.fullscreen else False
        elif key_name == 'e':
            print("E key detected - checking NPC interaction")
            # ตรวจสอบว่า Player อยู่ใกล้ NPC หรือไม่
            self.check_npc_interaction()

        self.pressed_keys.add(key_name)
        
    def _on_key_up(self, keyboard, keycode): 
        key_name = keycode[1] 
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)

    def move_step(self, dt):
        self.update_camera()

        # อัปเดต Debug Label แสดงข้อมูลโดยรวมแบบบรรทัดเดียวแต่จัดให้เป็นระเบียบ
        px, py = self.player.logic_pos
        grid_x, grid_y = px // TILE_SIZE, py // TILE_SIZE
        chunk_x, chunk_y = grid_x // 16, grid_y // 16
        self.debug_label.text = (
            f"FPS: {Clock.get_fps():.0f}\n"
            f"Pos: ({px}, {py})\n"
            f"Grid: ({grid_x}, {grid_y})\n"
            f"Chunk: ({chunk_x}, {chunk_y})"
        )
        
        # update dynamic map chunks based on camera center
        self.game_map.update_chunks(px, py)
        
        self.player.move(self.pressed_keys, self.npcs, self.reaper)  # ส่ง npcs และ reaper ไปด้วย
        
        # อัปเดตแถบ Stamina ของผู้เล่น
        stamina_ratio = max(0.0, self.player.stamina / self.player.max_stamina)
        self.heart_ui.update_stamina(stamina_ratio)
        
        # อัปเดตปุ่ม E สำหรับ NPC ที่อยู่ใกล้
        self.update_interaction_hints()
        
        # Update NPCs
        for npc in self.npcs:
            npc.update(dt)
            # Check collision with player
            if npc.check_player_collision(self.player.logic_pos):
                # Handle collision - you can add custom behavior here
                # For now, just print a message
                print("NPC collided with player!")
        
        # Update Reaper
        self.reaper.update(dt, self.player.logic_pos)
        
        # Collision cooldown to prevent message spam
        if not hasattr(self, 'reaper_collision_cooldown'):
            self.reaper_collision_cooldown = 0
        
        if self.reaper_collision_cooldown > 0:
            self.reaper_collision_cooldown -= dt
        
        # Check Reaper collision with player (friendly interaction)
        if self.reaper.check_player_collision(self.player.logic_pos) and self.reaper_collision_cooldown <= 0:
            print("You touched the friendly Reaper!")
            self.reaper_collision_cooldown = 1.0  # 1 second cooldown
        
        # ใช้ logic_pos ของผู้เล่นสำหรับการคำนวณระยะห่าง
        player_pos = self.player.logic_pos
        
        # Update Enemies
        # ใช้ [:] เพื่อคัดลอกลิสต์ ป้องกันการ error ขณะลบไอเทมในลูป
        for enemy in self.enemies[:]:
            reaper_pos = (self.reaper.x, self.reaper.y)
            enemy.update(dt, player_pos, reaper_pos)
            if enemy.check_player_collision_logic(self.player.logic_pos, TILE_SIZE):
                enemy.destroy()           # ลบรูปสี่เหลี่ยมออกจากจอ
                self.enemies.remove(enemy) # ลบตรรกะศัตรูออกจากระบบ
                self.heart_ui.take_damage() # ลดเลือดผู้เล่นและเปลี่ยนภาพ 1 -> 2 -> 3
                print("Enemy attacked player and disappeared!")
        
        # อัปเดต timer สำหรับข้อความคุย
        if self.dialogue_timer > 0:
            self.dialogue_timer -= dt
            
            # ตรวจสอบระยะห่างระหว่าง Player และ NPC/Reaper ที่กำลังคุย
            if self.dialogue_text and self.dialogue_bg:
                player_pos = self.player.logic_pos
                player_center_x = player_pos[0] + TILE_SIZE / 2
                player_center_y = player_pos[1] + TILE_SIZE / 2
                
                # หา NPC ที่อยู่ใกล้ที่สุดเพื่อคำนวณทิศทาง
                closest_npc = None
                min_distance = float('inf')
                
                for npc in self.npcs:
                    npc_center_x = npc.x + (NPC_WIDTH - TILE_SIZE) / 2
                    npc_center_y = npc.y + (NPC_HEIGHT - TILE_SIZE) / 2
                    distance_x = abs(player_pos[0] - npc_center_x)
                    distance_y = abs(player_pos[1] - npc_center_y)
                    total_distance = distance_x + distance_y
                    
                    if distance_x <= TILE_SIZE * 2 and distance_y <= TILE_SIZE * 2 and total_distance < min_distance:
                        closest_npc = npc
                        min_distance = total_distance
                
                # หันหน้า NPC ที่ใกล้ที่สุดไปหา Player ตลอดเวลา
                if closest_npc:
                    npc_center_x = closest_npc.x + (NPC_WIDTH - TILE_SIZE) / 2
                    npc_center_y = closest_npc.y + (NPC_HEIGHT - TILE_SIZE) / 2
                    distance_x = abs(player_pos[0] - npc_center_x)
                    distance_y = abs(player_pos[1] - npc_center_y)
                    
                    if distance_x > distance_y:
                        # Player อยู่ทางซ้ายหรือขวา
                        if player_center_x > npc_center_x:
                            closest_npc.direction = 'right'
                        else:
                            closest_npc.direction = 'left'
                    else:
                        # Player อยู่ทางบนหรือล่าง
                        if player_center_y > npc_center_y:
                            closest_npc.direction = 'up'
                        else:
                            closest_npc.direction = 'down'
                    closest_npc.frame_index = 0
                
                # ตรวจสอบ Reaper ด้วย
                reaper_center_x = self.reaper.x + (REAPER_WIDTH - TILE_SIZE) / 2
                reaper_center_y = self.reaper.y + (REAPER_HEIGHT - TILE_SIZE) / 2
                reaper_distance_x = abs(player_pos[0] - reaper_center_x)
                reaper_distance_y = abs(player_pos[1] - reaper_center_y)
                
                if reaper_distance_x <= TILE_SIZE * 2 and reaper_distance_y <= TILE_SIZE * 2:
                    # ให้ Reaper หันหน้าไปหา Player ตลอดเวลา
                    if reaper_distance_x > reaper_distance_y:
                        # Player อยู่ทางซ้ายหรือขวา
                        if player_center_x > reaper_center_x:
                            self.reaper.direction = 'right'
                        else:
                            self.reaper.direction = 'left'
                    else:
                        # Player อยู่ทางบนหรือล่าง
                        if player_center_y > reaper_center_y:
                            self.reaper.direction = 'up'
                        else:
                            self.reaper.direction = 'down'
                    self.reaper.frame_index = 0
            
            if self.dialogue_timer <= 0:
                # ลบข้อความและพื้นหลัง
                if self.dialogue_text:
                    self.remove_widget(self.dialogue_text)
                    self.dialogue_text = None
                if self.dialogue_bg:
                    self.canvas.remove(self.dialogue_bg)
                    self.dialogue_bg = None
    
    def update_interaction_hints(self):
        """อัปเดตปุ่ม E สำหรับ NPC ที่อยู่ใกล้"""
        # ลบปุ่ม E เก่าทั้งหมด
        for hint in self.interaction_hints:
            if hasattr(hint, 'remove_widget'):
                self.remove_widget(hint)
            else:
                self.canvas.remove(hint)
        self.interaction_hints.clear()
        
        player_pos = self.player.logic_pos
        
        # ตรวจสอบ NPC ที่อยู่ใกล้
        for i, npc in enumerate(self.npcs):
            # คำนวณระยะห่างระหว่าง Player และ NPC
            npc_center_x = npc.x + (NPC_WIDTH - TILE_SIZE) / 2
            npc_center_y = npc.y + (NPC_HEIGHT - TILE_SIZE) / 2
            
            distance_x = abs(player_pos[0] - npc_center_x)
            distance_y = abs(player_pos[1] - npc_center_y)
            
            # ถ้าอยู่ใกล้ NPC (ระยะ 2 ช่อง)
            if distance_x <= TILE_SIZE * 2 and distance_y <= TILE_SIZE * 2:
                # สร้างปุ่ม E เหนือหัว NPC
                with self.canvas:
                    Color(1, 1, 0, 0.8)  # สีเหลือง
                    hint = Rectangle(
                        size=(20, 20),
                        pos=(npc.x + NPC_WIDTH/2 - 10, npc.y + NPC_HEIGHT + 35)
                    )
                    self.interaction_hints.append(hint)
                
                # สร้างข้อความ E แยกต่างหาก
                hint_text = Label(
                    text="E",
                    size_hint=(None, None),
                    size=(20, 20),
                    pos=(npc.x + NPC_WIDTH/2 - 10, npc.y + NPC_HEIGHT + 35),
                    color=(0, 0, 0, 1),  # สีดำ
                    font_size=14,
                    halign='center',
                    valign='middle'
                )
                self.add_widget(hint_text)
                self.interaction_hints.append(hint_text)
        
        # ตรวจสอบ Reaper ที่อยู่ใกล้
        reaper_center_x = self.reaper.x + (REAPER_WIDTH - TILE_SIZE) / 2
        reaper_center_y = self.reaper.y + (REAPER_HEIGHT - TILE_SIZE) / 2
        
        reaper_distance_x = abs(player_pos[0] - reaper_center_x)
        reaper_distance_y = abs(player_pos[1] - reaper_center_y)
        
        # ถ้าอยู่ใกล้ Reaper (ระยะ 2 ช่อง)
        if reaper_distance_x <= TILE_SIZE * 2 and reaper_distance_y <= TILE_SIZE * 2:
            # สร้างปุ่ม E เหนือหัว Reaper
            with self.canvas:
                Color(1, 1, 0, 0.8)  # สีเหลือง
                hint = Rectangle(
                    size=(20, 20),
                    pos=(self.reaper.x + REAPER_WIDTH/2 - 10, self.reaper.y + REAPER_HEIGHT + 35)
                )
                self.interaction_hints.append(hint)
            
            # สร้างข้อความ E แยกต่างหาก
            hint_text = Label(
                text="E",
                size_hint=(None, None),
                size=(20, 20),
                pos=(self.reaper.x + REAPER_WIDTH/2 - 10, self.reaper.y + REAPER_HEIGHT + 35),
                color=(0, 0, 0, 1),  # สีดำ
                font_size=14,
                halign='center',
                valign='middle'
            )
            self.add_widget(hint_text)
            self.interaction_hints.append(hint_text)
                
    def create_npcs(self):
        # กำหนดตำแหน่ง NPC แบบตายตัว และระบุรูปภาพของแต่ละตัว
        NPC1x = (896 // TILE_SIZE) * TILE_SIZE
        NPC1y = (256 // TILE_SIZE) * TILE_SIZE
        NPC2x = (544 // TILE_SIZE) * TILE_SIZE
        NPC2y = (288 // TILE_SIZE) * TILE_SIZE
        NPC3x = (528 // TILE_SIZE) * TILE_SIZE
        NPC3y = (272 // TILE_SIZE) * TILE_SIZE
        NPC4x = (560 // TILE_SIZE) * TILE_SIZE
        NPC4y = (272 // TILE_SIZE) * TILE_SIZE
        NPC5x = (560 // TILE_SIZE) * TILE_SIZE
        NPC5y = (256 // TILE_SIZE) * TILE_SIZE

        npc_data = [
            ((NPC1x, NPC1y), 'assets/NPC/NPC1.png'),   # NPC 1
            ((NPC2x, NPC2y), 'assets/NPC/NPC2.png'),       # NPC 2
            ((NPC3x, NPC3y), 'assets/NPC/NPC3.png'),       # NPC 3
            ((NPC4x, NPC4y), 'assets/NPC/NPC4.png'),       # NPC 4
            ((NPC5x, NPC5y), 'assets/NPC/NPC5.png')        # NPC 5
        ]
        
        for i in range(NPC_COUNT):
            (x, y), img_path = npc_data[i]
            npc = NPC(self.canvas, x, y, image_path=img_path)
            self.npcs.append(npc)

    def create_enemies(self):
        # สร้างศัตรูชั่วคราว ดักจับตำแหน่งให้อยู่บน Grid ของช่อง 32x32 
        # ย้ายตำแหน่งศัตรูมาใกล้ๆ จุดเกิดตรงกลาง
        enemy_positions = [
            (800 + 64, 800 + 64), 
            (800 - 128, 800 - 128)
        ]
        for x, y in enemy_positions:
            enemy = Enemy(self.canvas, x, y)
            self.enemies.append(enemy)
    
    def check_npc_interaction(self):
        """ตรวจสอบว่า Player อยู่ใกล้ NPC หรือ Reaper และแสดงข้อความคุย"""
        player_pos = self.player.logic_pos
        print(f"Player position: {player_pos}")  # Debug: แสดงตำแหน่ง Player
        
        # ตรวจสอบ Reaper ก่อน
        reaper_center_x = self.reaper.x + (REAPER_WIDTH - TILE_SIZE) / 2
        reaper_center_y = self.reaper.y + (REAPER_HEIGHT - TILE_SIZE) / 2
        reaper_distance_x = abs(player_pos[0] - reaper_center_x)
        reaper_distance_y = abs(player_pos[1] - reaper_center_y)
        
        if reaper_distance_x <= TILE_SIZE * 2 and reaper_distance_y <= TILE_SIZE * 2:
            # ให้ Reaper หันหน้าไปหา Player
            player_center_x = player_pos[0] + TILE_SIZE / 2
            player_center_y = player_pos[1] + TILE_SIZE / 2
            
            if reaper_distance_x > reaper_distance_y:
                # Player อยู่ทางซ้ายหรือขวา
                if player_center_x > reaper_center_x:
                    self.reaper.direction = 'right'
                else:
                    self.reaper.direction = 'left'
            else:
                # Player อยู่ทางบนหรือล่าง
                if player_center_y > reaper_center_y:
                    self.reaper.direction = 'up'
                else:
                    self.reaper.direction = 'down'
            self.reaper.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง
            
            # แสดงข้อความคุยของ Reaper
            dialogue = self.get_reaper_dialogue(reaper_distance_x, reaper_distance_y)
            if dialogue:
                self.show_dialogue_above_reaper(dialogue)
            return
        
        # ตรวจสอบ NPC ทั้งหมด
        for i, npc in enumerate(self.npcs):
            # คำนวณระยะห่างระหว่าง Player และ NPC
            npc_center_x = npc.x + (NPC_WIDTH - TILE_SIZE) / 2
            npc_center_y = npc.y + (NPC_HEIGHT - TILE_SIZE) / 2
            
            distance_x = abs(player_pos[0] - npc_center_x)
            distance_y = abs(player_pos[1] - npc_center_y)
            
            print(f"NPC{i+1} center: ({npc_center_x}, {npc_center_y}), distance: ({distance_x}, {distance_y})")  # Debug
            
            # ถ้าอยู่ใกล้ NPC (ระยะ 2 ช่อง) เท่านั้น
            if distance_x <= TILE_SIZE * 2 and distance_y <= TILE_SIZE * 2:
                # ให้ NPC หันหน้าไปหา Player
                player_center_x = player_pos[0] + TILE_SIZE / 2
                player_center_y = player_pos[1] + TILE_SIZE / 2
                
                if distance_x > distance_y:
                    # Player อยู่ทางซ้ายหรือขวา
                    if player_center_x > npc_center_x:
                        npc.direction = 'right'
                    else:
                        npc.direction = 'left'
                else:
                    # Player อยู่ทางบนหรือล่าง
                    if player_center_y > npc_center_y:
                        npc.direction = 'up'
                    else:
                        npc.direction = 'down'
                npc.frame_index = 0  # รีเซ็ตเฟรมเมื่อเปลี่ยนทิศทาง
                
                npc_name = f"NPC{i+1}"
                dialogue = self.get_proximity_dialogue(npc_name, distance_x, distance_y)
                if dialogue:
                    self.show_dialogue_above_npc(npc, dialogue)
                return
        
        print("ไม่มี NPC หรือ Reaper อยู่ใกล้ๆ")
    
    def show_dialogue_above_npc(self, npc, dialogue):
        """แสดงข้อความคุยเหนือหัว NPC"""
        # ลบข้อความเก่าถ้ามี
        if self.dialogue_text:
            self.remove_widget(self.dialogue_text)
        
        # สร้างพื้นหลังสีดำสำหรับข้อความ
        with self.canvas:
            Color(0, 0, 0, 0.8)  # สีดำโปร่งแสด 80%
            self.dialogue_bg = Rectangle(
                size=(160, 30),
                pos=(npc.x + NPC_WIDTH/2 - 80, npc.y + NPC_HEIGHT + 8)
            )
        
        # สร้าง Label สำหรับแสดงข้อความ
        self.dialogue_text = Label(
            text=dialogue,
            size_hint=(None, None),
            size=(140, 20),
            pos=(npc.x + NPC_WIDTH/2 - 70, npc.y + NPC_HEIGHT + 10),
            color=(1, 1, 1, 1),  # สีขาว
            font_size=12,  # ลดขนาดฟอนต์
            halign='center',
            valign='middle'
        )
        
        # เพิ่ม Label ลงใน widget
        self.add_widget(self.dialogue_text)
        
        # ตั้ง timer ให้หายไปหลัง 3 วินาที
        self.dialogue_timer = 3.0
    
    # must fix
    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """สร้างข้อความพูดขึ้นมาตามระยะ"""
        if distance_x <= TILE_SIZE and distance_y <= TILE_SIZE:
            # ระยะใกล้มาก (1 ช่อง)
            return f"[{npc_name}]: เจ้ามาอยู่ใกล้มาก! ฉันชื่อ {npc_name}"
        elif distance_x <= TILE_SIZE * 1.5 and distance_y <= TILE_SIZE * 1.5:
            # ระยะปานกลาง (1.5 ช่อง)
            return f"[{npc_name}ะ]: โอ... มีอะไรให้ช่วยเหรือ?"
        elif distance_x <= TILE_SIZE * 2 and distance_y <= TILE_SIZE * 2:
            # ระยะไกล (2 ช่อง)
            return f"[{npc_name}]: สวัสดี! ฉันชื่อ {npc_name}"
        else:
            return None
    
    def show_dialogue_above_reaper(self, dialogue):
        """แสดงข้อความคุยเหนือหัว Reaper"""
        # ลบข้อความเก่าถ้ามี
        if self.dialogue_text:
            self.remove_widget(self.dialogue_text)
        
        # สร้างพื้นหลังสีดำสำหรับข้อความ
        with self.canvas:
            Color(0, 0, 0, 0.8)  # สีดำโปร่งแสด 80%
            self.dialogue_bg = Rectangle(
                size=(160, 30),
                pos=(self.reaper.x + REAPER_WIDTH/2 - 80, self.reaper.y + REAPER_HEIGHT + 8)
            )
        
        # สร้าง Label สำหรับแสดงข้อความ
        self.dialogue_text = Label(
            text=dialogue,
            size_hint=(None, None),
            size=(140, 20),
            pos=(self.reaper.x + REAPER_WIDTH/2 - 70, self.reaper.y + REAPER_HEIGHT + 10),
            color=(1, 1, 1, 1),  # สีขาว
            font_size=12,  # ลดขนาดฟอนต์
            halign='center',
            valign='middle'
        )
        
        # เพิ่ม Label ลงใน widget
        self.add_widget(self.dialogue_text)
        
        # ตั้ง timer ให้หายไปหลัง 3 วินาที
        self.dialogue_timer = 3.0
    
    def get_reaper_dialogue(self, distance_x, distance_y):
        """สร้างข้อความพูดของ Reaper ขึ้นมาตามระยะ"""
        if distance_x <= TILE_SIZE and distance_y <= TILE_SIZE:
            # ระยะใกล้มาก (1 ช่อง)
            return "[Reaper]: เจ้ามาอยู่ใกล้มาก! ฉันคือ Reaper ผู้้มคุ้มคุ้ม"
        elif distance_x <= TILE_SIZE * 1.5 and distance_y <= TILE_SIZE * 1.5:
            # ระยะปานกลาง (1.5 ช่อง)
            return "[Reaper]: โอ... มีอะไรให้ช่วยเหรือ? ฉันจะปกป้องเจ้า"
        elif distance_x <= TILE_SIZE * 2 and distance_y <= TILE_SIZE * 2:
            # ระยะไกล (2 ช่อง)
            return "[Reaper]: สวัสดี! ฉันคือ Reaper ผู้้มคุ้มคุ้ม"
        else:
            return None
    
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
        
        from kivy.uix.floatlayout import FloatLayout
        root = FloatLayout()
        
        # สร้างตัวเกม
        game = GameWidget()
        root.add_widget(game)
        
        # นำ debug_label แปะที่ FloatLayout (UI หน้าจอจริงๆ) ให้พ้นจากกล้องซูม/หมุน
        game.debug_label.pos_hint = {'right': 0.95, 'top': 0.95}
        root.add_widget(game.debug_label)
        
        return root 

if __name__ == '__main__': 
    MyApp().run()