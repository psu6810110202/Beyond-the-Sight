from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from data.settings import *

class InteractionManager:
    def __init__(self, game):
        self.game = game

    def get_interaction_target(self, targets, limit=32):
        """ค้นหาเป้าหมายที่อยู่ใกล้และผู้เล่นหันหน้าเข้าหา"""
        px, py = self.game.player.logic_pos
        p_dir = self.game.player.direction
        
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

    def get_search_target(self, limit=20):
        """ค้นหาจุดที่สามารถค้นหาได้ในแมพบ้าน (ต้องหันหน้าเข้าหาและห่าง 1 บล็อก)"""
        if "home.tmj" not in self.game.game_map.filename.lower():
            return None
        
        px, py = self.game.player.logic_pos
        p_dir = self.game.player.direction
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
        self.game.clear_interaction_hints()
        
        if self.game.is_dialogue_active or self.game.is_paused or self.game.is_cutscene_active or \
           getattr(self.game.dialogue_manager, 'is_item_notif_active', False):
            return
            
        root_to_check = self.game.dialogue_root.children if self.game.dialogue_root else self.game.children
        from ui.load import SaveLoadScreen
        if any(isinstance(child, SaveLoadScreen) for child in root_to_check):
            return
            
        # เช็คไอเทมดวงดาวก่อน (ระยะ 20)
        star_target, _, _ = self.get_interaction_target(self.game.stars, limit=20)
        self.game.current_star_target = star_target
        if star_target: return 
        
        # เช็คไอเทมเทียน (Day 3)
        candle_target, _, _ = self.get_interaction_target(self.game.candles, limit=20)
        self.game.current_candle_target = candle_target
        if candle_target: return

        # เช็ค NPC / Reaper (ระยะ 32)
        target, dx, dy = self.get_interaction_target(self.game.npcs + [self.game.reaper] + getattr(self.game, 'extra_reapers', []), limit=32)
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
            
            spos = self.game.camera.world_to_screen(target.logic_pos[0] + TILE_SIZE/2, target.logic_pos[1] + 45)
            hint.pos = (spos[0] - (box_width / 2), spos[1])
            
            if self.game.dialogue_root: self.game.dialogue_root.add_widget(hint)
            self.game.interaction_hints.append(hint)
            return

        # เช็ค Underground Portal
        px, py = self.game.player.logic_pos
        ux, uy = UNDERGROUND_PORTAL_POS
        dist = ((px - ux)**2 + (py - uy)**2)**0.5
        
        if dist <= 32 and self.game.current_day == 5:
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
            
            spos = self.game.camera.world_to_screen(ux + TILE_SIZE/2, uy + 45)
            hint.pos = (spos[0] - 12.5, spos[1])
            if self.game.dialogue_root: self.game.dialogue_root.add_widget(hint)
            self.game.interaction_hints.append(hint)
            return

        # เช็คจุดวางจดหมาย (Day 2)
        if self.game.current_day == 2 and getattr(self.game, 'letters_held', 0) > 0:
            for i, spot in enumerate(HOUSE_DOOR_SPOTS):
                if i in self.game.delivered_house_indices:
                    continue
                px, py = self.game.player.logic_pos
                if abs(px - spot[0]) <= 32 and abs(py - spot[1]) <= 32:
                    self.game.pending_drop_spot = (spot, i)
                    return

        self.game.current_search_target = self.get_search_target()

    def interact(self):
        """จัดการการกดปุ่ม [E] เพื่อคุยหรือสำรวจ"""
        self.game.clear_interaction_hints()
        
        # 0. เช็ค Underground Portal (Priority First on Day 5)
        px, py = self.game.player.logic_pos
        ux, uy = UNDERGROUND_PORTAL_POS
        dist = ((px - ux)**2 + (py - uy)**2)**0.5
        
        if dist <= 32 and self.game.current_day == 5:
            # ล้างทุกอย่างให้เกลี้ยงที่สุด
            for npc in self.game.npcs: npc.destroy()
            for enemy in self.game.enemies: enemy.destroy()
            for er in getattr(self.game, 'extra_reapers', []): er.destroy()
            
            self.game.sorting_layer.clear()
            self.game.npcs, self.game.enemies, self.game.stars = [], [], []
            self.game.extra_reapers = []

            if hasattr(self.game, 'reaper') and self.game.reaper:
                self.game.reaper.x, self.game.reaper.y = -5000, -5000 
                self.game.reaper.logic_pos = [-5000, -5000]
                if hasattr(self.game.reaper, 'sprite_color'): self.game.reaper.sprite_color.a = 0
                if hasattr(self.game.reaper, 'aura_color'): self.game.reaper.aura_color.a = 0
                self.game.reaper.update_visual_positions()

            self.game.change_map('assets/Tiles/underground.tmj')
            self.game.player.logic_pos = [1088, 16] 
            self.game.player.target_pos = [1088, 16]
            self.game.player.direction = 'up'
            self.game.player.update_frame()
            self.game.player.sync_graphics_pos()
            self.game.sorting_layer.add(self.game.player.group)
            
            self.game.create_npcs()
            self.game.create_enemies()
            self.game.world_manager.create_reapers() 
            self.game.create_stars()
            
            self.game.show_vn_dialogue("Little girl", "It's cold and damp down here... I should be careful.")
            return

        # 1. เช็คการวางจดหมาย (Day 2 Priority)
        if self.game.current_day == 2 and hasattr(self.game, 'pending_drop_spot') and self.game.pending_drop_spot:
            spot, spot_index = self.game.pending_drop_spot
            px, py = self.game.player.logic_pos
            if abs(px - spot[0]) <= 32 and abs(py - spot[1]) <= 32:
                if self.game.letters_held > 0 and spot_index not in self.game.delivered_house_indices:
                    mark_path = HOUSE_MARKS_MAPPING.get(tuple(spot))
                    self.game.house_inspection_step = True
                    self.game.show_vn_dialogue("Little girl", "I found a mark on this house door...", portrait=mark_path)
                    return

        if self.game.current_star_target:
            if self.game.find_sound: self.game.find_sound.play()
            if self.game.curious_sound: self.game.curious_sound.play()
                
            star_pos = (self.game.current_star_target.x, self.game.current_star_target.y)
            if 'underground.tmj' in self.game.game_map.filename.lower():
                self.game.show_vn_dialogue("Little girl", "I found one of those objects... should I search inside?", choices=["SEARCH", "LEAVE IT"])
            elif self.game.current_day == 4:
                portrait = DAY4_KEY_MAPPING.get(star_pos, {}).get("portrait")
                self.game.show_vn_dialogue("Little girl", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"], portrait=portrait)
            else:
                portrait = STAR_ITEM_MAPPING.get(star_pos, {}).get("portrait")
                self.game.show_vn_dialogue("Little girl", "There's a piece of something here...", choices=["PICK UP", "LEAVE IT"], portrait=portrait)
            return

        if self.game.current_candle_target:
            if self.game.current_candle_target.is_lit:
                self.game.show_vn_dialogue("Little girl", "This candle is already burning brightly.")
                return
            self.game.show_vn_dialogue("Little girl", CANDLE_LIGHT_DIALOGUE, choices=CANDLE_LIGHT_CHOICES)
            return

        target, dx, dy = self.get_interaction_target(self.game.npcs + [self.game.reaper] + getattr(self.game, 'extra_reapers', []), limit=32)
        if target:
            npc_index = self.game.npcs.index(target) if target in self.game.npcs else -1
            self.game.process_interaction(target, npc_index, dx, dy)
            return

        if self.game.current_search_target:
            self.interact_with_search_spot(self.game.current_search_target)
            return

        if 'underground.tmj' in self.game.game_map.filename.lower():
            layers = self.game.game_map.map_data.get('layers', [])
            objects_layer = next((l for l in layers if l.get('name') == "ของ"), None)
            if objects_layer:
                px, py = self.game.player.logic_pos
                for obj in objects_layer.get('objects', []):
                    ox, oy = obj.get('x', 0), obj.get('y', 0)
                    dist = ((px - ox)**2 + (py - (self.game.game_map.height * 16 - oy))**2)**0.5
                    if dist <= 32:
                        self.interact_with_search_spot(obj)
                        return

    def interact_with_search_spot(self, spot):
        """ประมวลผลการค้นหาตามจุดต่างๆ"""
        self.game.story_manager.process_search_spot(spot)

    def process_interaction(self, target, index, dx, dy):
        """ประมวลผลการคุยกับ NPC หรือ Reaper"""
        if target == self.game.reaper or target in getattr(self.game, 'extra_reapers', []):
            # เช็คว่าเป็น Reaper ปลอม/ตัวแถม ในพิกัดอันตรายหรือไม่
            is_extra = target in getattr(self.game, 'extra_reapers', [])
            dialogue = self.get_reaper_dialogue(dx, dy)
            self.show_dialogue_above_reaper(dialogue, can_save=not is_extra)
        elif target in self.game.npcs:
            npc_name = ""
            if hasattr(target, 'name') and target.name:
                npc_name = target.name
            elif hasattr(target, 'image_path'):
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

    def show_dialogue_above_npc(self, npc, dialogue, npc_name=None):
        if npc_name is None:
            npc_name = "The Sad Soul" if self.game.npcs.index(npc) == 0 else f"NPC{self.game.npcs.index(npc) + 1}"
        
        self.game.current_dialogue_queue = dialogue
        self.game.current_dialogue_index = 0
        self.game.current_character_name = npc_name
        self.game.current_portrait = None
        
        if self.game.current_dialogue_queue:
            self.game.is_dialogue_active = True
            self.game.player.stop()
            first_text = self.game.current_dialogue_queue[0]
            self.game.dialogue_manager.show_vn_dialogue(npc_name, first_text)

    def show_dialogue_above_reaper(self, dialogue, choices=None, portrait=None, can_save=True):
        self.game.is_reaper_save_prompt = can_save # เปิดธงให้ขึ้นเซฟหลังคุยจบ (ถ้าไม่ใช่พิกัดอันตราย)
        self.game.current_dialogue_queue = dialogue
        self.game.current_dialogue_index = 0
        self.game.current_character_name = "Reaper"
        self.game.current_portrait = portrait
        self.game.current_choices = choices
        
        if self.game.reaper_voice_sound:
            self.game.reaper_voice_sound.play()
        
        if self.game.current_dialogue_queue:
            self.game.is_dialogue_active = True
            self.game.player.stop()
            first_text = self.game.current_dialogue_queue[0]
            is_last = (self.game.current_dialogue_index == len(self.game.current_dialogue_queue) - 1)
            self.game.dialogue_manager.show_vn_dialogue(
                "Reaper", first_text, 
                choices=(choices if is_last else None),
                portrait=self.game.current_portrait
            )

    def get_proximity_dialogue(self, npc_name, distance_x, distance_y):
        from data.chat import NPC_DIALOGUES
        if npc_name == "The Sad Soul":
            quest = self.game.quest_manager.active_quests.get("doll_parts")
            if quest:
                if quest.current_count >= quest.target_count:
                    if getattr(self.game, 'quest_item_fail', False):
                        return ["Oh! You found them!", "Wait... these parts... they're just old scrap metal...", "Why would you give me these? This isn't my doll..."]
                    return ["Oh! You found them!", "My doll... it's whole again. Thank you so much!", "You really are a kind one."]
                elif quest.is_active:
                    return ["Were you able to find the pieces? It's still so dark..."]

        if npc_name == "The Postman":
            quest = self.game.quest_manager.active_quests.get("deliver_letters")
            if quest:
                if quest.current_count >= quest.target_count:
                    if getattr(self.game, "quest_item_fail", False):
                        return ["Are you sure these went to the right houses? ...I suppose it's done anyway.", "Thank you..."]
                    return ["Ah, you're back...", "My work here is finally done.", "Thank you, little one..."]
                elif quest.is_active:
                    return ["..."]

        if npc_name == "The Old Soul":
            quest = self.game.quest_manager.active_quests.get("light_candles")
            if quest:
                if quest.current_count >= quest.target_count:
                    from data.chat import OLD_SOUL_SUCCESS, OLD_SOUL_FAIL
                    if getattr(self.game, "quest_item_fail", False):
                        return [OLD_SOUL_FAIL]
                    return [OLD_SOUL_SUCCESS]
                elif quest.is_active:
                    return ["The red flowers in the vase...", "The blue rug in the hallway...", "The yellow sunlight on the porch...", "If only I could see those colors again..."]

        if npc_name == "The Lady at the Window":
            quest = self.game.quest_manager.active_quests.get("find_key")
            if quest:
                if quest.current_count >= quest.target_count:
                    if getattr(self.game, 'quest_item_fail', False):
                        return ["Wait... this isn't my key. I don't think it fits anything here.", "Thank you for trying, though."]
                    return ["Oh! The key... my music box can finally play its tune again.", "Thank you, little one. The melody... I've missed it so."]
                elif quest.is_active:
                    return ["It's so quiet... I just want to hear that song one more time."]

        if npc_name == "The Soul":
            quest = self.game.quest_manager.active_quests.get("soul_fragments")
            if quest:
                if quest.current_count >= quest.target_count:
                    from data.chat import NPC5_SUCCESS, NPC5_FAIL
                    if getattr(self.game, 'quest_item_fail', False):
                        return [NPC5_FAIL or "These aren't my fragments..."]
                    return [NPC5_SUCCESS or "I feel whole again... Thank you."]
                elif quest.is_active:
                    return ["Were you able to find the fragments? I can almost feel myself becoming whole again..."]

        if npc_name in NPC_DIALOGUES:
            return NPC_DIALOGUES[npc_name]
        return ["..."]

    def get_reaper_dialogue(self, distance_x, distance_y):
        from data.chat import REAPER_DIALOGUES
        import random
        quest_doll = self.game.quest_manager.active_quests.get("doll_parts")
        if quest_doll and quest_doll.is_active and quest_doll.current_count < quest_doll.target_count:
            return ["What he worries about... was thrown away with the unwanted things.", "Try searching that trash pile, you might find something."]
            
        quest_letters = self.game.quest_manager.active_quests.get("deliver_letters")
        if quest_letters and quest_letters.is_active and quest_letters.current_count < quest_letters.target_count:
            return ["Every silent message seeks its twin carved in wood... lead it home"]

        quest_candles = self.game.quest_manager.active_quests.get("light_candles")
        if quest_candles and quest_candles.is_active and quest_candles.current_count < quest_candles.target_count:
            return ["He already told you the order. Just follow the sequence of his memories."]

        return [random.choice(REAPER_DIALOGUES)]

    def clear_interaction_hints(self):
        for hint in self.game.interaction_hints:
            if hint.parent:
                hint.parent.remove_widget(hint)
        self.game.interaction_hints = []
