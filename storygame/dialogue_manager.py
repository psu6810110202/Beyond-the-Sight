from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.clock import Clock
from settings import GAME_FONT
from storygame.chat import DIALOGUE_CONFIG
from storygame.choice import draw_choice_buttons, clear_choices

class DialogueManager:
    def __init__(self, game):
        self.game = game
        self.dialogue_bg = None
        self.dialogue_text = None
        self.name_label = None

    def show_vn_dialogue(self, character_name, dialogue, choices=None):
        """วาดกล่องข้อความสไตล์ Visual Novel"""
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        cfg = DIALOGUE_CONFIG
        
        # อัปเดตรายการ Choice ปัจจุบันให้ GameWidget รู้
        self.game.current_choices = choices if choices else []

        # 1. ลบทิ้งหากมีของเดิมอยู่
        if self.dialogue_bg:
            if self.dialogue_bg.parent: self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None

        # 2. พื้นหลัง - ใช้ FloatLayout และ pos_hint เพื่อให้ชิดขอบล่างเสมอ
        bg_widget = FloatLayout(size_hint=(1, None), height=cfg["box_height"], pos_hint={'x': 0, 'y': 0})
        with bg_widget.canvas.before:
            Color(0, 0, 0, cfg["bg_opacity"])
            self.dialogue_bg_rect = Rectangle(size=bg_widget.size, pos=bg_widget.pos)
            
        def update_bg_rect(instance, value):
            self.dialogue_bg_rect.pos = instance.pos
            self.dialogue_bg_rect.size = instance.size
        bg_widget.bind(size=update_bg_rect, pos=update_bg_rect)
        
        root.add_widget(bg_widget)
        self.dialogue_bg = bg_widget

        # 3. ชื่อตัวละคร
        if character_name:
            self.name_label = Label(
                text=character_name,
                font_name=GAME_FONT,
                font_size=cfg["name_font_size"],
                color=cfg["name_color"],
                size_hint=(1, None),
                height=cfg["name_height"],
                pos_hint={'center_x': 0.5, 'top': 1 - (cfg["top_padding"] / cfg["box_height"])},
                halign='center',
                valign='middle'
            )
            self.name_label.bind(size=self.name_label.setter('text_size'))
            bg_widget.add_widget(self.name_label)

        # 4. ข้อความคุย
        text_top_ratio = (cfg["top_padding"] + cfg["name_height"] + cfg["msg_margin_top"]) / cfg["box_height"]
        
        self.dialogue_text = Label(
            text=dialogue,
            font_name=GAME_FONT,
            font_size=cfg["msg_font_size"],
            color=cfg["msg_color"],
            size_hint=(1, None),
            height=cfg["box_height"] * (1 - text_top_ratio) - 10,
            pos_hint={'center_x': 0.5, 'top': 1 - text_top_ratio},
            halign='center',
            valign='top'
        )
        
        def update_msg_text_size(instance, value):
            instance.text_size = (instance.width - (cfg["side_padding"] * 2), instance.height)
        self.dialogue_text.bind(size=update_msg_text_size)
        bg_widget.add_widget(self.dialogue_text)

        # 5. Choices (ปุ่มเลือก)
        if choices:
            draw_choice_buttons(self.game, choices)

        self.game.is_dialogue_active = True

    def close_dialogue(self):
        """ปิดกล่องข้อความคุย"""
        if self.dialogue_bg:
            if self.dialogue_bg.parent:
                self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None
            
        self.dialogue_text = None
        self.name_label = None
        clear_choices(self.game)

    def show_item_discovery(self, text, image_path=None):
        """แสดงแจ้งเตือนการได้รับไอเทมกลางหน้าจอ"""
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        
        notif_banner = FloatLayout(size_hint=(1, 0.3), pos_hint={'center_x': 0.5, 'center_y': 0.55})
        
        with notif_banner.canvas.before:
            Color(0, 0, 0, 0.75)
            banner_rect = Rectangle(size=notif_banner.size, pos=notif_banner.pos)
            Color(1, 1, 1, 0.1)
            line_top = Line(points=[0, 0, 0, 0], width=1)
            line_bottom = Line(points=[0, 0, 0, 0], width=1)
            
        def update_banner(instance, value):
            banner_rect.pos = instance.pos
            banner_rect.size = instance.size
            line_top.points = [instance.x, instance.top, instance.right, instance.top]
            line_bottom.points = [instance.x, instance.y, instance.right, instance.y]
        notif_banner.bind(size=update_banner, pos=update_banner)
        
        text_label = Label(
            text="FIND",
            font_name=GAME_FONT,
            font_size=36,
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=40,
            pos_hint={'center_x': 0.5, 'center_y': 0.78},
            bold=True
        )

        item_size = 100
        item_box = Widget(size_hint=(None, None), size=(item_size, item_size), 
                         pos_hint={'center_x': 0.5, 'center_y': 0.33})
        
        with item_box.canvas:
            Color(1, 1, 1, 0.15)
            glow_rect = Ellipse(size=(item_size*1.6, item_size*1.6))
            Color(1, 1, 1, 1)
            item_icon_rect = Rectangle(size=(item_size, item_size))
            
        def update_item_pos(instance, value):
            glow_rect.pos = (instance.center_x - (item_size*0.8), instance.center_y - (item_size*0.8))
            item_icon_rect.pos = instance.pos
        item_box.bind(pos=update_item_pos, size=update_item_pos)
        
        notif_banner.add_widget(text_label)
        notif_banner.add_widget(item_box)
        root.add_widget(notif_banner)
        
        def remove_notif(dt):
            if notif_banner.parent:
                notif_banner.parent.remove_widget(notif_banner)
        Clock.schedule_once(remove_notif, 2.0)
