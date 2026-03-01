from kivy.config import Config
from settings import *
from kivy.graphics import Color, Rectangle, Translate, Scale, PushMatrix, PopMatrix, Ellipse
from kivy.uix.label import Label
from kivy.uix.widget import Widget as KivyWidget
from kivy.uix.floatlayout import FloatLayout

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
from enemy import Enemy, ENEMY_START_POSITIONS
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
        
        # Widget สำหรับ dialogue box ใน screen space (จะถูก attach โดย MyApp.build)
        self.dialogue_root = None

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
        
        # 3. สร้าง Reaper (ตำแหน่งเริ่มต้นจัดการใน reaper.py)
        self.reaper = Reaper(self.canvas)
        
        # 4. สร้าง Enemies
        self.enemies = []
        self.create_enemies()

        self.player = Player(self.canvas)
        
        # Draw Map Foreground (Roofs, hanging objects, etc) - in the foreground layer
        with self.canvas.after:
            self.game_map.draw_foreground(self.canvas.after)
            
            # Debug: Draw Solid Hitboxes (Draw once, inside camera matrix)
            # You can comment this out once you're done testing
            for r in self.game_map.solid_rects:
                Color(1, 0, 0, 0.4) 
                Rectangle(pos=(r[0], r[1]), size=(r[2], r[3]))
                
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
        
        self.player.move(self.pressed_keys, self.npcs, self.reaper, self.game_map.solid_rects)  # ส่ง npcs, reaper และ map_rects ไปด้วย
        
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
                # ลบ widget ข้อความและพื้นหลัง
                if self.dialogue_text:
                    if self.dialogue_text.parent:
                        self.dialogue_text.parent.remove_widget(self.dialogue_text)
                    self.dialogue_text = None
                if self.dialogue_bg:
                    if self.dialogue_bg.parent:
                        self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
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
        # สร้างพิกัดและรูปภาพจากข้อมูลเริ่มต้นใน npc.py
        npc_data = [
            'assets/NPC/NPC1.png',   # NPC 1
            'assets/NPC/NPC2.png',   # NPC 2
            'assets/NPC/NPC3.png',   # NPC 3
            'assets/NPC/NPC4.png',   # NPC 4
            'assets/NPC/NPC5.png'    # NPC 5
        ]
        
        for i in range(NPC_COUNT):
            img_path = npc_data[i]
            npc = NPC(self.canvas, image_path=img_path)
            self.npcs.append(npc)

    def create_enemies(self):
        # สร้างศัตรูชั่วคราว ดักจับตำแหน่งให้อยู่บน Grid ของช่อง 32x32 
        # ย้ายตำแหน่งศัตรูมาใกล้ๆ จุดเกิดตรงกลาง
        for x, y in ENEMY_START_POSITIONS:
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
        """แสดงข้อความคุยของ NPC สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        npc_name = f"NPC{self.npcs.index(npc) + 1}"
        self._draw_vn_dialogue_box(npc_name, dialogue)

    def show_dialogue_above_reaper(self, dialogue):
        """แสดงข้อความคุยของ Reaper สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self._draw_vn_dialogue_box("Reaper", dialogue)

    def show_vn_dialogue(self, character_name, dialogue):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self._draw_vn_dialogue_box(character_name, dialogue)

    def show_text_box(self, text, duration=3.0):
        """สร้างข้อความในกล่องข้อความ - ฟังก์ชันใหม่ที่ง่ายต่อการใช้งาน"""
        self._draw_vn_dialogue_box("", text)
        self.dialogue_timer = duration

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าข้อความคุยตามระยะห่างของ NPC"""
        dialogues = {
            "NPC1": [
                "สวัสดี! ยินดีที่ได้พบคุณ",
                "ฉันชอบที่นี่มาก... มันเงียบสงบ",
                "คุณเคยเห็น Reaper ตัวนั้นไหม?"
            ],
            "NPC2": [
                "โอ้... ทุกอย่างดูมืดมน",
                "ฉันรู้สึกหนาว... ช่วยฉันด้วย",
                "ไม่เคยคิดว่าจะมาถึงที่แห่งนี้"
            ],
            "NPC3": [
                "คุณมาจากไหนกัน?",
                "ที่นี่มีเรื่องลึกลับมากมาย",
                "ระวังศัตรูให้ดีๆ นะ"
            ],
            "NPC4": [
                "ฉันกำลังมองหาทางออก...",
                "คุณเห็นทางออกไหม?",
                "อย่าทอดทิ้งฉัน!"
            ],
            "NPC5": [
                "เราต้องร่วมมือกัน",
                "มีอะไรแปลกๆ เกิดขึ้นที่นี่",
                "เราจะผ่านไปได้แน่ๆ"
            ]
        }
        
        import random
        if npc_name in dialogues:
            return random.choice(dialogues[npc_name])
        return "..."

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าข้อความคุยของ Reaper"""
        dialogues = [
            "ความตายมาเยือน... แต่ยังไม่ถึงเวลาของเธอ",
            "ฉันไม่ใช่ศัตรู... ฉันมาเพื่อพาเธอไป",
            "โลกนี้มืดมน... แต่ยังมีความหวัง",
            "เธอกำลังมองหาคำตอบอยู่ใช่ไหม?",
            "ทุกชีวิตต้องจบลง... แต่ไม่ใช่วันนี้",
            "มาติดต่อกันซะบ้าง... มันเหงาเหลือเกิน"
        ]
        
        import random
        return random.choice(dialogues)

    def _draw_vn_dialogue_box(self, name, dialogue):
        """ฟังก์ชันตัวช่วยสำหรับวาดกล่องข้อความใน screen space (ไม่ถูก camera transform)"""
        # กำหนด root สำหรับวาด — ถ้า dialogue_root ถูก set โดย MyApp.build ให้ใช้นั้น
        # ถ้าไม่มีก็ fallback ไปใช้ self
        root = self.dialogue_root if self.dialogue_root else self

        # 1. ลบ widget เก่าทิ้ง
        if hasattr(self, 'dialogue_text') and self.dialogue_text:
            if self.dialogue_text.parent:
                self.dialogue_text.parent.remove_widget(self.dialogue_text)
            self.dialogue_text = None
        if hasattr(self, 'dialogue_bg') and self.dialogue_bg:
            if self.dialogue_bg.parent:
                self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None

        # 2. กำหนดขนาดกล่องข้อความ (สำหรับ Visual Novel Style)
        box_height = 150
        box_width = root.width - 40  # กว้างเกือบเต็มหน้าจอ
        padding = 20

        # 3. คำนวณตำแหน่งด้านล่างของหน้าจอ
        dialogue_x = (root.width - box_width) / 2
        dialogue_y = 20  # ห่างจากขอบล่าง 20 พิกเซล

        # 4. สร้าง Widget พื้นหลังสีดำ (วาดใน screen space)
        bg_widget = KivyWidget(
            size_hint=(None, None),
            size=(box_width, box_height),
            pos=(dialogue_x, dialogue_y)
        )
        with bg_widget.canvas:
            Color(0, 0, 0, 0.8)
            Rectangle(size=(box_width, box_height), pos=(0, 0))
        root.add_widget(bg_widget)
        self.dialogue_bg = bg_widget

        # 5. จัดรูปแบบข้อความ (แสดงชื่อและข้อความคุย)
        if name:
            formatted_text = f"[color=#ffff00]{name}:[/color] {dialogue}"
        else:
            formatted_text = dialogue

        # 6. สร้าง Label ให้พอดีกับกล่องข้อความ
        text_area_width = box_width - (padding * 2)
        text_area_height = box_height - (padding * 2)

        self.dialogue_text = Label(
            text=formatted_text,
            markup=True,
            font_name='assets/Fonts/edit-undo.brk.ttf',
            size_hint=(None, None),
            size=(text_area_width, text_area_height),
            text_size=(text_area_width, text_area_height),
            pos=(dialogue_x + padding, dialogue_y + padding),
            color=(1, 1, 1, 1),
            font_size=22,
            halign='left',
            valign='top'
        )

        root.add_widget(self.dialogue_text)
        self.dialogue_timer = 3.0

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
        
        # บอก GameWidget ว่า root layout คืออะไร เพื่อให้ dialogue box วาดใน screen space
        game.dialogue_root = root
        
        # นำ debug_label แปะที่ FloatLayout (UI หน้าจอจริงๆ) ให้พ้นจากกล้องซูม/หมุน
        game.debug_label.pos_hint = {'right': 0.95, 'top': 0.95}
        root.add_widget(game.debug_label)
        
        return root 

if __name__ == '__main__': 
    MyApp().run()