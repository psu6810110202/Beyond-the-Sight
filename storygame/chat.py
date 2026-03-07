# storygame/chat.py

# ข้อความคุยของ NPC ต่างๆ ในเกม
NPC_DIALOGUES = {
    "The Sad Soul": [
        "......",
        "It's...it's gone. Everything is broken.",
        "My friend...someone took the pieces away. I can't find them in the dark.",
        "Please...it's so cold here...could you help me find them?"
    ],
    "The Postman": [
        "Oh dear... oh dear. This fog is a nightmare.",
        "I have all these letters to deliver, but I can't even see the doors anymore.",
        "I think I dropped some of them near the old well while I was trying to find my way.",
        "Could you help me? If you find the letters, please place them in front of the houses with the blue lanterns."
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

# ข้อความบทนำแยกตามวัน (Intro Dialogues for Day 1-5)
INTRO_DIALOGUES = {
    1: [
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
    ],
    2: [
        "Are you awake? You look like you'd prefer to sleep a little longer today.",
        "The alley is as noisy as ever, but do you see that well over there?",
        "There's a postman standing there who can't seem to finish his last job.",
        "He looks quite confused and lost; maybe you should go see if he's alright.",
        "It looks like he's just waiting for someone to lend him a hand.",
        "Don't forget, the blue stone you have... keep a firm grip on it. Its light will protect you.",
        "The alleys around here are quite a maze. Don't let the darkness trick you into losing your way.",
        "Don't worry. I'll be right here, quietly watching over you as I always do.",
        "If anything happens or if you feel unsafe, just run back to me.",
        "Go on then... Do your best."
    ],
    3: [
        "Are you awake? You look even more tired than yesterday.",
        "The alley is as noisy as ever, but do you see those deep alleys on the far left?",
        "There's an old soul lost inside... He looks frightened, as if he can't find his way home.",
        "His memories have all faded, leaving only a lingering sadness behind.",
        "Try to make your way over to him... perhaps the sound of your voice can help him remember something.",
        "Keep a firm grip on your blue stone, just like before. Its light should make you feel a bit safer in the dark.",
        "Remember that these alleys are a maze and can play tricks on you. Don't let the darkness lead you astray.",
        "Be careful... the darkness in those alleys moves. Don't let it catch up to you.",
        "I'll be waiting right here at this corner, quietly watching over you. Run back if it's too much.",
        "Go on then... I'm rooting for you."
    ],
    4: [
        "Are you awake? It looks like it was harder for you to get up today.",
        "The alley is as noisy and crowded as ever, but there’s a strange dullness hanging over that building.",
        "Do you see that woman sitting by the window over there? She's so still... it's as if time has stopped for her.",
        "Maybe she's just waiting for something she lost a long time ago.",
        "Why don't you go and see her? Perhaps your kindness can make her frozen time move once again.",
        "Keep a firm grip on that blue stone. The shadows today seem like they're constantly watching for a chance to strike.",
        "Don't let all this chaos lead you astray; the paths in these slums can change the moment you look away.",
        "I'll be standing right here, watching over you from a distance as I always do.",
        "If anything feels wrong or if it becomes too much, just run back to me.",
        "Go on then... I'm rooting for you."
    ],
    5: [
        "Are you awake? You look more exhausted today than ever before.",
        "The alley is as noisy as ever, but do you see that sewer entrance just a few steps away from you?",
        "There's a soul waiting for you down there; he's so faint you can barely see his shape.",
        "It seems he's been trapped in that darkness for so long, he's almost faded away completely.",
        "Why don't you go down and find him? Perhaps he's just waiting for someone to speak to.",
        "Keep a firm grip on your blue stone. In such a damp place, its light will be vital.",
        "The tunnels down there are narrow and confusing; don't let the darkness trick you into losing your way.",
        "I'll be waiting right here at this corner, watching over you from a distance. Don't be afraid.",
        "If anything goes wrong or if it becomes too much, just run back to me.",
        "Go on then. Stay safe."
    ]
}

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
