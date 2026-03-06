# storygame/chat.py

# ข้อความคุยของ NPC ต่างๆ ในเกม
NPC_DIALOGUES = {
    "The Sad Soul": [
        "......",
        "It's...it's gone. Everything is broken.",
        "My friend...someone took the pieces away. I can't find them in the dark.",
        "Please...it's so cold here...could you help me find them?"
    ],
    "NPC2": [
        "โอ้... ทุกอย่างดูมืดมน",
        "ฉันรู้สึกหนาว... ช่วยฉันด้วย",
        "ไม่เคยคิดว่าจะมาถึงที่แห่งนี้"
    ],
    "NPC3": [
        "คุณมาจากไหนกัน?",
        "ที่นี่มีเรื่องลึกลับมากมาย",
        "ระวังศัตรูให้ดีๆ นะ"
    ],
    "NPC4": [
        "ฉันกำลังมองหาทางออก...",
        "คุณเห็นทางออกไหม?",
        "อย่าทอดทิ้งฉัน!"
    ],
    "NPC5": [
        "เราต้องร่วมมือกัน",
        "มีอะไรแปลกๆ เกิดขึ้นที่นี่",
        "เราจะผ่านไปได้แน่ๆ"
    ]
}

# ข้อความคุยของ Reaper (จะถูกสุ่มเลือก)
REAPER_DIALOGUES = [
    "Rest for a while? I'll keep watch.",
    "Don't worry, I'll protect you.",
    "You're doing great! Keep it up.",
    "I'm always here for you.",
    "You're not alone.",
    "I'll be waiting."
]

# ข้อความตอนตาย
REAPER_DEATH_QUOTES = [
    "Open your eyes. You're safe now.",
    "Wake up. Don't let the cold settle in your bones.",
    "Stay alert. The shadows feed on those who linger too long."
]

# ข้อความบทนำ (Day 1 Intro)
INTRO_DIALOGUE = [
    "Oh, you're up?",
    "I've been waiting for you. It's a bit of a gloomy afternoon, isn't it?",
    "Anyway, I have a favor to ask. Deep in the alley, there's a child sitting by the trash.",
    "The poor kid's heart is broken because of a lost doll. Could you go and talk to them?",
    "Just follow the path to the left and keep going until you see them.",
    "Here, take this [Blue Stone] with you. You're going to need it.",
    "The shadows in these alleys can be... unfriendly. If something tries to get too close, use the stone.",
    "The light will stun them for a moment. That's your chance to run.",
    "If you're in trouble, just run back to me. I'll take care of the rest.",
    "Be careful, alright?"
]

# ข้อความเตือนเมื่อเดินไปพิกัดอันตราย (Day 1)
WARNING_DIALOGUE = [
    "Are you sure you want to go? It's pretty dangerous in there."
]
WARNING_CHOICES = ["I'll go", "Ok"]

# ข้อความสอนวิธีใช้ของ (Tutorial)
TUTORIAL_DIALOGUE = [
    "Look! There are shadows wandering around this area.",
    "Try using the [Blue Stone] I gave you by pressing the [Q] key.",
    "It will emit a flash that stuns any nearby shadows for a short moment.",
    "But be careful, the light takes about 15 seconds to recharge after each use.",
    "Use it wisely to escape if they get too close!"
]

# --- UI Settings สำหรับกล่องข้อความ ---
DIALOGUE_CONFIG = {
    "box_height": 180,
    "box_y": 0,
    "top_padding": 35,       # ระยะห่างจากขอบบนสุดของแถบดำถึงชื่อ
    "name_height": 45,
    "msg_margin_top": 20,    # ระยะห่างระหว่างชื่อและข้อความคุย
    "side_padding": 60,
    "name_font_size": 36,
    "msg_font_size": 28,
    "name_color": (1, 1, 0, 1), # สีเหลือง
    "msg_color": (1, 1, 1, 1),  # สีขาว
    "bg_opacity": 0.85
}
