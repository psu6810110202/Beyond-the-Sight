# storygame/cutscene.py
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader
from kivy.animation import Animation
from ui.intro import IntroScreen
from data.settings import *
from data.settings import PLAYER_PORTRAIT_IMG
from data.chat import ENDING_TITLES

class CutsceneManager:
    def __init__(self, game):
        self.game = game
        self._food_wait_timer = 0 # สำหรับหน่วงเวลาตอนกินข้าว
        self._anim_timer = 0
        self._pending_find_food_quest = False
        
        # โหลดเสียงประตู
        self.door_sound = SoundLoader.load('assets/sound/door/Door_squeeky_2.wav')
        self.door_close_sound = SoundLoader.load('assets/sound/door/Door_close.wav')
        
        if self.door_sound:
            self.door_sound.volume = 0.6
        if self.door_close_sound:
            self.door_close_sound.volume = 0.6
        
        # โหลดเสียงนั่ง
        self.sit_sound = SoundLoader.load('assets/sound/sit.wav')
        if self.sit_sound:
            self.sit_sound.volume = 0.5

    def play_door_full_sequence(self):
        """เล่นเสียงประตูเปิดตามด้วยเสียงปิด"""
        if self.door_sound:
            self.door_sound.play()
        # หน่วงเวลา 1.2 วินาทีเพื่อให้เสียงเอี๊ยดจบแล้วค่อยปิด
        if self.door_close_sound:
            Clock.schedule_once(lambda dt: self.door_close_sound.play(), 1.2)

    def start_quest_complete_cutscene(self, dt=None):
        """เริ่มลำดับ Cutscene เมื่อจบเควส"""
        self.game.clear_interaction_hints()
        self.game.is_cutscene_active = True
        self.game.cutscene_step = 1 # ขั้นตอนเดินออกจากจอ
        self.game.camera.locked = True
        
        # สำหรับ Day 3: ใช้ waypoint เพื่อเดินเลี้ยว
        self.game.waypoints = []
        if self.game.current_day == 3:
             # จากแมพบนซ้าย (แถว Old Soul) เลี้ยวไปทางขวาแล้วลงล่าง
             self.game.waypoints = [(800, 1472), (800, 1000), (1200, 1000), (1200, -100)] 
        
        for npc in self.game.npcs:
            npc.is_fading = True
            npc.is_moving = False

    def update(self, dt):
        """จัดการลำดับของ Cutscene"""
        self.game.clear_interaction_hints()
        
        # อัปเดตอนิเมชั่น father hit ถ้ากำลังแสดงอยู่
        if hasattr(self, 'father_hit_widget') and self.father_hit_widget:
            self.update_father_hit_animation(dt)
        
        if self.game.cutscene_step == 1:
            # อัปเดตการจางหายของ NPC
            for npc in self.game.npcs:
                npc.update(dt)

            npcs_to_remove = []
            for npc in self.game.npcs:
                if npc.fading_done:
                    npcs_to_remove.append(npc)
                    if npc.group in self.game.sorting_layer.children:
                        self.game.sorting_layer.remove(npc.group)
            
            for npc in npcs_to_remove:
                if npc in self.game.npcs:
                    self.game.npcs.remove(npc)
            
            # เมื่อจางหายไปจนหมดแล้ว ให้ตัวละครเริ่มเดินออกจากฉาก
            if len(self.game.npcs) == 0:
                # เฟสเดินออก
                cam_x = -self.game.camera.trans_pos.x
                cam_y = -self.game.camera.trans_pos.y
                scale_f = self.game.camera.scale.x
                visible_w = self.game.width / scale_f if scale_f != 0 else CAMERA_WIDTH
                visible_h = self.game.height / scale_f if scale_f != 0 else CAMERA_HEIGHT
                
                right_edge = cam_x + (visible_w / 2) + 64
                bottom_edge = cam_y - (visible_h / 2) - 64
                
                direction = 'down' if self.game.current_day in [2, 4] else 'right'
                
                reached_edge = False
                px, py = self.game.player.logic_pos

                if self.game.waypoints:
                    # เดินตาม waypoint (Day 3)
                    tx, ty = self.game.waypoints[0]
                    
                    # ตรวจสอบว่า "เข้าไกล้" จุดหมายหรือยัง (ใช้ระยะ 64 เพื่อความชัวร์กันก้าวขาพลาิดพิกัด)
                    if abs(px - tx) < 64 and abs(py - ty) < 64:
                        print(f"DEBUG: Reached waypoint ({tx}, {ty})")
                        self.game.waypoints.pop(0)
                        if not self.game.waypoints: 
                            reached_edge = True
                    else:
                        dx, dy = tx - px, ty - py
                        if abs(dx) > abs(dy): direction = 'right' if dx > 0 else 'left'
                        else: direction = 'up' if dy > 0 else 'down'
                else:
                    # เดินตรงๆ จนทะลุขอบจอ (Day 1, 2)
                    if direction == 'right' and self.game.player.logic_pos[0] > right_edge:
                        reached_edge = True
                    elif direction == 'down' and self.game.player.logic_pos[1] < bottom_edge:
                        reached_edge = True
                
                # FALLBACK: ถ้าตัวละครเดินทะลุขอบแผนที่ไปไกลแล้ว (กันบั๊ก Waypoint ไม่ทำงาน)
                if px < -64 or px > MAP_WIDTH + 64 or py < -64 or py > MAP_HEIGHT + 64:
                    print("DEBUG: Off-map fallback triggered.")
                    reached_edge = True
                
                # SAFETY: ถ้าหลุดขอบจอกราฟิกไปแล้ว (ในขณะที่กล้องล็อค) ให้ตัดฉากเลยไม่ต้องรอ Waypoint หมด
                if px > right_edge or py < bottom_edge:
                    print(f"DEBUG: Off-screen fallback triggered (px={px}, right={right_edge})")
                    reached_edge = True
                
                if self.game.player.is_moving:
                    self.game.player.continue_move()
                else:
                    self.game.player.cutscene_mode = True
                    # ใช้ความเร็วปกติ แต่สั่งเดินต่อเนื่อง
                    self.game.player.current_speed = WALK_SPEED
                    self.game.player.move({direction})
                
                if reached_edge:
                    self.game.cutscene_step = 2
                    self.show_black_screen_transition()

        elif self.game.cutscene_step == 20:
            # Day Transition: เดินไปพิกัดกินอาหาร
            tx, ty = HOME_EAT_POS
            px, py = self.game.player.logic_pos
            
            self.game.player.cutscene_mode = True 
            
            # 1. เช็คว่าถึงที่หมายหรือยัง
            at_target = abs(px - tx) < 2 and abs(py - ty) < 2
            if at_target and not self.game.player.is_moving:
                self.game.player.stop() 
                
                # ถึงที่หมายสนิทแล้ว
                if getattr(self.game, 'sit_sound', None):
                    self.game.sit_sound.play()
                    
                self.game.player.logic_pos = [tx, ty]
                self.game.player.target_pos = [tx, ty]
                self.game.player.sync_graphics_pos()
                self.game.player.direction = 'down' 
                self.game.player.state = 'idle'
                self.game.player.frame_index = 0
                self.game.player.update_frame()
                
                self.game.cutscene_step = 21
                self._food_wait_timer = 0
            else:
                # 2. ถ้ากำลังเดินอยู่ ให้ปล่อยให้ระบบเดินต่อไปจนจบช่อง
                if self.game.player.is_moving:
                    self.game.player.move(set(), self.game.npcs, self.game.reaper, self.game.game_map.solid_rects)
                else:
                    # 3. เลือกทิศทาง (Dodge Logic)
                    dx, dy = tx - px, ty - py
                    dirs = []
                    if abs(dx) >= 2: dirs.append(('right' if dx > 0 else 'left', abs(dx)))
                    if abs(dy) >= 2: dirs.append(('up' if dy > 0 else 'down', abs(dy)))
                    dirs.sort(key=lambda x: x[1], reverse=True)
                    priorities = [d[0] for d in dirs]
                    
                    chosen_key = None
                    def is_blocked(d):
                        sx, sy = 0, 0
                        if d == 'up': sy = TILE_SIZE
                        elif d == 'down': sy = -TILE_SIZE
                        elif d == 'left': sx = -TILE_SIZE
                        elif d == 'right': sx = TILE_SIZE
                        nx, ny = px + sx, py + sy
                        return (self.game.player.check_map_collision(nx, ny, self.game.game_map.solid_rects) or 
                                self.game.player.check_npc_collision(nx, ny, self.game.npcs))

                    for k in priorities:
                        if not is_blocked(k): chosen_key = k; break
                    
                    if not chosen_key and priorities:
                        all_dirs = ['up', 'down', 'left', 'right']
                        for k in all_dirs:
                            if k != priorities[0] and not is_blocked(k): chosen_key = k; break
                    
                    if chosen_key:
                        self.game.player.current_speed = WALK_SPEED
                        self.game.player.direction = chosen_key
                        self.game.player.move({chosen_key}, self.game.npcs, self.game.reaper, self.game.game_map.solid_rects)
                        self.game.player.update_animation_speed()

        elif self.game.cutscene_step == 21:
            # ยืนรอ 3 วิ
            if self.game.player.is_moving:
                self.game.player.move(set(), self.game.npcs, self.game.reaper, self.game.game_map.solid_rects)
            
            self.game.player.stop()
            self.game.player.update_frame()
            
            self._food_wait_timer += dt
            if self._food_wait_timer >= 3.0:
                self.game.cutscene_step = 0 
                self.game.handle_day_transition()
                    
        elif self.game.cutscene_step == 30:
            self._day2_wait_timer += dt
            if self._day2_wait_timer >= 3.0:
                self.game.cutscene_step = 31 # กำลังเข้าสู่บทสนทนา
                if hasattr(self, 'day2_black_bg') and self.day2_black_bg.parent:
                    from kivy.animation import Animation
                    anim = Animation(opacity=0, duration=2.0)
                    
                    def start_chat(*a):
                        if self.day2_black_bg.parent:
                            self.day2_black_bg.parent.remove_widget(self.day2_black_bg)
                            
                        # เริ่มบทสนทนาหลังจากจอสว่างแล้ว โดยดึงจาก chat.py
                        from data.chat import PARENT_FIGHT_DIALOGUE
                        data = PARENT_FIGHT_DIALOGUE
                        
                        self.game.current_dialogue_queue = [d["text"] for d in data]
                        self.game.temp_dialogue_chars = [d["char"] for d in data]
                        self.game.current_dialogue_index = 0
                        self.game.current_character_name = self.game.temp_dialogue_chars[0]
                        self.game.is_dialogue_active = True
                        self.game.dialogue_manager.show_vn_dialogue(self.game.current_character_name, self.game.current_dialogue_queue[0])
                        
                    anim.bind(on_complete=start_chat)
                    anim.start(self.day2_black_bg)
                    
        elif self.game.cutscene_step == 10:
            # Side story: แพนกล้องจากด้านล่างหน้าจอ เลื่อนกลับขึ้นมาหาผู้เล่น (150 pixels in 3 seconds = 50 px/s)
            pan_speed = 50 * dt  
            
            # เมื่อครู่เรา -150 (เลื่อนกล้องลง) ทำให้ตอนนี้ trans_pos.y น้อยกว่าเป้าหมาย
            # ดังนั้นเราต้อง ค่อยๆ บวกความเร็ว เพื่อให้กล้องขยับกลับขึ้นไปยังจุดที่ถูกต้อง
            if self.game.camera.trans_pos.y < self.target_cam_y:
                self.game.camera.trans_pos.y += pan_speed
                # ถ้าบวกไปจนทะลุเป้าหมาย แปลว่าเลื่อนเสร็จแล้ว
                if self.game.camera.trans_pos.y >= self.target_cam_y:
                    self.game.camera.trans_pos.y = self.target_cam_y
                    self._on_pan_complete()
            else:
                self._on_pan_complete()

        elif self.game.cutscene_step == 40:
            # ผู้เล่นเดินไปที่มุมห้อง (ที่นั่งประจำ) อัตโนมัติหลังคุยจบ
            tx, ty = (16, 176) # พิกัดมุมห้องเป้าหมาย
            px, py = self.game.player.logic_pos
            
            self.game.player.cutscene_mode = True 
            
            # 1. เช็คว่าถึงที่หมายหรือยัง
            at_target = abs(px - tx) < 2 and abs(py - ty) < 2
            
            if at_target and not self.game.player.is_moving:
                # หยุดตัวละครและรีเซ็ต FPS ครั้งเดียวก่อนเข้า step 41
                self.game.player.cutscene_mode = False
                self.game.player.is_moving = False
                self.game.player.state = 'idle'
                self.game.player.frame_index = 0
                self.game.player.update_animation_speed()  # รีเซ็ต FPS เป็น idle (2 fps)
                
                # ถึงที่หมายสนิทแล้ว
                if self.sit_sound:
                    self.sit_sound.play()
                    
                self.game.player.logic_pos = [tx, ty]
                self.game.player.target_pos = [tx, ty]
                self.game.player.sync_graphics_pos()
                self.game.player.direction = 'down' 
                self.game.player.update_frame()
                
                self.game.cutscene_step = 41
                self._anim_timer = 0
            else:
                # 2. ถ้ากำลังเดินอยู่ ให้เดินให้สุดช่อง (Grid) ก่อน
                if self.game.player.is_moving:
                    self.game.player.move(set(), self.game.npcs, self.game.reaper, self.game.game_map.solid_rects)
                else:
                    # 3. ลอจิกการเดินแบบ L-Shape (เดินเป็นเส้นตรง เนียนกว่าเดินเฉียง)
                    dx, dy = tx - px, ty - py
                    chosen_key = None
                    
                    def is_blocked(d):
                        sx, sy = 0, 0
                        if d == 'up': sy = TILE_SIZE
                        elif d == 'down': sy = -TILE_SIZE
                        elif d == 'left': sx = -TILE_SIZE
                        elif d == 'right': sx = TILE_SIZE
                        nx, ny = px + sx, py + sy
                        # เช็คทั้งแมพและ NPC (ใช้ logic ปกติไม่ข้ามคัตซีน)
                        return (self.game.player.check_map_collision(nx, ny, self.game.game_map.solid_rects) or 
                                self.game.player.check_npc_collision(nx, ny, self.game.npcs))

                    # พยายามเดินในแกนที่ระยะห่างเยอะที่สุดก่อน
                    if abs(dx) > 2 and abs(dy) > 2:
                        if abs(dx) > abs(dy):
                            pref_x = 'right' if dx > 0 else 'left'
                            pref_y = 'up' if dy > 0 else 'down'
                            if not is_blocked(pref_x): chosen_key = pref_x
                            elif not is_blocked(pref_y): chosen_key = pref_y
                        else:
                            pref_x = 'right' if dx > 0 else 'left'
                            pref_y = 'up' if dy > 0 else 'down'
                            if not is_blocked(pref_y): chosen_key = pref_y
                            elif not is_blocked(pref_x): chosen_key = pref_x
                    elif abs(dx) > 2:
                        pref_x = 'right' if dx > 0 else 'left'
                        if not is_blocked(pref_x): chosen_key = pref_x
                        else: 
                            if not is_blocked('up'): chosen_key = 'up'
                            elif not is_blocked('down'): chosen_key = 'down'
                    elif abs(dy) > 2:
                        pref_y = 'up' if dy > 0 else 'down'
                        if not is_blocked(pref_y): chosen_key = pref_y
                        else: 
                            if not is_blocked('left'): chosen_key = 'left'
                            elif not is_blocked('right'): chosen_key = 'right'

                    if chosen_key:
                        self.game.player.current_speed = WALK_SPEED
                        self.game.player.direction = chosen_key
                        # ในคัทซีนเดินที่นี่ เรายอมให้เดินชน hitbox ปกติ (ไม่ข้าม) เพื่อความเป๊ะ
                        self.game.player.move({chosen_key}, self.game.npcs, self.game.reaper, self.game.game_map.solid_rects)
                        self.game.player.update_animation_speed()
                    else:
                        self.game.player.logic_pos = [tx, ty]

        elif self.game.cutscene_step == 41:
            # ยืน/นั่งรอ 3 วิ (ไม่ต้อง reset state ซ้ำทุก frame เพราะทำไปแล้วใน step 40)
            
            self._anim_timer += dt
            if self._anim_timer >= 3.0:
                self.game.cutscene_step = 0 
                # เฉพาะ Day 2 ที่ไม่ต้องหาอาหารตามคำขอ USER - ขึ้น '...' แล้วเปลี่ยนวันทันที
                if self.game.current_day == 2:
                    self.game.is_cutscene_active = False
                    self.game.camera.locked = False
                    self.game.request_keyboard_back()
                    self.game.show_vn_dialogue("Little girl", "...", portrait=PLAYER_S_PORTRAIT_IMG)
                    # ตั้งธงให้ handle_dialogue_end รู้ว่าจะเปลี่ยนวันหลังจาก "..." จบ
                    self.game._pending_day_transition = True
                elif self.game.current_day == 3:
                    self.game._pending_day_transition = True
                    self.game.handle_day_transition(increment=True)
                else:
                    # วันอื่นๆ (1, 4, 5) ให้ปลดล็อกเพื่อให้ผู้เล่นเริ่มหาของกินได้
                    self.game.is_cutscene_active = False
                    self.game.camera.locked = False
                    self.game.request_keyboard_back()
                    # เริ่มเควสหาของกิน
                    self.game.quest_manager.start_quest("find_food", "Find Something to Eat", target=1, show_notif=True)

        elif self.game.cutscene_step >= 100:
            # Hidden Ending logic is primarily driven by animations and input events
            if hasattr(self.game, 'player'):
                self.game.player.is_moving = False
                self.game.player.state = 'idle'
                self.game.player.update_frame()

    def _get_scaled_font_size(self):
        """Scale font size (Single point of control)"""
        # ปรับจาก 120 ลงมาเป็น 80 เพื่อให้ตัวหนังสือไม่ใหญ่จนเกินไป (Downsized for better fit)
        from data.settings import WINDOW_HEIGHT
        return 80 * (self.height / WINDOW_HEIGHT if self.height > 0 else 1.0)

    def _on_pan_complete(self):
        """เมื่อเลื่อนกล้องเสร็จ ให้เริ่มบทสนทนา"""
        self.game.cutscene_step = 11
        data = self.side_story_data
        
        self.game.current_dialogue_queue = data["queue"]
        self.game.current_dialogue_index = 0
        self.game.current_character_name = data["character"]
        self.game.current_choices = data["choices"] if data["choices"] else []
        self.game.current_portrait = data["portrait"]
        
        if self.game.current_dialogue_queue:
            first_text = self.game.current_dialogue_queue[0]
            is_last = (len(self.game.current_dialogue_queue) == 1)
            self.game.is_dialogue_active = True
            self.game.dialogue_manager.show_vn_dialogue(
                data["character"], first_text,
                choices=(data["choices"] if is_last else None),
                portrait=data["portrait"]
            )

    def start_side_story_cutscene(self, dialogue_queue, character_name, portrait=None, choices=None):
        """เริ่มคัทซีนเนื้อเรื่องเสริม (ตัวละคร idle, กล้องเลื่อนจากล่างขึ้นบน แล้วค่อยคุย)"""
        self.game.clear_interaction_hints()
        
        # เล่นเสียงประตูเปิดตามด้วยปิด (สมมติว่าเพิ่งเดินเข้าบ้านมา)
        self.play_door_full_sequence()
        
        # 1. หยุดผู้เล่น
        self.game.pressed_keys.clear()
        self.game.player.stop()
        
        # 2. ตั้งสถานะ cutscene
        self.game.is_cutscene_active = True
        self.game.cutscene_step = 10  # 10 คือรหัส step สำหรับ Side Story Cutscene
        self.game.camera.locked = True
        
        # เก็บข้อมูลบทสนทนาไว้เปิดทีหลัง
        self.side_story_data = {
            "queue": dialogue_queue,
            "character": character_name,
            "portrait": portrait,
            "choices": choices
        }
        
        # 3. เซ็ตตำแหน่งเริ่มต้นกล้อง (แพนกล้อง)
        # เนื่องจากกล้องเพิ่งดึงไปโฟกัสตัวผู้เล่นที่ [160,0] ใน end_cutscene เราใช้ค่าปัจจุบันคืนเป็นเป้าหมายได้เลย
        self.target_cam_y = self.game.camera.trans_pos.y
        # จับกล้องเลื่อนลงไปด้านล่างจอตอนเริ่ม (ลบอีก 150 ทำให้ trans_pos ติดลบมากขึ้น กล้องมองต่ำลง)
        self.game.camera.trans_pos.y = self.target_cam_y - 150.0

        # 4. ปิดจอดำ (ทำที่นี่เพื่อให้การแพนกล้องดูต่อเนื่อง ไม่เห็นจังหวะ Jump)
        if self.game.black_overlay:
            if self.game.black_overlay.parent:
                self.game.black_overlay.parent.remove_widget(self.game.black_overlay)
            self.game.black_overlay = None

    def end_side_story_cutscene(self):
        """จบเนื้อเรื่องเสริม คืนสถานะเกมให้ปกติ"""
        # ถ้ามีแฟล็กที่ต้องหาอาหาร หรือต้องเดินเข้าที่ประจำ (ทุกวันหลังจากแชทจบตอนเข้าบ้าน)
        if getattr(self, '_pending_find_food_quest', False):
            # วันที่ 3 ขึ้น "..." ตามคำขอ USER (ถ้าบทสนทนาที่เพิ่งจบไปไม่ใช่ "...")
            if self.game.current_day == 3 and self.side_story_data.get("queue") != ["..."]:
                 self.game.show_vn_dialogue("Little girl", "...", portrait=PLAYER_S_PORTRAIT_IMG)
                 # ยังไม่ต้อง self.game.cutscene_step = 40 เดี๋ยว Step ต่อไปจะเรียก end_side_story_cutscene อีกรอบหลัง "..." จบ
                 return

            # --- เริ่มเควสทันทีหลังคุยจบ (Day 1 และ Day 4 ใช้ flow เดียวกัน) ---
            if self.game.current_day in [1, 4]:
                self.game.quest_manager.start_quest("find_food", "Find Something to Eat", target=1, show_notif=True)
                # จบคัทซีนทันทีเพื่อให้ผู้เล่นเดินหาได้เลย ไม่ต้องเดินไปมุมห้อง
                self._pending_find_food_quest = False
                self.game.is_cutscene_active = False
                self.game.cutscene_step = 0
                self.game.camera.locked = False
                self.game.player.cutscene_mode = False
                self.game.player.stop()
                self.game.request_keyboard_back()
                return

            # ทุกวันอื่นๆ ที่มีคัทซีนเข้าบ้าน (2, 4, 5): เดินไปที่มุมประจำก่อน
            print(f"DEBUG: end_side_story_cutscene - Triggering walk to sit for Day {self.game.current_day}")
            self.game.cutscene_step = 40
            self.game.is_cutscene_active = True
            self._pending_find_food_quest = False # ล้างแฟล็กเพื่อไม่ให้วนลูป
            self._anim_timer = 0
            return

        # กรณีทั่วไปที่ไม่ได้เข้าแมพบ้านหรือไม่มีเควสค้าง
        self.game.is_cutscene_active = False
        self.game.cutscene_step = 0
        self.game.camera.locked = False
        self.game.player.cutscene_mode = False
        self.game.player.is_moving = False
        self.game.player.state = 'idle'
        self.game.player.update_frame()
        self.game.request_keyboard_back()

    def start_food_transition_cutscene(self):
        """เริ่มคัทซีนบังคับเดินไปกินแล้วเปลี่ยนวัน"""
        print("DEBUG: Starting food transition cutscene...")
        self.game.clear_interaction_hints()
        self.game.is_cutscene_active = True
        self.game.cutscene_step = 20 # รหัสมุ่งหน้าไปหาอาหาร
        self.game.camera.locked = False # ให้กล้องเลื่อนตามตัวละครปกติ
        self.game.pressed_keys.clear()
        self.game._pending_day_transition = True # สำคัญ: เพื่อให้ handle_day_transition ทำงานได้
        # บังคับหยุดเดินเดิมก่อน
        self.game.player.stop()
        
    def show_black_screen_transition(self):
        """แสดงฉากสีดำและบทสนทนาของ Angel"""
        # หยุดการเดินและอนิเมชั่นของผู้เล่นทันที
        self.game.player.stop()

        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        self.game.black_overlay = Widget(size_hint=(1, 1))
        with self.game.black_overlay.canvas:
            Color(1, 1, 1, 1) # ใช้สีขาวเพื่อให้รูป background แสดงสีตามจริง
            self.game.black_rect = Rectangle(
                source='assets/background/bd_ed.png',
                size=root.size, 
                pos=(0, 0)
            )
            
        def update_overlay(instance, value):
            self.game.black_rect.size = (instance.width * 1.5, instance.height * 1.5)
            self.game.black_rect.pos = (-instance.width * 0.25, -instance.height * 0.25)
            
        self.game.black_overlay.bind(size=update_overlay, pos=update_overlay)
        update_overlay(self.game.black_overlay, None)
        root.add_widget(self.game.black_overlay)
        
        # ตัดสินใจเนื่อเรื่อง (สั่งทอดๆ)
        success = not getattr(self.game, 'quest_item_fail', False)
        from data.chat import DAY_END_DIALOGUES
        
        day = self.game.current_day
        cfg = DAY_END_DIALOGUES.get(day, DAY_END_DIALOGUES[1])
        character_name = "Angel" if day in [1, 3] else "Devil"

        if day == 5:
            current_total_success = self.game.quest_success_count
            if success: current_total_success += 1
            
            if current_total_success >= 5:
                # Perfect
                data = cfg["perfect"]
                texts = data["text"]
                self.game.temp_dialogue_chars = data["char"]
                character_name = self.game.temp_dialogue_chars[0]
            elif current_total_success > 0:
                # 1-4
                data = cfg["middle"]
                texts = data["text"]
                self.game.temp_dialogue_chars = data["char"]
                character_name = self.game.temp_dialogue_chars[0]
            else:
                # 0
                data = cfg["failure"]
                texts = data["text"]
                self.game.temp_dialogue_chars = data["char"]
                character_name = self.game.temp_dialogue_chars[0]
        elif day == 3:
            from data.chat import ANGEL_DAY3_SUCCESS, ANGEL_DAY3_FAIL
            texts = ANGEL_DAY3_SUCCESS if success else ANGEL_DAY3_FAIL
            character_name = "Angel"
        else:
            texts = cfg["success"] if success else cfg["fail"]
        
        self.game.current_dialogue_queue = texts
        self.game.current_dialogue_index = 0
        self.game.current_character_name = character_name
        self.game.is_dialogue_active = True
        self.game.dialogue_manager.show_vn_dialogue(character_name, texts[0])

    def end_cutscene(self):
        """จบ Cutscene และย้ายตัวละครเข้าบ้าน"""
        self.game.sorting_layer.clear()              
        self.game.sorting_layer.add(self.game.player.group) 
        self.game.npcs, self.game.enemies, self.game.stars = [], [], []
        
        if hasattr(self.game, 'reaper') and self.game.reaper:
            self.game.reaper.x, self.game.reaper.y = -9999, -9999
            self.game.reaper.logic_pos = [-9999, -9999]
            self.game.reaper.update_visual_positions()
            
        # จัดการ Extra Reapers ด้วย (ถ้ามี)
        for er in getattr(self.game, 'extra_reapers', []):
            er.x, er.y = -9999, -9999
            er.logic_pos = [-9999, -9999]
            er.update_visual_positions()
            
        # ย้ายไปแมพบ้าน (สั่งทอดๆ ผ่าน WorldManager ในอนาคต)
        self.game.world_manager.change_map('assets/Tiles/home.tmj')
        
        home_x = (160 // TILE_SIZE) * TILE_SIZE
        home_y = (0 // TILE_SIZE) * TILE_SIZE
        self.game.player.logic_pos = [home_x, home_y]
        self.game.player.target_pos = [home_x, home_y]
        self.game.player.sync_graphics_pos()
        self.game.player.direction = 'up'
        self.game.player.update_frame()
        self.game.update_camera()
        
        self.game.world_manager.refresh_darkness()
        
        # ตั้งแฟล็กไว้บอกว่าเล่นเสร็จแล้วค่อย เด้งเควสหิว ขึ้นมา
        self._pending_find_food_quest = True

        # ปลดสถานะ cutscene เพื่อเตรียมเริ่มฉากใหม่
        self.game.is_cutscene_active = False
        self.game.cutscene_step = 0
        self.game.camera.locked = False
        self.game.player.stop()
        self.game.request_keyboard_back()

        if getattr(self.game, 'current_day', 1) == 2:
            Clock.schedule_once(self.start_day2_parent_cutscene, 0.5)
        elif getattr(self.game, 'current_day', 1) == 3:
            # Day 3: พิกัดอันตรายจะเป็นสีดำตามปกติ แต่ในบ้านจะมีหมอกฟ้าเสมอ
            self._apply_blue_tint()
            # ปลดล็อกกล้องเพื่อให้ตามตัวละครในบ้าน
            self.game.camera.locked = False
            
            # ไม่ต้องถามเรื่องอาหาร เปลี่ยนเป็น "..." พร้อมรูปหน้าเศร้า
            dialogue_queue = ["..."]
            Clock.schedule_once(lambda dt: self.start_side_story_cutscene(dialogue_queue, "Little girl", portrait=PLAYER_S_PORTRAIT_IMG), 0.5)
        else:
            # เริ่มเข้าสู่เนื้อเรื่องเสริมแทรกตอนเข้าบ้านทันที
            dialogue_queue = ["So hungry...I need to find something to eat."]
            Clock.schedule_once(lambda dt: self.start_side_story_cutscene(dialogue_queue, "Little girl"), 0.5)

    def _apply_blue_tint(self):
        """เพิ่มฟิลเตอร์สีฟ้าลงในแมพ (คุมตัวละครและหลังคา แต่ไม่ล้นไปบัง UI)"""
        # เอาไปใส่ใน map_after_group เพื่อให้อยู่ในระบบของกล้อง (ไม่ล้นจอ)
        target_group = self.game.map_after_group
        
        # ลบฟิลเตอร์เก่าออกก่อนหากมีการเรียกซ้ำ
        if hasattr(self, 'blue_tint_instr') and self.blue_tint_instr:
            if self.blue_tint_instr in target_group.children:
                target_group.remove(self.blue_tint_instr)
            # เผื่อของเก่าค้างอยู่ในเลเยอร์อื่น
            if self.blue_tint_instr in self.game.canvas.after.children:
                self.game.canvas.after.remove(self.blue_tint_instr)
            if self.blue_tint_instr in self.game.canvas.children:
                self.game.canvas.remove(self.blue_tint_instr)
        
        from kivy.graphics import InstructionGroup, Color, Rectangle
        from data.settings import TILE_SIZE
        
        self.blue_tint_instr = InstructionGroup()
        # สีฟ้า Alpha 0.15 
        self.blue_tint_color = Color(0.2, 0.4, 0.8, 0.15) 
        
        # คำนวณขนาดให้ครอบคลุมทั้งแผนที่
        map_w = self.game.game_map.width * TILE_SIZE
        map_h = self.game.game_map.height * TILE_SIZE
        
        # สร้างสี่เหลี่ยมสีฟ้าทับซ้อนลงไป
        self.blue_tint_rect = Rectangle(size=(map_w, map_h), pos=(0, 0))
        
        self.blue_tint_instr.add(self.blue_tint_color)
        self.blue_tint_instr.add(self.blue_tint_rect)
        
        # แอดเข้าไปในกลุ่มกราฟิกเพื่อให้แสดงผลในเกม
        target_group.add(self.blue_tint_instr)

    def start_day2_parent_cutscene(self, dt=None):
        """เริ่มคัทซีนบังคับจอดำฟังเสียงประตูใน Day 2 ก่อนพ่อแม่ทะเลาะกัน"""
        # ลบจอดำอันเก่า (ที่มีรูป bd_ed.png) ออกก่อน เพื่อไม่ให้มันค้างอยู่ข้างหลัง
        if self.game.black_overlay:
            if self.game.black_overlay.parent:
                self.game.black_overlay.parent.remove_widget(self.game.black_overlay)
            self.game.black_overlay = None
            
        self.game.is_cutscene_active = True
        self.game.cutscene_step = 30
        self.game.pressed_keys.clear()
        self.game.player.stop()
        self.game.camera.locked = True
        self.game.clear_interaction_hints()
        
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        self.day2_black_bg = Widget(size_hint=(1, 1))
        with self.day2_black_bg.canvas:
            Color(0, 0, 0, 1)
            self.day2_rect = Rectangle(size=root.size, pos=(0, 0))
            
        def _u_dt2(instance, value):
            self.day2_rect.size = instance.size
            self.day2_rect.pos = instance.pos
        self.day2_black_bg.bind(size=_u_dt2, pos=_u_dt2)
        root.add_widget(self.day2_black_bg)
        
        self.play_door_full_sequence()
            
        self._day2_wait_timer = 0

    def start_father_hit_animation(self, dt=None):
        """เริ่มอนิเมชั่นพ่อกระทืบผู้เล่น (sprite sheet 1x5)"""
        self.game.clear_interaction_hints()
        self.game.pressed_keys.clear()
        self.game.player.stop()
        self.game.is_cutscene_active = True
        self.game.camera.locked = True
        
        # สร้างวิดเจ็ตสำหรับแสดงอนิเมชั่น
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        self.father_hit_widget = Widget(size_hint=(1, 1))
        
        # คำนวณขนาดและตำแหน่งตรงกลาง
        sprite_width, sprite_height = 32, 32  # ขนาดเหมือนตัวละคร player
        img_width, img_height = sprite_width * 4, sprite_height * 4  # ขยาย 4 เท่าให้เห็นชัด
        center_x = self.game.width // 2 - img_width // 2
        center_y = self.game.height // 2 - img_height // 2
        
        # โหลดภาพ fatherhit (เป็นภาพเดี่ยว ไม่ใช่ sprite sheet)
        from kivy.core.image import Image as CoreImage
        try:
            tex = CoreImage('assets/characters/fatherhit.png').texture
            tex.mag_filter = 'nearest'
            tex.min_filter = 'nearest'
            
            # ใช้ภาพเดี่ยว ไม่ต้องทำ sprite animation
            self.father_hit_frames = 1
            self.current_frame = 0
            
            with self.father_hit_widget.canvas:
                Color(1, 1, 1, 1)
                self.father_hit_rect = Rectangle(texture=tex, size=(img_width, img_height), 
                                               pos=(center_x, center_y))
        except Exception:
            with self.father_hit_widget.canvas:
                Color(1, 1, 1, 1)
                self.father_hit_rect = Rectangle(source='assets/characters/fatherhit.png', size=(img_width, img_height),
                                               pos=(center_x, center_y))
            self.father_hit_frames = 1
            self.current_frame = 0
        
        # ฟังก์ชันอัปเดตตำแหน่งเมื่อขนาดหน้าจอเปลี่ยน
        def update_hit_pos(instance, value):
            new_center_x = instance.width // 2 - img_width // 2
            new_center_y = instance.height // 2 - img_height // 2
            if hasattr(self, 'father_hit_rect'):
                self.father_hit_rect.pos = (new_center_x, new_center_y)
        
        self.father_hit_widget.bind(size=update_hit_pos, pos=update_hit_pos)
        root.add_widget(self.father_hit_widget)
        
        # เริ่มอนิเมชั่น
        self.father_hit_total_time = 2.0  # แสดง 2 วินาที
        Clock.schedule_once(self.end_father_hit_animation, self.father_hit_total_time)
        
        # เล่นเสียงกระทืบ (ถ้ามี)
        self.play_hit_sound()

    def get_frame_uv(self, frame_index):
        """คำนวณ UV coordinates สำหรับ sprite sheet"""
        if self.father_hit_frames <= 1:
            return (0, 0, 1, 1)
        
        # Sprite sheet 1x5: 1 แถว 5 คอลัมน์ (เรียงกันในแนวนอน)
        u_per_frame = 1.0 / self.father_hit_frames
        u_start = frame_index * u_per_frame
        u_end = u_start + u_per_frame
        
        # Kivy ใช้ (u1, v1, u2, v2) โดย v กลับด้าน
        # สำหรับ 5 คอลัมน์: แบ่งในแนวนอน
        return (u_start, 0, u_end, 1)

    def update_father_hit_animation(self, dt):
        """อัปเดตเฟรมอนิเมชั่น"""
        if not hasattr(self, 'father_hit_rect') or not hasattr(self, 'father_hit_frames'):
            return
            
        # ถ้าเป็นภาพเดี่ยว (1 เฟรม) ไม่ต้องทำ animation
        if self.father_hit_frames <= 1:
            return
            
        self.animation_timer += dt
        if self.animation_timer >= self.frame_duration:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % self.father_hit_frames
            
            # อัปเดต UV coordinates
            self.father_hit_rect.tex_coords = self.get_frame_uv(self.current_frame)

    def play_hit_sound(self):
        """เล่นเสียงการกระทืบ"""
        # สามารถเพิ่มเสียงที่นี่ได้ถ้ามีไฟล์เสียง
        pass

    def end_father_hit_animation(self, dt=None):
        """จบอนิเมชั่นการกระทืบและไปต่อ"""
        if hasattr(self, 'father_hit_widget') and self.father_hit_widget:
            if self.father_hit_widget.parent:
                self.father_hit_widget.parent.remove_widget(self.father_hit_widget)
            self.father_hit_widget = None
        
        # ไปฉากต่อไป (เดินไปที่นั่ง)
        self.game.cutscene_step = 40
        self.game.is_cutscene_active = True
        self._anim_timer = 0

    def end_day2_parent_cutscene(self):
        """จบฉากพ่อแม่ทะเลาะกัน"""
        # เริ่มอนิเมชั่นพ่อกระทืบผู้เล่น
        Clock.schedule_once(self.start_father_hit_animation, 0.5)

    def start_succumb_ending(self):
        """เริ่มคัทซีนฉากจบ Succumb (ตายครบ 3 ครั้ง)"""
        self.game.is_cutscene_active = True
        self.game.stop_all_sounds()
        self.game.cutscene_step = 100
        self.game.pressed_keys.clear()
        if hasattr(self.game.player, 'stop'):
            self.game.player.stop()
        self.game.camera.locked = True
        self.game.clear_interaction_hints()
        
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        # ลบวิดเจ็ตเก่าที่อาจค้างอยู่
        if hasattr(self.game, 'succumb_bg') and self.game.succumb_bg:
            if self.game.succumb_bg.parent: self.game.succumb_bg.parent.remove_widget(self.game.succumb_bg)
        if hasattr(self.game, 'hidden_end_widget') and self.game.hidden_end_widget:
            if self.game.hidden_end_widget.parent: self.game.hidden_end_widget.parent.remove_widget(self.game.hidden_end_widget)
        
        # 1. วิดเจ็ตจอดำ (ใช้สำหรับ Fade In ครั้งแรก)
        self.succumb_bg = Widget(size_hint=(1, 1), opacity=0)
        with self.succumb_bg.canvas:
            Color(0, 0, 0, 1)
            self.succumb_rect = Rectangle(size=root.size, pos=(0, 0))
            
        def _u(i, v):
            self.succumb_rect.size = i.size
            self.succumb_rect.pos = i.pos
        self.succumb_bg.bind(size=_u, pos=_u)
        root.add_widget(self.succumb_bg)
        
        # ขั้นตอน: ค่อยๆ มืดลง
        anim = Animation(opacity=1, duration=1.5)
        def on_dark(*args):
            self.game.cutscene_step = 101
            # 2. ขั้นตอน: ขึ้นพื้นหลัง Hidden Ending (ใช้ Widget แยกต่างหากเพื่อให้แอนิเมชันเสถียร)
            self.hidden_end_widget = Widget(size_hint=(1, 1), opacity=0)
            with self.hidden_end_widget.canvas:
                Color(1, 1, 1, 1)
                self.hidden_end_rect = Rectangle(
                    source='assets/background/Hidden Endding.png',
                    size=root.size, pos=(0, 0)
                )
            
            def _u2(i, v):
                if hasattr(self, 'hidden_end_rect'):
                    self.hidden_end_rect.size = i.size
                    self.hidden_end_rect.pos = i.pos
            self.hidden_end_widget.bind(size=_u2, pos=_u2)
            root.add_widget(self.hidden_end_widget)
            
            anim2 = Animation(opacity=1, duration=2.0)
            def on_img_visible(*args):
                # 3. ขั้นตอน: ขึ้นชื่อ ?? และพูด "######"
                # ต้องตั้งค่าสถานะตัวละครเพื่อให้ StoryManager ตรวจสอบตอนจบแชทได้
                self.game.current_character_name = "??"
                self.game.current_dialogue_queue = ["######"]
                self.game.current_dialogue_index = 0
                self.game.is_dialogue_active = True
                self.game.show_vn_dialogue("??", "######")
            anim2.bind(on_complete=on_img_visible)
            anim2.start(self.hidden_end_widget)
            
        anim.bind(on_complete=on_dark)
        anim.start(self.succumb_bg)

    def continue_succumb_ending(self):
        """เฟส 2: มืดลงและขึ้นชื่อ Ending"""
        print(f"DEBUG: continue_succumb_ending called. Step: {self.game.cutscene_step}")
        self.game.cutscene_step = 102
        
        # ค่อยๆ จางภาพพื้นหลังออกให้เหลือแต่จอดำ
        anim = Animation(opacity=0, duration=1.5)
        def on_fade_back(*args):
            print("DEBUG: Background faded out. Showing Ending Label.")
            root = self.game.dialogue_root if self.game.dialogue_root else self.game
            
            # 4. เรียกใช้ IntroScreen แบบ custom_text เหมือนเวลาเปลี่ยนวัน
            intro = IntroScreen(
                callback=self.game.return_to_main_menu, 
                custom_text=ENDING_TITLES[1], 
                play_sound=False, 
                duration=4.5
            )
            root.add_widget(intro)
            self.game.cutscene_step = 103
            
        anim.bind(on_complete=on_fade_back)
        if hasattr(self, 'hidden_end_widget') and self.hidden_end_widget:
            anim.start(self.hidden_end_widget)
        else:
            print("DEBUG WARNING: hidden_end_widget not found, skipping animation.")
            on_fade_back()

    def start_day5_ending(self, total_success):
        """เริ่มคัทซีนฉากจบจริง (เล่นเมื่อเคลียร์วัน 5 จบ)"""
        print(f"DEBUG: Starting Day 5 Ending with {total_success} success.")
        self.game.is_cutscene_active = True
        self.game.stop_all_sounds()
        self.game.cutscene_step = 200 # รหัสสำหรับเฟสฉากจบปกติ
        self.game.pressed_keys.clear()
        if hasattr(self.game.player, 'stop'):
            self.game.player.stop()
        self.game.camera.locked = True
        self.game.clear_interaction_hints()
        
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        self.ending_bg = Widget(size_hint=(1, 1), opacity=0)
        with self.ending_bg.canvas:
            Color(0, 0, 0, 1)
            self.ending_bg_rect = Rectangle(size=root.size, pos=(0, 0))
        def _u(i, v):
            if hasattr(self, 'ending_bg_rect'):
                self.ending_bg_rect.size = i.size
                self.ending_bg_rect.pos = i.pos
        self.ending_bg.bind(size=_u, pos=_u)
        root.add_widget(self.ending_bg)
        
        anim = Animation(opacity=1, duration=1.5)
        def on_dark(*args):
            if hasattr(self.game, 'black_overlay') and self.game.black_overlay:
                if self.game.black_overlay.parent:
                    self.game.black_overlay.parent.remove_widget(self.game.black_overlay)
                self.game.black_overlay = None
            
            import os, json
            os.makedirs('saves', exist_ok=True)

            if total_success >= 5:
                ending_title = ENDING_TITLES[4]
                json.dump({'ending': 'true'}, open('saves/ending.flag', 'w'))
                self._show_true_ending_dialogue(root, ending_title)

            elif total_success > 0:
                ending_title = ENDING_TITLES[3]
                json.dump({'ending': 'normal'}, open('saves/ending.flag', 'w'))
                self._show_normal_ending_sequence(root, ending_title)

            else:
                ending_title = ENDING_TITLES[2]
                json.dump({'ending': 'bad'}, open('saves/ending.flag', 'w'))
                self._show_bad_ending_sequence(root, ending_title)

                

        anim.bind(on_complete=on_dark)
        anim.start(self.ending_bg)

    def _show_true_ending_dialogue(self, root, ending_title):
        """แสดง dialogue ก่อน True Ending title card พร้อม bg.jpg เป็นพื้นหลัง"""
        from data.settings import PLAYER_PORTRAIT_IMG, REAPER_PORTRAIT_IMG
        from kivy.core.image import Image as CoreImage

        # วาง bg.jpg เหนือ ending_bg (ดำ) แต่ใต้ dialogue
        self._true_ending_bg_widget = Widget(size_hint=(1, 1))
        with self._true_ending_bg_widget.canvas:
            Color(1, 1, 1, 1)
            try:
                tex = CoreImage('assets/background/bg.jpg').texture
                self._true_ending_bg_rect = Rectangle(texture=tex, size=root.size, pos=root.pos)
            except Exception:
                self._true_ending_bg_rect = Rectangle(source='assets/background/bg.jpg', size=root.size, pos=root.pos)
        def _upd_bg(inst, val):
            self._true_ending_bg_rect.size = root.size
            self._true_ending_bg_rect.pos = root.pos
        root.bind(size=_upd_bg, pos=_upd_bg)
        root.add_widget(self._true_ending_bg_widget)

        dialogues = [
            ("Little girl", "Who are you? ...Why are you standing there?", PLAYER_PORTRAIT_IMG),
            ("M",           "...",                                           None),
            ("M",           "I am the one who will take you to a place where the sun never sets... Do you want to go with me?", None),
        ]
        self._true_ending_queue = list(dialogues)
        self._true_ending_root = root
        self._true_ending_title = ending_title
        self._advance_true_ending_dialogue()

    def _advance_true_ending_dialogue(self, *args):
        """เล่น dialogue ถัดไปใน True Ending queue"""
        if self._true_ending_queue:
            name, text, portrait = self._true_ending_queue.pop(0)
            self.game.show_vn_dialogue(name, text, portrait=portrait)
            # เก็บ callback สำหรับตอนผู้เล่นกด Enter/E ต่อไป
            self.game._true_ending_next = self._advance_true_ending_dialogue
        else:
            # Queue หมดแล้ว — เล่นเสียง Nod แล้วโชว์ title
            self.game.close_dialogue()
            nod_sound = SoundLoader.load('assets/sound/feeling/Nod.wav')
            if nod_sound:
                nod_sound.play()
                # รอเสียงจบ (ประมาณ 1.5 วิ) แล้วโชว์ IntroScreen
                Clock.schedule_once(lambda dt: self._show_true_ending_title(), nod_sound.length or 1.5)
            else:
                Clock.schedule_once(lambda dt: self._show_true_ending_title(), 0.5)

    def _show_true_ending_title(self):
        root = self._true_ending_root
        # ลบ bg.jpg widget ก่อนโชว์ IntroScreen
        if hasattr(self, '_true_ending_bg_widget') and self._true_ending_bg_widget:
            if self._true_ending_bg_widget.parent:
                self._true_ending_bg_widget.parent.remove_widget(self._true_ending_bg_widget)
            self._true_ending_bg_widget = None
        intro = IntroScreen(
            callback=self.game.return_to_main_menu,
            custom_text=self._true_ending_title,
            play_sound=False,
            duration=4.5
        )
        root.add_widget(intro)

    def _show_normal_ending_sequence(self, root, ending_title):
        """Normal Ending: แสดง bd_ed.png + เสียงวิ่ง 7 วิ + breath พร้อมกัน แล้วขึ้น title"""
        import os, glob
        from kivy.core.image import Image as CoreImage

        # 1. วาง background bd_ed.png เต็มจอ
        self._normal_end_bg = Widget(size_hint=(1, 1))
        with self._normal_end_bg.canvas:
            Color(1, 1, 1, 1)
            try:
                tex = CoreImage('assets/background/bd_ed.png').texture
                self._ne_bg_rect = Rectangle(texture=tex, size=root.size, pos=root.pos)
            except Exception:
                self._ne_bg_rect = Rectangle(source='assets/background/bd_ed.png',
                                             size=root.size, pos=root.pos)
        def _upd(inst, val):
            self._ne_bg_rect.size = root.size
            self._ne_bg_rect.pos  = root.pos
        root.bind(size=_upd, pos=_upd)
        root.add_widget(self._normal_end_bg)

        # 2. โหลดไฟล์เสียงวิ่งทั้งหมดและเรียงลำดับ
        run_dir = 'assets/sound/run'
        run_files = sorted(
            [f for f in os.listdir(run_dir) if f.lower().endswith('.wav')]
        )
        self._ne_run_sounds  = [SoundLoader.load(os.path.join(run_dir, f)) for f in run_files]
        self._ne_run_idx     = 0
        self._ne_run_events  = []

        # ตั้งค่า volume
        for s in self._ne_run_sounds:
            if s: s.volume = 0.85

        # 3. โหลด breath.wav และเล่นพร้อมกัน
        self._ne_breath = SoundLoader.load('assets/sound/breath.wav')
        if self._ne_breath:
            self._ne_breath.volume = 0.7
            self._ne_breath.loop   = True
            self._ne_breath.play()

        # 4. เล่นเสียงวิ่งวนไปเรื่อยๆ ทุก ~0.7 วิ (10 ไฟล์ ≈ 7 วิ)
        step_interval = 7.0 / max(len(run_files), 1)  # หาร 7 วิ ด้วยจำนวนไฟล์

        def _play_step(dt):
            sounds = self._ne_run_sounds
            if not sounds: return
            idx = self._ne_run_idx % len(sounds)
            if sounds[idx]:
                sounds[idx].play()
            self._ne_run_idx += 1

        # Schedule ทุก step_interval จนครบ 7 วิ
        for i, fname in enumerate(run_files):
            ev = Clock.schedule_once(_play_step, i * step_interval)
            self._ne_run_events.append(ev)

        # 5. หลัง 7 วิ หยุดเสียง → เอา bg ออก → โชว์ title
        def _finish_normal_ending(dt):
            # หยุดเสียงทั้งหมด
            for s in getattr(self, '_ne_run_sounds', []):
                if s: s.stop()
            if getattr(self, '_ne_breath', None):
                self._ne_breath.stop()
            # ลบ background
            if getattr(self, '_normal_end_bg', None) and self._normal_end_bg.parent:
                self._normal_end_bg.parent.remove_widget(self._normal_end_bg)
            # โชว์ IntroScreen title
            intro = IntroScreen(
                callback=self.game.return_to_main_menu,
                custom_text=ending_title,
                play_sound=False,
                duration=4.5
            )
            root.add_widget(intro)

        Clock.schedule_once(_finish_normal_ending, 7.0)

    # ------------------------------------------------------------------
    # Bad Ending Sequence
    # ------------------------------------------------------------------
    def _show_bad_ending_sequence(self, root, ending_title):
        """Bad Ending: home map BG + parent dialogue → Gore+Scream → black 3s → child dialogue → title"""
        import os
        from kivy.graphics import InstructionGroup, PushMatrix, PopMatrix, Translate
        from kivy.core.window import Window

        self._bad_root  = root
        self._bad_title = ending_title

        # 1. Black base background
        self._bad_black_w = Widget(size_hint=(1, 1))
        with self._bad_black_w.canvas:
            Color(0, 0, 0, 1)
            Rectangle(pos=(0, 0), size=(10000, 10000))
        root.add_widget(self._bad_black_w)

        # 2. Home map centered on screen (no player)
        self._bad_map_w = Widget(size_hint=(1, 1))
        try:
            from assets.Tiles.map_loader import KivyTiledMap
            home_map = KivyTiledMap('assets/Tiles/home.tmj')
            map_px_w = home_map.width  * TILE_SIZE
            map_px_h = home_map.height * TILE_SIZE
            sw, sh = Window.width, Window.height
            ox = (sw - map_px_w) / 2
            oy = (sh - map_px_h) / 2
            ig = InstructionGroup()
            ig.add(PushMatrix())
            ig.add(Translate(ox, oy, 0))
            ig.add(Color(1, 1, 1, 1))
            home_map.draw_ground(ig)
            home_map.draw_background(ig)
            home_map.draw_foreground(ig)
            home_map.draw_roof(ig)
            ig.add(PopMatrix())
            self._bad_map_w.canvas.add(ig)
        except Exception as e:
            print(f"Bad ending home map error: {e}")
        root.add_widget(self._bad_map_w)

        # 3. Phase 1: Mother → Father dialogue
        self._bad_q1 = [
            ("Mother", "She's a curse... Every time she looks at us, everything goes wrong. She doesn't deserve to see anything!", None),
            ("Father", "You're right... If she's such a curse, then she doesn't need those eyes to look at us anymore!", None),
        ]
        self.game._bad_ending_next = self._bad_next_1
        self._bad_next_1()

    def _bad_next_1(self):
        if not self._bad_q1:
            self.game._bad_ending_next = None
            self._bad_play_sounds()
            return
        char, text, portrait = self._bad_q1.pop(0)
        self.game.show_vn_dialogue(char, text, portrait_path=portrait, can_save=False)

    def _bad_play_sounds(self):
        """เล่น Gore.wav ก่อน แล้วต่อด้วย Scream.wav"""
        import os
        from kivy.app import App
        app = App.get_running_app()
        if hasattr(app, 'bg_loop') and app.bg_loop:
            app.bg_loop.stop()

        gore_path   = 'assets/sound/hit/Gore.wav'
        scream_path = 'assets/sound/feeling/Scream.wav'

        gore_dur = 0.0
        if os.path.exists(gore_path):
            self._bad_gore = SoundLoader.load(gore_path)
            if self._bad_gore:
                self._bad_gore.volume = 0.9
                self._bad_gore.play()
                gore_dur = self._bad_gore.length if self._bad_gore.length > 0 else 1.5

        scream_dur = 0.0
        if os.path.exists(scream_path):
            self._bad_scream = SoundLoader.load(scream_path)
            if self._bad_scream:
                scream_dur = self._bad_scream.length if self._bad_scream.length > 0 else 2.5
                def _play_scream(dt):
                    self._bad_scream.volume = 0.9
                    self._bad_scream.play()
                Clock.schedule_once(_play_scream, gore_dur + 0.1)

        total = gore_dur + 0.1 + scream_dur + 0.3
        Clock.schedule_once(lambda dt: self._bad_go_dark(), total)

    def _bad_go_dark(self):
        """ลบแมพออก → จอดำ → รอ 3 วิ"""
        if getattr(self, '_bad_map_w', None) and self._bad_map_w.parent:
            self._bad_map_w.parent.remove_widget(self._bad_map_w)
        # จอดำ (_bad_black_w) ยังอยู่ รอ 3 วิ
        Clock.schedule_once(lambda dt: self._bad_phase2(), 3.0)

    def _bad_phase2(self, dt=None):
        """Phase 2: Little Girl → Reaper dialogue"""
        self._bad_q2 = [
            ("Little Girl", "It hurts... It hurts so much... Mr. Reaper, I can't see anything. Why is it so dark?", None),
            ("Reaper",      "Hush now... The world you saw was too ugly for a soul like yours. In this darkness, they can't hurt you anymore.", None),
        ]
        self.game._bad_ending_next = self._bad_next_2
        self._bad_next_2()

    def _bad_next_2(self):
        if not self._bad_q2:
            self.game._bad_ending_next = None
            intro = IntroScreen(
                callback=self.game.return_to_main_menu,
                custom_text=self._bad_title,
                play_sound=False,
                duration=4.5
            )
            self._bad_root.add_widget(intro)
            return
        char, text, portrait = self._bad_q2.pop(0)
        self.game.show_vn_dialogue(char, text, portrait_path=portrait, can_save=False)
