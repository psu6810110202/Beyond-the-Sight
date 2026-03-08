# storygame/story.py
from data.chat import WARNING_DIALOGUE, WARNING_CHOICES, TUTORIAL_DIALOGUE, SEARCH_DIALOGUES_HOME, UNDERGROUND_STRINGS
from data.settings import ENEMY_DETECTION_RADIUS, TILE_SIZE, MAP_FILE, HOME_EAT_POS, EMPTY_SPOT_HOME
from kivy.clock import Clock

# ข้อมูลการตั้งค่าของแต่ละวัน
STORY_CONFIG = {
    1: {
        "name": "Day 1",
        "visible_npcs": [0],  # เฉพาะ NPC1 (Index 0)
        "warning_triggers": [
            {"type": "coordinate", "x": 656, "y": None, "buffer": 16, "dialogue": WARNING_DIALOGUE, "choices": WARNING_CHOICES},
            {"type": "coordinate", "x": None, "y": 464, "buffer": 16, "dialogue": WARNING_DIALOGUE, "choices": WARNING_CHOICES}
        ]
    },
    2: {
        "name": "Day 2", 
        "visible_npcs": [1], # เฉพาะ NPC2 (The Postman)
        "warning_triggers": [
            {"type": "coordinate", "x": None, "y": 464, "buffer": 16, "dialogue": WARNING_DIALOGUE, "choices": WARNING_CHOICES}
        ]
    },
    3: {
        "name": "Day 3", 
        "visible_npcs": [2], 
        "warning_triggers": [
            {"type": "coordinate", "x": 880, "y": None, "buffer": 16, "min_y": 464, "dialogue": WARNING_DIALOGUE, "choices": WARNING_CHOICES},
            {"type": "coordinate", "x": None, "y": 464, "buffer": 16, "min_x": 880, "dialogue": WARNING_DIALOGUE, "choices": WARNING_CHOICES}
        ]
    },
    4: {"name": "Day 4", "visible_npcs": [3], "warning_triggers": []},
    5: {"name": "Day 5", "visible_npcs": [4], "warning_triggers": []}
}

class StoryManager:
    def __init__(self, game):
        self.game = game

    def get_config(self):
        """ดึงข้อมูลของวันปัจจุบัน"""
        return STORY_CONFIG.get(self.game.current_day, {})

    def is_npc_visible(self, npc_index):
        """เช็คว่า NPC ตัวนี้ควรโชว์ในวันนี้มั้ย"""
        config = self.get_config()
        visible = config.get("visible_npcs")
        return visible is None or npc_index in visible

    def update(self, dt):
        """ตรวจสอบ Trigger ทุกอย่างในเกม (เรียกจาก main loop)"""
        # 1. ตรวจสอบพื้นที่อันตราย (Warning)
        if not self.game.warning_dismissed:
            self._check_warning_triggers()
            
        # 2. ตรวจสอบ Tutorial (หินสตัน)
        if not self.game.tutorial_triggered and self.game.has_received_blue_stone:
            self._check_tutorial_triggers()

    def _check_warning_triggers(self):
        config = self.get_config()
        px, py = self.game.player.logic_pos
        triggers = config.get("warning_triggers", [])
        
        hit = False
        for trigger in triggers:
            target_x, target_y = trigger.get("x"), trigger.get("y")
            buffer = trigger.get("buffer", 16)
            
            # ตรวจสอบเงื่อนไขเพิ่มเติม (ถ้ามี)
            min_x, max_x = trigger.get("min_x"), trigger.get("max_x")
            min_y, max_y = trigger.get("min_y"), trigger.get("max_y")
            
            if (target_x is None or abs(px - target_x) <= buffer) and \
               (target_y is None or abs(py - target_y) <= buffer):
                
                # ตรวจสอบขอบเขตเพิ่มเติม
                if min_x is not None and px < min_x: continue
                if max_x is not None and px > max_x: continue
                if min_y is not None and py < min_y: continue
                if max_y is not None and py > max_y: continue

                hit = True
                if not self.game.warning_triggered:
                    self._stop_player_and_snap()
                    self.game.show_dialogue_above_reaper(trigger["dialogue"], choices=trigger.get("choices"), can_save=False)
                    self.game.warning_triggered = True
                    break
        
        if not hit:
            self.game.warning_triggered = False

    def _check_tutorial_triggers(self):
        px, py = self.game.player.logic_pos
        for enemy in self.game.enemies:
            ex, ey = enemy.logic_pos
            if ((px - ex)**2 + (py - ey)**2)**0.5 < ENEMY_DETECTION_RADIUS:
                if enemy.has_line_of_sight(self.game.player.logic_pos, self.game.game_map.solid_rects):
                    if not self.game.tutorial_triggered:
                        self._stop_player_and_snap()
                        self.game.tutorial_mode = True
                        self.game.show_dialogue_above_reaper(TUTORIAL_DIALOGUE, can_save=False)
                        self.game.tutorial_triggered = True
                        break

    def _stop_player_and_snap(self):
        """หยุดผู้เล่นและ Snap ลง Grid เพื่อให้อยู่กึ่งกลางช่อง"""
        self.game.pressed_keys.clear()
        self.game.player.is_moving = False
        snapped_x = round(self.game.player.logic_pos[0] / TILE_SIZE) * TILE_SIZE
        snapped_y = round(self.game.player.logic_pos[1] / TILE_SIZE) * TILE_SIZE
        self.game.player.logic_pos = [snapped_x, snapped_y]
        self.game.player.target_pos = [snapped_x, snapped_y]
        self.game.player.sync_graphics_pos()
        self.game.player.state = 'idle'
        self.game.player.update_frame()

    def handle_dialogue_end(self, last_character, has_choices):
        """จัดการ Event หลังบทสนทนาจบลง (Logic Story ทอดๆ มาที่นี่)"""
        # 0. True Ending dialogue queue — ให้ advance ต่อก่อน logic อื่น
        if getattr(self.game, '_true_ending_next', None):
            fn = self.game._true_ending_next
            self.game._true_ending_next = None
            fn()
            return

        # 0b. Bad Ending dialogue queue
        if getattr(self.game, '_bad_ending_next', None):
            fn = self.game._bad_ending_next
            self.game._bad_ending_next = None
            fn()
            return

        # 1. Reaper: เปิดหน้าจอเซฟ (ทำเฉพาะเมื่อกดคุยเอง และไม่มีทางเลือก/ไม่ได้อยู่ในโหมดสอน)
        if last_character == "Reaper" and not has_choices and not self.game.tutorial_mode and getattr(self.game, 'is_reaper_save_prompt', False):
            # ตรวจสอบว่ากำลังแสดงหน้าจอ "ไอเทม" อยู่หรือไม่ (เช่น เพิ่งได้รับ Blue Stone)
            if self.game.dialogue_manager.is_item_notif_active:
                # ตั้งธงให้ขึ้นเซฟหลังจากผู้เล่นกดปิด Banner ไอเทม
                self.game.pending_save_prompt = True
            else:
                self.game.show_save_screen()
            
            # รีเซ็ตธงเพื่อให้การคุยครั้งต่อไป (ถ้ามี) ต้องตั้งธงใหม่
            self.game.is_reaper_save_prompt = False
        
        # 2. จบคัทซีนท้ายวัน (เข้าบ้านสำหรับวันที่ 1-4 หรือฉากจบสำหรับวันที่ 5)
        if getattr(self.game, 'is_cutscene_active', False) and getattr(self.game, 'black_overlay', None) is not None:
            if self.game.current_day == 5:
                success = not getattr(self.game, 'quest_item_fail', False)
                # ใช้ค่าสูงสุดระหว่างที่นับได้ในรอบนี้ กับที่เคยบันทึกไว้ใน Persistent 
                base_success = self.game.quest_success_count
                if hasattr(self.game, 'persistent_stats'):
                    base_success = max(base_success, self.game.persistent_stats.get('max_quest_success', 0))
                
                total_success = base_success + (1 if success else 0)
                if hasattr(self.game, 'cutscene_manager'):
                    self.game.cutscene_manager.start_day5_ending(total_success)
            else:
                self.game.end_cutscene()
            return
            
        # 3. The Sad Soul (Quest Day 1)
        if last_character == "The Sad Soul":
            self._handle_sad_soul_logic()
            
        # 4. The Postman (Quest Day 2)
        if last_character == "The Postman":
            self._handle_postman_logic()

        # 5. The Old Soul (Quest Day 3)
        if last_character == "The Old Soul":
            self._handle_old_soul_logic()

        # 6. The Lady at the Window (Quest Day 4)
        if last_character == "The Lady at the Window":
            self._handle_lady_logic()

        # 7. The Soul (Quest Day 5)
        if last_character == "The Soul":
            self._handle_soul_logic()

        # 4.1 หลังจากกดรับไอเทม "LETTERS" ให้ขึ้นประโยคบ่น (User Request)
        if last_character == "LETTERS":
            self.game.show_vn_dialogue("Little girl", "I got the letters from the postman. I should find the houses with blue marks to deliver these.")
            
        # 5. Little girl (Quest Search Food)
        if last_character == "Little girl" and getattr(self.game, '_pending_food_success', False):
            self.game._pending_food_success = False
            # อัปเดตเควส
            quest = self.game.quest_manager.active_quests.get("find_food")
            if quest and quest.is_active:
                self.game.quest_manager.update_quest_progress("find_food", 1)
                
            # เริ่มลำดับคัทซีนเดินไปกินและเปลี่ยนวัน
            if hasattr(self.game, 'cutscene_manager'):
                self.game.cutscene_manager.start_food_transition_cutscene()

        # 6. Mother (จบสุดของ Day 2 Parent Cutscene)
        if last_character == "Mother" and self.game.current_day == 2:
            if hasattr(self.game, 'cutscene_manager'):
                self.game.cutscene_manager.end_day2_parent_cutscene()
        
        # 6.1 Little girl (จบ "..." ใน Day 2 แล้วเปลี่ยนวันทันที)
        if last_character == "Little girl" and self.game.current_day == 2 and getattr(self.game, '_pending_day_transition', False):
            self.game._pending_day_transition = False
            self.game.handle_day_transition(increment=True)

        # 7. ?? (Hidden Ending)
        # ตรวจสอบชื่อตัวละครปริศนา (รองรับทั้ง ?? และ ???)
        if last_character in ["??", "???"]:
            if hasattr(self.game, 'cutscene_manager'):
                # ตรวจสอบว่ากำลังอยู่ในเฟสของ Succumb Ending หรือไม่ (cutscene_step 101)
                if getattr(self.game, 'cutscene_step', 0) == 101:
                    self.game.cutscene_manager.continue_succumb_ending()

    def _handle_sad_soul_logic(self):
        quest = self.game.quest_manager.active_quests.get("doll_parts")
        if not quest:
            self.game.quest_manager.start_quest("doll_parts", "Find doll parts", target=3)
            self.game.create_stars()
        elif quest.is_active and quest.current_count >= quest.target_count:
            # ตรวจสอบความสำเร็จเควส
            if not getattr(self.game, 'quest_item_fail', False):
                self.game.quest_success_count += 1
                self.game.save_persistent_stats() # บันทึกสถิติแบบ Global ทันที
            
            quest.is_active = False
            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)

    def _handle_postman_logic(self):
        quest = self.game.quest_manager.active_quests.get("deliver_letters")
        if not quest:
            # มอบหมายเควสและให้จดหมาย (เปลี่ยนเป้าหมายเป็น 3 หลัง)
            self.game.quest_manager.start_quest("deliver_letters", "Deliver the letters", target=3)
            self.game.letters_held = 3
            # แสดงหน้าจอพบไอเทม (โชว์รูปจดหมายทั้ง 3 แบบ: circle, cross, square)
            letter_images = [
                "assets/Items/note/circle.png",
                "assets/Items/note/cross.png",
                "assets/Items/note/square.png"
            ]
            self.game.show_item_discovery("LETTERS", letter_images)
        elif quest.is_active and quest.current_count >= quest.target_count:
            # ตรวจสอบความสำเร็จเควส (ใน Day 2 จดหมายทุพฉบับจริงหมด)
            self.game.quest_success_count += 1
            self.game.save_persistent_stats() # บันทึกสถิติแบบ Global ทันที
            
            quest.is_active = False
            # แสดงชื่อเควสที่ถูกต้องในการแจ้งเตือนตอนจบ
            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)
            
    def _handle_old_soul_logic(self):
        quest = self.game.quest_manager.active_quests.get("light_candles")
        if not quest:
            # เริ่มเควสทันทีหลังคุยจบ
            self.game.quest_manager.start_quest("light_candles", "Light the candles", target=3)
            self.game.create_candles()
        elif quest.is_active and quest.current_count >= quest.target_count:
            # ตรวจสอบความสำเร็จเควส
            if not getattr(self.game, 'quest_item_fail', False):
                self.game.quest_success_count += 1
                self.game.save_persistent_stats() # บันทึกสถิติแบบ Global ทันที
            
            quest.is_active = False
            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)

    def _handle_lady_logic(self):
        quest = self.game.quest_manager.active_quests.get("find_key")
        if not quest:
            # เริ่มเควส "Find Key" (ไม่ต้องโชว์ตัวเลขจำนวน)
            self.game.quest_manager.start_quest("find_key", "Find Key", target=1)
            self.game.create_stars()
        elif quest.is_active and quest.current_count >= quest.target_count:
            # ตรวจสอบความสำเร็จเควส
            if not getattr(self.game, 'quest_item_fail', False):
                self.game.quest_success_count += 1
                self.game.save_persistent_stats() # บันทึกสถิติแบบ Global ทันที
                # User Request: เล่นเสียงกล่องดนตรีเมื่อเควส NPC4 (Lady) สำเร็จแบบไม่เฟล
                if hasattr(self.game, 'music_box_sound') and self.game.music_box_sound:
                    self.game.music_box_sound.play()
            
            quest.is_active = False

            # ลบดาวที่เหลืออยู่บนแมพออกทั้งหมดเมื่อเควสสำเร็จ
            for s in self.game.stars[:]:
                s.destroy()
            self.game.stars.clear()

            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)

    def _handle_soul_logic(self):
        quest = self.game.quest_manager.active_quests.get("soul_fragments")
        if not quest:
            # เริ่มเควส "Find Soul Fragments" (เก็บ 3 ชิ้น)
            self.game.quest_manager.start_quest("soul_fragments", "Find Soul Fragments", target=3)
            self.game.create_stars()
        elif quest.is_active and quest.current_count < quest.target_count:
            # ถ้าเควสยังไม่เสร็จแต่เคยโหลดมาแล้วดาวหาย ให้สร้างคืน
            if not self.game.stars:
                self.game.create_stars()
        elif quest.is_active and quest.current_count >= quest.target_count:
            # สำเร็จเควส — เช็ค fail ก่อนนับ success เหมือนวันอื่นๆ
            if not getattr(self.game, 'quest_item_fail', False):
                self.game.quest_success_count += 1
                self.game.save_persistent_stats() # บันทึกสถิติแบบ Global ทันที
            quest.is_active = False

            # ลบดาวทิ้งทันทีเมื่อจบเควสที่ NPC
            for s in self.game.stars[:]: s.destroy()
            self.game.stars.clear()

            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            # เข้าสู่ฉากจบของเควส
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)

    def process_search_spot(self, spot):
        """ประมวลผลการค้นหาตามจุดต่างๆ (เรียกจาก InteractionManager)"""
        # เล่นเสียง 'ค้นหา' ทุกครั้งที่มีการสำรวจตามคำขอของผู้เล่น
        if hasattr(self.game, 'find_sound') and self.game.find_sound:
            self.game.find_sound.play()
            
        # 1. การค้นหาในบ้าน (ทุกวัน)
        if "home.tmj" in self.game.game_map.filename.lower():
            # ถ้าเป็นวันที่ต้องหาอาหาร (1, 4)
            if self.game.current_day in [1, 4]:
                if spot == EMPTY_SPOT_HOME:
                    self.game.show_vn_dialogue("Little girl", SEARCH_DIALOGUES_HOME["empty"])
                    return

                if spot == getattr(self.game, 'correct_food_spot', None):
                    self.game._pending_food_success = True
                    self.game.show_vn_dialogue("Little girl", SEARCH_DIALOGUES_HOME["found"])
                else:
                    self.game.show_vn_dialogue("Little girl", SEARCH_DIALOGUES_HOME["nothing"])
                return
            else:
                # วันที่ 3 หรือวันอื่นๆ ที่ไม่ต้องหาอาหารในบ้าน
                self.game.show_vn_dialogue("Little girl", SEARCH_DIALOGUES_HOME["empty"])
                return

        # 2. การค้นหาในแมพใต้ดิน (Day 5) — จัดการผ่าน choice.py แล้ว ไม่ต้องทำที่นี่
        if 'underground.tmj' in self.game.game_map.filename.lower():
            return  # ข้ามทันที ให้ choice.py จัดการ SEARCH result