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
        self.current_choices = []        # เก็บรายการ Choice ปัจจุบัน
        self.name_label = None           # Label สำหรับแสดงชื่อโดยเฉพาะ
        self.choice_layout = None        # Widget ที่เก็บปุ่มทางเลือก
        self.choice_buttons = []         # ลิสต์เก็บปุ่มทางเลือก
        self.choice_index = 0            # ดัชนีตัวเลือกที่ถูกเลือกอยู่
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC
        self.stars = []             # เก็บวัตถุดาว (Day 1)
        self.current_star_target = None # เก็บดาวที่กำลังสำรวจ
        self.is_paused = False
        self.pause_menu = None
        
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
            # ตรวจสอบว่า Player อยู่ใกล้ NPC หรือ Star หรือไม่
            if not self.check_star_interaction():
                self.check_npc_interaction()
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
        if not (self.is_dialogue_active or self.is_paused):
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
            if self.reaper_collision_cooldown > 0:
                self.reaper_collision_cooldown -= dt
            
            # อัปเดตปุ่ม E
            self.update_interaction_hints()
        else:
            # ถ้าอยู่ในโหมดคุย/หยุดเกม ให้ตรวจสอบเพื่อล้าง Hint ที่อาจค้างอยู่
            if self.interaction_hints:
                self.update_interaction_hints()

        # 2. กราฟิกที่ต้องอัปเดตเสมอทุกลูกเฟรมเพื่อให้ภาพลื่นไหลและ Sync กับตำแหน่งล่าสุด
        px, py = self.player.logic_pos
        self.update_camera()
        self.game_map.update_chunks(px, py)
        
        # อัปเดต Debug Label
        grid_x, grid_y = px // TILE_SIZE, py // TILE_SIZE
        chunk_x, chunk_y = grid_x // 16, grid_y // 16
        self.debug_label.text = (
            f"FPS: {Clock.get_fps():.0f}\n"
            f"Pos: ({px}, {py})\n"
            f"Grid: ({grid_x}, {grid_y})\n"
            f"Chunk: ({chunk_x}, {chunk_y})"
        )
        
        # จัดเลเยอร์การวาดตัวละคร (Y-Sorting) เสมอ
        self.y_sorting()

    def y_sorting(self):
        """จัดลำดับการวาดตัวละครตามค่า Y (Y-Sorting)"""
        # หากกำลังคุยอยู่ และตัวละครไม่ขยับ (is_moving = False)
        # เราไม่จำเป็นต้องลำดับใหม่ทุกลูกเฟรมเพื่อลดการกระพริบ (Blinking)
        if self.is_dialogue_active and not self.player.is_moving:
            return

        # รวบรวมตัวละครและวัตถุทั้งหมดที่มีชีวิตอยู่
        sortable_chars = [self.player, self.reaper] + self.npcs + self.enemies + self.stars

        # เรียงลำดับจาก Y มากไปน้อย (Kivy Y เริ่มจากล่างขึ้นบน ดังนั้น Y มากคืออยู่หลัง)
        # เราใช้จุดเท้าในการตัดสิน และให้ Player มีลำดับความสำคัญสูงกว่าเล็กน้อยเมื่อยืนระนาบเดียวกัน (X-axis)
        def get_sort_y(char):
            base_y = char.y if hasattr(char, 'y') else char.logic_pos[1]
            # ถ้าเป็น Player ให้ลบนิดหน่อยเพื่อให้ถูกจัดไว้ทีหลัง (บนสุด) เมื่อ Y เท่ากัน
            if char == self.player:
                return base_y - 0.1
            return base_y

        sortable_chars.sort(key=get_sort_y, reverse=True)
        
        # ล้าง Layer แล้วใส่กลับเข้าไปใหม่ตามลำดับที่เรียงแล้ว
        self.sorting_layer.clear()
        for char in sortable_chars:
            if hasattr(char, 'group'):
                self.sorting_layer.add(char.group)

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
        
        # หากกำลังคุยอยู่ ไม่ต้องแสดงปุ่ม Hint
        if self.is_dialogue_active:
            return

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
            
        for x, y in STAR_SPAWN_LOCATIONS:
            # ตรวจสอบว่าดาวจุดนี้ถูกเก็บไปแล้วหรือยัง (ทั้งแบบ list และ tuple)
            if [x, y] in self.collected_stars or (x, y) in self.collected_stars:
                continue
            star = Star(self.sorting_layer, x, y)
            self.stars.append(star)

    def check_star_interaction(self):
        """ตรวจสอบการ Interact กับดาว"""
        px, py = self.player.logic_pos
        for star in self.stars:
            dist_x = abs(px - star.x)
            dist_y = abs(py - star.y)
            if dist_x <= TILE_SIZE and dist_y <= TILE_SIZE:
                # ตั้งเป้าหมายเป็นดาวดวงนี้
                self.current_star_target = star
                # แสดง Choice พร้อมชื่อ Little girl
                self._draw_vn_dialogue_box("Little girl", "Found a part of the doll. Pick it up?", choices=["PICK UP", "LEAVE IT"])
                return True
        return False
    
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
            if dist_x > dist_y:
                if player_center_x > target_center_x:
                    self.reaper.direction = 'right'
                    self.player.direction = 'left'
                else:
                    self.reaper.direction = 'left'
                    self.player.direction = 'right'
            else:
                if player_center_y > target_center_y:
                    self.reaper.direction = 'up'
                    self.player.direction = 'down'
                else:
                    self.reaper.direction = 'down'
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
            self._draw_vn_dialogue_box("Reaper", first_text, choices=(self.current_choices if is_last else None))

    def show_vn_dialogue(self, character_name, dialogue):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self._draw_vn_dialogue_box(character_name, dialogue)

    def show_item_discovery(self, text, image_path=None):
        """แสดงแจ้งเตือนการได้รับไอเทมกลางหน้าจอ"""
        root = self.dialogue_root if self.dialogue_root else self
        
        # สร้าง Layout เป็นแถบยาว (Banner) กลางจอ
        notif_banner = FloatLayout(size_hint=(1, 0.3), pos_hint={'center_x': 0.5, 'center_y': 0.55})
        
        with notif_banner.canvas.before:
            # พื้นหลังแถบดำจางๆ
            Color(0, 0, 0, 0.75)
            self.banner_rect = Rectangle(size=notif_banner.size, pos=notif_banner.pos)
            # เส้นขอบบน/ล่างเพิ่มความพรีเมียม
            Color(1, 1, 1, 0.1)
            self.line_top = Line(points=[0, 0, 0, 0], width=1)
            self.line_bottom = Line(points=[0, 0, 0, 0], width=1)
            
        def update_banner(instance, value):
            self.banner_rect.pos = instance.pos
            self.banner_rect.size = instance.size
            self.line_top.points = [instance.x, instance.top, instance.right, instance.top]
            self.line_bottom.points = [instance.x, instance.y, instance.right, instance.y]
        notif_banner.bind(size=update_banner, pos=update_banner)
        
        # 1. ข้อความประกาศ (อยู่ด้านบนสุดของแถบ)
        text_label = Label(
            text="FIND",
            font_name=GAME_FONT,
            font_size=36,
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=40,
            pos_hint={'center_x': 0.5, 'center_y': 0.78}, # ปรับระยะห่างระดับกลาง
            bold=True
        )

        # 2. กล่องรูปไอเทม (อยู่ด้านล่างข้อความ)
        item_size = 100
        item_box = Widget(size_hint=(None, None), size=(item_size, item_size), 
                         pos_hint={'center_x': 0.5, 'center_y': 0.33}) # ปรับระยะห่างระดับกลาง
        
        with item_box.canvas:
            # ใช้แสงเรืองสีขาว (White Glow)
            Color(1, 1, 1, 0.15)
            self.glow_rect = Ellipse(size=(item_size*1.6, item_size*1.6))
            # ตัวสี่เหลี่ยมไอเทม
            Color(1, 1, 1, 1)
            self.item_icon_rect = Rectangle(size=(item_size, item_size))
            
        def update_item_pos(instance, value):
            self.glow_rect.pos = (instance.center_x - (item_size*0.8), instance.center_y - (item_size*0.8))
            self.item_icon_rect.pos = instance.pos
        item_box.bind(pos=update_item_pos, size=update_item_pos)
        
        notif_banner.add_widget(text_label)
        notif_banner.add_widget(item_box)
        root.add_widget(notif_banner)
        
        def remove_notif(dt):
            if notif_banner.parent:
                notif_banner.parent.remove_widget(notif_banner)
        Clock.schedule_once(remove_notif, 2.0)

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

        # ลบวิดเจ็ตทางเลือก (ถ้ามี) - เรียกใช้จาก choice.py
        clear_choices(self)

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
            "day": self.current_day, 
            "heart": self.heart_ui.current_health,
            "destroyed_enemies": self.destroyed_enemies,
            "collected_stars": self.collected_stars,
            "quests": self.quest_manager.to_dict(),
            "play_time": self.play_time,
            "warning_dismissed": self.warning_dismissed  # เซฟข้ามวัน/โหลดใหม่ให้หมอกหายถาวร
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
        # ถ้ามี Choice และเป็นหน้าสุดท้าย ห้ามกดข้าม
        if self.current_choices and self.current_dialogue_index == len(self.current_dialogue_queue) - 1:
            return

        self.current_dialogue_index += 1
        
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            # แสดงข้อความถัดไป
            next_text = self.current_dialogue_queue[self.current_dialogue_index]
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self._draw_vn_dialogue_box(self.current_character_name, next_text, choices=(self.current_choices if is_last else None))
        else:
            # หมดข้อความแล้ว ปิดกล่องข้อความ
            self.close_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC (ดึงจาก chat.py)"""
        # ถ้าเป็น The Sad Soul ให้เช็คสถานะเควส
        if npc_name == "The Sad Soul":
            quest = self.quest_manager.active_quests.get("doll_parts")
            if quest:
                if quest.current_count >= quest.target_count:
                    # ถ้าเก็บครบแล้วแต่ยังไม่ได้ส่ง
                    return [
                        "Oh! You found them!",
                        "My doll... it's whole again. Thank you so much!",
                        "You really are a kind one."
                    ]
                elif quest.is_active:
                    # ถ้ายังเก็บไม่ครบ
                    return ["Were you able to find the pieces? It's still so dark..."]

        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper (ดึงจาก chat.py)"""
        import random
        # สุ่มเลือกข้อความ 3 ข้อจากลิสต์ที่ดึงมาจาก chat.py
        selected_dialogues = random.sample(REAPER_DIALOGUES, min(3, len(REAPER_DIALOGUES)))
        return selected_dialogues

    def _draw_vn_dialogue_box(self, name, dialogue, choices=None):
        """วาดกล่องข้อความสไตล์ Visual Novel (ดึงค่าตั้งค่าจาก chat.py)"""
        root = self.dialogue_root if self.dialogue_root else self
        cfg = DIALOGUE_CONFIG
        
        # อัปเดตรายการ Choice ปัจจุบันให้ GameWidget รู้ (ป้องกัน IndexError)
        self.current_choices = choices if choices else []

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

        # 3. ชื่อตัวละคร
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

        # 4. ข้อความคุย
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

        # 5. Choices (ปุ่มเลือก)
        if choices:
            draw_choice_buttons(self, choices)

        self.is_dialogue_active = True

    def on_choice_selected(self, choice):
        """จัดการเมื่อผู้เล่นเลือก Choice (เรียกใช้ตรรกะจาก choice.py)"""
        handle_choice_selection(self, choice)

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