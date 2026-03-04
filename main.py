from kivy.config import Config
from settings import *

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'position', 'auto')
Config.set('graphics', 'multisampling', '2')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle, InstructionGroup
from kivy.uix.label import Label
from kivy.uix.widget import Widget 
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App 
from kivy.core.window import Window 
from kivy.clock import Clock 
from kivy.core.image import Image as CoreImage
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

from storygame.intro import IntroScreen # นำเข้าหน้าจอ Intro (Day 1)
from storygame.chat import NPC_DIALOGUES, REAPER_DIALOGUES, INTRO_DIALOGUE, DIALOGUE_CONFIG # นำเข้าข้อความและค่าตั้งค่า

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
        self.name_label = None           # Label สำหรับแสดงชื่อโดยเฉพาะ
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC
        self.is_paused = False
        self.pause_menu = None
        
        # Widget สำหรับ dialogue box ใน screen space (จะถูก attach โดย MyApp.build)
        self.dialogue_root = None

        # Draw Map Background
        with self.canvas.before:
            self.game_map = KivyTiledMap(MAP_FILE)
            self.game_map.draw_background(self.canvas.before)

        # 1. สร้าง Sorting Layer สำหรับตัวละคร (เพื่อให้วาดทับกันตามค่า Y)
        self.sorting_layer = InstructionGroup()
        self.canvas.add(self.sorting_layer)

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        
        # 2. สร้าง NPCs
        self.npcs = []
        self.create_npcs()
        
        # 3. สร้าง Reaper
        self.reaper = Reaper(self.sorting_layer)
        
        # 4. สร้าง Enemies
        self.enemies = []
        self.create_enemies()

        self.player = Player(self.sorting_layer)
        
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

        # ตรวจสอบว่าต้องขึ้นบทนำ (คุยกับ Reaper ทันที) หรือไม่
        if initial_data is None:
            Clock.schedule_once(self._start_intro_dialogue, 1.0)
            
        Clock.schedule_interval(self.move_step, 1.0 / FPS)  

    def _start_intro_dialogue(self, dt):
        """เริ่มบทสนทนาแรกของเกมกับ Reaper โดยดึงข้อความจาก chat.py"""
        # ตั้งทิศทางให้หันหน้าเข้าหากันตอนเริ่มเกม (Reaper อยู่ขวา Player อยู่ซ้าย)
        self.reaper.direction = 'left'
        self.reaper.update_frame()
        self.player.direction = 'right'
        self.player.update_frame()
        
        self.show_dialogue_above_reaper(INTRO_DIALOGUE)

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

        # 5. ทำ Y-Sorting เพื่อให้ตัวละครที่อยู่ "ล่าง" ทับตัวละครที่อยู่ "บน"
        self.y_sorting()

    def y_sorting(self):
        """จัดลำดับการวาดตัวละครตามค่า Y (Y-Sorting)"""
        # รวบรวมตัวละครทั้งหมดที่มีชีวิตอยู่
        sortable_chars = [self.player, self.reaper] + self.npcs + self.enemies
        
        # เรียงลำดับจาก Y มากไปน้อย (Kivy Y เริ่มจากล่างขึ้นบน ดังนั้น Y มากคืออยู่หลัง)
        # เราใช้จุดเท้า (logic_pos[1]) ในการตัดสิน
        sortable_chars.sort(key=lambda char: char.y if hasattr(char, 'y') else char.logic_pos[1], reverse=True)
        
        # ล้าง Layer แล้วใส่กลับเข้าไปใหม่ตามลำดับที่เรียงแล้ว
        self.sorting_layer.clear()
        for char in sortable_chars:
            if hasattr(char, 'group'):
                self.sorting_layer.add(char.group)

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
        """อัปเดตปุ่ม E สำหรับ NPC และ Reaper ที่อยู่ใกล้"""
        # ลบปุ่ม E เก่าทั้งหมด
        for hint in self.interaction_hints:
            if hasattr(hint, 'parent') and hint.parent:
                hint.parent.remove_widget(hint)
            else:
                try: self.canvas.remove(hint)
                except: pass
        self.interaction_hints.clear()
        
        player_pos = self.player.logic_pos
        player_cx, player_cy = player_pos[0] + TILE_SIZE/2, player_pos[1] + TILE_SIZE/2

        # 1. ตรวจสอบ NPC
        for i, npc in enumerate(self.npcs):
            npc_cx, npc_cy = npc.x + TILE_SIZE/2, npc.y + TILE_SIZE/2
            dist_x, dist_y = abs(player_cx - npc_cx), abs(player_cy - npc_cy)
            
            if (dist_x <= 4 and dist_y <= TILE_SIZE + 2) or (dist_y <= 4 and dist_x <= TILE_SIZE + 2):
                self._add_interaction_hint(npc.x + NPC_WIDTH/2, npc.y + NPC_HEIGHT + 40)
        
        # 2. ตรวจสอบ Reaper
        reaper_cx, reaper_cy = self.reaper.x + TILE_SIZE/2, self.reaper.y + TILE_SIZE/2
        rdist_x, rdist_y = abs(player_cx - reaper_cx), abs(player_cy - reaper_cy)
        
        if (rdist_x <= 4 and rdist_y <= TILE_SIZE + 2) or (rdist_y <= 4 and rdist_x <= TILE_SIZE + 2):
            self._add_interaction_hint(self.reaper.x + REAPER_WIDTH/2, self.reaper.y + REAPER_HEIGHT + 40)

    def _add_interaction_hint(self, x, y):
        """สร้างกราฟิกปุ่ม E เหนือตัวละคร"""
        size = (10, 10)
        off_x, off_y = int(x - size[0]/2), int(y)
        
        with self.canvas:
            # 1. วาดพื้นหลังปุ่ม (สีดำ Opacity 50% และมุมมน)
            Color(0, 0, 0, 0.5)
            # radius=[2] หมายถึงความมนของมุม 2 พิกเซล
            hint_bg = RoundedRectangle(pos=(off_x, off_y), size=size, radius=[2])
            self.interaction_hints.append(hint_bg)
            
            # 2. วาดตัวอักษร E (สีขาว คมชัดพรีเมียม)
            # สร้าง Label ชั่วคราวขนาดใหญ่เพื่อให้ได้ Font ที่สวยงาม
            temp_label = Label(text="E", font_name=GAME_FONT, font_size=40, color=(1, 1, 1, 1))
            temp_label.texture_update()
            text_tex = temp_label.texture
            
            # คำนวณขนาดโดยรักษา Aspect Ratio
            tw, th = text_tex.size
            max_inner = 7.0
            scale = min(max_inner / tw, max_inner / th)
            draw_w, draw_h = tw * scale, th * scale
            
            # จัดตำแหน่งกึ่งกลางในปุ่ม
            text_pos = (off_x + (size[0] - draw_w)/2, off_y + (size[1] - draw_h)/2)
            
            hint_text_rect = Rectangle(texture=text_tex, size=(draw_w, draw_h), pos=text_pos)
            self.interaction_hints.append(hint_text_rect)
                
    def create_npcs(self):
        # สร้างพิกัดและรูปภาพจากข้อมูลเริ่มต้นใน settings.py
        for i in range(min(NPC_COUNT, len(NPC_IMAGE_LIST))):
            img_path = NPC_IMAGE_LIST[i]
            npc = NPC(self.sorting_layer, image_path=img_path)
            self.npcs.append(npc)

    def create_enemies(self):
        # สร้างพิกัดและชนิดของศัตรูตามที่กำหนดใน settings.py
        for i, data in enumerate(ENEMY_SPAWN_DATA):
            x, y = data['pos']
            etype = data.get('type', 1)
            
            # ถ้าศัตรูตัวนี้ (ID ตาม index) ถูกกำจัดไปแล้วในเซฟนี้ ไม่ต้องสร้างใหม่
            if i in self.destroyed_enemies:
                continue
                
            enemy = Enemy(self.sorting_layer, x, y, enemy_id=i, enemy_type=etype)
            self.enemies.append(enemy)
    
    def check_npc_interaction(self):
        """ตรวจสอบว่า Player อยู่ใกล้ NPC หรือ Reaper และแสดงข้อความคุย"""
        target, target_type, npc_index, dist_x, dist_y = self.player.interact(self.npcs, self.reaper)
        
        if not target:
            print("ไม่มี NPC หรือ Reaper อยู่ใกล้ๆ")
            return

        # คำนวณตำแหน่งกึ่งกลางเพื่อหันหน้า
        player_pos = self.player.logic_pos
        player_center_x = player_pos[0] + TILE_SIZE / 2
        player_center_y = player_pos[1] + TILE_SIZE / 2
        
        target_center_x = target.x + (getattr(target, 'width', TILE_SIZE) - TILE_SIZE) / 2
        target_center_y = target.y + (getattr(target, 'height', TILE_SIZE) - TILE_SIZE) / 2

        # 1. จัดการ Reaper
        if target_type == "reaper":
            self.reaper.direction = 'left' # หันซ้ายตลอดตามคำขอ
            
            if dist_x > dist_y:
                if player_center_x > target_center_x:
                    self.player.direction = 'left'
                else:
                    self.player.direction = 'right'
            else:
                if player_center_y > target_center_y:
                    self.player.direction = 'down'
                else:
                    self.player.direction = 'up'
            
            self.reaper.frame_index = 0
            self.reaper.update_frame()
            self.player.update_frame()
            
            dialogue = self.get_reaper_dialogue(dist_x, dist_y)
            if dialogue:
                self.show_dialogue_above_reaper(dialogue)

        # 2. จัดการ NPC
        elif target_type == "npc":
            if dist_x > dist_y:
                if player_center_x > target_center_x:
                    target.direction = 'right'
                    self.player.direction = 'left'
                else:
                    target.direction = 'left'
                    self.player.direction = 'right'
            else:
                if player_center_y > target_center_y:
                    target.direction = 'up'
                    self.player.direction = 'down'
                else:
                    target.direction = 'down'
                    self.player.direction = 'up'
            
            target.frame_index = 0
            target.update_frame()
            self.player.update_frame()
            
            npc_name = "The Sad Soul" if npc_index == 0 else f"NPC{npc_index + 1}"
            dialogue = self.get_proximity_dialogue(npc_name, dist_x, dist_y)
            if dialogue:
                self.show_dialogue_above_npc(target, dialogue)
    
    def show_dialogue_above_npc(self, npc, dialogue):
        """แสดงข้อความคุยของ NPC สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # คำนวณชื่อ NPC - ถ้าเป็นตัวแรก (index 0) ให้ชื่อ "The Sad Soul"
        npc_name = "The Sad Soul" if self.npcs.index(npc) == 0 else f"NPC{self.npcs.index(npc) + 1}"
        
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
        # ลบ widget พื้นหลัง (โดยลูกๆ จะถูกลบตามไปด้วย)
        if self.dialogue_bg:
            if self.dialogue_bg.parent:
                self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None
            
        # เคลียร์ reference อื่นๆ
        self.dialogue_text = None
        self.name_label = None

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
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC (ดึงจาก chat.py)"""
        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper (ดึงจาก chat.py)"""
        import random
        # สุ่มเลือกข้อความ 3 ข้อจากลิสต์ที่ดึงมาจาก chat.py
        selected_dialogues = random.sample(REAPER_DIALOGUES, min(3, len(REAPER_DIALOGUES)))
        return selected_dialogues

    def _draw_vn_dialogue_box(self, name, dialogue):
        """วาดกล่องข้อความสไตล์ Visual Novel (ดึงค่าตั้งค่าจาก chat.py)"""
        root = self.dialogue_root if self.dialogue_root else self
        cfg = DIALOGUE_CONFIG

        # 1. ลบทิ้งหากมีของเดิมอยู่
        if self.dialogue_bg:
            if self.dialogue_bg.parent: self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None

        # 2. พื้นหลัง - ใช้ FloatLayout และ pos_hint เพื่อให้ชิดขอบล่างเสมอ
        bg_widget = FloatLayout(size_hint=(1, None), height=cfg["box_height"], pos_hint={'x': 0, 'y': 0})
        with bg_widget.canvas.before:
            Color(0, 0, 0, cfg["bg_opacity"])
            self.dialogue_bg_rect = Rectangle(size=bg_widget.size, pos=bg_widget.pos)
            
        def update_bg_rect(instance, value):
            if hasattr(self, 'dialogue_bg_rect'):
                self.dialogue_bg_rect.pos = instance.pos
                self.dialogue_bg_rect.size = instance.size
        bg_widget.bind(size=update_bg_rect, pos=update_bg_rect)
        
        root.add_widget(bg_widget)
        self.dialogue_bg = bg_widget

        # 3. ชื่อตัวละคร (ใส่ลงใน bg_widget เพื่อให้เคลื่อนที่ไปด้วยกัน)
        if name:
            self.name_label = Label(
                text=name,
                font_name=GAME_FONT,
                font_size=cfg["name_font_size"],
                color=cfg["name_color"],
                size_hint=(1, None),
                height=cfg["name_height"],
                pos_hint={'center_x': 0.5, 'top': 1 - (cfg["top_padding"] / cfg["box_height"])},
                halign='center',
                valign='middle'
            )
            self.name_label.bind(size=self.name_label.setter('text_size'))
            bg_widget.add_widget(self.name_label)

        # 4. ข้อความคุย (ใส่ลงใน bg_widget)
        text_top_ratio = (cfg["top_padding"] + cfg["name_height"] + cfg["msg_margin_top"]) / cfg["box_height"]
        
        self.dialogue_text = Label(
            text=dialogue,
            font_name=GAME_FONT,
            font_size=cfg["msg_font_size"],
            color=cfg["msg_color"],
            size_hint=(1, None),
            height=cfg["box_height"] * (1 - text_top_ratio) - 10,
            pos_hint={'center_x': 0.5, 'top': 1 - text_top_ratio},
            halign='center',
            valign='top'
        )
        
        def update_msg_text_size(instance, value):
            instance.text_size = (instance.width - (cfg["side_padding"] * 2), instance.height)
        self.dialogue_text.bind(size=update_msg_text_size)
        
        bg_widget.add_widget(self.dialogue_text)
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
        """แสดงเกมหลังจบหน้าปกเกม หรือหน้าโหลดเซฟ"""
        # ลบ splash screen หรือ UI ก่อนหน้า
        self.root.clear_widgets()
        
        # ถ้าไม่มีข้อมูลโหลด (คือเลือก New Game) ให้แสดงหน้าจอ Day 1 ก่อน
        if initial_data is None:
            intro = IntroScreen(callback=lambda: self._start_actual_game(initial_data))
            self.root.add_widget(intro)
        else:
            # ถ้าโหลดเซฟมา ให้ข้ามไปเริ่มเกมเลย
            self._start_actual_game(initial_data)

    def _start_actual_game(self, initial_data):
        """รันตรรกะการสร้างตัวเกมจริงๆ หลังจบ Intro หรือ Load"""
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