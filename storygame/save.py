# storygame/save.py
import os
import json
from menu.load import SaveLoadScreen

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
        
        save_screen = SaveLoadScreen(
            mode="SAVE",
            callback=self.on_save_confirmed
        )
        if self.game.dialogue_root:
            self.game.dialogue_root.add_widget(save_screen)

    def on_save_confirmed(self, slot_id, save_screen=None):
        """บันทึกข้อมูลทอดๆ เก็บไว้ในไฟล์ JSON โดยตรง"""
        if not os.path.exists('saves'):
            os.makedirs('saves')
            
        save_data = {
            "day": self.game.current_day, 
            "current_map": self.game.game_map.filename,
            "player_pos": [self.game.player.x, self.game.player.y],
            "heart": self.game.heart_ui.current_health,
            "destroyed_enemies": self.game.destroyed_enemies,
            "collected_stars": self.game.collected_stars,
            "quests": self.game.quest_manager.to_dict(),
            "play_time": self.game.play_time,
            "quest_success_count": self.game.quest_success_count,
            "quest_item_fail": self.game.quest_item_fail,
            "death_count": self.game.death_count,
            "warning_dismissed": self.game.warning_dismissed,
            "has_received_blue_stone": self.game.has_received_blue_stone,
            "tutorial_triggered": self.game.tutorial_triggered
        }
        
        file_path = f'saves/slot_{slot_id}.json'
        with open(file_path, 'w') as f:
            json.dump(save_data, f)
            
        if save_screen:
            save_screen.close()
        
        self.game.is_dialogue_active = False
        self.game.request_keyboard_back()

    def load_game_from_pause(self):
        """เปิดหน้าจอโหลดเซฟจากเมนู Pause"""
        load_screen = SaveLoadScreen(
            mode="LOAD", 
            callback=self._on_pause_load_selected
        )
        if self.game.dialogue_root:
            self.game.dialogue_root.add_widget(load_screen)

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
