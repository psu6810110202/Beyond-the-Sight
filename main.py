from kivy.config import Config
from settings import *

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'position', 'auto')
Config.set('graphics', 'multisampling', '0')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('input', 'wm_pen', ' ')
Config.set('input', 'wm_touch', ' ')
# ซ่อนเมาส์เมื่ออยู่ในจอเกม
from kivy.core.window import Window
Window.show_cursor = False

from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle, InstructionGroup, Line, StencilPush, StencilUse, StencilUnUse, StencilPop
from kivy.uix.label import Label
from kivy.uix.widget import Widget 
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App 
from kivy.clock import Clock 
from kivy.animation import Animation
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
import os 
import json
import random

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
from storygame.chat import NPC_DIALOGUES, REAPER_DIALOGUES, REAPER_DEATH_QUOTES, INTRO_DIALOGUE, WARNING_DIALOGUE, WARNING_CHOICES, DIALOGUE_CONFIG # นำเข้าข้อความและค่าตั้งค่า
from storygame.choice import handle_choice_selection, draw_choice_buttons, clear_choices, update_choice_visuals # นำเข้าการจัดการ Choice
from storygame.story import StoryManager # นำเข้า Story Manager
from storygame.quest import QuestManager # นำเข้าหน้าจอกองเควส
from storygame.dialogue_manager import DialogueManager # นำเข้า Dialogue Manager มารวมศูนย์ UI
from items.star import Star # นำเข้า Star
from storygame.world import WorldManager
from storygame.save import SaveManager
from storygame.cutscene import CutsceneManager
class GameWidget(Widget): 
    def __init__(self, initial_data=None, **kwargs): 
        super().__init__(**kwargs) 
        self.initial_data = initial_data
        
        # จัดการข้อมูลศัตรูที่ถูกกำจัดไปแล้ว (ไม่เกิดใหม่)
        self.destroyed_enemies = initial_data.get('destroyed_enemies', []) if initial_data else []
        self.collected_stars = initial_data.get('collected_stars', []) if initial_data else []
        self.has_received_blue_stone = initial_data.get('has_received_blue_stone', False) if initial_data else False
        
        # สถานะวันปัจจุบัน (ค่าเริ่มต้นคือ Day 1)
        self.current_day = initial_data.get('current_day', 1) if initial_data else 1
        self.warning_triggered = False # ป้องกันแจ้งเตือนรัว
        self.warning_dismissed = initial_data.get('warning_dismissed', False) if initial_data else False # โหลดสถานะการผ่านทางจากเซฟ
        self.tutorial_triggered = initial_data.get('tutorial_triggered', False) if initial_data else False
        self.tutorial_mode = False # สถานะชั่วคราวบอกว่ากำลังเล่นบทเรียนสอนใช้ของหรือไม่
        
        # ระบบเวลาเล่น (Play Time)
        self.play_time = initial_data.get('play_time', 0) if initial_data else 0
        
        # เก็บค่าความสำเร็จของเควส (มีผลต่อฉากจบ)
        self.quest_success_count = initial_data.get('quest_success_count', 0) if initial_data else 0
        self.quest_item_fail = initial_data.get('quest_item_fail', False) if initial_data else False
        self.death_count = initial_data.get('death_count', 0) if initial_data else 0
        self.last_death_quote_index = -1

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
        self.story_manager = StoryManager(self)
        self.world_manager = WorldManager(self)
        self.save_manager = SaveManager(self)
        self.cutscene_manager = CutsceneManager(self)
        self.dialogue_timer = 0
        self.is_dialogue_active = False # คืนสถานะการคุย
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        self.current_choices = []
        self.current_portrait = None
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
        
        # Stun Cooldown
        self.stun_cooldown = 0
        
        # ป้องกันการเดินตอนเริ่มเกมที่ยังโหลดไม่เสร็จ (Stutter prevention เฉพาะเริ่มเกมใหม่)
        if initial_data is None:
            self.is_ready = False
            Clock.schedule_once(self._set_game_ready, 0.5) # เริ่มเกมใหม่รอแป๊บนึง
        else:
            self.is_ready = True # โหลดเซฟให้เดินได้ทันที
            
        # เคลียร์ปุ่มค้างเสมอ
        self.current_search_target = None
        self.is_forced_moving = False
        self.forced_move_target = None
        
        # สุ่มจุดที่มีของกินจริงๆ แค่ 1 จุดจากรายการ
        self.correct_food_spot = random.choice(SEARCHABLE_SPOTS_HOME)
        
        # โหลดเสียงผีไล่ตามประเภท
        self.ghost_sounds = {}
        sound_files = {
            1: 'assets/sound/ghost/Ghost chior.wav',
            2: 'assets/sound/ghost/Ghost_scream_3.wav',
            3: 'assets/sound/ghost/Ghost_moan_2.wav'
        }
        for etype, path in sound_files.items():
            s = SoundLoader.load(path)
            if s:
                s.loop = True
                s.volume = 0.4 if etype == 1 else 0.5 # ปรับ volume ตามความเหมาะสม
                self.ghost_sounds[etype] = s

        # 1. สร้าง Sorting Layer สำหรับตัวละคร (เพื่อให้วาดทับกันตามค่า Y)
        # ต้องสร้างก่อน Quest/Stars เผื่อมีการโหลดเซฟแล้วเรียกใช้ทันที
        self.sorting_layer = InstructionGroup()
        self.canvas.add(self.sorting_layer)

        # 1.1 สร้างระบบ Clipping เพื่อตัดส่วนเกืนของแมพ (Stencil)
        # จะถูกแปะลงใน canvas.before ให้เริ่มหลังจาก Camera PushMatrix
        self.stencil_push = StencilPush()
        self.canvas.before.add(self.stencil_push)
        
        # สี่เหลี่ยมระบุขอบเขตที่จะให้วาด (จะอัปเดตขนาดตามขนาดแมพจริงใน change_map)
        self.clip_rect = Rectangle(pos=(0, 0), size=(0, 0))
        self.canvas.before.add(self.clip_rect)
        
        self.stencil_use = StencilUse()
        self.canvas.before.add(self.stencil_use)

        # 1.2 สร้าง Containers สำหรับแผนที่ (รับผิดชอบการล้างและโหลดใหม่ได้คลีน)
        self.map_before_group = InstructionGroup()
        self.canvas.before.add(self.map_before_group)
        self.map_after_group = InstructionGroup()
        self.canvas.after.add(self.map_after_group)
        
        # จัดการเควส
        self.quest_manager = QuestManager(self)
        if initial_data and 'quests' in initial_data:
            self.quest_manager.from_dict(initial_data['quests'])
            # ถ้าโหลดมาระหว่างทำเควสดวงดาว ให้สร้างดาวขึ้นมา
            if "doll_parts" in self.quest_manager.active_quests:
                quest = self.quest_manager.active_quests["doll_parts"]
                if quest.is_active:
                    self.create_stars()
        
        # 1.2 เลือกและโหลดแผนที่ (ดึงจากเซฟถ้ามี ไม่เช่นนั้นใช้แผนที่หลัก)
        starting_map = MAP_FILE
        start_pos = [PLAYER_START_X, PLAYER_START_Y]
        
        if initial_data:
            starting_map = initial_data.get('current_map', MAP_FILE)
            if 'player_pos' in initial_data:
                start_pos = initial_data['player_pos']

        self.game_map = KivyTiledMap(starting_map)
        
        # วาดพื้นดินและวัตถุลงใน Container
        # อัปเดตขนาด Clipping Rectangle ตามขนาดแมพใหม่
        map_w_px = self.game_map.width * TILE_SIZE
        map_h_px = self.game_map.height * TILE_SIZE
        self.clip_rect.size = (map_w_px, map_h_px)
        
        self.map_before_group.add(Color(1, 1, 1, 1))
        self.game_map.draw_ground(self.map_before_group)
        self.game_map.draw_background(self.map_before_group)
        self.game_map.draw_foreground(self.map_before_group)
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

        # 5. สร้างตัวละครหลัก (ใช้พิกัดจากเซฟถ้ามี)
        self.player = Player(self.sorting_layer, x=start_pos[0], y=start_pos[1])
        
        # Draw Map Foreground ใน Container ใหม่
        self.map_after_group.add(Color(1, 1, 1, 1)) # รับประกันสีปกติ
        self.game_map.draw_roof(self.map_after_group)
            
        # 5. สร้างเลเยอร์หมอกสีดำ (Darkness Overlay) ให้ทับทุกอย่างยกเว้น UI
        self.darkness_group = InstructionGroup()
        self.canvas.after.add(self.darkness_group)

        # ปิด Stencil ก่อน PopMatrix ของกล้อง
        self.canvas.after.add(StencilUnUse())
        self.canvas.after.add(self.clip_rect)
        self.canvas.after.add(StencilPop())
                
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
            self.is_dialogue_active = True # ล็อกการขยับตั้งแต่วินาทีแรกของ New Game
            Clock.schedule_once(self._start_intro_dialogue, 0.3)
            
        # สถานะช่วงรอยต่อวัน
        self._pending_day_transition = False

        # เริ่มลูปเกม
        self._main_loop_event = Clock.schedule_interval(self.move_step, 1.0 / FPS)  

    def _set_game_ready(self, dt):
        """ปลดล็อกให้ผู้เล่นเดินได้หลังจากเริ่มเกมไปแล้ว 1 วินาที"""
        self.is_ready = True
        self.pressed_keys.clear() # เคลียร์ปุ่มที่อาจกดค้างไว้ตอนโหลด
        print("Game is now ready!")

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



    def update_ui_positions(self, *args):
        # เรียกปรับตำแหน่งของหัวใจเมื่อหน้าจอมีการเปลี่ยนแปลงขนาด
        if getattr(self, 'heart_ui', None):
            self.heart_ui.update_position(self.width, self.height)
        
        # เรียกปรับสเกลของแชท/บทสนทนา
        if getattr(self, 'dialogue_manager', None):
            self.dialogue_manager.update_ui_scaling()

    def _on_keyboard_closed(self): 
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)  
            self._keyboard.unbind(on_key_up=self._on_key_up) 
            self._keyboard = None 

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1]
        key_code = keycode[0]
        print(f"Key pressed: {key_name} (code: {key_code})")  # Debug: แสดงปุ่มที่กด
        
        if key_name == 'e' or key_name == 'enter':
            # 1. ถ้ามีแจ้งเตือนไอเทมอยู่ ให้ปิดแจ้งเตือนก่อน
            if self.dialogue_manager.is_item_notif_active:
                self.dialogue_manager.close_item_discovery()
                # ถ้ากำลังคุยค้างอยู่ (กรณีได้รับไอเทมกลางบทสนทนา) ให้แสดงบทสนทนาต่อทันที
                if self.is_dialogue_active:
                    self.next_dialogue()
                return True
        
        # คีย์ Q สำหรับกดใช้ไอเทม Blue Stone (แยกจากปุ่มคุยเพื่อไม่ให้สับสน)
        if key_name == 'q':
            if self.has_received_blue_stone:
                if self.stun_cooldown <= 0:
                    self.use_stun_item()
                else:
                    print(f"Stun on cooldown: {self.stun_cooldown:.1f}s")
            return True

        if key_name == 'e':
            # ถ้ากำลังคุยอยู่ ให้ปุ่ม E ทำหน้าที่เดียวกับ Enter คือไปประโยคถัดไป (ไม่ interact ซ้อน)
            if self.is_dialogue_active:
                if not self.choice_buttons: # ถ้าไม่มี choice ให้กด E ไปต่อได้
                    self.next_dialogue()
                return True
                
            print("E key detected - checking interaction")
            self.interact()
        elif key_name == 'enter':
            print("Enter key detected - next dialogue")
            
            # 2. ถ้ากำลังคุยอยู่
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
        try:
            self._move_step_logic(dt)
        except Exception as e:
            # ใช้ print ให้เห็น Error ใน console ชัดๆ
            import traceback
            print(f"DEBUG ERROR in move_step: {e}")
            traceback.print_exc()

    def _move_step_logic(self, dt):
        # ป้องกันอาการ 'กระโดด' หลังจากการชะงักโหลด (Cap DT)
        dt = min(dt, 0.05)
        
        # 1. จัดการตรรกะเกม (Logic) - ทำงานเฉพาะเมื่อไม่ได้คุยหรือหยุดเกม
        if self.is_cutscene_active:
            self.update_cutscene(dt)
        elif not (self.is_dialogue_active or self.is_paused or not self.is_ready):
            self.play_time += dt
            
            # 1. การเคลื่อนที่ของตัวละคร
            self.player.move(self.pressed_keys, self.npcs, self.reaper, self.game_map.solid_rects)
            self.heart_ui.update_stamina(self.player.get_stamina_ratio())
            
            # อัปเดต NPCs / Reaper / Enemies
            for npc in self.npcs:
                npc.update(dt)
            self.reaper.update(dt, self.player.logic_pos)
            
            for enemy in self.enemies[:]:
                reaper_pos = (self.reaper.x, self.reaper.y)
                # ส่ง solid_rects เข้าไปด้วยเพื่อให้ศัตรูไม่เดินทะลุกำแพง
                enemy.update(dt, self.player.logic_pos, reaper_pos, self.game_map.solid_rects)

                # บันทึกสถานะศัตรูที่กำลังจางหาย (ไม่ว่าจะจากชนหรือวง Reaper) ให้จดจำในเซฟ
                if enemy.is_fading:
                    if enemy.id not in self.destroyed_enemies:
                        self.destroyed_enemies.append(enemy.id)
                
                # ถ้าจางหายจนจบแล้ว ให้ลบจริงออกจากฉาก
                if enemy.fading_done:
                    enemy.destroy()
                    if enemy in self.enemies:
                        self.enemies.remove(enemy)
                    continue

                # ถ้ากำลังจางหาย ไม่ต้องตรวจจับการชนซ้ำ
                if enemy.is_fading:
                    continue

                # เช็คการชนระหว่าง Player กับ Enemy
                if enemy.check_player_collision_logic(self.player.logic_pos, TILE_SIZE):
                    if enemy.id not in self.destroyed_enemies:
                        self.destroyed_enemies.append(enemy.id)
                    enemy.start_fade()
                    self.heart_ui.take_damage()
                    
                    # ตรวจสอบว่าเลือดหมดหรือยัง
                    if self.heart_ui.current_health <= 0:
                        self.respawn_at_reaper()
                
                # ตรวจสอบว่าศัตรูเข้าใกล้ Reaper หรือยัง (Safe Zone)
                reaper_center_x = self.reaper.x + TILE_SIZE / 2
                reaper_center_y = self.reaper.y + TILE_SIZE / 2
                enemy_center_x = enemy.logic_pos[0] + TILE_SIZE / 2
                enemy_center_y = enemy.logic_pos[1] + TILE_SIZE / 2
                dist_to_reaper = ((enemy_center_x - reaper_center_x)**2 + (enemy_center_y - reaper_center_y)**2)**0.5
                
                if dist_to_reaper < SAFE_ZONE_RADIUS:
                    print(f"Enemy {enemy.id} entered safe zone and starting fade!")
                    if enemy.id not in self.destroyed_enemies:
                        self.destroyed_enemies.append(enemy.id)
                    enemy.start_fade()

            # --- จัดการเสียงผีไล่ตามประเภทตัวละคร ---
            chasing_types = {e.enemy_type for e in self.enemies if e.is_chasing}
            
            for etype, sound in self.ghost_sounds.items():
                if etype in chasing_types:
                    if sound.state != 'play':
                        sound.play()
                else:
                    if sound.state == 'play':
                        sound.stop()

            if self.stun_cooldown > 0:
                self.stun_cooldown -= dt

            # เช็คการโต้ตอบ (Interactive Hints)
            self.update_interaction_hints()
            
            # เช็คพื้นที่อันตรายตามเนื้อเรื่อง (Story Manager)
            self.story_manager.update(dt)
        else:
            # ถ้าอยู่ในโหมดคุย/หยุดเกม ให้บังคับล้าง Hint และหยุดเสียงผีไล่ทั้งหมด
            self.clear_interaction_hints()
            for sound in self.ghost_sounds.values():
                if sound.state == 'play':
                    sound.stop()

        # ---------------------------------------------------------
        # 2. กราฟิกที่ต้องอัปเดตเสมอทุกลูกเฟรม
        px, py = self.player.logic_pos
        self.update_camera()
        self.game_map.update_chunks(px, py)
        
        # อัปเดต Debug Label
        self._update_debug_text(px, py)
        
        # จัดเลเยอร์การวาดตัวละคร (Y-Sorting)
        self.y_sorting()

    def respawn_at_reaper(self):
        """เมื่อหัวใจหมด วาปผู้เล่นกลับไปหา Reaper และรีเซ็ตหัวใจ"""
        self.death_count += 1
        print(f"Player died. Total deaths: {self.death_count}")
        
        # รีเซ็ตสถานะการเคลื่อนไหว
        self.pressed_keys.clear()
        self.player.is_moving = False
        self.player.state = 'idle'
        
        # วาร์ปผู้เล่นไปยังจุดเริ่มต้นแรกสุด
        start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
        start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
        self.player.logic_pos = [start_x, start_y]
        self.player.target_pos = [start_x, start_y]
        self.player.sync_graphics_pos()
        self.player.direction = 'up'
        self.player.update_animation_speed()
        self.player.update_frame()
        
        # รีเซ็ตเลือด
        self.heart_ui.reset_health()
            
        # สุ่มคำพูดโดยไม่ให้ซ้ำกับรอบล่าสุด
        available_indices = [i for i in range(len(REAPER_DEATH_QUOTES)) if i != self.last_death_quote_index]
        q_idx = random.choice(available_indices)
        self.last_death_quote_index = q_idx
        
        self.dialogue_manager.show_vn_dialogue("Reaper", REAPER_DEATH_QUOTES[q_idx])

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

        # เพิ่ม Reaper เฉพาะเมื่อไม่อยู่ในจุดพัก (เช่น ตอนเปลี่ยนแมพมาบ้าน)
        reaper_list = [self.reaper] if (self.reaper.logic_pos[0] > -1000) else []
        sortable_chars = [self.player] + reaper_list + self.npcs + self.enemies + self.stars
        
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
        # ป้องกันไม่ให้โดนดึงกลับไปหาผู้เล่นในขณะที่มีคัทซีนแพนกล้อง
        if getattr(self, 'is_cutscene_active', False) and getattr(self, 'cutscene_step', 0) == 10:
            return

        # ถ้าเป็นแมพบ้าน ไม่ต้อง Clamp กล้อง (ให้ตัวละครอยู่กลางจอเสมอแม้จะอยู่ขอบแมพ)
        should_clamp = (self.game_map.filename != 'assets/Tiles/home.tmj')
        
        self.camera.update(
            self.width, self.height,
            self.player.logic_pos,
            self.game_map.width,
            self.game_map.height,
            should_clamp=should_clamp
        )

    # ---------------------------------------------------------
    # Interaction & Triggers
    # ---------------------------------------------------------
    def clear_interaction_hints(self):
        """ล้างปุ่มและ Hints การโต้ตอบทั้งหมดออกจากจอ"""
        if hasattr(self, 'interaction_hints'):
            for hint in self.interaction_hints:
                if hint.parent:
                    hint.parent.remove_widget(hint)
            self.interaction_hints = []

    def cleanup(self):
        """ล้างทรัพยากรทั้งหมดก่อนทำลาย Widget เพื่อป้องกันลูปค้าง"""
        if hasattr(self, '_main_loop_event'):
            Clock.unschedule(self._main_loop_event)
        
        self.clear_interaction_hints()
        
        if hasattr(self, 'dialogue_manager'):
            self.dialogue_manager.close_dialogue()
            
        # เคลียร์ลูปย่อยอื่นๆ ถ้ามี
        Clock.unschedule(self._set_game_ready)
        Clock.unschedule(self._start_intro_dialogue)

    def _get_interaction_target(self, targets, limit=32):
        """ค้นหาเป้าหมายที่อยู่ใกล้และผู้เล่นหันหน้าเข้าหา"""
        px, py = self.player.logic_pos
        p_dir = self.player.direction
        
        for tar in targets:
            tx, ty = tar.logic_pos
            dx, dy = tx - px, ty - py
            dist = (dx**2 + dy**2)**0.5
            
            if dist >= limit:
                continue
                
            # ตรรกะการหันหน้าเข้าหาเป้าหมาย
            facing = False
            if p_dir == 'up' and dy > 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'down' and dy < 0 and abs(dy) >= abs(dx): facing = True
            elif p_dir == 'left' and dx < 0 and abs(dx) >= abs(dy): facing = True
            elif p_dir == 'right' and dx > 0 and abs(dx) >= abs(dy): facing = True
            
            if facing:
                return tar, dx, dy
        return None, 0, 0

    def _get_search_target(self, limit=20):
        """ค้นหาจุดที่สามารถค้นหาได้ในแมพบ้าน (ต้องหันหน้าเข้าหาและห่าง 1 บล็อก)"""
        if "home.tmj" not in self.game_map.filename.lower():
            return None
        
        px, py = self.player.logic_pos
        p_dir = self.player.direction
        all_spots = SEARCHABLE_SPOTS_HOME + [EMPTY_SPOT_HOME]
        
        for spot in all_spots:
            sx, sy = spot
            dx, dy = sx - px, sy - py
            
            # ต้องห่างกันไม่เกิน 1 บล็อก (16 pixels) และต้องไม่อยู่แนวทแยง (ตัวหนึ่งต้องเป็น 0)
            is_close = (abs(dx) <= TILE_SIZE and abs(dy) <= TILE_SIZE)
            is_orthogonal = (dx == 0 or dy == 0)
            
            if is_close and is_orthogonal:
                # ตรวจสอบการหันหน้าเข้าหา
                facing = False
                if p_dir == 'up' and dy > 0: facing = True
                elif p_dir == 'down' and dy < 0: facing = True
                elif p_dir == 'left' and dx < 0: facing = True
                elif p_dir == 'right' and dx > 0: facing = True
                
                if facing:
                    return spot
        return None

    def update_interaction_hints(self):
        """จัดการแสดงผลปุ่ม [E] ขึ้นเหนือหัว NPC หรือไอเทม เมื่อเดินไปใกล้"""
        self.clear_interaction_hints()
        
        if self.is_dialogue_active or self.is_paused or self.is_cutscene_active:
            return
            
        root_to_check = self.dialogue_root.children if self.dialogue_root else self.children
        if any(isinstance(child, SaveLoadScreen) for child in root_to_check):
            return
            
        # เช็คไอเทมดวงดาวก่อน (ระยะ 20)
        star_target, _, _ = self._get_interaction_target(self.stars, limit=20)
        self.current_star_target = star_target
        if star_target: return 

        # เช็ค NPC / Reaper (ระยะ 32)
        target, dx, dy = self._get_interaction_target(self.npcs + [self.reaper], limit=32)
        if target:
            hint_text = "E"
            box_width = 25
            hint = Label(
                text=hint_text, font_name=GAME_FONT, font_size='12sp',
                color=(1, 1, 1, 1), size_hint=(None, None), size=(box_width, 25),
                halign='center', valign='middle', bold=True
            )
            hint.bind(size=lambda l, s: setattr(l, 'text_size', s))
            
            with hint.canvas.before:
                Color(0, 0, 0, 0.8)
                hint.bg_rect = RoundedRectangle(pos=hint.pos, size=hint.size, radius=[3])
            
            hint.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos))
            hint.bind(size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))
            
            spos = self.camera.world_to_screen(target.logic_pos[0] + TILE_SIZE/2, target.logic_pos[1] + 45)
            hint.pos = (spos[0] - (box_width / 2), spos[1])
            
            if self.dialogue_root: self.dialogue_root.add_widget(hint)
            self.interaction_hints.append(hint)
            return

        # เช็คจุดค้นหา (ไม่แสดงปุ่ม E ตามคำขอ)
        self.current_search_target = self._get_search_target()

    def interact(self):
        """จัดการการกดปุ่ม [E] เพื่อคุยหรือสำรวจ"""
        self.clear_interaction_hints()
        
        if self.current_star_target:
            star_pos = (self.current_star_target.x, self.current_star_target.y)
            portrait = STAR_ITEM_MAPPING.get(star_pos, {}).get("portrait")
            self.show_vn_dialogue("Little girl", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"], portrait=portrait)
            return

        target, dx, dy = self._get_interaction_target(self.npcs + [self.reaper], limit=32)
        if target:
            npc_index = self.npcs.index(target) if target in self.npcs else -1
            self.process_interaction(target, npc_index, dx, dy)
            return

        # 3. เช็คจุดค้นหา
        if self.current_search_target:
            self.process_search_spot(self.current_search_target)

    def use_stun_item(self):
        """ใช้ Blue Stone เพื่อสตันผีรอบๆ ตัว"""
        # เอฟเฟกต์การส่องแสง Blue Stone
        stun_range = 100 # ระยะสตัน
        self.stun_cooldown = 15.0 # คูลดาวน์ 15 วินาที
        
        px, py = self.player.logic_pos
        player_center_x = px + TILE_SIZE / 2
        player_center_y = py + TILE_SIZE / 2
        
        stunned_any = False
        for enemy in self.enemies:
            ex, ey = enemy.logic_pos
            enemy_center_x = ex + TILE_SIZE / 2
            enemy_center_y = ey + TILE_SIZE / 2
            
            dist = ((player_center_x - enemy_center_x)**2 + (player_center_y - enemy_center_y)**2)**0.5
            if dist <= stun_range:
                enemy.stun(duration=3.0)
                stunned_any = True
        
        # Visual Effect (กะพริบจอสีฟ้าอ่อนๆ แป๊บนึง)
        if stunned_any:
            print("Stun activated!")
            # เพิ่มการสั่นหน้าจอหรือเอฟเฟกต์แสงในอนาคตที่นี่ได้
            
    def process_search_spot(self, spot):
        """ประมวลผลการค้นหาตามจุดต่างๆ ในบ้าน"""
        self.clear_interaction_hints()
        
        if spot == EMPTY_SPOT_HOME:
            self.show_vn_dialogue("Little girl", "Empty... they never leave anything for me anyway.")
            return

        if spot == self.correct_food_spot:
            self.show_vn_dialogue("Little girl", "Found it. This will keep me going tonight.")
            # ตั้งสถานะรอเควสสำเร็จ (จะถูกเรียกใน story_manager.handle_dialogue_end)
            self._pending_food_success = True
        else:
            self.show_vn_dialogue("Little girl", "Just dust and old rags. There’s nothing to eat here.")

        
    def process_interaction(self, target, index, dx, dy):
        """ประมวลผลการคุยกับ NPC หรือ Reaper"""
        # ล้าง Hint ทันทีเมื่อเริ่มการโต้ตอบ
        self.clear_interaction_hints()
        
        # หยุดการเดินของ Player ทันที
        self.pressed_keys.clear()
        self.player.is_moving = False
        self.player.state = 'idle'
        self.player.update_animation_speed()
        
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
        self.current_portrait = None # หรือระบุถ้ามีหน้าเฉพาะ
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            first_text = self.current_dialogue_queue[0]
            self.dialogue_manager.show_vn_dialogue(npc_name, first_text)
            
    def show_dialogue_above_reaper(self, dialogue, choices=None, portrait=None):
        """แสดงข้อความคุยของ Reaper สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        self.current_character_name = "Reaper"
        self.current_choices = choices if choices else []
        self.current_portrait = portrait
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            first_text = self.current_dialogue_queue[0]
            # แสดง Choice เฉพาะเมื่ออยู่หน้าสุดท้าย
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self.dialogue_manager.show_vn_dialogue(
                "Reaper", first_text, 
                choices=(self.current_choices if is_last else None),
                portrait=self.current_portrait
            )

    def show_vn_dialogue(self, character_name, dialogue, choices=None, portrait=None):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self.current_character_name = character_name
        if choices:
            self.current_choices = choices
        if portrait:
            self.current_portrait = portrait
            
        self.dialogue_manager.show_vn_dialogue(
            character_name, dialogue, 
            choices=choices, 
            portrait=self.current_portrait
        )

    def show_item_discovery(self, text, image_path=None):
        """แสดงแจ้งเตือนการได้รับไอเทมกลางหน้าจอ (Delegated)"""
        self.is_dialogue_active = True
        self.pressed_keys.clear()
        self.player.is_moving = False
        self.player.state = 'idle'
        self.player.update_animation_speed()
        self.player.update_frame()
        self.dialogue_manager.show_item_discovery(text, image_path)
        root = self.dialogue_root if self.dialogue_root else self
        
    def close_dialogue(self):
        """ปิดกล่องข้อความคุยและคืนสถานะเกม"""
        self.dialogue_manager.close_dialogue()

        # จำสถานะ Choice ไว้ก่อนรีเซ็ต
        last_char = self.current_character_name
        has_choices = len(self.current_choices) > 0
        
        # คืนสถานะการคุย
        self.is_dialogue_active = False
        self._on_close_dialogue_reset()
        
        # ตรวจสอบว่าเป็นการจบคัทซีนเนื้อเรื่องเสริมหรือไม่
        if self.is_cutscene_active and getattr(self, 'cutscene_step', 0) == 11:
            self.cutscene_manager.end_side_story_cutscene()
        
        # ส่งต่อ Logic เนื้อเรื่องให้ Story Manager จัดการทอดๆ ต่อไป
        self.story_manager.handle_dialogue_end(last_char, has_choices)
        
        # รีเซ็ตสถานะโหมดสอนเสมอ (Story Manager จะเป็นคนคุม tutorial_mode ในอนาคต)
        self.tutorial_mode = False
        
    def _on_close_dialogue_reset(self):
        """รีเซ็ตค่าพื้นฐานหลังปิดบทสนทนา"""
        self.dialogue_timer = 0
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        self.current_choices = []

    def next_dialogue(self):
        """ไปยังข้อความถัดไปในคิว"""
        if self.current_choices and self.current_dialogue_index == len(self.current_dialogue_queue) - 1:
            return

        # 1. เช็คก่อนว่าแชทปัจจุบันคือประโยคที่ต้องให้หินหรือไม่ (ถ้าใช่ ให้โชว์แจ้งเตือนไอเทมก่อนขยับไปประโยคถัดไป)
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            current_text = self.current_dialogue_queue[self.current_dialogue_index]
            if "Here, take this [Blue Stone] with you" in current_text and not self.has_received_blue_stone:
                # ซ่อนแชทก่อนโชว์ไอเทมตามคำขอ
                self.dialogue_manager.close_dialogue()
                self.show_item_discovery("Received [Blue Stone]", "assets/items/blue stone.png")
                self.has_received_blue_stone = True
                return # กลับออกไปเพื่อให้ user กด Enter ปิดไอเทมก่อน

        # 2. ขยับไปยังข้อความถัดไป
        self.current_dialogue_index += 1
        
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            next_text = self.current_dialogue_queue[self.current_dialogue_index]
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self.dialogue_manager.show_vn_dialogue(
                self.current_character_name, next_text, 
                choices=(self.current_choices if is_last else None),
                portrait=self.current_portrait
            )
        else:
            self.close_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC"""
        if npc_name == "The Sad Soul":
            quest = self.quest_manager.active_quests.get("doll_parts")
            if quest:
                if quest.current_count >= quest.target_count:
                    if self.quest_item_fail:
                        return ["Oh! You found them!", "Wait... these parts... they're just old scrap metal...", "Why would you give me these? This isn't my doll..."]
                    return ["Oh! You found them!", "My doll... it's whole again. Thank you so much!", "You really are a kind one."]
                elif quest.is_active:
                    return ["Were you able to find the pieces? It's still so dark..."]

        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper ครั้งละ 1 ประโยคแบบสุ่ม"""
        return [random.choice(REAPER_DIALOGUES)]

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
        
        # ปิด Interaction Hints ทันที
        self.clear_interaction_hints()
        
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
        self.save_manager.show_save_screen()

    def on_save_confirmed(self, slot_id, save_screen=None):
        self.save_manager.on_save_confirmed(slot_id, save_screen)

    def load_game_from_pause(self):
        self.save_manager.load_game_from_pause()

    def _on_pause_load_selected(self, slot_id, load_screen=None):
        self.save_manager._on_pause_load_selected(slot_id, load_screen)

    def return_to_main_menu(self):
        """กลับไปหน้าจอหลัก (Title Screen)"""
        self.resume_game()
        app = App.get_running_app()
        app.root.clear_widgets()
        
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
        self.world_manager.create_npcs()

    def create_enemies(self):
        self.world_manager.create_enemies()
            
    def create_stars(self):
        self.world_manager.create_stars()

    # ---------------------------------------------------------
    # Visual Effects & World
    # ---------------------------------------------------------
    def change_map(self, map_file):
        self.world_manager.change_map(map_file)

    def refresh_darkness(self):
        self.world_manager.refresh_darkness()
        
    def recreate_world(self):
        self.world_manager.recreate_world()

    def handle_day_transition(self):
        """จัดการการตัดฉากขึ้นวันใหม่"""
        if not self._pending_day_transition: return
        self._pending_day_transition = False
        
        # 1. แสดงจอดำ (Fade Out)
        root = self.dialogue_root if self.dialogue_root else self
        black_overlay = Widget(size_hint=(1, 1), opacity=0)
        with black_overlay.canvas:
            Color(0, 0, 0, 1)
            self.black_rect_trans = Rectangle(size=root.size, pos=(0, 0))
            
        def update_black_rect_trans(instance, value):
            self.black_rect_trans.size = (instance.width * 2, instance.height * 2)
            self.black_rect_trans.pos = (-instance.width * 0.5, -instance.height * 0.5)
        black_overlay.bind(size=update_black_rect_trans, pos=update_black_rect_trans)
        update_black_rect_trans(black_overlay, None)
        root.add_widget(black_overlay)
        
        # 2. เพิ่ม Day Counter
        self.current_day += 1
        
        # 3. Animation Sequence
        anim = Animation(opacity=1, duration=1.5) # จอค่อยๆ มืดลง
        
        def on_dark(*args):
            # ระหว่างที่จอมืด ให้รีเซ็ตโลกใหม่
            self.recreate_world()
            
            # 4. แสดง IntroScreen (Day X) เหมือนหน้าจอแรกสุดของเกม
            def start_fading_in():
                # เมื่อโชว์ Day X จบแล้ว ให้ค่อยๆ จางจอดำออก
                fade_in = Animation(opacity=0, duration=1.5)
                fade_in.bind(on_complete=lambda *a: root.remove_widget(black_overlay))
                fade_in.start(black_overlay)

            intro = IntroScreen(callback=start_fading_in, day=self.current_day)
            root.add_widget(intro)
            
        anim.bind(on_complete=on_dark)
        anim.start(black_overlay)

    # ---------------------------------------------------------
    # Cutscenes Logic
    # ---------------------------------------------------------
    def start_side_story_cutscene(self, dialogue_queue, character_name, portrait=None, choices=None):
        self.cutscene_manager.start_side_story_cutscene(dialogue_queue, character_name, portrait, choices)

    def start_quest_complete_cutscene(self, dt):
        self.cutscene_manager.start_quest_complete_cutscene(dt)

    def update_cutscene(self, dt):
        self.cutscene_manager.update(dt)

    def show_black_screen_transition(self):
        self.cutscene_manager.show_black_screen_transition()


    def end_cutscene(self):
        """จบโหมดคัทซีน กลับสู่การเล่นปกติ"""
        self.is_cutscene_active = False
        self.cutscene_step = 0
        if hasattr(self, 'camera'):
            self.camera.locked = False
        self.request_keyboard_back()
        if hasattr(self, 'cutscene_manager') and hasattr(self.cutscene_manager, 'end_cutscene'):
            self.cutscene_manager.end_cutscene()
        print("DEBUG: Cutscene ended.")

class MyApp(App): 
    def build(self): 
        self.title = TITLE
        
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
        # ลบวิดเจ็ตเก่าและหยุดลูปเดิมก่อน
        for child in self.root.children[:]:
            if isinstance(child, GameWidget):
                child.cleanup()
        
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