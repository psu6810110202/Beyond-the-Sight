from kivy.core.window import Window
from data.settings import *

class InputHandler:
    def __init__(self, game):
        self.game = game
        self.pressed_keys = set()
        self._keyboard = None
        self.request_keyboard()

    def request_keyboard(self):
        """ขอคีย์บอร์ดกลับมาให้ GameWidget อีกครั้ง (ใช้หลังปิดเมนู/หน้าจอโหลด)"""
        if self._keyboard:
            self.unbind_keyboard()
            
        self._keyboard = Window.request_keyboard(self.on_keyboard_closed, self.game) 
        self._keyboard.bind(on_key_down=self.on_key_down) 
        self._keyboard.bind(on_key_up=self.on_key_up) 
        # เคลียร์ปุ่มที่ค้างอยู่ป้องกันตัวละครเดินค้าง
        self.pressed_keys.clear()

    def unbind_keyboard(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self.on_key_down)  
            self._keyboard.unbind(on_key_up=self.on_key_up) 
            self._keyboard = None

    def on_keyboard_closed(self): 
        self.unbind_keyboard()

    def on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1]
        
        # ป้องกันการกดปุ่มถ้าเกมหยุดหรือยังไม่พร้อม (ยกเว้นตอนจบ Ending)
        if (self.game.is_paused or not self.game.is_ready) and getattr(self.game, 'cutscene_step', 0) != 103:
            return True
            
        # User Request: Ending Sequence Exit
        if getattr(self.game, 'cutscene_step', 0) == 103:
            if key_name in ['enter', 'e', 'space']:
                self.game.return_to_main_menu()
            return True
            
        if key_name == 'e' or key_name == 'enter':
            # 1. ถ้ามีแจ้งเตือนไอเทมอยู่ ให้ปิดแจ้งเตือนก่อน
            if self.game.dialogue_manager.is_item_notif_active:
                self.game.dialogue_manager.close_item_discovery()
                
                # ถ้ามีแชทที่รอขึ้นต่อ (เช่น หลังเก็บของ Day 4)
                if getattr(self.game, 'pending_post_discovery_dialogue', None):
                    d = self.game.pending_post_discovery_dialogue
                    self.game.pending_post_discovery_dialogue = None
                    self.game.show_vn_dialogue(d['name'], d['text'], portrait=d.get('portrait'))
                # ถ้าไม่มีแชทต่อ แต่กำลังคุยค้างอยู่ (กรณีได้รับไอเทมกลางบทสนทนา) 
                elif self.game.is_dialogue_active:
                    self.game.next_dialogue()
                return True
        
        # คีย์ Q สำหรับกดใช้ไอเทม Blue Stone
        if key_name == 'q':
            # ห้ามใช้ขณะคุย หรือ มีกระดานแจ้งเตือนไอเทมโชว์อยู่
            if self.game.is_dialogue_active or self.game.dialogue_manager.is_item_notif_active:
                return True
                
            if getattr(self.game, 'has_received_blue_stone', False):
                if getattr(self.game, 'stun_cooldown', 0) <= 0:
                    self.game.use_stun_item()
                else:
                    print(f"Stun on cooldown: {self.game.stun_cooldown:.1f}s")
            else:
                print("You don't have the Blue Stone yet!")
            return True

        if key_name == 'e':
            # ถ้ากำลังคุยอยู่ ให้ปุ่ม E ทำหน้าที่เดียวกับ Enter คือไปประโยคถัดไป
            if self.game.is_dialogue_active:
                if not getattr(self.game, 'choice_buttons', []): 
                    self.game.next_dialogue()
                return True
                
            self.game.interact()
        elif key_name == 'enter':
            # ถ้ากำลังคุยอยู่
            if self.game.is_dialogue_active:
                # ถ้ามี Choice ให้เลือกตัวเลือกที่ไฮไลท์อยู่
                if getattr(self.game, 'choice_buttons', []):
                    if self.game.choice_index < len(self.game.current_choices):
                        self.game.on_choice_selected(self.game.current_choices[self.game.choice_index])
                    else:
                        self.game.close_dialogue()
                else:
                    self.game.next_dialogue()
        
        # จัดการการเลื่อน Choice ด้วยลูกศร ขึ้น/ลง
        elif self.game.is_dialogue_active and getattr(self.game, 'choice_buttons', []):
            from ui.choice import update_choice_visuals
            if key_name == 'up':
                self.game.choice_index = (self.game.choice_index - 1) % len(self.game.choice_buttons)
                update_choice_visuals(self.game)
                return True
            elif key_name == 'down':
                self.game.choice_index = (self.game.choice_index + 1) % len(self.game.choice_buttons)
                update_choice_visuals(self.game)
                return True
        
        elif key_name == 'escape':
            self.game.toggle_pause()
            return True

        self.pressed_keys.add(key_name)
        return True
        
    def on_key_up(self, keyboard, keycode): 
        key_name = keycode[1] 
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)
        return True
