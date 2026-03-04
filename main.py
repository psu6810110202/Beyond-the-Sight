from kivy.config import Config
from settings import *

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'position', 'auto')
Config.set('graphics', 'multisampling', '2')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.graphics import Color, Rectangle, Ellipse
from kivy.uix.label import Label
from kivy.uix.widget import Widget as KivyWidget
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App 
from kivy.uix.widget import Widget 
from kivy.core.window import Window 
from kivy.clock import Clock 
import os # นำเข้า os สำหรับจัดการโฟลเดอร์เซฟ

from characters.player import Player
from characters.npc import NPC
from characters.reaper import Reaper
from characters.enemy import Enemy

from assets.Heart.heart import HeartUI
from assets.Tiles.map_loader import KivyTiledMap

from menu.load import SaveLoadScreen # นำเข้าหน้าจอเซฟ
from menu.screen import SplashScreen
from menu.camera import Camera
from menu.pause import PauseMenu

class GameWidget(Widget): 
    def __init__(self, initial_data=None, **kwargs): 
        super().__init__(**kwargs) 
        self.initial_data = initial_data
        
        # จัดการข้อมูลศัตรูที่ถูกกำจัดไปแล้ว (ไม่เกิดใหม่)
        self.destroyed_enemies = initial_data.get('destroyed_enemies', []) if initial_data else []

        # Setup Camera
        self.camera = Camera(self.canvas.before)

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
        self.is_dialogue_active = False  # เพิ่มสถานะการคุย
        self.current_dialogue_queue = []  # คิวข้อความสำหรับการคุยแบบหลายบรรทัด
        self.current_dialogue_index = 0  # ดัชนีข้อความปัจจุบัน
        self.current_character_name = ""  # ชื่อตัวละครที่กำลังคุย
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC
        self.is_paused = False
        self.pause_menu = None
        
        # Widget สำหรับ dialogue box ใน screen space (จะถูก attach โดย MyApp.build)
        self.dialogue_root = None

        # Draw Map Background (Floor, Walls, etc) - in the background layer
        with self.canvas.before:
            self.game_map = KivyTiledMap(MAP_FILE)
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
                
        self.camera.end_camera(self.canvas.after)
            
        initial_health = initial_data.get('heart', 3) if initial_data else 3
        # สร้างคลาสหัวใจโดยส่ง canvas และเลือดเริ่มต้นเข้าไป
        self.heart_ui = HeartUI(self.canvas, initial_health=initial_health)
            
        # Initial chunk update setup
        self.game_map.update_chunks(self.player.logic_pos[0], self.player.logic_pos[1])
            
        # Ensure UI updates position correctly on window resize AFTER everything is created
        self.bind(size=self.update_ui_positions)
        
        # Manually force the first UI positioning update
        self.update_ui_positions()
            
        Clock.schedule_interval(self.move_step, 1.0 / FPS)  

    def request_keyboard_back(self):
        """ขอคีย์บอร์ดกลับมาให้ GameWidget อีกครั้ง (ใช้หลังปิดเมนู/หน้าจอโหลด)"""
        if self._keyboard:
            self._on_keyboard_closed()
            
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 
        # เคลียร์ปุ่มที่ค้างอยู่ป้องกันตัวละครเดินค้าง
        self.pressed_keys.clear()

    def update_camera(self):
        self.camera.update(
            self.width, self.height,
            self.player.logic_pos,
            self.game_map.width,
            self.game_map.height
        )

    def update_ui_positions(self, *args):
        # เรียกปรับตำแหน่งของหัวใจเมื่อหน้าจอมีการเปลี่ยนแปลงขนาด
        if getattr(self, 'heart_ui', None):
            self.heart_ui.update_position(self.width, self.height)

    def _on_keyboard_closed(self): 
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)  
            self._keyboard.unbind(on_key_up=self._on_key_up) 
            self._keyboard = None 

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1]
        key_code = keycode[0]
        print(f"Key pressed: {key_name} (code: {key_code})")  # Debug: แสดงปุ่มที่กด
        
        if key_name == 'e':
            print("E key detected - checking NPC interaction")
            # ตรวจสอบว่า Player อยู่ใกล้ NPC หรือไม่
            self.check_npc_interaction()
        elif key_name == 'enter':
            print("Enter key detected - next dialogue")
            # ถ้ากำลังคุยอยู่ ให้ไปข้อความถัดไป
            if self.is_dialogue_active:
                self.next_dialogue()
        elif key_name == 'escape':
            self.toggle_pause()
            return True

        self.pressed_keys.add(key_name)
        return True
        
    def _on_key_up(self, keyboard, keycode): 
        key_name = keycode[1] 
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)

    def move_step(self, dt):
        self.update_camera()
        
        # ถ้ากำลังคุยหรือพักเกมอยู่ ให้หยุดการอัปเดตเกม
        if self.is_dialogue_active or self.is_paused:
            return
        
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
        
        # Update Player's Stamina Bar
        self.heart_ui.update_stamina(self.player.get_stamina_ratio())
        
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
        
        # ใช้ logic_pos ของผู้เล่นสำหรับการคำนวณระยะห่าง
        player_pos = self.player.logic_pos
        
        # Update Enemies
        # ใช้ [:] เพื่อคัดลอกลิสต์ ป้องกันการ error ขณะลบไอเทมในลูป
        for enemy in self.enemies[:]:
            reaper_pos = (self.reaper.x, self.reaper.y)
            enemy.update(dt, player_pos, reaper_pos)
            if enemy.check_player_collision_logic(self.player.logic_pos, TILE_SIZE):
                # บันทึก ID ศัตรูที่โดนทำลายลงในลิสต์ (เพื่อไม่ให้เกิดใหม่ตอนโหลดเซฟ)
                self.destroyed_enemies.append(enemy.id)
                
                enemy.destroy()           # ลบรูปสี่เหลี่ยมออกจากจอ
                self.enemies.remove(enemy) # ลบตรรกะศัตรูออกจากระบบ
                self.heart_ui.take_damage() # ลดเลือดผู้เล่น
                print(f"Enemy {enemy.id} attacked player and was removed!")

    def toggle_pause(self):
        """Toggle pause state and show/hide pause menu."""
        if self.is_paused:
            self.resume_game()
        else:
            self.pause_game()

    def pause_game(self):
        """หยุดเกมและแสดงเมนู"""
        if self.is_paused: return
        self.is_paused = True
        
        # เคลียร์ปุ่มที่ค้างอยู่ป้องกันตัวละครเดินค้างเมื่อพักเกม
        self.pressed_keys.clear()
        
        # สร้างเมนู Pause
        self.pause_menu = PauseMenu(
            resume_cb=self.resume_game,
            load_cb=self.load_game_from_pause,
            menu_cb=self.return_to_main_menu,
            exit_cb=self.exit_game
        )
        # นำไปแปะที่ป้ายบนสุด (dialogue_root คือ FloatLayout ของ App)
        if self.dialogue_root:
            self.dialogue_root.add_widget(self.pause_menu)

    def resume_game(self):
        """กลับเข้าสู่เกม"""
        if not self.is_paused: return
        self.is_paused = False
        
        if self.pause_menu:
            self.pause_menu.close()
            self.pause_menu = None
            
        # ขอคีย์บอร์ดกลับมาให้ GameWidget (ฟังก์ชันนี้มีการเคลียร์ปุ่มค้างให้แล้ว)
        self.request_keyboard_back()

    def load_game_from_pause(self):
        """เปิดหน้าจอโหลดเซฟจากเมนู Pause"""
        load_screen = SaveLoadScreen(
            mode="LOAD", 
            callback=self._on_pause_load_selected
        )
        if self.dialogue_root:
            self.dialogue_root.add_widget(load_screen)

    def _on_pause_load_selected(self, slot_id, load_screen=None):
        import json
        save_path = f'saves/slot_{slot_id}.json'
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                data = json.load(f)
            
            # ปิดเมนูและหน้าจอโหลด
            if load_screen: load_screen.close()
            self.resume_game()
            
            # รีเซ็ตเกมด้วยข้อมูลใหม่ (เรียก show_game ของ App)
            app = App.get_running_app()
            app.show_game(initial_data=data)

    def return_to_main_menu(self):
        """กลับไปหน้าจอหลัก (Title Screen)"""
        self.resume_game()
        app = App.get_running_app()
        app.root.clear_widgets()
        
        # สร้าง SplashScreen ใหม่
        from menu.screen import SplashScreen
        splash = SplashScreen(
            SPLASH_COVER_IMG,
            app.show_game
        )
        app.root.add_widget(splash)

    def exit_game(self):
        """ออกจากเกม"""
        Window.close()
                    
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
        # สร้างพิกัดและรูปภาพจากข้อมูลเริ่มต้นใน settings.py
        for i in range(min(NPC_COUNT, len(NPC_IMAGE_LIST))):
            img_path = NPC_IMAGE_LIST[i]
            npc = NPC(self.canvas, image_path=img_path)
            self.npcs.append(npc)

    def create_enemies(self):
        # สร้างพิกัดและชนิดของศัตรูตามที่กำหนดใน settings.py
        for i, data in enumerate(ENEMY_SPAWN_DATA):
            x, y = data['pos']
            etype = data.get('type', 1)
            
            # ถ้าศัตรูตัวนี้ (ID ตาม index) ถูกกำจัดไปแล้วในเซฟนี้ ไม่ต้องสร้างใหม่
            if i in self.destroyed_enemies:
                continue
                
            enemy = Enemy(self.canvas, x, y, enemy_id=i, enemy_type=etype)
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
        
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        self.current_character_name = npc_name
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            first_text = self.current_dialogue_queue[0]
            self._draw_vn_dialogue_box(npc_name, first_text)

    def show_dialogue_above_reaper(self, dialogue):
        """แสดงข้อความคุยของ Reaper สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        self.current_character_name = "Reaper"
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            first_text = self.current_dialogue_queue[0]
            self._draw_vn_dialogue_box("Reaper", first_text)

    def show_vn_dialogue(self, character_name, dialogue):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self._draw_vn_dialogue_box(character_name, dialogue)

    def show_text_box(self, text, duration=3.0):
        """สร้างข้อความในกล่องข้อความ - ฟังก์ชันใหม่ที่ง่ายต่อการใช้งาน"""
        self._draw_vn_dialogue_box("", text)
        self.dialogue_timer = duration

    def close_dialogue(self):
        """ปิดกล่องข้อความคุยและคืนสถานะเกม"""
        # ลบ widget ข้อความและพื้นหลัง
        if self.dialogue_text:
            if self.dialogue_text.parent:
                self.dialogue_text.parent.remove_widget(self.dialogue_text)
            self.dialogue_text = None
        if self.dialogue_bg:
            if self.dialogue_bg.parent:
                self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None

        # จำชื่อตัวละครไว้ก่อนรีเซ็ต
        last_character = self.current_character_name
        
        # คืนสถานะการคุย
        self.is_dialogue_active = False
        self.dialogue_timer = 0
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        
        # ถ้าคุยกับ Reaper จบ ให้เปิดหน้าจอเซฟ
        if last_character == "Reaper":
            self.show_save_screen()

    def show_save_screen(self):
        """เปิดหน้าจอเลือกสล็อตเพื่อเซฟเกม"""
        save_screen = SaveLoadScreen(
            mode="SAVE",
            callback=self.on_save_confirmed
        )
        # นำไปแปะไว้ใน dialogue_root (FloatLayout หลัก)
        if self.dialogue_root:
            self.dialogue_root.add_widget(save_screen)

    def on_save_confirmed(self, slot_id, save_screen=None):
        # สร้างโฟลเดอร์ saves ถ้ายังไม่มี
        if not os.path.exists('saves'):
            os.makedirs('saves')
            
        # เก็บข้อมูลจริงจากตัวเกม
        import json
        save_data = {
            "day": 1, 
            "heart": self.heart_ui.current_health,
            "destroyed_enemies": self.destroyed_enemies
        }
        
        file_path = f'saves/slot_{slot_id}.json'
        with open(file_path, 'w') as f:
            json.dump(save_data, f)
            
        print(f"Game saved to Slot {slot_id}: {save_data}")
        
        # ปิดหน้าจอเซฟทันทีและกลับสู่เกม
        if save_screen:
            save_screen.close()
        
        # คืนค่าสถานะเพื่อให้ตัวละครเดินได้และรับคีย์บอร์ดได้อีกครั้ง
        self.is_dialogue_active = False
        self.request_keyboard_back()

    def next_dialogue(self):
        """ไปยังข้อความถัดไปในคิว"""
        self.current_dialogue_index += 1
        
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            # แสดงข้อความถัดไป
            next_text = self.current_dialogue_queue[self.current_dialogue_index]
            self._draw_vn_dialogue_box(self.current_character_name, next_text)
        else:
            # หมดข้อความแล้ว ปิดกล่องข้อความ
            self.close_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC"""
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
        
        if npc_name in dialogues:
            return dialogues[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper"""
        dialogues = [
            "ความตายมาเยือน... แต่ยังไม่ถึงเวลาของเธอ",
            "ฉันไม่ใช่ศัตรู... ฉันมาเพื่อพาเธอไป",
            "โลกนี้มืดมน... แต่ยังมีความหวัง",
            "เธอกำลังมองหาคำตอบอยู่ใช่ไหม?",
            "ทุกชีวิตต้องจบลง... แต่ไม่ใช่วันนี้",
            "มาติดต่อกันซะบ้าง... มันเหงาเหลือเกิน"
        ]
        
        import random
        # สุ่มเลือกข้อความ 3 ข้อจากลิสต์
        selected_dialogues = random.sample(dialogues, min(3, len(dialogues)))
        return selected_dialogues

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
        box_height = 200  # เพิ่มความสูง
        box_width = root.width  # กว้างเต็มจอตาม root widget
        padding = 20

        # 3. คำนวณตำแหน่งให้ตามด้านล่างของหน้าจอ
        dialogue_x = 0  # เริ่มต้นที่ขอบซ้ายสุด
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
            font_name=GAME_FONT,
            size_hint=(None, None),
            size=(text_area_width, text_area_height),
            text_size=(text_area_width, text_area_height),
            pos=(dialogue_x + padding, dialogue_y + padding),
            color=(1, 1, 1, 1),
            font_size=30,  # เพิ่มขนาดฟอนต์
            halign='left',
            valign='top'
        )

        root.add_widget(self.dialogue_text)
        
        # ตั้งค่าสถานะการคุย
        self.is_dialogue_active = True

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
        self.root = FloatLayout()
        
        # แสดงหน้าจอปกเกมที่เริ่มเล่น (กด Enter เพื่อเริ่ม)
        splash = SplashScreen(
            SPLASH_COVER_IMG,
            self.show_game
        )
        self.root.add_widget(splash)
        
        return self.root
    
    def show_game(self, initial_data=None):
        """แสดงเกมหลังจบหน้าปกเกม"""
        # ลบ splash screen
        self.root.clear_widgets()
        
        # สร้างตัวเกมโดยส่งข้อมูลเริ่มต้นไป (ถ้ามี)
        game = GameWidget(initial_data=initial_data)
        self.root.add_widget(game)
        
        # บอก GameWidget ว่า root layout คืออะไร เพื่อให้ dialogue box วาดใน screen space
        game.dialogue_root = self.root
        
        # นำ debug_label แปะที่ FloatLayout (UI หน้าจอจริงๆ) ให้พ้นจากกล้องซูม/หมุน
        game.debug_label.pos_hint = {'right': 0.95, 'top': 0.95}
        self.root.add_widget(game.debug_label) 

    def on_start(self):
        # ผูกเหตุการณ์คีย์บอร์ดระดับ Window เพื่อให้กด F11 ได้ทุกหน้าจอ
        Window.bind(on_key_down=self._on_window_key_down)

    def _on_window_key_down(self, window, key, scancode, codepoint, modifiers):
        # 292 คือ keycode ของ F11, 27 คือ keycode ของ Escape
        if key == 27:
            # ตรวจสอบว่ามี GameWidget อยู่ใน root หรือไม่
            has_game = any(isinstance(c, GameWidget) for c in self.root.children)
            if not has_game:
                # ถ้าอยู่หน้า SplashScreen (หน้าแรก) ให้ปิดโปรแกรมทันที
                Window.close()
                return True
            # ถ้าอยู่ในเกม ให้ส่งต่อ (Return False) เพื่อให้ GameWidget หรือหน้าจออื่นจัดการเปิด Pause Menu
            return False
        
        if key == 292:
            print("F11 detected (Global) - toggling fullscreen")
            if Window.fullscreen:
                Window.fullscreen = False
            else:
                Window.fullscreen = 'auto'
            return True # บอกว่าประมวลผลคีย์นี้แล้ว
        return False
        
if __name__ == '__main__': 
    MyApp().run()