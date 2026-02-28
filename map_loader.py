import json
import base64
import zlib
import struct
import os
import xml.etree.ElementTree as ET
from kivy.graphics import Color, Rectangle, InstructionGroup, Mesh
from kivy.core.image import Image as CoreImage
from settings import TILE_SIZE, CAMERA_WIDTH, CAMERA_HEIGHT

FLIPPED_HORIZONTALLY_FLAG = 0x80000000
FLIPPED_VERTICALLY_FLAG   = 0x40000000
FLIPPED_DIAGONALLY_FLAG   = 0x20000000
ALL_FLAGS = FLIPPED_HORIZONTALLY_FLAG | FLIPPED_VERTICALLY_FLAG | FLIPPED_DIAGONALLY_FLAG

class KivyTiledMap:
    def __init__(self, filename):
        self.filename = filename
        self.map_dir = os.path.dirname(filename)
        self.map_data = {}
        self.tilesets = []
        self.textures = {}  # Map gid to texture
        self.core_images = [] # Prevent garbage collection of loaded images
        self.map_group = InstructionGroup()
        
        # Load JSON map
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.map_data = json.load(f)
        except Exception as e:
            print(f"Failed to load map {filename}: {e}")
            return
            
        self.width = self.map_data.get('width', 0)
        self.height = self.map_data.get('height', 0)
        self.tile_w = self.map_data.get('tilewidth', 16)
        self.tile_h = self.map_data.get('tileheight', 16)
        
        # Load tilesets and build meshes
        self.load_tilesets()
        self._build_meshes()
        
    def load_tilesets(self):
        for ts_info in self.map_data.get('tilesets', []):
            firstgid = ts_info.get('firstgid', 1)
            source = ts_info.get('source')
            if not source:
                continue
                
            # Search for the tsx file in the map directory and subdirectories
            # The user explicitly requested to read from the .tsx directory
            tsx_name = os.path.basename(source)
            tsx_path = os.path.join(self.map_dir, '.tsx', tsx_name)
            
            if not os.path.exists(tsx_path):
                tsx_path = self.find_file(source, self.map_dir)
            
            if not tsx_path or not os.path.exists(tsx_path):
                print(f"Warning: Tileset file '{source}' not found. Please ensure .tsx and image files are present in assets/Tiles/!")
                continue
                
            try:
                tree = ET.parse(tsx_path)
                root = tree.getroot()
                
                image_element = root.find('image')
                if image_element is None:
                    continue
                    
                image_source = image_element.get('source')
                
                # Search for the image file
                # Prioritize prop directory for images
                image_name = os.path.basename(image_source)
                image_path = os.path.join(self.map_dir, 'prop', image_name)
                
                if not os.path.exists(image_path):
                    image_path = self.find_file(image_source, self.map_dir)
                
                if not image_path or not os.path.exists(image_path):
                    print(f"Warning: Image file '{image_source}' not found. Map will be missing textures.")
                    continue
                
                tile_w = int(root.get('tilewidth', self.tile_w))
                tile_h = int(root.get('tileheight', self.tile_h))
                columns = int(root.get('columns', 1))
                tilecount = int(root.get('tilecount', 0))
                margin = int(root.get('margin', 0))
                spacing = int(root.get('spacing', 0))
                
                # Load image texture
                core_image = CoreImage(image_path)
                self.core_images.append(core_image) # Keep reference so it doesn't get destroyed
                tex = core_image.texture
                # Crisp pixel art scaling
                tex.mag_filter = 'nearest'
                tex.min_filter = 'nearest'
                
                # Small padding to prevent visible bleeding gaps (anti-pixel bleeding)
                pad_x = 0.05 / tex.width
                pad_y = 0.05 / tex.height
                
                for i in range(tilecount):
                    gid = firstgid + i
                    col = i % columns
                    row = i // columns
                    
                    x = margin + col * (tile_w + spacing)
                    y = margin + row * (tile_h + spacing)
                    
                    # Convert Tiled (Y-down) to Kivy Texture origin (Y-up)
                    # Use actual image height for inversion, not the potentially padded tex.height
                    inv_y = core_image.height - y - tile_h
                    
                    # Let Kivy calculate the actual UV coordinates safely (handles textures padded to Power-Of-Two naturally)
                    region = tex.get_region(x, inv_y, tile_w, tile_h)
                    
                    # region.tex_coords format: (u0,v0, u1,v0, u1,v1, u0,v1) for BL, BR, TR, TL
                    u0 = region.tex_coords[0]
                    v0 = region.tex_coords[1]
                    u1 = region.tex_coords[4]
                    v1 = region.tex_coords[5]
                    
                    # Apply anti-bleeding padding
                    u0_pad = u0 + pad_x
                    v0_pad = v0 + pad_y
                    u1_pad = u1 - pad_x
                    v1_pad = v1 - pad_y
                    
                    # Store as tuple: (atlas texture, [BL_u, BL_v, TR_u, TR_v], specific_tile_w, specific_tile_h, x, inv_y)
                    # We store just the corners, and calculate others during draw
                    self.textures[gid] = (tex, (u0_pad, v0_pad, u1_pad, v1_pad), tile_w, tile_h, x, inv_y)
                            
            except Exception as e:
                print(f"Error loading tileset {tsx_path}: {e}")
                
        # Prepare mesh groups once
        self.bg_group = InstructionGroup()
        self.fg_group = InstructionGroup()

        
    def find_file(self, filename, search_dir):
        # Check if absolute path directly exists
        if os.path.exists(filename):
            return filename
            
        # Recursively search for a file in a given directory
        lookup_name = os.path.basename(filename)
        for root, dirs, files in os.walk(search_dir):
            if lookup_name in files:
                return os.path.join(root, lookup_name)
        return None
        
    def draw_background(self, canvas):
        canvas.add(self.bg_group)
        
    def draw_foreground(self, canvas):
        canvas.add(self.fg_group)

    def _build_meshes(self):
        self.bg_group.clear()
        self.fg_group.clear()
        self.chunk_groups_bg = {}
        self.chunk_groups_fg = {}
        self.visible_chunks = set()
        
        CHUNK_SIZE = 16
        chunk_world_size = TILE_SIZE * CHUNK_SIZE
        
        scale = TILE_SIZE / self.tile_w
        
        chunk_data_bg = {}
        chunk_data_fg = {}
        
        for layer in self.map_data.get('layers', []):
            layer_type = layer.get('type')
            if layer_type not in ('tilelayer', 'objectgroup') or not layer.get('visible', True):
                continue
                
            layer_name = layer.get('name', '')
            # Determine if this layer is foreground (e.g. "หลังคา", "หลังคา2 ชั้น", etc)
            is_foreground = ("หลังคา" in layer_name or layer_name.lower().startswith("roof"))
            
            instances = []
            
            if layer_type == 'tilelayer':
                data = layer.get('data')
                encoding = layer.get('encoding')
                compression = layer.get('compression')
                
                width = layer.get('width', self.width)
                height = layer.get('height', self.height)
                
                tiles = []
                if encoding == 'base64':
                    try:
                        decoded = base64.b64decode(data)
                        if compression == 'zlib':
                            decompressed = zlib.decompress(decoded)
                        elif compression == 'gzip':
                            import gzip
                            decompressed = gzip.decompress(decoded)
                        else:
                            decompressed = decoded
                            
                        format_str = f"<{width * height}I"
                        tiles = struct.unpack(format_str, decompressed)
                    except Exception as e:
                        print(f"Error parsing layer {layer.get('name')}: {e}")
                        continue
                elif type(data) is list:
                    tiles = data
                else:
                    continue
                
                for i, global_id in enumerate(tiles):
                    if global_id == 0:
                        continue
                    col = i % width
                    row = i // width
                    x = col * self.tile_w * scale
                    y = (height - 1 - row) * self.tile_h * scale
                    instances.append((global_id, x, y, None, None))
                    
            elif layer_type == 'objectgroup':
                total_height_px = self.height * self.tile_h
                for obj in layer.get('objects', []):
                    global_id = obj.get('gid', 0)
                    if global_id == 0:
                        continue
                    px = obj.get('x', 0)
                    py = obj.get('y', 0)
                    x = px * scale
                    y = (total_height_px - py) * scale
                    pw = obj.get('width')
                    ph = obj.get('height')
                    w = pw * scale if pw is not None else None
                    h = ph * scale if ph is not None else None
                    instances.append((global_id, x, y, w, h))
            
            # We will group tiles in this layer by chunk
            layer_chunk_meshes = {} # (cx, cy) -> {tex: {'vertices': [], 'indices': []}}
            
            for global_id, x, y, custom_w, custom_h in instances:
                gid = global_id & ~ALL_FLAGS
                flip_h = bool(global_id & FLIPPED_HORIZONTALLY_FLAG)
                flip_v = bool(global_id & FLIPPED_VERTICALLY_FLAG)
                flip_d = bool(global_id & FLIPPED_DIAGONALLY_FLAG)
                
                tex_data = self.textures.get(gid)
                if not tex_data:
                    continue
                
                # Fetch raw atlas, base padded UVs, and actual size of this specific tile
                tex, base_uvs, ts_tile_w, ts_tile_h, tex_x, tex_inv_y = tex_data
                
                cx = int(x // chunk_world_size)
                cy = int(y // chunk_world_size)
                
                # Check if this is a custom-sized object differing from the tileset's standard tile size
                obj_px_w = int(custom_w / scale) if custom_w is not None else ts_tile_w
                obj_px_h = int(custom_h / scale) if custom_h is not None else ts_tile_h
                
                w = obj_px_w * scale
                h = obj_px_h * scale
                
                if obj_px_w != ts_tile_w or obj_px_h != ts_tile_h:
                    # The user placed a 64x64 component from a 16x16 tileset. Extract the larger UV region securely.
                    new_inv_y = tex_inv_y + ts_tile_h - obj_px_h
                    region = tex.get_region(tex_x, new_inv_y, obj_px_w, obj_px_h)
                    
                    pad_x = 0.05 / tex.width
                    pad_y = 0.05 / tex.height
                    
                    u0 = region.tex_coords[0] + pad_x
                    v0 = region.tex_coords[1] + pad_y
                    u1 = region.tex_coords[4] - pad_x
                    v1 = region.tex_coords[5] - pad_y
                    
                    obj_uvs = (u0, v0, u1, v1)
                else:
                    obj_uvs = base_uvs
                
                # Extrapolate full UV corners mapped to Tiled flip requests
                u0, v0, u1, v1 = obj_uvs
                if flip_h: u0, u1 = u1, u0
                if flip_v: v0, v1 = v1, v0
                
                if flip_d:
                    uvs = [u1, v0, u1, v1, u0, v1, u0, v0]
                else:
                    uvs = [u0, v0, u1, v0, u1, v1, u0, v1]
                
                # Vertices for this quad (format: x,y, u,v)
                verts = [
                    x, y, uvs[0], uvs[1],
                    x + w, y, uvs[2], uvs[3],
                    x + w, y + h, uvs[4], uvs[5],
                    x, y + h, uvs[6], uvs[7]
                ]
                
                if (cx, cy) not in layer_chunk_meshes:
                    layer_chunk_meshes[(cx, cy)] = {}
                    
                if tex not in layer_chunk_meshes[(cx, cy)]:
                    layer_chunk_meshes[(cx, cy)][tex] = {'vertices': [], 'indices': []}
                    
                mesh_data = layer_chunk_meshes[(cx, cy)][tex]
                idx_offset = len(mesh_data['vertices']) // 4
                
                mesh_data['vertices'].extend(verts)
                mesh_data['indices'].extend([
                    idx_offset, idx_offset + 1, idx_offset + 2,
                    idx_offset + 2, idx_offset + 3, idx_offset
                ])
                
            opacity = layer.get('opacity', 1.0)
            target_dict = chunk_data_fg if is_foreground else chunk_data_bg
            
            for chunk_coord, tex_dict in layer_chunk_meshes.items():
                if chunk_coord not in target_dict:
                    target_dict[chunk_coord] = []
                target_dict[chunk_coord].append((opacity, tex_dict))
                
        # Now construct the Kivy InstructionGroups for each chunk
        for chunk_coord, layers in chunk_data_bg.items():
            grp = InstructionGroup()
            for opacity, tex_dict in layers:
                grp.add(Color(1, 1, 1, opacity))
                for tex, mesh_data in tex_dict.items():
                    grp.add(Mesh(
                        vertices=mesh_data['vertices'],
                        indices=mesh_data['indices'],
                        fmt=[(b'vPosition', 2, 'float'), (b'vTexCoords0', 2, 'float')],
                        texture=tex,
                        mode='triangles'
                    ))
            self.chunk_groups_bg[chunk_coord] = grp
            
        for chunk_coord, layers in chunk_data_fg.items():
            grp = InstructionGroup()
            for opacity, tex_dict in layers:
                grp.add(Color(1, 1, 1, opacity))
                for tex, mesh_data in tex_dict.items():
                    grp.add(Mesh(
                        vertices=mesh_data['vertices'],
                        indices=mesh_data['indices'],
                        fmt=[(b'vPosition', 2, 'float'), (b'vTexCoords0', 2, 'float')],
                        texture=tex,
                        mode='triangles'
                    ))
            self.chunk_groups_fg[chunk_coord] = grp

    def update_chunks(self, cam_x, cam_y):
        CHUNK_SIZE = 16
        chunk_world_size = TILE_SIZE * CHUNK_SIZE
        
        # Define the viewport area bounds
        # Expand bounds massively (+1000 on each side) to prevent clipping or black borders 
        # caused by widescreen scaling or zooming
        min_x = cam_x - 1000
        max_x = cam_x + 1000
        min_y = cam_y - 1000
        max_y = cam_y + 1000
        
        # Use integer division (//) to properly round down negative coordinates
        cx_min = int(min_x // chunk_world_size)
        cx_max = int(max_x // chunk_world_size)
        cy_min = int(min_y // chunk_world_size)
        cy_max = int(max_y // chunk_world_size)
        
        new_visible = set()
        for cx in range(cx_min, cx_max + 1):
            for cy in range(cy_min, cy_max + 1):
                new_visible.add((cx, cy))
                
        # Detach old chunks
        for chunk in self.visible_chunks - new_visible:
            if chunk in self.chunk_groups_bg:
                self.bg_group.remove(self.chunk_groups_bg[chunk])
            if chunk in self.chunk_groups_fg:
                self.fg_group.remove(self.chunk_groups_fg[chunk])
                
        # Attach new chunks
        for chunk in new_visible - self.visible_chunks:
            if chunk in self.chunk_groups_bg:
                self.bg_group.add(self.chunk_groups_bg[chunk])
            if chunk in self.chunk_groups_fg:
                self.fg_group.add(self.chunk_groups_fg[chunk])
                
        self.visible_chunks = new_visible

