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
        "Who's there?... Oh, it's just a child.",
        "Please, help me... I have these letters, and the seals on them are clear enough to read.",
        "But these alleys are like a maze... I've been walking in circles and simply cannot find the houses.",
        "If you know your way around these slums... please switch the letters back to where they belong.",
        "There are still letters left in this bag... Look at the covers; the symbols aren't hard to see at all.",
        "Go on, little one... I'm counting on you."
    ],
    "The Old Soul": [
        "I... I can't find my way home. Everything looks the same in this alley.",
        "I only remember a few things from my house. The red flowers in the vase...",
        "The old blue rug in the hallway... and the yellow sunlight that hit the porch every afternoon.",
        "If I could see those colors again, maybe I could find the door. Can you help me?"
    ],
    "The Lady at the Window": [
        "It's so quiet... the music box stopped, and the melody went with it.",
        "I think I dropped the key somewhere near the trash and those old rags. Everything is such a mess...",
        "Could you find it? I just want to hear that song one more time."
    ],
    "The Soul": [
        "I'm fading... I can't even feel my own shape anymore.",
        "Could you find the sparks hidden under those piles for the lantern?",
        "I don't want to disappear in this cold."
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
        "Here, take this [Blue Stone] with you. ",
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
        "Are you awake? You look even more tired than yesterday.", #
        "The alley is as noisy as ever, but do you see those deep alleys on the far left?", #
        "There's an old soul lost inside... He looks frightened, as if he can't find his way home.", #
        "Try to make your way over to him... perhaps the sound of your voice can help him remember something.", #
        "Take this lantern. You'll need it to light the candles along the way. As for your blue stone, keep it ready to stun anything that gets too close.", #
        "Remember that these alleys are a maze and can play tricks on you. Don't let the darkness lead you astray.", #
        "Be careful... the darkness in those alleys moves. Don't let it catch up to you.", #
        "I'll be waiting right here at this corner, quietly watching over you. Run back if it's too much.", #
        "Go on then... I'm rooting for you."
    ],
    4: [
        "Are you awake? It looks like it was harder for you to get up today.",
        "The alley is as noisy and crowded as ever, but there's a strange dullness hanging over that building.",
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

# เควสเทียน Day 3
CANDLE_LIGHT_DIALOGUE = "The candle is unlit. Which color should I light it with?"
CANDLE_LIGHT_CHOICES = ["RED", "YELLOW", "BLUE"]
CANDLE_SUCCESS_DIALOGUE = "All the candles are lit now. I should go back and tell the old soul."
OLD_SOUL_SUCCESS = "The light... it's back. I remember the way home now. Thank you, child. I don't think I'll get lost again."
OLD_SOUL_FAIL = "No... that's not it. Everything is getting blurry again."

ANGEL_DAY3_SUCCESS = [
    "That makes three souls now... You've done so well.",
    "But look at you, your body seems so exhausted.",
    "Those bruises... your parents did this to you again, didn't they?",
    "Hang in there. The light is almost here."
]

ANGEL_DAY3_FAIL = [
    "Your heart is starting to darken, little one...",
    "I wish I could help you more, but this is all we can do today.",
    "Go back and hide in your safe corner for now."
]


# --- ฉกาจบวัน (End of Day Dialogues) ---
DAY_END_DIALOGUES = {
    1: {
        "success": [
            "You still hold the light in your hands, little one...",
            "Though this place is shrouded in darkness, your kindness has saved that soul.",
            "Go and rest now. You will need your strength for tomorrow."
        ],
        "fail": [
            "Your hands are trembling... It’s alright.",
            "Sometimes, destiny is too heavy for a child to carry alone.",
            "Let’s go home for now. We can always start again tomorrow."
        ]
    },
    2: {
        "success": [
            "Heh... keep playing the hero, kid.",
            "You can save a ghost, but the humans lurking behind you? They haven't changed a bit.",
            "But fine, I'll give it to you—you did well today.",
            "Now, get back home before those people start getting suspicious."
        ],
        "fail": [
            "See that? In the end, you can't save anyone—not even yourself.",
            "But don't you go crying now; this wretched world has always been this way.",
            "Come here, let me escort you back to that hell you call 'home' yourself."
        ]
    },
    4: {
        "success": [
            "Heh... You're one stubborn brat. Being called a jinx like that and you still go around helping others?",
            "Fine, fine... I'll stop scolding you. Get inside already.",
            "Those humans seem to be in a foul mood today. I'll shroud your shadow for you."
        ],
        "fail": [
            "Good grief! Stop looking like it's the end of the world. You're no god, kid—you can't save everyone.",
            "A mistake is just a mistake. Go back to sleep.",
            "We'll try again tomorrow... if you even wake up, that is."
        ]
    },
    5: {
        "perfect": {
            "char": ["Angel", "Devil"],
            "text": [
                "The breeze is lovely today... It’s time for you to head back there, little one.",
                "Well... what are you staring at me for? Go on, get back. I’ll be in the same spot tomorrow... assuming you still want to see me, that is."
            ]
        },
        "middle": {
            "char": ["Devil", "Angel"],
            "text": [
                "Your shadow stretches all the way to the main road out there, kid... Do you think a place like that has any room for someone like you?",
                "Sometimes getting lost is the first step toward finding your true home... May your heart lead you to a place where no one can ever hurt you again."
            ]
        },
        "failure": {
            "char": ["Devil", "Angel"],
            "text": [
                "Look at you, kid... you’re stumbling so much you’re practically walking into walls. Just go back and get some rest tonight. Keep the lights off, and don't you dare turn them back on.",
                "Don’t be afraid, little one... the darkness isn’t always something to be feared. Sometimes, it’s the only shield left to protect you from the pain of everything you see."
            ]
        }
    }
}

# --- บทสนทนาพ่อแม่ทะเลาะกัน Day 2 ---
PARENT_FIGHT_DIALOGUE = [
    {"char": "Father", "text": "Still... you're still glaring at me with those eyes?! I told you—if you're stepping foot into this house, don't you ever dare look at me with that curse!"},
    {"char": "Mother", "text": "Stop it, husband... don't touch him too much. I don't want whatever 'curse' he sees in those eyes rubbing off on your hands. Just living under the same roof as this demon is enough to drive me insane!"},
    {"char": "Father", "text": "What are you looking at?! Is there some spirit standing behind me now? You're nothing but my own flesh and blood that I regret ever fathering—a total jinx! Talking to the air like a madman! You’ve become a blight, dragging our family down for the whole neighborhood to mock!"},
    {"char": "Mother", "text": "I'm dying of shame... Our lives were finally turning around, but then we ended up with a freak like you who does nothing but see ghosts! I truly wish I could announce to everyone that I have no such disgusting child!"},
    {"char": "Father", "text": "You're getting nothing to eat today! Since you love those spirits so much, go beg them for scraps yourself! I don't care if you starve or rot, just don't you dare bring more shame to my name with your wretched behavior!"},
    {"char": "Mother", "text": "Go rot in your dark corner! If I see you whispering to yourself or staring at anyone with those creepy eyes again... I'll be the one to gouge them out of your head myself, forever!"}
]

# --- ข้อความในแมพใต้ดิน ---
UNDERGROUND_STRINGS = {
    "found_soul": "I found a fragment of the soul!",
    "found_dust": "Nothing here but dust...",
    "ghost_scare": "LEAVE THIS PLACE...",
    "interact_prompt": "I found one of those objects... should I search inside?"
}

# --- ข้อความการค้นหา Day 1 (Search Dialogues) ---
SEARCH_DIALOGUES_HOME = {
    "empty": "Empty... they never leave anything for me anyway.",
    "found": "Found it. This will keep me going tonight.",
    "nothing": "Just dust and old rags. There's nothing to eat here."
}

NPC5_SUCCESS = [
    "I can feel it... my soul is whole again.",
    "The cold is finally fading away. Thank you, little one.",
    "You have a kindness that this world has forgotten."
]
NPC5_FAIL = [
    "Wait... these fragments... they don't belong to me.",
    "My essence is still scattered... I feel even emptier than before."
]

ENDING_TITLES = {
    1: "Ending 1/4 :\n\nSuccumb",
    2: "Bad Ending 2/4 :\n\nThe Silent Eternal Darkness",
    3: "Normal Ending 3/4 :\n\nFreedom on a Lonely Road",
    4: "True Ending 4/4 :\n\nThe Guide to a New Home"
}
