# Window Settings
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
FPS = 60
TITLE = "Beyond the Sight"

# Camera Settings
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

# กรอบภาพตัวละครดั้งเดิมเป็น 1:1 (จตุรัส) แก้ขนาดให้ใหญ่ขึ้นเป็น 64x64 
# ภาพจะไม่ยืด และเมื่อวางกึ่งกลาง จะทำให้ตัวละครจริงๆ มีขนาดเหมาะสมกับพื้น 32พอดี
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32

# Tile Settings
TILE_SIZE = 16
WALK_SPEED = 2   # ความเร็วเดินปกติ
RUN_SPEED = 4    # ความเร็วตอนวิ่ง (ต้องหาร TILE_SIZE ลงตัวจะดีที่สุด)

# Stamina
MAX_STAMINA = 100
STAMINA_DRAIN = MAX_STAMINA / (4 * FPS)  # ใช้เวลา 4 วินาทีจนกว่า Stamina จะหมด
STAMINA_REGEN = MAX_STAMINA / (5 * FPS)  # ใช้เวลา 5 วินาทีในการฟื้นฟูจนเต็ม

# NPC Settings
NPC_WIDTH = 64
NPC_HEIGHT = 64
NPC_SPEED = 1
NPC_COUNT = 5

# NPC Sprite Settings
NPC_SPRITE_WIDTH = 32
NPC_SPRITE_HEIGHT = 48
NPC_ANIMATION_SPEED = 0.2

# Reaper Settings
REAPER_WIDTH = 80
REAPER_HEIGHT = 64
REAPER_SPEED = 1.5
SAFE_ZONE_RADIUS = 80
REAPER_DETECTION_RADIUS = 150

# Enemy Settings
ENEMY_WIDTH = 32
ENEMY_HEIGHT = 32
ENEMY_SPEED = WALK_SPEED
ENEMY_DETECTION_RADIUS = 200
ENEMY_SAFE_ZONE_RADIUS = 150  # รัศมี safe zone สำหรับ enemy ไม่สามารถเข้ามาได้