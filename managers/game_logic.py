import random
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.animation import Animation
from kivy.clock import Clock
from data.settings import *

class GameplayManager:
    def __init__(self, game):
        self.game = game

    def respawn_at_reaper(self):
        """เมื่อหัวใจหมด วาปผู้เล่นกลับไปยังจุดเริ่มต้นและรีเซ็ตหัวใจ"""
        # หยุดเสียงทั้งหมดทันที (รวมถึงเสียงผีไล่)
        self.game.stop_all_sounds()
        
        self.game.death_count += 1
        print(f"Player died. Total deaths: {self.game.death_count}")
        
        # รีเซ็ตสถานะการเคลื่อนไหว
        self.game.pressed_keys.clear()
        self.game.player.is_moving = False
        self.game.player.state = 'idle'
        
        # วาร์ปผู้เล่นไปยังจุดที่เซฟไว้ล่าสุด (ถ้ามี) ไม่เช่นนั้นใช้จุดเริ่มต้นดั้งเดิม
        start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
        start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
        target_map = MAP_FILE
        
        if getattr(self.game, 'save_manager', None):
            latest_save = self.game.save_manager.get_latest_save_data()
            if latest_save and 'player_pos' in latest_save:
                saved_x, saved_y = latest_save['player_pos']
                start_x = (saved_x // TILE_SIZE) * TILE_SIZE
                start_y = (saved_y // TILE_SIZE) * TILE_SIZE
                target_map = latest_save.get('current_map', MAP_FILE)
                
        # ถ้าพิกัดที่เซฟไว้ไม่ได้อยู่ในแมพปัจจุบัน ให้ทำการเปลี่ยนแมพก่อน
        if self.game.game_map.filename != target_map:
            self.game.world_manager.change_map(target_map)

        self.game.player.logic_pos = [start_x, start_y]
        self.game.player.target_pos = [start_x, start_y]
        self.game.player.sync_graphics_pos()
        self.game.player.direction = 'up'
        self.game.player.update_animation_speed()
        self.game.player.update_frame()
        
        # รีเซ็ตเลือด
        self.game.heart_ui.reset_health()
            
        # สุ่มคำพูดโดยไม่ให้ซ้ำกับรอบล่าสุด
        from data.chat import REAPER_DEATH_QUOTES
        
        # User Request: เมื่อตายครบ 3 ครั้ง (death_count = 3) ให้ขึ้น Hidden Ending
        if self.game.death_count == 3:
            if hasattr(self.game, 'cutscene_manager'):
                # ตรวจสอบและหยุดเสียง NPC ทั้งหมดก่อนเริ่มฉากจบ
                self.game.stop_all_sounds()
                self.game.cutscene_manager.start_succumb_ending()
            return

        # ส่งคำพูดผ่าน InteractionManager เพื่อให้ระบบ Dialogue ทำงานถูกต้อง (และหยุดเสียงผี)
        available_indices = [i for i in range(len(REAPER_DEATH_QUOTES)) if i != self.game.last_death_quote_index]
        if available_indices:
            q_idx = random.choice(available_indices)
            self.game.last_death_quote_index = q_idx
            # เรียกผ่านระบบ Interaction เพื่อให้ is_dialogue_active = True
            # พอตายแล้วขึ้น chat reaper ไม่ต้องให้ขึ้น save (can_save=False)
            self.game.interaction_manager.show_dialogue_above_reaper(
                [REAPER_DEATH_QUOTES[q_idx]], 
                can_save=False
            )

    def use_stun_item(self):
        """ใช้ Blue Stone เพื่อสตันผีรอบๆ ตัว"""
        stun_range = 100 
        self.game.stun_cooldown = 15.0 
        
        px, py = self.game.player.logic_pos
        player_center_x = px + TILE_SIZE / 2
        player_center_y = py + TILE_SIZE / 2
        
        stunned_any = False
        for enemy in self.game.enemies:
            ex, ey = enemy.logic_pos
            enemy_center_x = ex + TILE_SIZE / 2
            enemy_center_y = ey + TILE_SIZE / 2
            
            dist = ((player_center_x - enemy_center_x)**2 + (player_center_y - enemy_center_y)**2)**0.5
            if dist <= stun_range:
                enemy.stun(duration=3.0)
                stunned_any = True
        
        if stunned_any:
            # การอัปเดต Label คูลดาวน์จะทำใน main.py ทุกเฟรม
            print("Stun activated!")
        else:
            print("Stun used but no enemies nearby.")

    def handle_day_transition(self, increment=True):
        """จัดการการตัดฉากขึ้นวันใหม่"""
        if not getattr(self.game, '_pending_day_transition', False): return
        self.game._pending_day_transition = False
        
        # 1. แสดงจอดำ (Fade Out)
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        black_overlay = Widget(size_hint=(1, 1), opacity=0)
        with black_overlay.canvas:
            Color(0, 0, 0, 1)
            self.game.black_rect_trans = Rectangle(size=root.size, pos=(0, 0))
            
        def update_black_rect_trans(instance, value):
            self.game.black_rect_trans.size = (instance.width * 2, instance.height * 2)
            self.game.black_rect_trans.pos = (-instance.width * 0.5, -instance.height * 0.5)
        black_overlay.bind(size=update_black_rect_trans, pos=update_black_rect_trans)
        update_black_rect_trans(black_overlay, None)
        root.add_widget(black_overlay)
        
        # 2. เพิ่ม Day Counter
        if increment:
            self.game.current_day += 1
        
        # 3. Animation Sequence
        anim = Animation(opacity=1, duration=1.5) 
        
        def on_dark(*args):
            self.game.warning_dismissed = False
            self.game.warning_triggered = False
            self.game.is_dialogue_active = True
            self.game.is_cutscene_active = False 
            self.game.is_ready = True            
            self.game.player.is_in_home = False
            
            if self.game.current_day > 1:
                self.game.collected_stars = []
                self.game.destroyed_enemies = [] 
                day1_quests = ["doll_parts", "find_food"]
                for qid in day1_quests:
                    if qid in self.game.quest_manager.active_quests:
                        del self.game.quest_manager.active_quests[qid]
            
            if self.game.current_day > 2:
                self.game.letters_held = 0
                self.game.delivered_house_indices = []
                if "deliver_letters" in self.game.quest_manager.active_quests:
                    del self.game.quest_manager.active_quests["deliver_letters"]
                    
            self.game.quest_manager.update_quest_list_ui()
            self.game.recreate_world()
            self.game.world_manager.create_house_marks()
            
            from ui.intro import IntroScreen
            def start_fading_in():
                fade_in = Animation(opacity=0, duration=1.5)
                def on_fade_complete(*a):
                    root.remove_widget(black_overlay)
                    self.game.is_dialogue_active = True
                    self.game.is_cutscene_active = False
                    self.game.is_ready = True
                    self.game.player.is_in_home = False
                    self.game.player.state = 'idle'
                    self.game.player.is_moving = False
                    self.game.request_keyboard_back()
                    self.game._start_intro_dialogue(0)
                fade_in.bind(on_complete=on_fade_complete)
                fade_in.start(black_overlay)

            intro = IntroScreen(callback=start_fading_in, day=self.game.current_day)
            root.add_widget(intro)
            
        anim.bind(on_complete=on_dark)
        anim.start(black_overlay)
