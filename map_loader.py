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
        self.solid_rects = []
        self.well_fg_gids = set()
        self.well_solid_gids = set()
        
        # Prepare mesh groups once
        self.bg_group = InstructionGroup()
        self.fg_group = InstructionGroup()
        
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
                
                self.setup_well(tsx_name, firstgid, columns, tilecount)
                
                # Load image texture
                core_image = CoreImage(image_path)
                self.core_images.append(core_image) # Keep reference so it doesn't get destroyed
                tex = core_image.texture
                # Crisp pixel art scaling
                tex.mag_filter = 'nearest'
                tex.min_filter = 'nearest'
                
                # Small padding to prevent visible bleeding gaps (anti-pixel bleeding)
                pad_x, pad_y = self._get_uv_padding(tex)
                
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
    def _get_uv_padding(self, tex):
        """Calculate small padding to prevent visible bleeding gaps."""
        return 0.05 / tex.width, 0.05 / tex.height

    def setup_well(self, tsx_name, firstgid, columns, tilecount):
        if "Well1" in tsx_name:
            well_cols = columns
            fg_row_limit = 1
            fg_end_index = firstgid + (well_cols * fg_row_limit)
            
            self.well_fg_gids.update(range(firstgid, fg_end_index))
            self.well_solid_gids.update(range(fg_end_index, firstgid + tilecount))
        
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
        self.solid_rects = [] # ล้างข้อมูล Hitbox เก่าออกให้หมดก่อนเริ่มสร้างใหม่
        
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
            # เลเยอร์ที่ต้องการให้มี hitbox (solid)
            # ใช้การตรวจสอบแบบแม่นยำขึ้น เพื่อไม่ให้ well2 หรือชื่ออื่นมาปน
            clean_name = layer_name.strip().lower()
            is_solid_layer = ("ผนังบ้าน" in clean_name)
            
            # เฉพาะเลเยอร์ "well1" เท่านั้นที่จะใช้ตรรกะแยกส่วนและ hitbox ของบ่อน้ำ
            is_well_layer = (clean_name == "well1")
            
            # Determine if this layer is foreground (e.g. "หลังคา", "หลังคา2 ชั้น", etc)
            is_foreground = ("หลังคา" in layer_name or "หลังคา2 ชั้น" in layer_name)
            
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
                    y = (height - 1 - row) * self.tile_h * scale # Kivy Y-up coordinate
                    
                    gid = global_id & ~ALL_FLAGS
                    
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
            layer_chunk_meshes_fg = {} # For tiles that should be foreground
            layer_chunk_meshes_bg = {} # For tiles that should be background
            
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
                
                # Decide if this specific tile is foreground or background
                is_tile_fg = False
                potential_well = is_well_layer and (gid in self.well_fg_gids or gid in self.well_solid_gids)
                
                if potential_well and (obj_px_w != ts_tile_w or obj_px_h != ts_tile_h):
                    # Special split for 'Well 1' if placed as a single large object
                    # We create two separate mesh entries: bottom (BG+Solid) and top (FG)
                    
                    # 1. Bottom Half (Background + Solid)
                    bh_px_h = int(obj_px_h * 0.75)
                    bh_h = bh_px_h * scale
                    bh_inv_y = tex_inv_y + ts_tile_h - bh_px_h
                    bh_region = tex.get_region(tex_x, bh_inv_y, obj_px_w, bh_px_h)
                    
                    pad_x, pad_y = self._get_uv_padding(tex)
                    bu0, bv0 = bh_region.tex_coords[0] + pad_x, bh_region.tex_coords[1] + pad_y
                    bu1, bv1 = bh_region.tex_coords[4] - pad_x, bh_region.tex_coords[5] - pad_y
                    
                    # Vertices for bottom half
                    b_verts = [
                        x, y, bu0, bv0,
                        x + w, y, bu1, bv0,
                        x + w, y + bh_h, bu1, bv1,
                        x, y + bh_h, bu0, bv1
                    ]
                    
                    # Add to BG meshes and Solid Rects
                    # Shrink hitbox slightly so player can get closer to the stones (natural feel)
                    hitbox_padding = 4 * scale
                    new_rect = [x + hitbox_padding, y, w - (hitbox_padding * 2), bh_h]
                    if new_rect not in self.solid_rects:
                        self.solid_rects.append(new_rect)
                    
                    self._add_to_mesh_data(layer_chunk_meshes_bg, cx, cy, tex, b_verts)
                    
                    # 2. Top Half (Foreground)
                    th_px_h = obj_px_h - bh_px_h
                    th_h = th_px_h * scale
                    th_y = y + bh_h
                    th_inv_y = bh_inv_y - th_px_h
                    th_region = tex.get_region(tex_x, th_inv_y, obj_px_w, th_px_h)
                    
                    tu0, tv0 = th_region.tex_coords[0] + pad_x, th_region.tex_coords[1] + pad_y
                    tu1, tv1 = th_region.tex_coords[4] - pad_x, th_region.tex_coords[5] - pad_y
                    
                    # Vertices for top half
                    t_verts = [
                        x, th_y, tu0, tv0,
                        x + w, th_y, tu1, tv0,
                        x + w, th_y + th_h, tu1, tv1,
                        x, th_y + th_h, tu0, tv1
                    ]
                    
                    # Add to FG meshes
                    self._add_to_mesh_data(layer_chunk_meshes_fg, cx, cy, tex, t_verts)
                    continue # Skip the standard processing since we've split it
                
                # Standard processing for single tiles or non-well objects
                if is_solid_layer:
                    new_rect = [x, y, w, h]
                    if new_rect not in self.solid_rects:
                        self.solid_rects.append(new_rect)
                elif is_well_layer and gid in self.well_solid_gids:
                    # In well1, even if it's not a large object (split above), we apply the solid check
                    new_rect = [x, y, w, h]
                    if new_rect not in self.solid_rects:
                        self.solid_rects.append(new_rect)
                
                if obj_px_w != ts_tile_w or obj_px_h != ts_tile_h:
                    # The user placed a 64x64 component from a 16x16 tileset. Extract the larger UV region securely.
                    new_inv_y = tex_inv_y + ts_tile_h - obj_px_h
                    region = tex.get_region(tex_x, new_inv_y, obj_px_w, obj_px_h)
                    
                    pad_x, pad_y = self._get_uv_padding(tex)
                    
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
                
                # Decide if this specific tile is foreground or background
                if gid in self.well_fg_gids:
                    is_tile_fg = True
                elif gid in self.well_solid_gids:
                    is_tile_fg = False
                else:
                    is_tile_fg = is_foreground
                
                target_meshes = layer_chunk_meshes_fg if is_tile_fg else layer_chunk_meshes_bg
                self._add_to_mesh_data(target_meshes, cx, cy, tex, verts)

            opacity = layer.get('opacity', 1.0)
            
            for chunk_coord, tex_dict in layer_chunk_meshes_fg.items():
                if chunk_coord not in chunk_data_fg:
                    chunk_data_fg[chunk_coord] = []
                chunk_data_fg[chunk_coord].append((opacity, tex_dict))
                
            for chunk_coord, tex_dict in layer_chunk_meshes_bg.items():
                if chunk_coord not in chunk_data_bg:
                    chunk_data_bg[chunk_coord] = []
                chunk_data_bg[chunk_coord].append((opacity, tex_dict))
                
        # Now construct the Kivy InstructionGroups for each chunk
        self.chunk_groups_bg = self._create_chunk_instruction_groups(chunk_data_bg)
        self.chunk_groups_fg = self._create_chunk_instruction_groups(chunk_data_fg)

    def _add_to_mesh_data(self, meshes_dict, cx, cy, tex, verts):
        """Helper to append vertex data and generate indices for a specific mesh."""
        if (cx, cy) not in meshes_dict:
            meshes_dict[(cx, cy)] = {}
            
        if tex not in meshes_dict[(cx, cy)]:
            meshes_dict[(cx, cy)][tex] = {'vertices': [], 'indices': []}
            
        mesh_data = meshes_dict[(cx, cy)][tex]
        idx_offset = len(mesh_data['vertices']) // 4
        
        mesh_data['vertices'].extend(verts)
        mesh_data['indices'].extend([
            idx_offset, idx_offset + 1, idx_offset + 2,
            idx_offset + 2, idx_offset + 3, idx_offset
        ])

    def _create_chunk_instruction_groups(self, chunk_data):
        """Helper to create Kivy InstructionGroups for chunk meshes."""
        chunk_groups = {}
        for chunk_coord, layers in chunk_data.items():
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
            chunk_groups[chunk_coord] = grp
        return chunk_groups

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

