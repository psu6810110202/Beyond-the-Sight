# storygame/quest.py
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from settings import GAME_FONT

class QuestData:
    def __init__(self, name, target_count=3):
        self.name = name
        self.current_count = 0
        self.target_count = target_count
        self.is_active = False

class QuestManager:
    def __init__(self, game):
        self.game = game
        self.active_quests = {}
        self.quest_ui_label = None
        self.notification_box = None

    def to_dict(self):
        """แปลงข้อมูลเควสเป็น dictionary เพื่อเซฟ"""
        data = {}
        for q_id, q in self.active_quests.items():
            data[q_id] = {
                "name": q.name,
                "current_count": q.current_count,
                "target_count": q.target_count,
                "is_active": q.is_active
            }
        return data

    def from_dict(self, data):
        """โหลดข้อมูลเควสจาก dictionary"""
        if not data:
            return
        for q_id, q_data in data.items():
            quest = QuestData(q_data["name"], q_data["target_count"])
            quest.current_count = q_data["current_count"]
            quest.is_active = q_data["is_active"]
            self.active_quests[q_id] = quest
        
        # อัปเดต UI หลังจากโหลดข้อมูลเสร็จ (ไม่ต้องให้เลื่อนอนิเมชั่น)
        self.update_quest_list_ui(animate=False)

    def start_quest(self, quest_id, quest_name, target=3):
        """เริ่มเควสใหม่: 1. แจ้งเตือน -> 2. เลือนรายการเควสออกมา"""
        if quest_id not in self.active_quests:
            self.active_quests[quest_id] = QuestData(quest_name, target)
            self.active_quests[quest_id].is_active = True
            
            # 1. แสดงแจ้งเตือนบนหน้าจอก่อน
            self.show_quest_notification(f"NEW QUEST: {quest_name}")
            
            # 2. ตั้งเวลาให้รายการเควสด้านข้าง "เลือนออกมา" หลังจากแจ้งเตือนหายไป (ประมาณ 3.5 วินาที)
            Clock.schedule_once(lambda dt: self.update_quest_list_ui(animate=True), 3.5)

    def show_quest_notification(self, text):
        """แสดงกล่องแจ้งเตือน -> ค้างไว้ -> ค่อยๆ เลือนหายไป (Fade Out)"""
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        if self.notification_box:
            root.remove_widget(self.notification_box)

        label = Label(
            text=text,
            font_name=GAME_FONT,
            size_hint=(0.4, 0.06),
            pos_hint={'center_x': 0.5, 'top': 0.98},
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            opacity=0, # เริ่มจากจางหาย
            bold=True
        )

        with label.canvas.before:
            Color(0, 0, 0, 0.85)
            label.bg_rect = RoundedRectangle(pos=label.pos, size=label.size, radius=[5,])
            
        def update_notif_graphics(instance, value):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size
            instance.font_size = instance.height * 0.5
            instance.text_size = instance.size # บังคับให้ขอบเขตข้อความเท่ากับขนาดกล่องเพื่อให้ Align ทำงาน
        
        label.bind(pos=update_notif_graphics, size=update_notif_graphics)

        self.notification_box = label
        root.add_widget(label)

        # Sequence: Fade In (0.5s) -> Wait (2s) -> Fade Out (1s) -> Remove
        anim = Animation(opacity=1, duration=0.5)
        anim += Animation(opacity=1, duration=2.0) # ค้างไว้
        anim += Animation(opacity=0, duration=1.0) # ค่อยๆ เลือนหาย
        
        anim.bind(on_complete=lambda *args: self._remove_notification(label))
        anim.start(label)

    def _remove_notification(self, widget):
        if widget.parent:
            widget.parent.remove_widget(widget)
        if self.notification_box == widget:
            self.notification_box = None

    def update_quest_list_ui(self, animate=False):
        """อัปเดตรายการเควส พร้อมเอฟเฟกต์ค่อยๆ เลือนออกมา (Fade In / Slide In)"""
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        if not self.quest_ui_label:
            self.quest_ui_label = Label(
                text="",
                font_name=GAME_FONT,
                size_hint=(None, 0.05), # ใช้ None เพื่อให้ขยายตามตัวอักษรได้จริงๆ
                width=200,
                pos_hint={'x': -0.25, 'top': 0.86},
                halign='left',
                valign='middle',
                color=(1, 1, 1, 1),
                padding=[15, 0],
                opacity=0
            )
            
            with self.quest_ui_label.canvas.before:
                Color(0, 0, 0, 0.5)
                self.quest_ui_label.bg_rect = RoundedRectangle(
                    pos=self.quest_ui_label.pos, 
                    size=self.quest_ui_label.size, 
                    radius=[0, 15, 15, 0]
                )
            
            def update_quest_graphics(instance, value):
                # อัปเดตพื้นหลังอย่างเดียว (ห้ามแก้ text_size ที่นี่เด็ดขาด)
                instance.bg_rect.pos = instance.pos
                instance.bg_rect.size = instance.size

            def update_width_by_texture(instance, value):
                # ปรับความกว้างตามเนื้อหาข้อความ + padding
                # การเปลี่ยน width ที่นี่จะไป trigger size ซึ่งจะไปรัน update_quest_graphics ต่อ
                new_width = instance.texture_size[0] + 40
                if abs(instance.width - new_width) > 1:
                    instance.width = new_width

            self.quest_ui_label.bind(pos=update_quest_graphics, size=update_quest_graphics)
            self.quest_ui_label.bind(texture_size=update_width_by_texture)
            
            def update_font_size(instance, value):
                # ปรับขนาดฟอนต์ตามความสูงหน้าจอ (Responsive)
                # แถบสูง 0.05 ของหน้าจอ, ฟอนต์เอา 70% ของแถบ
                self.quest_ui_label.font_size = Window.height * 0.05 * 0.7
            
            Window.bind(height=update_font_size)
            update_font_size(None, Window.height) # เรียกครั้งแรก
        
        # ตรวจสอบว่า Widget อยู่ในตำแหน่ง Root ที่ถูกต้องหรือไม่ (ป้องกันปัญหาโหลดเซฟแล้ว UI หาย)
        if self.quest_ui_label.parent != root:
            if self.quest_ui_label.parent:
                self.quest_ui_label.parent.remove_widget(self.quest_ui_label)
            root.add_widget(self.quest_ui_label)

        quest_text = ""
        count = 0
        for q in self.active_quests.values():
            if q.is_active:
                if q.current_count >= q.target_count:
                    # ถ้าครบแล้ว ให้โชว์แค่ชื่อเควส (เช่น RETURN TO THE SAD SOUL)
                    quest_text += f"• {q.name.upper()}"
                else:
                    quest_text += f"• {q.name.upper()}: {q.current_count}/{q.target_count}"
                count += 1
        
        self.quest_ui_label.text = quest_text
        
        if count > 0:
            if animate:
                # ค่อยๆ เลื่อนออกมา (Slide In) และเลือนชัดขึ้น (Fade In)
                anim = Animation(pos_hint={'x': 0, 'top': 0.86}, opacity=1, duration=1.0, t='out_quad')
                anim.start(self.quest_ui_label)
            else:
                self.quest_ui_label.pos_hint = {'x': 0, 'top': 0.86}
                self.quest_ui_label.opacity = 1
        else:
            self.quest_ui_label.opacity = 0
    def update_quest_progress(self, quest_id, amount=1):
        """อัปเดตความคืบหน้าของเควส"""
        if quest_id in self.active_quests:
            quest = self.active_quests[quest_id]
            if quest.is_active:
                quest.current_count += amount
                if quest.current_count >= quest.target_count:
                    quest.current_count = quest.target_count
                    # ไม่ปิดเควสทันที เพื่อให้แสดงเป้าหมายใหม่ (เช่น Return to NPC)
                    if quest_id != "doll_parts":
                        quest.is_active = False 
                        self.show_quest_notification(f"COMPLETED: {quest.name}")
                
                self.update_quest_list_ui(animate=False)
