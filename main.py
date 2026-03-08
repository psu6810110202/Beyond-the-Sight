from kivy.config import Config
from data.settings import *

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

from entities.characters.player import Player
from entities.characters.npc import NPC
from entities.characters.reaper import Reaper
from entities.items.candle import Candle
from entities.characters.enemy import Enemy

from ui.heart import HeartUI
from assets.Tiles.map_loader import KivyTiledMap

from ui.load import SaveLoadScreen # นำเข้าหน้าจอเซฟ
from ui.screen import SplashScreen
from ui.camera import Camera
from ui.pause import PauseMenu

from ui.intro import IntroScreen # นำเข้าหน้าจอ Intro (Day 1)
from data.chat import NPC_DIALOGUES, REAPER_DIALOGUES, REAPER_DEATH_QUOTES, INTRO_DIALOGUES, WARNING_DIALOGUE, WARNING_CHOICES, DIALOGUE_CONFIG, CANDLE_LIGHT_DIALOGUE, CANDLE_LIGHT_CHOICES # นำเข้าข้อความและค่าตั้งค่า
from ui.choice import handle_choice_selection, draw_choice_buttons, clear_choices, update_choice_visuals # นำเข้าการจัดการ Choice
from managers.story import StoryManager # นำเข้า Story Manager
from managers.quest import QuestManager # นำเข้าหน้าจอกองเควส
from ui.dialogue_manager import DialogueManager # นำเข้า Dialogue Manager มารวมศูนย์ UI
from entities.items.star import Star # นำเข้า Star
from managers.world import WorldManager
from managers.save import SaveManager
from managers.cutscene import CutsceneManager
from managers.input_handler import InputHandler
from managers.interaction import InteractionManager
from managers.game_logic import GameplayManager
class GameWidget(Widget): 
    def __init__(self, initial_data=None, **kwargs): 
        super().__init__(**kwargs) 
        self.initial_data = initial_data
        
        # จัดการข้อมูลศัตรูที่ถูกกำจัดไปแล้ว (ไม่เกิดใหม่)
        self.destroyed_enemies = initial_data.get('destroyed_enemies', []) if initial_data else []
        # แปลงพิกัดจาก List ใน JSON ให้เป็น Tuple เพื่อให้เช็คกับพิกัดใน Settings ได้ถูกต้อง
        self.collected_stars = [tuple(pos) for pos in initial_data.get('collected_stars', [])] if initial_data else []
        
        self.candles = []
        self.current_candle_target = None
        # โหลดจำนวนเทียนที่จุดไปแล้วจากเซฟ
        self.current_candle_lit_count = initial_data.get('current_candle_lit_count', 0) if initial_data else 0
        self.player_candle_sequence = [] # เก็บสีที่ผู้เล่นจุดจริงตามลำดับ
        
        # คลีนข้อมูล Day 1 ถ้าโหลดมาเป็นวันอื่น (User Request)
        if initial_data and initial_data.get('day', 1) > 1:
            self.collected_stars = []
        else:
            # ถ้าเป็น Day 1 หรือเริ่มเกมใหม่ ให้รีเซ็ตจำนวนเทียนด้วย
            self.current_candle_lit_count = 0
            
        self.has_received_blue_stone = initial_data.get('has_received_blue_stone', False) if initial_data else False
        self.has_received_lantern = initial_data.get('has_received_lantern', False) if initial_data else False
        
        self.is_dialogue_active = False
        self.is_reaper_save_prompt = False
        
        # สถานะวันปัจจุบัน (ค่าเริ่มต้นคือ Day 1)
        self.current_day = initial_data.get('day', 1) if initial_data else 1
        self.warning_triggered = False # ป้องกันแจ้งเตือนรัว
        self.warning_dismissed = initial_data.get('warning_dismissed', False) if initial_data else False # โหลดสถานะการผ่านทางจากเซฟ
        self.tutorial_triggered = initial_data.get('tutorial_triggered', False) if initial_data else False
        self.tutorial_mode = False # สถานะชั่วคราวบอกว่ากำลังเล่นบทเรียนสอนใช้ของหรือไม่
        self.letters_held = initial_data.get('letters_held', 0) if initial_data else 0
        self.delivered_house_indices = initial_data.get('delivered_house_indices', []) if initial_data else []
        self.is_reaper_save_prompt = False
        self.is_dialogue_active = False
        self.extra_reapers = []  # Initialize early to avoid attribute errors
        
        # ระบบเวลาเล่น (Play Time)
        self.play_time = initial_data.get('play_time', 0) if initial_data else 0
        
        # เก็บค่าความสำเร็จของเควส (มีผลต่อฉากจบ)
        self.quest_success_count = initial_data.get('quest_success_count', 0) if initial_data else 0
        self.quest_item_fail = initial_data.get('quest_item_fail', False) if initial_data else False
        self.death_count = initial_data.get('death_count', 0) if initial_data else 0
        self.stun_cooldown = initial_data.get('stun_cooldown', 0) if initial_data else 0
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
        self.interaction_manager = InteractionManager(self)
        self.gameplay_manager = GameplayManager(self)
        self.input_handler = InputHandler(self)
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
        self.pending_post_discovery_dialogue = None # เก็บแชทที่ต้องขึ้นต่อจากตอนหยิบของเสร็จ
        self._pending_food_success = False
        
        self.interaction_hints = []  # เก็บปุ่ม E ของแต่ละ NPC
        self.stars = []             # เก็บวัตถุดาว (Day 1)
        self.current_star_target = None # เก็บดาวที่กำลังสำรวจ
        self.is_paused = False
        self.pause_menu = None
        
        # Cutscene states
        self.is_cutscene_active = False
        self.cutscene_timer = 0
        self.cutscene_step = 0
        self.black_overlay = None            # ดำ/จาง ของหน้าจอ
        self.dialogue_root = None             # Root สำหรับ UI ทุกอย่างที่อยู่หน้าสุด
        self._main_loop_event = None          # ตัวแปรเก็บ Event Loop
        
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
        if initial_data and 'correct_food_spot' in initial_data:
            self.correct_food_spot = tuple(initial_data['correct_food_spot'])
        else:
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
        
        # โหลดเสียงรื้อของ/หาของ
        self.find_sound = SoundLoader.load('assets/sound/find.wav')
        if self.find_sound:
            self.find_sound.volume = 0.7
            
        # โหลดเสียงกินอาหาร/ชุดคลุมขยับ
        self.sit_sound = SoundLoader.load('assets/sound/sit.wav')
        if self.sit_sound:
            self.sit_sound.volume = 0.6
            
        # โหลดเสียงตกใจเมื่อชนผี
        self.shock_sound = SoundLoader.load('assets/sound/feeling/shocked.wav')
        if self.shock_sound:
            self.shock_sound.volume = 0.8
            
        # โหลดเสียงสงสัย (Curious) เมื่อมีทางเลือก
        self.curious_sound = SoundLoader.load('assets/sound/feeling/curious.wav')
        if self.curious_sound:
            self.curious_sound.volume = 0.7
            
        # โหลดเสียงคร่ำครวญของ The Sad Soul (NPC1)
        self.sad_soul_sound = SoundLoader.load('assets/sound/ghost/Crying_moaning_ambience_3.wav')
        if self.sad_soul_sound:
            self.sad_soul_sound.loop = True
            self.sad_soul_sound.volume = 0.5
            
        # โหลดเสียงพูดของ Reaper
        self.reaper_voice_sound = SoundLoader.load('assets/sound/feeling/reaper.wav')
        if self.reaper_voice_sound:
            self.reaper_voice_sound.volume = 0.8
            
        # โหลดเสียงคลิก (Click) เวลากดปุ่ม
        self.click_sound = SoundLoader.load('assets/sound/click.wav')
        if self.click_sound:
            self.click_sound.volume = 0.6

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
        
        # เลเยอร์สำหรับเครื่องหมายที่วางไปแล้ว (Day 2)
        self.delivered_marks_group = InstructionGroup()
        self.canvas.before.add(self.delivered_marks_group)

        # เลเยอร์สำหรับเครื่องหมายบนผนัง (Day 2)
        self.house_marks_group = InstructionGroup()
        self.canvas.before.add(self.house_marks_group)
        
        # จัดการเควส
        self.quest_manager = QuestManager(self)
        if initial_data and 'quests' in initial_data:
            self.quest_manager.from_dict(initial_data['quests'])
            
            # คลีนเควสของวันเก่าๆ (User Request)
            if self.current_day > 1:
                day1_quests = ["doll_parts", "find_food"]
                for qid in day1_quests:
                    if qid in self.quest_manager.active_quests:
                        del self.quest_manager.active_quests[qid]
            
            if self.current_day > 2:
                self.letters_held = 0
                self.delivered_house_indices = []
                if "deliver_letters" in self.quest_manager.active_quests:
                    del self.quest_manager.active_quests["deliver_letters"]
            
            if self.current_day > 3:
                # ล้างเควส Old Soul (light_candles) เมื่อจบ Day 3
                if "light_candles" in self.quest_manager.active_quests:
                    del self.quest_manager.active_quests["light_candles"]
                
            self.quest_manager.update_quest_list_ui(animate=False)
            
            # ถ้าโหลดมาระหว่างทำเควสดวงดาว (Day 1 หรือ Day 4) ให้สร้างดาวขึ้นมา
            if "doll_parts" in self.quest_manager.active_quests:
                quest = self.quest_manager.active_quests["doll_parts"]
                if quest.is_active:
                    self.create_stars()
            elif "find_key" in self.quest_manager.active_quests:
                quest = self.quest_manager.active_quests["find_key"]
                # สำหรับ Day 4 ถ้าเก็บไปแล้ว (count=1) ไม่ต้องสร้างดาวแล้ว
                if quest.is_active and quest.current_count == 0:
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
        # self.input_handler is initialized above and handles keyboard binding
        self.pressed_keys = self.input_handler.pressed_keys 
        
        # 2. สร้าง NPCs
        self.npcs = []
        self.create_npcs()
        
        # 3. สร้าง Reapers (หลักและ Extra) ผ่าน WorldManager เพื่อความสอดคล้องกันทุกวันและการโหลดเกม
        self.world_manager.create_reapers()
        
        # 4. สร้าง Enemies
        self.enemies = []
        self.create_enemies()
        
        # 4.5. วาดรอยประทับหน้าบ้าน (หากเป็น Day 2) ไว้รองรับกรณีโหลดเซฟใหม่
        self.world_manager.create_house_marks()
        
        # 4.6. สร้างเทียน (กรณีโหลดเซฟแล้วมีเควสค้างอยู่)
        if "light_candles" in self.quest_manager.active_quests:
            self.create_candles()
            
        # 4.7. สร้างดวงดาว (กรณีโหลดเซฟแล้วมีเควสค้างอยู่)
        active_q = self.quest_manager.active_quests
        if ("doll_parts" in active_q and active_q["doll_parts"].is_active) or \
           ("find_key" in active_q and active_q["find_key"].is_active) or \
           ("soul_fragments" in active_q and active_q["soul_fragments"].is_active):
            self.create_stars()
            
        self.world_manager.restore_delivered_marks()
        
        # 5. Stars จะถูกสร้างหลังคุยกับ NPC1

        # 5. สร้างตัวละครหลัก (ใช้พิกัดจากเซฟถ้ามี)
        self.player = Player(self.sorting_layer, x=start_pos[0], y=start_pos[1])
        # ตั้งค่าเสียงเดินครั้งแรก
        self.player.is_in_home = 'home.tmj' in starting_map
        
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

        # อัปเดตความมืด (Fog of War)
        # ถ้าอยู่ในแมพ Underground ให้ปิดหมอก (User Request: เอาหมอกออก)
        is_underground = 'underground.tmj' in self.game_map.filename.lower()
        if is_underground:
            if hasattr(self, 'darkness_instr') and self.darkness_instr:
                self.canvas.after.remove(self.darkness_instr)
                self.darkness_instr = None
        else:
            self.refresh_darkness()

        # ตรวจสอบว่าต้องขึ้นบทนำ (คุยกับ Reaper ทันที) หรือไม่
        if initial_data is None:
            self.is_dialogue_active = True # ล็อกการขยับตั้งแต่วินาทีแรกของ New Game
            Clock.schedule_once(self._start_intro_dialogue, 0.3)
            
        # สถานะช่วงรอยต่อวัน
        self._pending_day_transition = False

        # เริ่มลูปเกม
        self._main_loop_event = Clock.schedule_interval(self.move_step, 1.0 / FPS)  

    def stop_all_sounds(self):
        """หยุดเสียงทั้งหมดที่มีใน GameWidget นี้ (ยกเว้น Ambiance หลักที่คุมโดย App)"""
        # 1. หยุดเสียงผีไล่ล่า
        if getattr(self, 'ghost_sounds', None):
            for s in self.ghost_sounds.values():
                if getattr(s, 'state', '') == 'play': s.stop()
        
        # 2. รายชื่อเสียงอื่นๆ
        sound_attrs = [
            'find_sound', 'shock_sound', 'curious_sound',
            'sad_soul_sound', 'reaper_voice_sound', 'click_sound',
            'sit_sound'
        ]
        for attr in sound_attrs:
            s_obj = getattr(self, attr, None)
            if s_obj and getattr(s_obj, 'state', '') == 'play':
                s_obj.stop()
        
        # 3. หยุดเสียงเดิน/หายใจของผู้เล่น
        if hasattr(self, 'player'):
            self.player.cleanup()

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
        
        # ดึงบทสนทนาเริ่มต้นตามวัน (Safe fallback to Day 1)
        dialogue = INTRO_DIALOGUES.get(self.current_day, INTRO_DIALOGUES[1])
        self.show_dialogue_above_reaper(dialogue)

    def request_keyboard_back(self):
        """ขอคีย์บอร์ดกลับมาให้ GameWidget อีกครั้ง (ใช้หลังปิดเมนู/หน้าจอโหลด)"""
        self.input_handler.request_keyboard()



    def update_ui_positions(self, *args):
        # เรียกปรับตำแหน่งของหัวใจเมื่อหน้าจอมีการเปลี่ยนแปลงขนาด
        if getattr(self, 'heart_ui', None):
            self.heart_ui.update_position(self.width, self.height)
        
        # เรียกปรับสเกลของแชท/บทสนทนา
        if getattr(self, 'dialogue_manager', None):
            self.dialogue_manager.update_ui_scaling()
        
        # จัดการการแสดงผลแถบสตัน (โชว์เมื่อได้ไอเทมแล้วเท่านั้น)
        if getattr(self, 'heart_ui', None):
            self.heart_ui.set_stun_visibility(self.has_received_blue_stone)
            # เพิ่ม Label เข้า Root ถ้ายังไม่มี
            if self.has_received_blue_stone and self.heart_ui.stun_label and \
               self.heart_ui.stun_label.parent is None and self.dialogue_root:
                self.dialogue_root.add_widget(self.heart_ui.stun_label)

    def _on_keyboard_closed(self): 
        self.input_handler.on_keyboard_closed()

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        return self.input_handler.on_key_down(keyboard, keycode, text, modifiers)
        
    def _on_key_up(self, keyboard, keycode): 
        return self.input_handler.on_key_up(keyboard, keycode)

    def set_candle_color(self, color_name):
        # ลำดับที่ถูกต้อง: แดง (ดอกไม้) -> ฟ้า (พรม) -> เหลือง (แดด)
        correct_order = ["Red", "Blue", "Yellow"]
        
        if not self.has_received_lantern:
            self.show_vn_dialogue("Little girl", "I need something to light this...")
            return

        if self.current_candle_target and not self.current_candle_target.is_lit:
            current_step = len(self.player_candle_sequence)
            
            # ตรวจสอบว่าสีที่เลือกตรงกับลำดับที่ต้องจุดในขั้นตอนนี้หรือไม่
            if color_name != correct_order[current_step]:
                # ผิด: บันทึกความล้มเหลว และแสดงบทพูดเตือน (แต่ไม่ดับไฟ เพื่อให้เปลี่ยนไม่ได้)
                self.quest_item_fail = True
                self.show_vn_dialogue("Old Soul", "No... that's not it. Everything is getting blurry again.")
            
            # บันทึกสถานะไม่ว่าจะถูกหรือผิด (เพื่อให้จุดไฟแล้วติดเลย เปลี่ยนไม่ได้)
            self.player_candle_sequence.append(color_name)
            self.current_candle_target.set_color(color_name)
            self.current_candle_lit_count += 1
            
            if self.current_candle_lit_count >= 3:
                # สำเร็จภารกิจ (จะล้มเหลวหรือสำเร็จจริงจะไปตัดสินตอนคุยกับ Old Soul)
                self.show_vn_dialogue("Little girl", "The path is clear now. I should return to him.")
                q = self.quest_manager.active_quests.get("light_candles")
                if q: q.name = "Return to The Old Soul"
                self.quest_manager.update_quest_list_ui()


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
        
        # จัดการเสียงของ Sad Soul (NPC1) จนกว่าจะข้ามวัน/หายไป
        if self.sad_soul_sound:
            # เช็คว่ามี NPC1 อยู่ในจอไหม (เช็คจาก image_path) และยังจางหายไม่จบ
            sad_soul_active = any('NPC1' in n.image_path and not n.fading_done for n in self.npcs)
            # ต้องไม่เล่นในช่วง หยุดเกม หรือคัทซีน (แต่ยอมให้เล่นตอนคุยเพื่อความต่อเนื่อง)
            if not (self.is_paused or self.is_cutscene_active) and sad_soul_active:
                if self.sad_soul_sound.state != 'play':
                    self.sad_soul_sound.play()
            else:
                # ถ้ากำลังคุยอยู่ ให้ยอมให้เสียงเล่นต่อไปได้ (แต่ตอนกดหยุดเกม หรือคัทซีนเปลี่ยนฉากต้องหยุดจริง)
                if self.is_dialogue_active and sad_soul_active and not self.is_paused:
                    if self.sad_soul_sound.state != 'play':
                        self.sad_soul_sound.play()
                else:
                    if self.sad_soul_sound.state == 'play':
                        self.sad_soul_sound.stop()

        # 1. จัดการตรรกะเกม (Logic) - ทำงานเฉพาะเมื่อไม่ได้คุยหรือหยุดเกม
        if self.is_cutscene_active:
            self.update_cutscene(dt)
        elif not (self.is_dialogue_active or self.is_paused or not self.is_ready):
            self.play_time += dt
            
            # 1. การเคลื่อนที่ของตัวละคร
            all_reapers = [self.reaper] + getattr(self, 'extra_reapers', [])
            self.player.move(self.pressed_keys, self.npcs, all_reapers, self.game_map.solid_rects, getattr(self, 'candles', []))
            self.heart_ui.update_stamina(self.player.get_stamina_ratio())
            
            # อัปเดต NPCs / Reaper / Enemies (Culling - อัปเดตเฉพาะที่อยู่ใกล้)
            px, py = self.player.logic_pos
            for npc in self.npcs:
                # Cull distance: 600px
                if abs(npc.x - px) + abs(npc.y - py) < 600:
                    npc.update(dt)
            
            if abs(self.reaper.x - px) + abs(self.reaper.y - py) < 600:
                self.reaper.update(dt, self.player.logic_pos)
            
            for er in getattr(self, 'extra_reapers', []):
                if abs(er.x - px) + abs(er.y - py) < 600:
                    er.update(dt, self.player.logic_pos)
            
            for enemy in self.enemies[:]:
                # Cull far enemies
                if abs(enemy.logic_pos[0] - px) + abs(enemy.logic_pos[1] - py) > 600:
                    enemy.is_chasing = False # หยุดไล่ถ้าไกลเกินไป
                    continue
                # ส่งรายการตำแหน่ง reaper ทั้งหมด (หลัก + extra) ไปให้ศัตรูตรวจสอบ Safe Zone
                reaper_positions = [(self.reaper.x, self.reaper.y)]
                for er in getattr(self, 'extra_reapers', []):
                    reaper_positions.append((er.x, er.y))
                    
                # ส่ง solid_rects และ enemies เข้าไปด้วยเพื่อให้ศัตรูไม่เดินทะลุกำแพงและไม่ชนกัน
                enemy.update(dt, self.player.logic_pos, reaper_positions, self.game_map.solid_rects, self.enemies)

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
                    
                    # เล่นเสียงตกใจ
                    if self.shock_sound:
                        self.shock_sound.play()
                    
                    # ตรวจสอบว่าเลือดหมดหรือยัง
                    if self.heart_ui.current_health <= 0:
                        self.respawn_at_reaper()
                
                # ตรวจสอบว่าศัตรูเข้าใกล้ Reaper หรือยัง (Safe Zone)
                # Optimization: ใช้ Squared Distance เพื่อเลี่ยง sqrt
                enemy_center_x = enemy.logic_pos[0] + TILE_SIZE / 2
                enemy_center_y = enemy.logic_pos[1] + TILE_SIZE / 2
                
                safe_radius_sq = SAFE_ZONE_RADIUS ** 2
                for r_obj in [self.reaper] + getattr(self, 'extra_reapers', []):
                    r_cx = r_obj.x + TILE_SIZE / 2
                    r_cy = r_obj.y + TILE_SIZE / 2
                    dist_sq = (enemy_center_x - r_cx)**2 + (enemy_center_y - r_cy)**2
                    
                    if dist_sq < safe_radius_sq:
                        # ตรวจสอบว่ามีกำแพงกั้นระหว่างศัตรูกับ Reaper หรือไม่
                        if enemy.has_line_of_sight((r_obj.x, r_obj.y), self.game_map.solid_rects):
                            print(f"Enemy {enemy.id} entered safe zone and starting fade!")
                            if enemy.id not in self.destroyed_enemies:
                                self.destroyed_enemies.append(enemy.id)
                            enemy.start_fade()
                            break

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
                if self.stun_cooldown < 0: self.stun_cooldown = 0
                self.heart_ui.update_stun_cooldown(self.stun_cooldown)
            else:
                self.heart_ui.update_stun_cooldown(0)

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
            if self.player.breath_sound and self.player.breath_sound.state == 'play':
                self.player.breath_sound.stop()
            
            # ยอมให้เสียง Sad Soul เล่นได้แม้จะอยู่ในโหมดคุย (is_dialogue_active) ถ้าตัวยังอยู่
            sad_soul_active = any('NPC1' in n.image_path and not n.fading_done for n in self.npcs)
            if self.sad_soul_sound and self.sad_soul_sound.state == 'play':
                if self.is_paused or self.is_cutscene_active or not sad_soul_active:
                    self.sad_soul_sound.stop()

        # ---------------------------------------------------------
        # 2. กราฟิกที่ต้องอัปเดตเสมอทุกลูกเฟรม
        px, py = self.player.logic_pos
        self.update_camera()
        
        # Optimization: อัปเดต Chunk เฉพาะตอนขยับเกิน 2px เพื่อลดภาระ Grid search
        if not hasattr(self, '_last_chunk_px'): self._last_chunk_px, self._last_chunk_py = -999, -999
        if abs(px - self._last_chunk_px) > 2 or abs(py - self._last_chunk_py) > 2:
            self.game_map.update_chunks(px, py)
            self._last_chunk_px, self._last_chunk_py = px, py
        
        # อัปเดต Debug Label (อัปเดตแค่บางเฟรมเพื่อลดภาระ CPU ในการจัดการ String)
        if not hasattr(self, '_debug_frame_count'): self._debug_frame_count = 0
        self._debug_frame_count += 1
        if self._debug_frame_count % 60 == 0:
            map_name = os.path.basename(self.game_map.filename)
            self.debug_label.text = (
                f"FPS: {int(Clock.get_fps())}\n"
                f"Map: {map_name}\n"
                f"Pos: ({int(px)}, {int(py)})\n"
                f"Grid: ({int(px/16)}, {int(py/16)})\n"
                f"Chunk: ({int(px/16/16)}, {int(py/16/16)})"
            )
        
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
        # Optimization: ถ้าไม่มีอะไรขยับ ไม่ต้องเสียเวลาจัดเลเยอร์ใหม่
        is_anything_moving = self.player.is_moving or any(e.is_chasing for e in self.enemies)
        if not is_anything_moving and hasattr(self, '_y_sorted_done') and self._y_sorted_done:
            return
            
        if self.is_dialogue_active and not self.player.is_moving:
            return

        # เพิ่ม Reaper เฉพาะเมื่อไม่อยู่ในจุดพัก (เช่น ตอนเปลี่ยนแมพมาบ้าน)
        reaper_list = [self.reaper] if (self.reaper.logic_pos[0] > -1000) else []
        reaper_list.extend(getattr(self, 'extra_reapers', []))
        sortable_chars = [self.player] + reaper_list + self.npcs + self.enemies + self.stars + self.candles
        
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
        self._y_sorted_done = True

    def update_camera(self):
        """อัปเดตตำแหน่งกล้องตามผู้เล่น"""
        # ป้องกันไม่ให้โดนดึงกลับไปหาผู้เล่นในขณะที่มีคัทซีนแพนกล้อง
        if getattr(self, 'is_cutscene_active', False) and getattr(self, 'cutscene_step', 0) == 11:
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

    def cleanup(self):
        """ล้างทรัพยากรทั้งหมดก่อนทำลาย Widget เพื่อป้องกันลูปค้าง"""
        if hasattr(self, '_main_loop_event'):
            Clock.unschedule(self._main_loop_event)
        
        # ปิดเสียงทั้งหมด
        sounds_to_stop = [
            self.curious_sound, self.sad_soul_sound, self.reaper_voice_sound,
            self.click_sound, self.find_sound, self.shock_sound
        ]
        for s in sounds_to_stop:
            if s and s.state == 'play':
                s.stop()
        
        # ปิดเสียงผี
        if hasattr(self, 'ghost_sounds'):
            for s in self.ghost_sounds.values():
                if s.state == 'play':
                    s.stop()
                    
        # ล้าง Player (เสียงเท้า/เสียงหอบ)
        if hasattr(self, 'player'):
            self.player.cleanup()

        self.clear_interaction_hints()
        
        if hasattr(self, 'dialogue_manager'):
            self.dialogue_manager.close_dialogue()
            
        # เคลียร์ลูปย่อยอื่นๆ ถ้ามี
        Clock.unschedule(self._set_game_ready)
        Clock.unschedule(self._start_intro_dialogue)

    def _get_interaction_target(self, targets, limit=32):
        return self.interaction_manager.get_interaction_target(targets, limit)

    def _get_search_target(self, limit=20):
        return self.interaction_manager.get_search_target(limit)

    def update_interaction_hints(self):
        self.interaction_manager.update_interaction_hints()

    def interact(self):
        self.interaction_manager.interact()

    def stop_all_sounds(self):
        """หยุดเสียงประกอบเกมทั้งหมด (เช่น เมื่อเริ่มคัทซีนฉากจบ) ยกเว้นเสียง Ambiance หลัก"""
        sounds = [
            self.curious_sound, self.sad_soul_sound, self.reaper_voice_sound,
            self.click_sound, self.find_sound, self.shock_sound
        ]
        if hasattr(self, 'ghost_sounds'):
            sounds.extend(self.ghost_sounds.values())
        
        for s in sounds:
            if s and s.state == 'play':
                # ตรวจสอบว่าเป็นเสียงบรรยากาศหลักหรือไม่ ถ้าใช่ให้ผ่านไป
                if hasattr(s, 'source') and 'Ambiance_Cave_Dark_Loop_Stereo.wav' in s.source:
                    continue
                s.stop()
        
        # ตรวจสอบเสียงจาก App (ถ้ามี)
        from kivy.app import App
        app = App.get_running_app()
        if hasattr(app, 'bg_loop') and app.bg_loop:
            if app.bg_loop.state != 'play':
                app.bg_loop.play() # ให้แน่ใจว่ายังเล่นอยู่
        
        if hasattr(self, 'player'):
            self.player.cleanup() # หยุดเสียงเดินและเสียงหอบของ Player

    def clear_interaction_hints(self):
        self.interaction_manager.clear_interaction_hints()

    def respawn_at_reaper(self):
        self.gameplay_manager.respawn_at_reaper()

    def use_stun_item(self):
        self.gameplay_manager.use_stun_item()

    def process_search_spot(self, spot):
        self.interaction_manager.interact_with_search_spot(spot)

    def process_interaction(self, target, index, dx, dy):
        self.interaction_manager.process_interaction(target, index, dx, dy)


    # ---------------------------------------------------------
    # Dialogue & Quest Logic
    # ---------------------------------------------------------
    def show_dialogue_above_npc(self, npc, dialogue, npc_name=None):
        self.interaction_manager.show_dialogue_above_npc(npc, dialogue, npc_name)

    def show_dialogue_above_reaper(self, dialogue, choices=None, portrait=None, can_save=True):
        self.interaction_manager.show_dialogue_above_reaper(dialogue, choices, portrait, can_save)

    def show_vn_dialogue(self, character_name, dialogue, choices=None, portrait=None, left_portrait=None):
        self.current_character_name = character_name
        self.dialogue_manager.show_vn_dialogue(character_name, dialogue, choices, portrait, left_portrait)

    def show_item_discovery(self, text, image_path=None, choices=None):
        self.dialogue_manager.show_item_discovery(text, image_path, choices)

    def close_dialogue(self):
        self.dialogue_manager.close_dialogue()

    def _on_close_dialogue_reset(self):
        self.dialogue_manager._on_close_dialogue_reset()

    def next_dialogue(self):
        self.dialogue_manager.next_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        return self.interaction_manager.get_proximity_dialogue(npc_name, distance_x, distance_y)

    def get_reaper_dialogue(self, distance_x, distance_y):
        return self.interaction_manager.get_reaper_dialogue(distance_x, distance_y)

    def on_choice_selected(self, choice):
        self.dialogue_manager.on_choice_selected(choice)

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

    def cleanup(self):
        """ล้างสถานะและปิดเสียงทั้งหมด และหยุดลูปหลักเมื่อออกจากเกม"""
        # 1. หยุดลูปเกมทันที ไม่ให้ไปสั่งเล่นเสียงซ้ำในเฟรมถัดไป
        if self._main_loop_event:
            self._main_loop_event.cancel()
            self._main_loop_event = None
            
        # 2. ปิดเสียงทั้งหมด
        self.stop_all_sounds()
        
        # 3. ล้างสถานะปุ่มกด และ UI ลอยตัว
        self.pressed_keys.clear()
        self.clear_interaction_hints()
        
        # 4. ล้าง Stun Label ที่ผูกกับ HeartUI ออกจากจอ
        if hasattr(self, 'heart_ui') and self.heart_ui.stun_label:
            if self.heart_ui.stun_label.parent:
                self.heart_ui.stun_label.parent.remove_widget(self.heart_ui.stun_label)
        
        if hasattr(self, 'player'):
            self.player.cleanup()

    def return_to_main_menu(self):
        """กลับไปหน้าจอหลัก (Title Screen)"""
        # 1. ล้างทรัพยากรทั้งหมด (เสียง/ลูป/ปุ่มค้าง)
        self.cleanup()
        
        # 2. เข้าสู่สถานะ Resume เพื่อปลดล็อก Input เผื่อค้าง
        self.resume_game()
        
        # 3. เคลียร์ Widget ทั้งหมดใน App Root เพื่อกลับหน้าเมนู
        app = App.get_running_app()
        app.root.clear_widgets()
        
        from ui.screen import SplashScreen
        from data.settings import SPLASH_COVER_IMG
        
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

    def create_candles(self):
        self.world_manager.create_candles()

    # ---------------------------------------------------------
    # Visual Effects & World
    # ---------------------------------------------------------
    def change_map(self, map_file):
        self.world_manager.change_map(map_file)

    def refresh_darkness(self):
        self.world_manager.refresh_darkness()
        
    def recreate_world(self):
        self.world_manager.recreate_world()

    def handle_day_transition(self, increment=True):
        self.gameplay_manager.handle_day_transition(increment)

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
        
        # เล่นเสียง Ambiance Loop ตั้งแต่เริ่มเกม (เปิดโปรแกรมปุ๊บเปิดเสียงเลย)
        ambiance_path = 'assets/sound/loop/Ambiance_Cave_Dark_Loop_Stereo.wav'
        if os.path.exists(ambiance_path):
            self.bg_loop = SoundLoader.load(ambiance_path)
            if self.bg_loop:
                self.bg_loop.loop = True
                self.bg_loop.volume = 0.8
                self.bg_loop.play()
                
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
            # ใช้ฟังก์ชันช่วยเช็คแบบเจาะลึก (Recursive) โดยใช้ชื่อคลาสเพื่อความแม่นยำสูงสุด
            def has_active_layer(root):
                # ตรวจสอบว่าหน้าจอนี้เป็นหน้าจอที่เราต้องการบล็อกการปิดหรือไม่
                name = root.__class__.__name__
                if name in ('SaveLoadScreen', 'GameWidget', 'PauseMenu', 'IntroScreen'):
                    return True
                # ค้นหาในลูกหลาน
                for child in root.children:
                    if has_active_layer(child):
                        return True
                return False

            # ตรวจสอบว่ามีหน้าจอสำคัญเปิดอยู่หรือไม่
            if not has_active_layer(self.root):
                # ถ้าอยู่หน้า SplashScreen เปล่าๆ จริงๆ (ไม่มี Overlay ใดๆ) ค่อยปิดโปรแกรม
                print("Global Escape: Closing App (No active layers found)")
                Window.close()
                return True
                
            # ถ้ามีหน้าจออื่นเปิดอยู่ ให้ส่งต่อ (Return False) เพื่อให้ Widget นั้นๆ จัดการ ESC เอง
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