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
from items.candle import Candle
from characters.enemy import Enemy

from assets.Heart.heart import HeartUI
from assets.Tiles.map_loader import KivyTiledMap

from menu.load import SaveLoadScreen # นำเข้าหน้าจอเซฟ
from menu.screen import SplashScreen
from menu.camera import Camera
from menu.pause import PauseMenu

from storygame.intro import IntroScreen # นำเข้าหน้าจอ Intro (Day 1)
from storygame.chat import NPC_DIALOGUES, REAPER_DIALOGUES, REAPER_DEATH_QUOTES, INTRO_DIALOGUES, WARNING_DIALOGUE, WARNING_CHOICES, DIALOGUE_CONFIG, CANDLE_LIGHT_DIALOGUE, CANDLE_LIGHT_CHOICES # นำเข้าข้อความและค่าตั้งค่า
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
        
        self.candles = []
        self.current_candle_target = None
        # โหลดจำนวนเทียนที่จุดไปแล้วจากเซฟ
        self.current_candle_lit_count = initial_data.get('current_candle_lit_count', 0) if initial_data else 0
        
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
        self.pending_post_discovery_dialogue = None # เก็บแชทที่ต้องขึ้นต่อจากตอนหยิบของเสร็จ
        
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
        
        # โหลดเสียงรื้อของ/หาของ
        self.find_sound = SoundLoader.load('assets/sound/find.wav')
        if self.find_sound:
            self.find_sound.volume = 0.7
            
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
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        
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
        
        # เปิดธงเพื่อให้แสดงหน้าจอเซฟหลังคุยจบ
        self.is_reaper_save_prompt = True
        
        # ดึงบทสนทนาเริ่มต้นตามวัน (Safe fallback to Day 1)
        dialogue = INTRO_DIALOGUES.get(self.current_day, INTRO_DIALOGUES[1])
        self.show_dialogue_above_reaper(dialogue)

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
                
                # ถ้ามีแชทที่รอขึ้นต่อ (เช่น หลังเก็บของ Day 4)
                if self.pending_post_discovery_dialogue:
                    d = self.pending_post_discovery_dialogue
                    self.pending_post_discovery_dialogue = None
                    self.show_vn_dialogue(d['name'], d['text'], portrait=d.get('portrait'))
                # ถ้าไม่มีแชทต่อ แต่กำลังคุยค้างอยู่ (กรณีได้รับไอเทมกลางบทสนทนา) 
                elif self.is_dialogue_active:
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

    def set_candle_color(self, color_name):
        """เปลี่ยนสีเทียนตามที่เลือกและอัปเดตสถานะ"""
        from settings import CANDLE_COLOR_MAPPING
        from storygame.chat import CANDLE_SUCCESS_DIALOGUE
        if self.current_candle_target and not self.current_candle_target.is_lit:
            candle = self.current_candle_target
            candle.set_color(color_name)
            
            # ตรวจสอบความถูกต้อง (User Request: แดง=688,1312, ฟ้า=528,960, เหลือง=462,560)
            target_color = CANDLE_COLOR_MAPPING.get((candle.x, candle.y))
            if color_name != target_color:
                self.quest_item_fail = True
                print(f"DEBUG: Incorrect color at ({candle.x}, {candle.y}). Expected {target_color}, got {color_name}")
            
            self.current_candle_lit_count += 1
            print(f"Candle lit with {color_name}. Total lit: {self.current_candle_lit_count}")

            # อัปเดตความคืบหน้าเควสผ่าน Quest Manager
            if "light_candles" in self.quest_manager.active_quests:
                self.quest_manager.update_quest_progress("light_candles", 1)

            if self.current_candle_lit_count >= 3:
                # ปรับข้อความให้ชัดเจน (Return to Old Soul)
                self.show_vn_dialogue("Little girl", CANDLE_SUCCESS_DIALOGUE)
                
                # เปลี่ยนเป้าหมายเควสให้กลับไปหา Old Soul
                q = self.quest_manager.active_quests.get("light_candles")
                if q:
                    q.name = "Return to The Old Soul"
                    self.quest_manager.update_quest_list_ui()
            else:
                self.show_vn_dialogue("Little girl", f"The candle glows {color_name.lower()}.")
        else:
            self.show_vn_dialogue("Little girl", "This candle is already burning brightly.")


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
            if not self.is_paused and sad_soul_active:
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

    def respawn_at_reaper(self):
        """เมื่อหัวใจหมด วาปผู้เล่นกลับไปยังจุดเริ่มต้นและรีเซ็ตหัวใจ"""
        self.death_count += 1
        print(f"Player died. Total deaths: {self.death_count}")
        
        # รีเซ็ตสถานะการเคลื่อนไหว
        self.pressed_keys.clear()
        self.player.is_moving = False
        self.player.state = 'idle'
        
        # วาร์ปผู้เล่นไปยังจุดที่เซฟไว้ล่าสุด (ถ้ามี) ไม่เช่นนั้นใช้จุดเริ่มต้นดั้งเดิม
        start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
        start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
        target_map = MAP_FILE
        
        if getattr(self, 'save_manager', None):
            latest_save = self.save_manager.get_latest_save_data()
            if latest_save and 'player_pos' in latest_save:
                saved_x, saved_y = latest_save['player_pos']
                start_x = (saved_x // TILE_SIZE) * TILE_SIZE
                start_y = (saved_y // TILE_SIZE) * TILE_SIZE
                target_map = latest_save.get('current_map', MAP_FILE)
                
        # ถ้าพิกัดที่เซฟไว้ไม่ได้อยู่ในแมพปัจจุบัน ให้ทำการเปลี่ยนแมพก่อน
        if self.game_map.filename != target_map:
            self.world_manager.change_map(target_map)

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
        
        # เช็คไอเทมเทียน (Day 3)
        candle_target, _, _ = self._get_interaction_target(self.candles, limit=20)
        self.current_candle_target = candle_target
        if candle_target: return

        # เช็ค NPC / Reaper (ระยะ 32)
        target, dx, dy = self._get_interaction_target(self.npcs + [self.reaper] + getattr(self, 'extra_reapers', []), limit=32)
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

        # เช็ค Underground Portal
        from settings import UNDERGROUND_PORTAL_POS
        px, py = self.player.logic_pos
        ux, uy = UNDERGROUND_PORTAL_POS
        dist = ((px - ux)**2 + (py - uy)**2)**0.5
        # DEBUG print to help user see their current pos vs portal pos
        # print(f"DEBUG: Pos ({px}, {py}), Portal ({ux}, {uy}), Dist: {dist:.1f}, Day: {self.current_day}")
        
        if dist <= 32 and self.current_day == 5: # Increased range slightly for easier hit
            hint = Label(
                text="E", font_name=GAME_FONT, font_size='12sp',
                color=(1, 1, 1, 1), size_hint=(None, None), size=(25, 25),
                halign='center', valign='middle', bold=True
            )
            hint.bind(size=lambda l, s: setattr(l, 'text_size', s))
            with hint.canvas.before:
                Color(0, 0, 0, 0.8)
                hint.bg_rect = RoundedRectangle(pos=hint.pos, size=hint.size, radius=[3])
            hint.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', inst.pos))
            hint.bind(size=lambda inst, val: setattr(inst.bg_rect, 'size', inst.size))
            
            spos = self.camera.world_to_screen(ux + TILE_SIZE/2, uy + 45)
            hint.pos = (spos[0] - 12.5, spos[1])
            if self.dialogue_root: self.dialogue_root.add_widget(hint)
            self.interaction_hints.append(hint)
            return

        # เช็คจุดวางจดหมาย (Day 2) - ไม่แสดงปุ่ม E และ Marker ตามคำขอ
        if self.current_day == 2 and self.letters_held > 0:
            for i, spot in enumerate(HOUSE_DOOR_SPOTS):
                # ถ้าพิกัดนี้ถูกส่งไปแล้ว ให้ข้าม
                if i in self.delivered_house_indices:
                    continue
                    
                px, py = self.player.logic_pos
                if abs(px - spot[0]) <= 32 and abs(py - spot[1]) <= 32:
                    # ไม่สร้าง Hint Label แล้ว แต่เก็บค่าเป้าหมายไว้ให้ interact() ทำงานได้เมื่อกด E
                    self.pending_drop_spot = (spot, i)
                    return

        # เช็คจุดค้นหา (ไม่แสดงปุ่ม E ตามคำขอ)
        self.current_search_target = self._get_search_target()

    def interact(self):
        """จัดการการกดปุ่ม [E] เพื่อคุยหรือสำรวจ"""
        self.clear_interaction_hints()
        
        # 0. เช็ค Underground Portal (Priority First on Day 5)
        from settings import UNDERGROUND_PORTAL_POS, PLAYER_START_X, PLAYER_START_Y
        px, py = self.player.logic_pos
        ux, uy = UNDERGROUND_PORTAL_POS
        dist = ((px - ux)**2 + (py - uy)**2)**0.5
        
        print(f"DEBUG: Interact pressed at ({px}, {py}). Portal dist: {dist:.1f}, Day: {self.current_day}")
        
        if dist <= 32 and self.current_day == 5:
            print("DEBUG: UNDERGROUND PORTAL TRIGGERED!")
            # ล้างทุกอย่างให้เกลี้ยงที่สุด (เหมือนตอนเข้าบ้าน แต่เน้นทำลายวัตถุด้วย)
            for npc in self.npcs: npc.destroy()
            for enemy in self.enemies: enemy.destroy()
            for er in getattr(self, 'extra_reapers', []): er.destroy()
            
            self.sorting_layer.clear()
            self.npcs, self.enemies, self.stars = [], [], []
            self.extra_reapers = []

            # ซ่อน Reaper หลักและย้ายไปไกลๆ (เฉพาะแมพนี้)
            if hasattr(self, 'reaper') and self.reaper:
                self.reaper.x, self.reaper.y = -5000, -5000 # ย้ายไปพิกัดที่ไม่มีใครเห็น
                self.reaper.logic_pos = [-5000, -5000]
                if hasattr(self.reaper, 'sprite_color'):
                    self.reaper.sprite_color.a = 0 # ซ่อน
                if hasattr(self.reaper, 'aura_color'):
                    self.reaper.aura_color.a = 0 # ซ่อนออร่า
                self.reaper.update_visual_positions()

            # 1. เปลี่ยนแมพ
            self.change_map('assets/Tiles/underground.tmj')
            
            # 2. วางตำแหน่งตัวละครในแมพใหม่
            # ตั้งพิกัดเกิดในแมพ underground (1088,16) ตามคำขอล่าสุด
            self.player.logic_pos = [1088, 16] 
            self.player.target_pos = [1088, 16]
            self.player.direction = 'up'
            self.player.update_frame()
            self.player.sync_graphics_pos()
            
            # 3. ใส่ตัวละครคืนเข้าไปใน Sorting Layer
            self.sorting_layer.add(self.player.group)
            
            # 4. สร้าง Entity ใหม่
            self.create_npcs()
            self.create_enemies()
            self.world_manager.create_reapers() 
            
            self.show_vn_dialogue("Little girl", "It's cold and damp down here... I should be careful.")
            return

        # 1. เช็คการวางจดหมาย (Day 2 Priority)
        if self.current_day == 2 and hasattr(self, 'pending_drop_spot') and self.pending_drop_spot:
            from settings import HOUSE_MARKS_MAPPING
            spot, spot_index = self.pending_drop_spot
            px, py = self.player.logic_pos
            if abs(px - spot[0]) <= 32 and abs(py - spot[1]) <= 32:
                if self.letters_held > 0 and spot_index not in self.delivered_house_indices:
                    # ขั้นตอนที่ 0: โชว์รูปสัญลักษณ์และสำรวจก่อน (ยังไม่มีช้อย)
                    mark_path = HOUSE_MARKS_MAPPING.get(tuple(spot))
                    self.pending_drop_spot = (spot, spot_index)
                    self.house_inspection_step = True # Flag เพื่อให้ก้าวต่อไปโชว์ Choice
                    self.show_vn_dialogue("Little girl", "I found a mark on this house door...", portrait=mark_path)
                    return

        if self.current_star_target:
            # เล่นเสียงรื้อค้น (Find) และเสียงสงสัย (Curious) เพราะมีทางเลือก
            if self.find_sound:
                self.find_sound.play()
            if self.curious_sound:
                self.curious_sound.play()
                
            star_pos = (self.current_star_target.x, self.current_star_target.y)
            # เช็คข้อมูลไอเทมตามวัน
            if 'underground.tmj' in self.game_map.filename.lower():
                # แมพใต้ดินใช้ช้อย SEARCH
                self.show_vn_dialogue("Little girl", "I found one of those objects... should I search inside?", choices=["SEARCH", "LEAVE IT"])
            elif self.current_day == 4:
                from settings import DAY4_KEY_MAPPING
                portrait = DAY4_KEY_MAPPING.get(star_pos, {}).get("portrait")
                self.show_vn_dialogue("Little girl", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"], portrait=portrait)
            else:
                from settings import STAR_ITEM_MAPPING
                portrait = STAR_ITEM_MAPPING.get(star_pos, {}).get("portrait")
                self.show_vn_dialogue("Little girl", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"], portrait=portrait)
            return

        # 1. เช็คจุดไฟเทียน (Day 3)
        if self.current_candle_target:
            if self.current_candle_target.is_lit:
                self.show_vn_dialogue("Little girl", "This candle is already burning brightly.")
                return
                
            self.show_vn_dialogue("Little girl", CANDLE_LIGHT_DIALOGUE, choices=CANDLE_LIGHT_CHOICES)
            return

        target, dx, dy = self._get_interaction_target(self.npcs + [self.reaper] + getattr(self, 'extra_reapers', []), limit=32)
        if target:
            npc_index = self.npcs.index(target) if target in self.npcs else -1
            self.process_interaction(target, npc_index, dx, dy)
            return

            self.show_vn_dialogue("Little girl", "It's cold and damp down here... I should be careful.")
            return

        # 3. เช็คจุดค้นหา (ทั่วไป และ Object ใน Underground)
        if self.current_search_target:
            self.process_search_spot(self.current_search_target)
            return

        # 4. เช็ค Object ใน Underground (Interaction with layers)
        if 'underground.tmj' in self.game_map.filename.lower():
            # ดึง Object จากเลเยอร์ "ของ" มาเช็ค Interaction
            objects_layer = next((l for l in self.game_map.tmx_data.layers if l.name == "ของ"), None)
            if objects_layer:
                px, py = self.player.logic_pos
                for obj in objects_layer:
                    dist = ((px - obj.x)**2 + (py - (self.game_map.height * 16 - obj.y))**2)**0.5
                    if dist <= 32:
                        print(f"DEBUG: Interacting with object {obj.id}")
                        self.process_search_spot(obj)
                        return

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
        
        # เล่นเสียงรื้อของ/หาของ
        if self.find_sound:
            self.find_sound.play()
        
        if spot == EMPTY_SPOT_HOME:
            self.show_vn_dialogue("Little girl", "Empty... they never leave anything for me anyway.")
            return

        if spot == self.correct_food_spot:
            self.show_vn_dialogue("Little girl", "Found it. This will keep me going tonight.")
            # ตั้งสถานะรอเควสสำเร็จ (จะถูกเรียกใน story_manager.handle_dialogue_end)
            self._pending_food_success = True
            return

        # 1. การค้นหาใน Underground (ดาว/Spark)
        if 'underground.tmj' in self.game_map.filename.lower():
            # ต้องคุยกับ The Soul ก่อนถึงจะหาเจอ (เช็คว่าเควส active หรือยัง)
            quest = self.quest_manager.active_quests.get("soul_fragments")
            if not quest or not quest.is_active:
                self.show_vn_dialogue("Little girl", "I don't know what I'm looking for... I should talk to the soul first.")
                return
            
            # สุ่มเจอ Spark (เลียนแบบระบบ Day 1)
            import random
            if random.random() < 0.4: # โอกาส 40%
                self.quest_manager.update_quest_progress("soul_fragments", 1)
                self.show_item_discovery("SOUL FRAGMENT", "assets/Items/star/doll1.png") # ใช้รูปชั่วคราว
                self.show_vn_dialogue("Little girl", "I found a soul fragment!")
            else:
                self.show_vn_dialogue("Little girl", "Nothing here but damp earth.")
            return

        self.show_vn_dialogue("Little girl", "Just dust and old rags. There’s nothing to eat here.")

        
    def process_interaction(self, target, index, dx, dy):
        """ประมวลผลการคุยกับ NPC หรือ Reaper"""
        # ล้าง Hint ทันทีเมื่อเริ่มการโต้ตอบ
        self.clear_interaction_hints()
        
        # หยุดการเดินของ Player ทันที
        self.pressed_keys.clear()
        self.player.stop()
        
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
            self.is_reaper_save_prompt = True
            dialogue = self.get_reaper_dialogue(dx, dy)
            self.show_dialogue_above_reaper(dialogue)
        else:
            # NPC - ระบุชื่อตามไฟล์รูปภาพเพื่อความแม่นยำ (แก้ปัญหา Index เลื่อนเมื่อบางตัวไม่โผล่)
            if hasattr(target, 'image_path'):
                if 'NPC1' in target.image_path: 
                    npc_name = "The Sad Soul"
                elif 'NPC2' in target.image_path: 
                    npc_name = "The Postman"
                elif 'NPC3' in target.image_path: 
                    npc_name = "The Old Soul"
                elif 'NPC4' in target.image_path: 
                    npc_name = "The Lady at the Window"
                elif 'NPC5' in target.image_path: 
                    npc_name = "The Soul"
                else:
                    npc_name = f"NPC{index + 1}"
            else:
                npc_name = f"NPC{index + 1}"
                
            dialogue = self.get_proximity_dialogue(npc_name, dx, dy)
            if dialogue:
                self.show_dialogue_above_npc(target, dialogue, npc_name=npc_name)

    # ---------------------------------------------------------
    # Dialogue & Quest Logic
    # ---------------------------------------------------------
    def show_dialogue_above_npc(self, npc, dialogue, npc_name=None):
        """แสดงข้อความคุยของ NPC สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # ถ้าไม่ได้ระบุชื่อมา ให้คำนวณตาม Index (Fallback)
        if npc_name is None:
            npc_name = "The Sad Soul" if self.npcs.index(npc) == 0 else f"NPC{self.npcs.index(npc) + 1}"
        
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        self.current_character_name = npc_name
        self.current_portrait = None # หรือระบุถ้ามีหน้าเฉพาะ
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            self.is_dialogue_active = True
            self.player.stop()
            first_text = self.current_dialogue_queue[0]
            self.dialogue_manager.show_vn_dialogue(npc_name, first_text)
            
    def show_dialogue_above_reaper(self, dialogue, choices=None, portrait=None):
        """แสดงข้อความคุยของ Reaper สไตล์ Visual Novel ด้านล่างหน้าจอ"""
        # ตั้งค่าคิวข้อความ
        self.current_dialogue_queue = dialogue
        self.current_dialogue_index = 0
        
        self.current_character_name = "Reaper"
        self.current_portrait = portrait
        
        # เล่นเสียงพูดของ Reaper ทุกครั้งที่เริ่มบทสนทนา
        if self.reaper_voice_sound:
            self.reaper_voice_sound.play()
        
        # แสดงข้อความแรก
        if self.current_dialogue_queue:
            self.is_dialogue_active = True
            self.player.stop()
            first_text = self.current_dialogue_queue[0]
            # แสดง Choice เฉพาะเมื่ออยู่หน้าสุดท้าย
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            self.dialogue_manager.show_vn_dialogue(
                "Reaper", first_text, 
                choices=(self.current_choices if is_last else None),
                portrait=self.current_portrait
            )

    def show_vn_dialogue(self, character_name, dialogue, choices=None, portrait=None, left_portrait=None):
        """แสดงกล่องข้อความสไตล์ Visual Novel ด้านล่างหน้าจอ"""
        self.is_dialogue_active = True
        self.player.stop()
        self.current_character_name = character_name
        if choices:
            self.current_choices = choices
        if portrait is not None:
            self.current_portrait = portrait
        else:
            self.current_portrait = None # รีเซ็ตเป็น None ถ้าฝั่งเรียกไม่ได้ส่งมา (ให้ใช้ Default)
            
        self.dialogue_manager.show_vn_dialogue(
            character_name, dialogue, 
            choices=choices, 
            portrait=self.current_portrait,
            left_portrait=left_portrait
        )

    def show_item_discovery(self, text, image_path=None, choices=None):
        """แสดงแจ้งเตือนการได้รับไอเทมกลางหน้าจอ (Delegated)"""
        self.is_dialogue_active = True
        self.pressed_keys.clear()
        self.player.stop()
        self.current_character_name = text # เพื่อให้ Story Manager รู้ว่าอะไรเพิ่งจบ
        self.dialogue_manager.show_item_discovery(text, image_path, choices=choices)
        root = self.dialogue_root if self.dialogue_root else self
        
    def close_dialogue(self):
        """ปิดกล่องข้อความคุยและคืนสถานะเกม"""
        # จำสถานะก่อนรีเซ็ต (ต้องทำก่อนเรียก dialogue_manager.close_dialogue เพราะมันจะเคลียร์ current_choices)
        last_char = getattr(self, 'current_character_name', None)
        has_choices = len(getattr(self, 'current_choices', [])) > 0
        
        self.dialogue_manager.close_dialogue()

        # คืนสถานะการคุย
        self.is_dialogue_active = False
        self._on_close_dialogue_reset()
        
        # ปลดล็อกกล้องถ้าไม่ได้ติดคัทซีนตัวเมือง/เนื้อเรื่องหลัก
        if not self.is_cutscene_active:
            self.camera.locked = False
        
        # ตรวจสอบว่าเป็นการจบคัทซีนเนื้อเรื่องเสริมหรือไม่
        if self.is_cutscene_active and getattr(self, 'cutscene_step', 0) == 11:
            self.cutscene_manager.end_side_story_cutscene()
            self.camera.locked = False
        
        # ส่งต่อ Logic เนื้อเรื่องให้ Story Manager จัดการทอดๆ ต่อไป
        self.story_manager.handle_dialogue_end(last_char, has_choices)
        self.is_reaper_save_prompt = False
        
        # รีเซ็ตสถานะโหมดสอนเสมอ (Story Manager จะเป็นคนคุม tutorial_mode ในอนาคต)
        self.tutorial_mode = False
        
    def _on_close_dialogue_reset(self):
        """รีเซ็ตค่าพื้นฐานหลังปิดบทสนทนา"""
        self.dialogue_timer = 0
        self.current_dialogue_queue = []
        self.current_dialogue_index = 0
        self.current_character_name = ""
        self.current_choices = []
        if hasattr(self, 'temp_dialogue_chars'):
            self.temp_dialogue_chars = []

    def next_dialogue(self):
        """ไปยังข้อความถัดไปในคิว"""
        if self.current_choices and self.current_dialogue_index == len(self.current_dialogue_queue) - 1:
            return

        # 1. เช็คก่อนว่าแชทปัจจุบันคือประโยคที่ต้องให้ของหรือไม่ (ถ้าใช่ ให้โชว์แจ้งเตือนไอเทมก่อนขยับไปประโยคถัดไป)
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            current_text = self.current_dialogue_queue[self.current_dialogue_index]
            
            # Event: ได้รับ Blue Stone (Day 1)
            if "Here, take this [Blue Stone] with you" in current_text and not self.has_received_blue_stone:
                self.preserved_character_name = self.current_character_name 
                self.dialogue_manager.close_dialogue()
                self.show_item_discovery("Received [Blue Stone]", "assets/items/blue stone.png")
                self.has_received_blue_stone = True
                return 
                
            # Event: ได้รับ Lantern (Day 3)
            if "Take this lantern. You'll need it to light the candles" in current_text and not self.has_received_lantern:
                self.preserved_character_name = self.current_character_name
                self.dialogue_manager.close_dialogue()
                self.show_item_discovery("Received [Lantern]", "assets/Items/Lantern.png")
                self.has_received_lantern = True
                return

        if getattr(self, 'preserved_character_name', None) is not None:
            self.current_character_name = self.preserved_character_name
            self.preserved_character_name = None

        # 2. ขยับไปยังข้อความถัดไป
        self.current_dialogue_index += 1
        
        if self.current_dialogue_index < len(self.current_dialogue_queue):
            next_text = self.current_dialogue_queue[self.current_dialogue_index]
            is_last = (self.current_dialogue_index == len(self.current_dialogue_queue) - 1)
            
            # เช็คว่ามีลิสต์ชื่อตัวละครชั่วคราวหรือไม่ (เช่น คัทซีนสลับคุย)
            if hasattr(self, 'temp_dialogue_chars') and self.temp_dialogue_chars:
                if self.current_dialogue_index < len(self.temp_dialogue_chars):
                    self.current_character_name = self.temp_dialogue_chars[self.current_dialogue_index]
            
            self.dialogue_manager.show_vn_dialogue(
                self.current_character_name, next_text, 
                choices=(self.current_choices if is_last else None),
                portrait=self.current_portrait
            )
        else:
            # ตรวจสอบลำดับการตรวจบ้าน Day 2 (ลำดับที่ 0 -> 1)
            if getattr(self, 'house_inspection_step', False) and hasattr(self, 'pending_drop_spot'):
                from settings import HOUSE_MARKS_MAPPING
                self.house_inspection_step = False
                spot = self.pending_drop_spot[0]
                mark_path = HOUSE_MARKS_MAPPING.get(tuple(spot))
                self.show_vn_dialogue("Little girl", "Should I leave a letter?", 
                                     choices=["Leave a letter", "Let me think"], portrait=mark_path)
                return

            self.close_dialogue()

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยตามระยะห่างของ NPC"""
        if npc_name == "The Soul":
            quest = self.quest_manager.active_quests.get("soul_fragments")
            if quest:
                if quest.current_count >= quest.target_count:
                    from storygame.chat import NPC5_SUCCESS
                    return [NPC5_SUCCESS]
                elif quest.is_active:
                    return ["Were you able to find the fragments? I can almost feel myself becoming whole again..."]

        if npc_name == "The Sad Soul":
            quest = self.quest_manager.active_quests.get("doll_parts")
            if quest:
                if quest.current_count >= quest.target_count:
                    if self.quest_item_fail:
                        return ["Oh! You found them!", "Wait... these parts... they're just old scrap metal...", "Why would you give me these? This isn't my doll..."]
                    return ["Oh! You found them!", "My doll... it's whole again. Thank you so much!", "You really are a kind one."]
                elif quest.is_active:
                    return ["Were you able to find the pieces? It's still so dark..."]

        if npc_name == "The Postman":
            quest = self.quest_manager.active_quests.get("deliver_letters")
            if quest:
                if quest.current_count >= quest.target_count:
                    if getattr(self, "quest_item_fail", False): # Just in case day 2 has a fail state later
                        return ["Are you sure these went to the right houses? ...I suppose it's done anyway.", "Thank you..."]
                    return ["Ah, you're back...", "My work here is finally done.", "Thank you, little one..."]
                elif quest.is_active:
                    return ["..."]

        if npc_name == "The Old Soul":
            quest = self.quest_manager.active_quests.get("light_candles")
            if quest:
                if quest.current_count >= quest.target_count:
                    from storygame.chat import OLD_SOUL_SUCCESS, OLD_SOUL_FAIL
                    if getattr(self, "quest_item_fail", False):
                        return [OLD_SOUL_FAIL]
                    return [OLD_SOUL_SUCCESS]
                elif quest.is_active:
                    return ["The red flowers in the vase...", "The blue rug in the hallway...", "The yellow sunlight on the porch...", "If only I could see those colors again..."]

        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        """คืนค่าลิสต์ข้อความคุยของ Reaper ครั้งละ 1 ประโยคแบบสุ่ม หรือคำใบ้ถ้ามีเควสอยู่"""
        quest_doll = self.quest_manager.active_quests.get("doll_parts")
        if quest_doll and quest_doll.is_active and quest_doll.current_count < quest_doll.target_count:
            return ["What he worries about... was thrown away with the unwanted things.", "Try searching that trash pile, you might find something."]
            
        quest_letters = self.quest_manager.active_quests.get("deliver_letters")
        if quest_letters and quest_letters.is_active and quest_letters.current_count < quest_letters.target_count:
            return ["Every silent message seeks its twin carved in wood... lead it home"]

        quest_candles = self.quest_manager.active_quests.get("light_candles")
        if quest_candles and quest_candles.is_active and quest_candles.current_count < quest_candles.target_count:
            return ["He already told you the order. Just follow the sequence of his memories."]

        return [random.choice(REAPER_DIALOGUES)]

    def on_choice_selected(self, choice):
        """จัดการเมื่อผู้เล่นเลือก Choice (เรียกใช้ตรรกะจาก choice.py)"""
        if self.click_sound:
            self.click_sound.play()
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
        # ล้างทรัพยากรทั้งหมด (เสียง/ปุ่มค้าง) ก่อนออกจาก GameWidget
        self.cleanup()
        
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
        if increment:
            self.current_day += 1
        
        # 3. Animation Sequence
        anim = Animation(opacity=1, duration=1.5) # จอค่อยๆ มืดลง
        
        def on_dark(*args):
            # ระหว่างที่จอมืด ให้รีเซ็ตโลกใหม่
            self.warning_dismissed = False
            self.warning_triggered = False
            self.is_dialogue_active = True
            self.is_cutscene_active = False # ปลดล็อกคัทซีนเดิม
            self.is_ready = True            # ยืนยันว่าเกมพร้อม
            self.player.is_in_home = False
            
            # ล้างข้อมูลของวันเก่าที่จบไปแล้ว (Cleanup - User Request)
            if self.current_day > 1:
                self.collected_stars = []
                self.destroyed_enemies = [] # รีศัตรูให้กลับมาเกิดใหม่ทุกวัน
                day1_quests = ["doll_parts", "find_food"]
                for qid in day1_quests:
                    if qid in self.quest_manager.active_quests:
                        del self.quest_manager.active_quests[qid]
            
            if self.current_day > 2:
                self.letters_held = 0
                self.delivered_house_indices = []
                if "deliver_letters" in self.quest_manager.active_quests:
                    del self.quest_manager.active_quests["deliver_letters"]
                    
            self.quest_manager.update_quest_list_ui()

            self.recreate_world()
            self.world_manager.create_house_marks()
            
            # 4. แสดง IntroScreen (Day X) เหมือนหน้าจอแรกสุดของเกม
            def start_fading_in():
                # เมื่อโชว์ Day X จบแล้ว ให้ค่อยๆ จางจอดำออก
                fade_in = Animation(opacity=0, duration=1.5)
                def on_fade_complete(*a):
                    root.remove_widget(black_overlay)
                    
                    # เริ่มบทสนทนาประจำวันทันทีหลังจอจางลง (ขาสู่ Day 2, 3, 4, 5)
                    self.is_dialogue_active = True
                    self.is_cutscene_active = False
                    self.is_ready = True
                    self.player.is_in_home = False
                    self.player.state = 'idle'
                    self.player.is_moving = False
                    self.request_keyboard_back()
                    
                    # เรียก Reaper มาคุยบทนำของวันนั้นๆ
                    self._start_intro_dialogue(0)
                fade_in.bind(on_complete=on_fade_complete)
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
        
        # เล่นเสียง Ambiance Loop ตั้งแต่เริ่มเกม (เปิดโปรแกรมปุ๊บเปิดเสียงเลย)
        ambiance_path = 'assets/sound/loop/Ambiance_Cave_Dark_Loop_Stereo.wav'
        if os.path.exists(ambiance_path):
            self.bg_loop = SoundLoader.load(ambiance_path)
            if self.bg_loop:
                self.bg_loop.loop = True
                self.bg_loop.volume = 0.4
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

    def create_candles(self):
        """สร้างไอเทมเทียนตามพิกัดใน settings.py"""
        from settings import CANDLE_SPAWN_LOCATIONS
        # ล้างของเดิมก่อน
        for c in self.candles:
            c.destroy()
        self.candles = []
        
        for x, y in CANDLE_SPAWN_LOCATIONS:
            candle = Candle(self.sorting_layer, x, y)
            self.candles.append(candle)

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