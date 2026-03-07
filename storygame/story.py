# storygame/story.py
from storygame.chat import WARNING_DIALOGUE, WARNING_CHOICES, TUTORIAL_DIALOGUE
from settings import ENEMY_DETECTION_RADIUS, TILE_SIZE, MAP_FILE, HOME_EAT_POS
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
            
            if (target_x is None or abs(px - target_x) < buffer) and \
               (target_y is None or abs(py - target_y) < buffer):
                
                # ตรวจสอบขอบเขตเพิ่มเติม
                if min_x is not None and px < min_x: continue
                if max_x is not None and px > max_x: continue
                if min_y is not None and py < min_y: continue
                if max_y is not None and py > max_y: continue

                hit = True
                if not self.game.warning_triggered:
                    self._stop_player_and_snap()
                    self.game.show_dialogue_above_reaper(trigger["dialogue"], choices=trigger.get("choices"))
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
                    self._stop_player_and_snap()
                    self.game.tutorial_mode = True
                    self.game.show_dialogue_above_reaper(TUTORIAL_DIALOGUE)
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
        # 1. Reaper: เปิดหน้าจอเซฟ (ทำเฉพาะเมื่อกดคุยเอง และไม่มีทางเลือก/ไม่ได้อยู่ในโหมดสอน)
        if last_character == "Reaper" and not has_choices and not self.game.tutorial_mode and getattr(self.game, 'is_reaper_save_prompt', False):
            self.game.show_save_screen()
        
        # 2. Angel/Devil: จบคัทซีนเข้าบ้าน (ทำเฉพาะเมื่ออยู่ในโหมด Cutscene จริงๆ เช่น ท้ายวัน)
        if last_character in ["Angel", "Devil"] and getattr(self.game, 'is_cutscene_active', False):
            self.game.end_cutscene()
            
        # 3. The Sad Soul (Quest Day 1)
        if last_character == "The Sad Soul":
            self._handle_sad_soul_logic()
            
        # 4. The Postman (Quest Day 2)
        if last_character == "The Postman":
            self._handle_postman_logic()

        # 5. The Old Soul (Quest Day 3)
        if last_character == "The Old Soul":
            self._handle_old_soul_logic()

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

    def _handle_sad_soul_logic(self):
        quest = self.game.quest_manager.active_quests.get("doll_parts")
        if not quest:
            self.game.quest_manager.start_quest("doll_parts", "Find doll parts", target=3)
            self.game.create_stars()
        elif quest.is_active and quest.current_count >= quest.target_count:
            # ตรวจสอบความสำเร็จเควส
            if not getattr(self.game, 'quest_item_fail', False):
                self.game.quest_success_count += 1
            
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
            
            quest.is_active = False
            self.game.quest_manager.show_quest_notification(f"COMPLETED: {quest.name.upper()}")
            self.game.quest_manager.update_quest_list_ui()
            Clock.schedule_once(self.game.start_quest_complete_cutscene, 1.5)