# storygame/save.py
import os
import json
from ui.load import SaveLoadScreen

class SaveManager:
    def __init__(self, game):
        self.game = game

    def show_save_screen(self):
        """เปิดหน้าจอเลือกสล็อตเพื่อเซฟเกม"""
        self.game.clear_interaction_hints()
        self.game.pressed_keys.clear()
        self.game.player.is_moving = False
        self.game.player.state = 'idle'
        self.game.player.update_animation_speed()
        self.game.player.update_frame()
        self.game.is_dialogue_active = True
        
        save_screen = SaveLoadScreen(
            mode="SAVE",
            callback=self.on_save_confirmed,
            on_close_cb=self.game.request_keyboard_back
        )
        if self.game.dialogue_root:
            self.game.dialogue_root.add_widget(save_screen)

    def on_save_confirmed(self, slot_id, save_screen=None):
        """บันทึกข้อมูลแบบแยกส่วนตามวัน (Day-specific save) เพื่อลดขนาดไฟล์และล้างข้อมูลเก่าที่ไม่จำเป็น"""
        if not os.path.exists('saves'):
            os.makedirs('saves')
            
        day = self.game.current_day
        
        # 1. ข้อมูลหลักที่ต้องสืบทอดไปทุกวัน (Core Data)
        save_data = {
            "day": day, 
            "current_map": self.game.game_map.filename,
            "player_pos": list(self.game.player.logic_pos),
            "heart": self.game.heart_ui.current_health,
            "play_time": self.game.play_time,
            "quest_success_count": self.game.quest_success_count,
            "quest_item_fail": self.game.quest_item_fail,
            "death_count": self.game.death_count,
            "warning_dismissed": self.game.warning_dismissed,
            "has_received_blue_stone": self.game.has_received_blue_stone,
            "has_received_lantern": self.game.has_received_lantern,
            "tutorial_triggered": self.game.tutorial_triggered,
            
            # สถานะของมอนสเตอร์และสภาพแวดล้อมในแมพปัจจุบัน
            "destroyed_enemies": self.game.destroyed_enemies,
            "enemies_data": [
                {
                    "id": enemy.id,
                    "pos": list(enemy.logic_pos),
                    "type": enemy.enemy_type
                }
                for enemy in self.game.enemies if not enemy.is_fading
            ]
        }
        
        # 2. กรองข้อมูลเฉพาะวัน (Day-Specific Logic)
        all_quests = self.game.quest_manager.to_dict()
        filtered_quests = {}
        
        # ค้นหาเควสที่เกี่ยวข้องกับวันนั้นๆ และเควส "หากิน" (ค้นหาเสบียงท้ายวัน)
        target_quests = {
            1: ["doll_parts"],
            2: ["deliver_letters"],
            3: ["light_candles"],
            4: ["find_key"],
            5: ["soul_fragments"]
        }.get(day, [])
        target_quests.append("find_food")
        
        for qid in target_quests:
            if qid in all_quests:
                filtered_quests[qid] = all_quests[qid]
        save_data["quests"] = filtered_quests

        # 3. ข้อมูลสิ่งของวางกระจายตามแมพ (Stars / Candles / Letters)
        if day in [1, 4, 5]:
            save_data["collected_stars"] = self.game.collected_stars
            
        if day == 2:
            save_data["letters_held"] = getattr(self.game, 'letters_held', 0)
            save_data["delivered_house_indices"] = getattr(self.game, 'delivered_house_indices', [])
            
        elif day == 3:
            save_data["current_candle_lit_count"] = getattr(self.game, 'current_candle_lit_count', 0)
            save_data["lit_candle_positions"] = [
                {"pos": list(c.logic_pos), "color": getattr(c, 'current_color', None)} 
                for c in getattr(self.game, 'candles', []) if c.is_lit
            ]
        
        file_path = f'saves/slot_{slot_id}.json'
        with open(file_path, 'w') as f:
            json.dump(save_data, f)
            
        if save_screen:
            save_screen.close()
        
        self.game.is_dialogue_active = False
        self.game.request_keyboard_back()

    def load_game_from_pause(self):
        """เปิดหน้าจอโหลดเซฟจากเมนู Pause"""
        def on_close_load():
            from kivy.core.window import Window
            if self.game.is_paused and getattr(self.game, 'pause_menu', None):
                pm = self.game.pause_menu
                if pm._keyboard:
                    pm._keyboard.unbind(on_key_down=pm._on_key_down)
                pm._keyboard = Window.request_keyboard(pm._keyboard_closed, pm)
                pm._keyboard.bind(on_key_down=pm._on_key_down)
            else:
                self.game.request_keyboard_back()

        load_screen = SaveLoadScreen(
            mode="LOAD", 
            callback=self._on_pause_load_selected,
            on_close_cb=on_close_load
        )
        if self.game.dialogue_root:
            self.game.dialogue_root.add_widget(load_screen)

    def get_latest_save_data(self):
        """ค้นหาไฟล์เซฟล่าสุดและคืนค่าข้อมูล โดยเช็คจาก file mtime"""
        saves_dir = 'saves'
        if not os.path.exists(saves_dir):
            return None
            
        files = [os.path.join(saves_dir, f) for f in os.listdir(saves_dir) if f.endswith('.json')]
        if not files:
            return None
            
        latest_file = max(files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r') as f:
                return json.load(f)
        except:
            return None

    def _on_pause_load_selected(self, slot_id, load_screen=None):
        save_path = f'saves/slot_{slot_id}.json'
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                data = json.load(f)
            
            if load_screen: load_screen.close()
            self.game.resume_game()
            
            # สั่งการ App ทอดๆ ให้รีโหลดเกมใหม่
            from kivy.app import App as KivyApp
            app = KivyApp.get_running_app()
            app.show_game(initial_data=data)
