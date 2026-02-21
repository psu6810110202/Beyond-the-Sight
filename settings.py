# Window Settings
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
FPS = 60
TITLE = "Beyond the Sight"

# Camera Settings
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

# Player Settings
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32

# Tile Settings
TILE_SIZE = 32
WALK_SPEED = 2   # ความเร็วเดินปกติ
RUN_SPEED = 4    # ความเร็วตอนวิ่ง (ต้องหาร TILE_SIZE ลงตัวจะดีที่สุด)

# Stamina
MAX_STAMINA = 100
STAMINA_DRAIN = MAX_STAMINA / (8 * FPS)  # ใช้เวลา 8 วินาทีจนกว่า Stamina จะหมด
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
REAPER_WIDTH = 20
REAPER_HEIGHT = 40
REAPER_SPEED = 1.5
SAFE_ZONE_RADIUS = 80
REAPER_DETECTION_RADIUS = 150