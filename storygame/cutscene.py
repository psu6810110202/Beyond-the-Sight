# storygame/cutscene.py
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader
from settings import *

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
            
        # โหลดเสียงผ้า (นั่ง)
        self.cloth_sound = SoundLoader.load('assets/sound/cloth.wav')
        if self.cloth_sound:
            self.cloth_sound.volume = 0.5

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
                
                direction = 'down' if self.game.current_day == 2 else 'right'
                
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
                self.game.player.cutscene_mode = False 
                
                # ถึงที่หมายสนิทแล้ว
                if self.cloth_sound:
                    self.cloth_sound.play()
                    
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
            
            self.game.player.state = 'idle'
            self.game.player.is_moving = False
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
                            
                        # เริ่มบทสนทนาหลังจอสว่างแล้ว
                        data = [
                            {"char": "Father", "text": "Still... you're still glaring at me with those eyes?! I told you—if you're stepping foot into this house, don't you ever dare look at me with that curse!"},
                            {"char": "Mother", "text": "Stop it, husband... don't touch him too much. I don't want whatever 'curse' he sees in those eyes rubbing off on your hands. Just living under the same roof as this demon is enough to drive me insane!"},
                            {"char": "Father", "text": "What are you looking at?! Is there some spirit standing behind me now? You're nothing but my own flesh and blood that I regret ever fathering—a total jinx! Talking to the air like a madman! You’ve become a blight, dragging our family down for the whole neighborhood to mock!"},
                            {"char": "Mother", "text": "I'm dying of shame... Our lives were finally turning around, but then we ended up with a freak like you who does nothing but see ghosts! I truly wish I could announce to everyone that I have no such disgusting child!"},
                            {"char": "Father", "text": "You're getting nothing to eat today! Since you love those spirits so much, go beg them for scraps yourself! I don't care if you starve or rot, just don't you dare bring more shame to my name with your wretched behavior!"},
                            {"char": "Mother", "text": "Go rot in your dark corner! If I see you whispering to yourself or staring at anyone with those creepy eyes again... I'll be the one to gouge them out of your head myself, forever!"}
                        ]
                        
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
                # --- แก้ไขตรงนี้: เรียกใช้ stop() เพื่อรีเซ็ต FPS และความเร็ว ---
                self.game.player.stop() 
                self.game.player.cutscene_mode = False # ปิดโหมดคัทซีนเพื่อให้เล่นอนิเมชั่น Idle
                
                # ถึงที่หมายสนิทแล้ว
                if self.cloth_sound:
                    self.cloth_sound.play()
                    
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
            # ยืน/นั่งรอ 3 วิ 
            self.game.player.cutscene_mode = False
            self.game.player.is_moving = False
            self.game.player.state = 'idle'
            self.game.player.update_frame()
            
            self._anim_timer += dt
            if self._anim_timer >= 3.0:
                self.game.cutscene_step = 0 
                self.game._pending_day_transition = True
                self.game.handle_day_transition(increment=True)

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
        if self.game.current_day == 3 and getattr(self, '_pending_find_food_quest', False):
            # Day 3: เดินไปที่มุมห้องก่อน
            self.game.cutscene_step = 40
            self.game.is_cutscene_active = True
            self._pending_find_food_quest = False
            return

        self.game.is_cutscene_active = False
        self.game.cutscene_step = 0
        self.game.camera.locked = False
        self.game.player.cutscene_mode = False
        self.game.player.is_moving = False
        self.game.player.state = 'idle'
        self.game.player.update_frame()
        self.game.request_keyboard_back()
        
        # ถ้านี่เป็นคัทซีนจบส่งวิญญาณ พอพูดจบให้เริ่มเควส "หาของกิน"
        if getattr(self, '_pending_find_food_quest', False):
            self.game.quest_manager.start_quest("find_food", "Find Something to Eat", target=1, show_notif=True)
            self._pending_find_food_quest = False

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
        
        if self.game.current_day == 1:
            character_name = "Angel"
            if self.game.quest_success_count >= 3 or success:
                texts = [
                    "You still hold the light in your hands, little one...",
                    "Though this place is shrouded in darkness, your kindness has saved that soul.",
                    "Go and rest now. You will need your strength for tomorrow."
                ]
            else:
                texts = [
                    "Your hands are trembling... It’s alright.",
                    "Sometimes, destiny is too heavy for a child to carry alone.",
                    "Let’s go home for now. We can always start again tomorrow."
                ]
        elif self.game.current_day == 2:
            character_name = "Devil"
            if success:
                texts = [
                    "Heh... keep playing the hero, kid.",
                    "You can save a ghost, but the humans lurking behind you? They haven't changed a bit.",
                    "But fine, I'll give it to you—you did well today.",
                    "Now, get back home before those people start getting suspicious."
                ]
            else:
                texts = [
                    "See that? In the end, you can't save anyone—not even yourself.",
                    "But don't you go crying now; this wretched world has always been this way.",
                    "Come here, let me escort you back to that hell you call 'home' yourself."
                ]
        elif self.game.current_day == 3:
            from storygame.chat import ANGEL_DAY3_SUCCESS, ANGEL_DAY3_FAIL
            character_name = "Angel"
            if success:
                texts = ANGEL_DAY3_SUCCESS
            else:
                texts = ANGEL_DAY3_FAIL
        else:
            character_name = "Angel"
            texts = ["The night continues..."]
        
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
            # Day 3: จอฟ้าขึ้น
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
        
        # ลบของเก่าถ้ามี
        if hasattr(self, 'blue_tint_instr') and self.blue_tint_instr:
            if self.blue_tint_instr in target_group.children:
                target_group.remove(self.blue_tint_instr)
            # เผื่อของเก่าค้างอยู่ในเลเยอร์อื่น
            if self.blue_tint_instr in self.game.canvas.after.children:
                self.game.canvas.after.remove(self.blue_tint_instr)
            if self.blue_tint_instr in self.game.canvas.children:
                self.game.canvas.remove(self.blue_tint_instr)
        
        from kivy.graphics import InstructionGroup, Color, Rectangle
        from settings import TILE_SIZE
        
        self.blue_tint_instr = InstructionGroup()
        # สีฟ้า Alpha 0.15 
        self.blue_tint_color = Color(0.2, 0.4, 0.8, 0.15) 
        
        # คำนวณขนาดความกว้าง/ยาวให้พอดีเป๊ะกับแมพ
        map_w = self.game.game_map.width * TILE_SIZE
        map_h = self.game.game_map.height * TILE_SIZE
        
        # สร้างสี่เหลี่ยมสีฟ้าขนาดเท่าแมพ วางที่พิกัด (0,0)
        self.blue_tint_rect = Rectangle(size=(map_w, map_h), pos=(0, 0))
        
        self.blue_tint_instr.add(self.blue_tint_color)
        self.blue_tint_instr.add(self.blue_tint_rect)
        
        # แอดเข้าไปทับหลังคา แต่ยังอยู่ภายใต้ระบบกล้อง
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

    def end_day2_parent_cutscene(self):
        """จบฉากพ่อแม่ทะเลาะกัน และตัดเข้าสู่ Day 3 ทันที"""
        self.game.is_cutscene_active = False
        self.game.cutscene_step = 0
        self.game.camera.locked = False
        self.game.request_keyboard_back()
        
        self._pending_find_food_quest = False
        self.game._pending_day_transition = True
        self.game.handle_day_transition()
