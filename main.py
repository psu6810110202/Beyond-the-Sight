from kivy.config import Config
from settings import *

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'position', 'auto')
Config.set('graphics', 'multisampling', '2')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle, InstructionGroup, Line
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
from storygame.chat import NPC_DIALOGUES, REAPER_DIALOGUES, INTRO_DIALOGUE, WARNING_DIALOGUE, WARNING_CHOICES, DIALOGUE_CONFIG # นำเข้าข้อความและค่าตั้งค่า
from storygame.choice import handle_choice_selection, draw_choice_buttons, clear_choices, update_choice_visuals # นำเข้าการจัดการ Choice
from storygame.story import is_npc_visible, check_story_triggers # นำเข้าตรรกะเนื้อเรื่อง
from storygame.quest import QuestManager # นำเข้าหน้าจอกองเควส
from storygame.dialogue_manager import DialogueManager # นำเข้า Dialogue Manager มารวมศูนย์ UI
from items.star import Star # นำเข้า Star

class GameWidget(Widget): 
    def __init__(self, initial_data=None, **kwargs): 
        super().__init__(**kwargs) 
        self.initial_data = initial_data
        
        # จัดการข้อมูลศัตรูที่ถูกกำจัดไปแล้ว (ไม่เกิดใหม่)
        self.destroyed_enemies = initial_data.get('destroyed_enemies', []) if initial_data else []
        self.collected_stars = initial_data.get('collected_stars', []) if initial_data else []
        
        # สถานะวันปัจจุบัน (ค่าเริ่มต้นคือ Day 1)
        self.current_day = initial_data.get('current_day', 1) if initial_data else 1
        self.warning_triggered = False # ป้องกันแจ้งเตือนรัว
        self.warning_dismissed = initial_data.get('warning_dismissed', False) if initial_data else False # โหลดสถานะการผ่านทางจากเซฟ
        
        # ระบบเวลาเล่น (Play Time)
        self.play_time = initial_data.get('play_time', 0) if initial_data else 0
        
        # เก็บค่าความสำเร็จของเควส (มีผลต่อฉากจบ)
        self.quest_success_count = initial_data.get('quest_success_count', 0) if initial_data else 0

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

        # ระบบจัดการ UI บทสนทนา
        self.dialogue_manager = DialogueManager(self)
        self.dialogue_timer = 0
        self.is_dialogue_active = False
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        self.current_choices = []
        self.choice_layout = None
        self.choice_buttons = []
        self.choice_index = 0
        
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC
        self.stars = []             # เก็บวัตถุดาว (Day 1)
        self.current_star_target = None # เก็บดาวที่กำลังสำรวจ
        self.is_paused = False
        self.pause_menu = None
        
        # Cutscene states
        self.is_cutscene_active = False
        self.cutscene_timer = 0
        self.cutscene_step = 0
        self.black_overlay = None
        
        # Widget สำหรับ dialogue box ใน screen space (จะถูก attach โดย MyApp.build)
        self.dialogue_root = None

        # 1. สร้าง Sorting Layer สำหรับตัวละคร (เพื่อให้วาดทับกันตามค่า Y)
        # ต้องสร้างก่อน Quest/Stars เผื่อมีการโหลดเซฟแล้วเรียกใช้ทันที
        self.sorting_layer = InstructionGroup()
        self.canvas.add(self.sorting_layer)
        
        # จัดการเควส
        self.quest_manager = QuestManager(self)
        if initial_data and 'quests' in initial_data:
            self.quest_manager.from_dict(initial_data['quests'])
            # ถ้าโหลดมาระหว่างทำเควสดวงดาว ให้สร้างดาวขึ้นมา
            if "doll_parts" in self.quest_manager.active_quests:
                quest = self.quest_manager.active_quests["doll_parts"]
                if quest.is_active:
                    self.create_stars()

        # Draw Map
        with self.canvas.before:
            self.game_map = KivyTiledMap(MAP_FILE)
            
            # 1. วาดพื้นดินและวัตถุบนแผนที่ (Ground + Background)
            self.game_map.draw_ground(self.canvas.before)
            self.game_map.draw_background(self.canvas.before)

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
        
        # 5. Stars จะถูกสร้างหลังคุยกับ NPC1

        self.player = Player(self.sorting_layer)
        
        # Draw Map Foreground (Roofs, hanging objects, etc) - in the foreground layer
        with self.canvas.after:
            self.game_map.draw_foreground(self.canvas.after)
            
            # 5. สร้างเลเยอร์หมอกสีดำ (Darkness Overlay) ให้ทับทุกอย่างยกเว้น UI
            self.darkness_group = InstructionGroup()
            self.canvas.after.add(self.darkness_group)
                
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

        # สร้างหมอกครั้งแรกตามสถานะปัจจุบัน
        self.refresh_darkness()

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
            print("E key detected - checking interaction")
            self.interact()
        elif key_name == 'enter':
            print("Enter key detected - next dialogue")
            # ถ้ากำลังคุยอยู่
            if self.is_dialogue_active:
                # ถ้ามี Choice ให้เลือกตัวเลือกที่ไฮไลท์อยู่
                if self.choice_buttons:
                    # ตรวจสอบว่าดัชนีอยู่ในขอบเขตของ current_choices หรือไม่
                    if self.choice_index < len(self.current_choices):
                        self.on_choice_selected(self.current_choices[self.choice_index])
                    else:
                        print(f"Warning: choice_index {self.choice_index} out of range for current_choices")
                        self.close_dialogue()
                else:
                    self.next_dialogue()
        
        # จัดการการเลื่อน Choice ด้วยลูกศร ขึ้น/ลง
        elif self.is_dialogue_active and self.choice_buttons:
            if key_name == 'up':
                self.choice_index = (self.choice_index - 1) % len(self.choice_buttons)
                update_choice_visuals(self)
                return True
            elif key_name == 'down':
                self.choice_index = (self.choice_index + 1) % len(self.choice_buttons)
                update_choice_visuals(self)
                return True
        
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
        # 1. จัดการตรรกะเกม (Logic) - ทำงานเฉพาะเมื่อไม่ได้คุยหรือหยุดเกม
        if self.is_cutscene_active:
            self.update_cutscene(dt)
        elif not (self.is_dialogue_active or self.is_paused):
            self.play_time += dt
            
            # การเคลื่อนที่ของตัวละคร
            self.player.move(self.pressed_keys, self.npcs, self.reaper, self.game_map.solid_rects)
            self.heart_ui.update_stamina(self.player.get_stamina_ratio())
            
            # ตรวจสอบจุดเงื่อนไขเนื้อเรื่อง (Snap ตำแหน่งจะเกิดขึ้นที่นี่หากชนพิกัด)
            check_story_triggers(self)
            
            # อัปเดต NPCs / Reaper / Enemies
            for npc in self.npcs:
                npc.update(dt)
            self.reaper.update(dt, self.player.logic_pos)
            
            for enemy in self.enemies[:]:
                reaper_pos = (self.reaper.x, self.reaper.y)
                enemy.update(dt, self.player.logic_pos, reaper_pos)
                if enemy.check_player_collision_logic(self.player.logic_pos, TILE_SIZE):
                    self.destroyed_enemies.append(enemy.id)
                    enemy.destroy()
                    self.enemies.remove(enemy)
                    self.heart_ui.take_damage()

            if not hasattr(self, 'reaper_collision_cooldown'):
                self.reaper_collision_cooldown = 0
            
            # อัปเดต NPC
            for npc in self.npcs:
                npc.update(dt)
                
            # เช็คการโต้ตอบ (Interactive Hints)
            self.update_interaction_hints()
            
            # เช็คพื้นที่อันตราย (Story Triggers)
            check_story_triggers(self)
        else:
            # ถ้าอยู่ในโหมดคุย/หยุดเกม ให้ตรวจสอบเพื่อล้าง Hint ที่อาจค้างอยู่
            if self.interaction_hints:
                self.update_interaction_hints()

        # 2. กราฟิกที่ต้องอัปเดตเสมอทุกลูกเฟรม
        px, py = self.player.logic_pos
        self.update_camera()
        self.game_map.update_chunks(px, py)
        
        # อัปเดต Debug Label
        self._update_debug_text(px, py)
        
        # จัดเลเยอร์การวาดตัวละคร (Y-Sorting)
        self.y_sorting()

    def _update_debug_text(self, px, py):
        """อัปเดตข้อมูล Debug ที่มุมจอ"""
        grid_x, grid_y = px // TILE_SIZE, py // TILE_SIZE
        chunk_x, chunk_y = grid_x // 16, grid_y // 16
        self.debug_label.text = (
            f"FPS: {Clock.get_fps():.0f}\n"
            f"Pos: ({px}, {py})\n"
            f"Grid: ({grid_x}, {grid_y})\n"
            f"Chunk: ({chunk_x}, {chunk_y})"
        )

    def y_sorting(self):
        """จัดลำดับการวาดตัวละครตามค่า Y (Y-Sorting)"""
        if self.is_dialogue_active and not self.player.is_moving:
            return

        sortable_chars = [self.player, self.reaper] + self.npcs + self.enemies + self.stars
        
        def get_sort_y(char):
            base_y = char.y if hasattr(char, 'y') else char.logic_pos[1]
            if char == self.player:
                return base_y - 0.1
            return base_y

        sortable_chars.sort(key=get_sort_y, reverse=True)
        self.sorting_layer.clear()
        for char in sortable_chars:
            if hasattr(char, 'group'):
                self.sorting_layer.add(char.group)

    def update_camera(self):
        """อัปเดตตำแหน่งกล้องตามผู้เล่น"""
        self.camera.update(
            self.width, self.height,
            self.player.logic_pos,
            self.game_map.width,
            self.game_map.height
        )

    # ---------------------------------------------------------
    # Interaction & Triggers
    # ---------------------------------------------------------
    def update_interaction_hints(self):
        """จัดการแสดงผลปุ่ม [E] ขึ้นเหนือหัว NPC หรือไอเทม เมื่อเดินไปใกล้"""
        # 1. ลบ Hint เก่าออกก่อนเสมอ (รวมถึงตอนกำลังคุยด้วยเพื่อไม่ให้ปุ่มค้าง)
        for hint in self.interaction_hints:
            if hint.parent:
                hint.parent.remove_widget(hint)
        self.interaction_hints = []
        
        # 2. ถ้ากำลังคุย, หยุดเกม หรืออยู่ใน Cutscene ไม่ต้องสร้าง Hint ใหม่
        if self.is_dialogue_active or self.is_paused or self.is_cutscene_active:
            return
            
        # 3. ค้นหาเป้าหมายที่อยู่ใกล้
        targets = self.npcs + [self.reaper] + self.stars
        self.current_star_target = None 
        
        # ระยะที่เริ่มเห็นปุ่ม (32 พิกเซล = 2 Tiles)
        interaction_dist = 32 
        
        for tar in targets:
            tx, ty = tar.logic_pos
            px, py = self.player.logic_pos
            dx, dy = tx - px, ty - py
            dist = (dx**2 + dy**2)**0.5
            
            # ตรรกะการหันหน้าเข้าหาเป้าหมาย
            facing = False
            p_dir = self.player.direction
            # ตรวจสอบว่าทิศทางที่ผู้เล่นหันไปสัมพันธ์กับตำแหน่งเป้าหมายหรือไม่
            if p_dir == 'up' and dy > 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'down' and dy < 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'left' and dx < 0 and abs(dx) >= abs(dy): facing = True
            elif p_dir == 'right' and dx > 0 and abs(dx) >= abs(dy): facing = True

            # ปรับระยะการตรวจสอบให้ต่างกัน: ของต้องอยู่ชิดกว่า (20px) ตัวละคร (32px)
            is_star = isinstance(tar, Star)
            limit = 20 if is_star else 32
            
            if dist < limit and facing:
                if is_star:
                    self.current_star_target = tar
                    continue # ไม่ต้องวาดปุ่ม E สำหรับดวงดาวตามคำสั่งก่อนหน้า
                
                hint_text = "E"
                box_width = 25
                    
                hint = Label(
                    text=hint_text,
                    font_name=GAME_FONT,
                    font_size='12sp',
                    color=(1, 1, 1, 1),
                    size_hint=(None, None),
                    size=(box_width, 25),
                    halign='center',
                    valign='middle',
                    bold=True
                )
                
                # ฟิกค่าให้ Label จัดข้อความตรงกลางจริงๆ 
                # (Kivy ต้องการการผูก text_size กับ size เพื่อให้ halign/valign ทำงาน)
                hint.bind(size=lambda l, s: setattr(l, 'text_size', s))
                
                # พื้นหลังสีดำแบบปุ่มกด
                with hint.canvas.before:
                    Color(0, 0, 0, 0.8)
                    hint.bg_rect = RoundedRectangle(pos=hint.pos, size=hint.size, radius=[3])
                
                def update_hint_bg(instance, value):
                    instance.bg_rect.pos = instance.pos
                    instance.bg_rect.size = instance.size
                hint.bind(pos=update_hint_bg)
                
                # คำนวณตำแหน่งกึ่งกลางของเป้าหมายจริง (World Space)
                target_center_x = tx + (TILE_SIZE / 2)
                target_top_y = ty + 45
                
                # แปลงเป็นพิกัดหน้าจอ
                spos = self.camera.world_to_screen(target_center_x, target_top_y)
                
                # วาง Hint โดยให้จุดกลางของ Hint (box_width/2) ตรงกับ spos[0]
                hint.pos = (spos[0] - (box_width / 2), spos[1])
                
                if self.dialogue_root:
                    self.dialogue_root.add_widget(hint)
                self.interaction_hints.append(hint)

    def interact(self):
        """จัดการการกดปุ่ม [E] เพื่อคุยหรือสำรวจ"""
        px, py = self.player.logic_pos
        
        # 1. เช็คเป้าหมายไอเทม (Stars)
        # current_star_target จะถูกเซ็ตใน update_interaction_hints เฉพาะเมื่ออยู่ใกล้และหันหน้าเข้าหา
        if self.current_star_target:
            self.dialogue_manager.show_vn_dialogue("Curiosity", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"])
            return

        # 2. เช็คเป้าหมาย NPC / Reaper
        targets = self.npcs + [self.reaper]
        for npc_index, target in enumerate(targets):
            tx, ty = target.logic_pos
            dx, dy = tx - px, ty - py
            dist = (dx**2 + dy**2)**0.5
            
            # ตรวจสอบว่าผู้เล่นหันหน้าเข้าหาเป้าหมายหรือไม่
            facing = False
            p_dir = self.player.direction
            if p_dir == 'up' and dy > 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'down' and dy < 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'left' and dx < 0 and abs(dx) >= abs(dy): facing = True
            elif p_dir == 'right' and dx > 0 and abs(dx) >= abs(dy): facing = True
            
            # ต้องอยู่ห่างไม่เกิน 32 พิกเซล และหันหน้าเข้าหา
            if dist < 32 and facing:
                self.process_interaction(target, npc_index, dx, dy)
                return

    def process_interaction(self, target, index, dx, dy):
        """ประมวลผลการคุยกับ NPC หรือ Reaper"""
        # หันหน้าเข้าหากัน
        if abs(dx) > abs(dy):
            if dx > 0:
                target.direction = 'left'
                self.player.direction = 'right'
            else:
                target.direction = 'right'
                self.player.direction = 'left'
        else:
            if dy > 0:
                target.direction = 'down'
                self.player.direction = 'up'
            else:
                target.direction = 'up'
                self.player.direction = 'down'
        
        target.update_frame()
        self.player.update_frame()
        
        if isinstance(target, Reaper):
            dialogue = self.get_reaper_dialogue(dx, dy)
            self.show_dialogue_above_reaper(dialogue)
        else:
            # NPC
            npc_name = "The Sad Soul" if index == 0 else f"NPC{index + 1}"
            dialogue = self.get_proximity_dialogue(npc_name, dx, dy)
            if dialogue:
                self.show_dialogue_above_npc(target, dialogue)

    # ---------------------------------------------------------
    # Dialogue & Quest Logic
    # ---------------------------------------------------------
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
            self.dialogue_manager.show_vn_dialogue(npc_name, first_text)
            
    def show_dialogue_above_reaper(self, dialogue, choices=None):
        """แสดงข้อความคุยของ Reaper สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        self.current_character_name = "Reaper"
        self.current_choices = choices if choices else []
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            first_text = self.current_dialogue_queue[0]
            # แสดง Choice เฉพาะเมื่ออยู่หน้าสุดท้าย
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self.dialogue_manager.show_vn_dialogue("Reaper", first_text, choices=(self.current_choices if is_last else None))

    def show_vn_dialogue(self, character_name, dialogue):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self.dialogue_manager.show_vn_dialogue(character_name, dialogue)

    def show_item_discovery(self, text, image_path=None):
        """แสดงแจ้งเตือนการได้รับไอเทมกลางหน้าจอ (Delegated)"""
        self.dialogue_manager.show_item_discovery(text, image_path)
        root = self.dialogue_root if self.dialogue_root else self
        
    def close_dialogue(self):
        """ปิดกล่องข้อความคุยและคืนสถานะเกม"""
        self.dialogue_manager.close_dialogue()

        # จำสถานะ Choice ไว้ก่อนรีเซ็ต
        last_character = self.current_character_name
        has_choices = len(self.current_choices) > 0
        
        # คืนสถานะการคุย
        self.is_dialogue_active = False
        self.dialogue_timer = 0
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        self.current_choices = []
        
        # ถ้าคุยกับ Reaper จบ ให้เปิดหน้าจอเซฟ (ยกเว้นตอนที่เป็นการเตือนแบบมี Choice)
        if last_character == "Reaper" and not has_choices:
            self.show_save_screen()
            
        # ถ้าคุยกับ Angel จบ ให้ปิด Cutscene
        if last_character == "Angel":
            self.end_cutscene()
            
        # ถ้าคุยกับ NPC "The Sad Soul" จบ ให้เริ่มเควสและสร้างดาว
        if last_character == "The Sad Soul":
            quest = self.quest_manager.active_quests.get("doll_parts")
            if not quest:
                # เริ่มเควสครั้งแรก
                self.quest_manager.start_quest("doll_parts", "Find doll parts", target=3)
                self.create_stars() # ดาวจะโผล่มาหลังคุยจบ
            elif quest.is_active and quest.current_count >= quest.target_count:
                # ถ้าคุยจบหลังจากเก็บครบแล้ว ให้จบเควสจริงๆ
                quest.is_active = False
                self.quest_manager.show_quest_notification("COMPLETED: FIND DOLL PARTS")
                self.quest_manager.update_quest_list_ui()
                
                # ลบ NPC1 (The Sad Soul) ออกจากฉากทันที
                for npc in self.npcs[:]:
                    if "NPC1" in npc.image_path:
                        if hasattr(npc, 'group') and npc.group in self.sorting_layer.children:
                            self.sorting_layer.remove(npc.group)
                        self.npcs.remove(npc)
                        break
                
                # เริ่ม Cutscene หลังจากจบเควส 2 วินาที
                Clock.schedule_once(self.start_quest_complete_cutscene, 2.0)

    def next_dialogue(self):
        """ไปยังข้อความถัดไปในคิว"""
        if self.current_choices and self.current_dialogue_index == len(self.current_dialogue_queue) - 1:
            return

        self.current_dialogue_index += 1
        
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            next_text = self.current_dialogue_queue[self.current_dialogue_index]
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self.dialogue_manager.show_vn_dialogue(self.current_character_name, next_text, choices=(self.current_choices if is_last else None))
        else:
            self.close_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC"""
        if npc_name == "The Sad Soul":
            quest = self.quest_manager.active_quests.get("doll_parts")
            if quest:
                if quest.current_count >= quest.target_count:
                    return ["Oh! You found them!", "My doll... it's whole again. Thank you so much!", "You really are a kind one."]
                elif quest.is_active:
                    return ["Were you able to find the pieces? It's still so dark..."]

        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper"""
        import random
        selected_dialogues = random.sample(REAPER_DIALOGUES, min(3, len(REAPER_DIALOGUES)))
        return selected_dialogues

    def on_choice_selected(self, choice):
        """จัดการเมื่อผู้เล่นเลือก Choice (เรียกใช้ตรรกะจาก choice.py)"""
        handle_choice_selection(self, choice)

    # ---------------------------------------------------------
    # Game State Management (Pause, Save/Load)
    # ---------------------------------------------------------
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
        # นำไปแปะที่ป้ายบนสุด (index=0 เพื่อให้อยู่หน้าสุดของทุกอย่าง)
        if self.dialogue_root:
            self.dialogue_root.add_widget(self.pause_menu, index=0)

    def resume_game(self):
        """กลับเข้าสู่เกม"""
        if not self.is_paused: return
        self.is_paused = False
        
        if self.pause_menu:
            self.pause_menu.close()
            self.pause_menu = None
            
        # ขอคีย์บอร์ดกลับมาให้ GameWidget (ฟังก์ชันนี้มีการเคลียร์ปุ่มค้างให้แล้ว)
        self.request_keyboard_back()

    def show_save_screen(self):
        """เปิดหน้าจอเลือกสล็อตเพื่อเซฟเกม"""
        save_screen = SaveLoadScreen(
            mode="SAVE",
            callback=self.on_save_confirmed
        )
        if self.dialogue_root:
            self.dialogue_root.add_widget(save_screen)

    def on_save_confirmed(self, slot_id, save_screen=None):
        if not os.path.exists('saves'):
            os.makedirs('saves')
            
        import json
        save_data = {
            "day": self.current_day, 
            "heart": self.heart_ui.current_health,
            "destroyed_enemies": self.destroyed_enemies,
            "collected_stars": self.collected_stars,
            "quests": self.quest_manager.to_dict(),
            "play_time": self.play_time,
            "quest_success_count": self.quest_success_count,
            "warning_dismissed": self.warning_dismissed
        }
        
        file_path = f'saves/slot_{slot_id}.json'
        with open(file_path, 'w') as f:
            json.dump(save_data, f)
            
        if save_screen:
            save_screen.close()
        
        self.is_dialogue_active = False
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
                    
    # ---------------------------------------------------------
    # Entity Creation & Management
    # ---------------------------------------------------------
    def create_npcs(self):
        # สร้างพิกัดและรูปภาพจากข้อมูลเริ่มต้นใน settings.py
        for i in range(min(NPC_COUNT, len(NPC_IMAGE_LIST))):
            # ตรรกะการแสดง NPC ตามวัน (ดึงมาจาก story.py)
            if not is_npc_visible(self, i):
                continue
                
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
            
    def create_stars(self):
        """สร้างดาวตามพิกัดที่กำหนดใน Day 1"""
        if self.current_day != 1:
            return
            
        for i, (x, y) in enumerate(STAR_SPAWN_LOCATIONS):
            # ตรวจสอบว่าดาวจุดนี้ถูกเก็บไปแล้วหรือยัง (ทั้งแบบ list และ tuple)
            if [x, y] in self.collected_stars or (x, y) in self.collected_stars:
                continue
            
            # กำหนดว่าดวงไหนเป็นของที่ใช่ (True) หรือของหลอก (False)
            # ตัวอย่าง: 3 ดวงแรกเป็นของจริง ดวงที่เหลือเป็นของหลอก
            is_true = (i < 3)
            
            star = Star(self.sorting_layer, x, y, is_true=is_true)
            self.stars.append(star)

    # ---------------------------------------------------------
    # Visual Effects
    # ---------------------------------------------------------
    def refresh_darkness(self):
        """วาดหรือล้างหมอกสีดำปิดโซนอันตรายแบบไล่สี"""
        if not hasattr(self, 'darkness_group') or self.darkness_group is None:
            return
            
        self.darkness_group.clear()
        
        # แสดงโซนดำเฉพาะเมื่อยังไม่กด "I'll go"
        if not self.warning_dismissed:
            # 1. ตั้งค่าความเข้มหลัก
            base_alpha = 0.4
            fade_range = 160 # ระยะการไล่สี
            
            # โซนอันตรายตามเนื้อเรื่อง Day 1 (อิง x=656 และ y=464)
            if self.current_day == 1:
                # จุดเริ่มความมืดที่แท้จริง (ถอยเข้าไปในโซนอันตรายเพื่อให้พื้นที่เดินได้สว่างไสว)
                dark_x_start = 656 - fade_range
                dark_y_start = 464 + fade_range
                
                # --- ส่วนที่ 1: พื้นที่มืด (Solid Blocks) - ถอยลึกเข้าไปข้างใน ---
                self.darkness_group.add(Color(0, 0, 0, base_alpha))
                # ปิดแมพทางด้านซ้ายสุด (ก่อนถึงจุดไล่สี)
                self.darkness_group.add(Rectangle(pos=(0, 0), size=(dark_x_start, MAP_HEIGHT)))
                # ปิดแมพทางด้านบนสุด (ก่อนถึงจุดไล่สี)
                self.darkness_group.add(Rectangle(pos=(dark_x_start, dark_y_start), size=(MAP_WIDTH - dark_x_start, MAP_HEIGHT - dark_y_start)))
                
                # --- ส่วนที่ 2: การไล่สี (Gradient) - ไล่ให้จางหายสนิทที่จุด Trigger ---
                fade_steps = 10
                step_size = fade_range / fade_steps
                
                for i in range(fade_steps):
                    # จะค่อยๆ จางลงเรื่อยๆ จนเป็น 0 (ใสสนิท) เมื่อถึงค่า 656 หรือ 464
                    alpha = base_alpha * (1 - (i / fade_steps))
                    self.darkness_group.add(Color(0, 0, 0, alpha))
                    
                    # ไล่สีจากซ้ายมาขวา (จะจางหายสนิทที่ x=656 พอดี)
                    self.darkness_group.add(Rectangle(pos=(dark_x_start + (i * step_size), 0), size=(step_size, dark_y_start)))
                    
                    # ไล่สีจากบนลงล่าง (จะจางหายสนิทที่ y=464 พอดี)
                    self.darkness_group.add(Rectangle(pos=(dark_x_start, dark_y_start - ((i+1) * step_size)), size=(MAP_WIDTH - dark_x_start, step_size)))

            # รีเซ็ตสีกลับเป็นปกติ
            self.darkness_group.add(Color(1, 1, 1, 1))

    # ---------------------------------------------------------
    # Cutscenes Logic
    # ---------------------------------------------------------
    def start_quest_complete_cutscene(self, dt):
        """เริ่มลำดับ Cutscene เมื่อจบเควส"""
        self.is_cutscene_active = True
        self.cutscene_step = 1 # ขั้นตอนเดินออกจากจอ
        self.camera.locked = True # ล็อกกล้องให้อยู่กับที่
        
    def update_cutscene(self, dt):
        """จัดการลำดับของ Cutscene"""
        if self.cutscene_step == 1:
            # ตัวละครเดินไปทางขวาเอง
            keys = {'right'}
            self.player.current_speed = WALK_SPEED
            # ไม่เช็คชนกับอะไรทั้งสิ้นเพื่อให้เดินออกจากจอได้แน่นอน
            self.player.move(keys)
            
            # ตรวจสอบว่าออกจากจองหรือยัง (คำนวณจากตำแหน่งกล้องที่ล็อกไว้)
            # ดึงตำแหน่งกล้องจริงจาก Translate (ติดลบเพราะเป็นจุดศูนย์กลาง)
            cam_x = -self.camera.trans_pos.x
            viewport_w = CAMERA_WIDTH 
            right_edge = cam_x + (viewport_w / 2)
            
            if self.player.logic_pos[0] > right_edge:
                self.cutscene_step = 2
                self.show_black_screen_transition()

    def show_black_screen_transition(self):
        """แสดงฉากสีดำและบทสนทนาของ Angel"""
        root = self.dialogue_root if self.dialogue_root else self
        
        # 1. สร้างพื้นหลังสีดำทับทั้งจอ
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, Rectangle
        
        self.black_overlay = Widget(size_hint=(1, 1))
        with self.black_overlay.canvas:
            Color(0.12, 0.12, 0.12, 1) # สีเทาเข้ม (Dark Grey) แทนจอดำ
            Rectangle(size=(2000, 2000), pos=(-500, -500)) # คลุมให้มิด
            
        root.add_widget(self.black_overlay)
        
        # 2. ขึ้นบทสนทนาสไตล์ VN แต่พื้นหลังดำ
        # ตรวจสอบความสำเร็จของเควสล่าสุด
        # ใน Day 1 เควสที่ 1 (doll_parts) เป้าหมายคือ 3
        # ถ้า quest_success_count >= 3 แสดงว่าเก็บของจริงครบ
        if self.quest_success_count >= 3:
            angel_text = [
                "You still hold the light in your hands, little one...",
                "Though this place is shrouded in darkness, your kindness has saved that soul.",
                "Go and rest now. You will need your strength for tomorrow."
            ]
        else:
            angel_text = [
                "Your hands are trembling... It’s alright.",
                "Sometimes, destiny is too heavy for a child to carry alone.",
                "Let’s go home for now. We can always start again tomorrow."
            ]
        
        # ตั้งค่าคิวข้อความสำหรับ Angel
        self.current_dialogue_queue = angel_text
        self.current_dialogue_index = 0
        self.current_character_name = "Angel"
        self.is_dialogue_active = True
        
        # แสดงข้อความแรก
        self._draw_vn_dialogue_box("Angel", angel_text[0])
        
        # เมื่อคุยจบ Angel จะต้องปิด Cutscene (ผ่าน close_dialogue ที่เช็คชื่อ Angel)
        
    # เราต้องแก้ close_dialogue เพิ่มเพื่อรองรับการปิดฉากของ Angel
    
    def end_cutscene(self):
        """จบ Cutscene และเคลียร์ state"""
        if self.black_overlay:
            if self.black_overlay.parent:
                self.black_overlay.parent.remove_widget(self.black_overlay)
            self.black_overlay = None
            
        self.is_cutscene_active = False
        self.cutscene_step = 0
        self.camera.locked = False
        
        # ขึ้น Day 2 (หรือวันถัดไป)
        self.current_day += 1
        intro = IntroScreen(callback=self.recreate_world, day=self.current_day)
        if self.dialogue_root:
            self.dialogue_root.add_widget(intro)

    def recreate_world(self):
        """รีเฟรชโลกใหม่สำหรับวันถัดไป (NPCs, หมอก, ดาว)"""
        # 1. ล้าง NPCs, Enemies, Stars เก่าออก
        for npc in self.npcs:
            if hasattr(npc, 'group') and npc.group in self.sorting_layer.children:
                self.sorting_layer.remove(npc.group)
        self.npcs = []
        
        for enemy in self.enemies:
            if hasattr(enemy, 'group') and enemy.group in self.sorting_layer.children:
                self.sorting_layer.remove(enemy.group)
        self.enemies = []
        
        for star in self.stars:
            if hasattr(star, 'group') and star.group in self.sorting_layer.children:
                self.sorting_layer.remove(star.group)
        self.stars = []
        
        # 1.5 รีเซ็ตพิกัดตัวละครมาที่จุดเริ่มต้นเหมือนวันแรก
        start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
        start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
        self.player.logic_pos = [start_x, start_y]
        self.player.target_pos = [start_x, start_y]
        self.player.direction = 'up'
        self.player.sync_graphics_pos()
        self.player.update_frame()
        
        # 2. สร้างใหม่ตามวันปัจจุบัน
        self.create_npcs()
        self.create_enemies()
        self.create_stars()
        
        # 3. อัปเดตหมอก (Darkness Overlay)
        self.refresh_darkness()
        
        # 4. ขอคีย์บอร์ดคืน
        self.request_keyboard_back()

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
        
        # อัปเดต UI เควสเพื่อให้ไปอยู่ใน root ที่ถูกต้อง (กรณีโหลดเซฟ)
        game.quest_manager.update_quest_list_ui(animate=False)
        
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