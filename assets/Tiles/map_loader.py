import json
import base64
import zlib
import struct
import os
import xml.etree.ElementTree as ET
from kivy.graphics import Color, Rectangle, InstructionGroup, Mesh
from kivy.core.image import Image as CoreImage
from data.settings import TILE_SIZE, CAMERA_WIDTH, CAMERA_HEIGHT

# Tiled Flip Flags
FLIPPED_HORIZONTALLY_FLAG = 0x80000000
FLIPPED_VERTICALLY_FLAG   = 0x40000000
FLIPPED_DIAGONALLY_FLAG   = 0x20000000
ALL_FLAGS = FLIPPED_HORIZONTALLY_FLAG | FLIPPED_VERTICALLY_FLAG | FLIPPED_DIAGONALLY_FLAG

class KivyTiledMap:
    def __init__(self, filename):
        self.filename = filename
        self.map_dir = os.path.dirname(filename)
        self.map_data = {}
        self.width = 0
        self.height = 0
        self.tile_w = 16
        self.tile_h = 16
        self.tilesets = []
        self.textures = {}  # gid -> (tex, uvs, w, h, x, inv_y)
        self.core_images = [] # Prevent garbage collection
        self.solid_rects = []
        self.well_fg_gids = set()
        self.well_roof_gids = set()
        self.well_solid_gids = set()
        self.tile_hitboxes = {} # gid -> list of (x, y, w, h)
        self.visible_chunks = set()
        self.chunk_groups_bg = {}
        self.chunk_groups_fg = {}
        self.chunk_groups_ground = {} # ชั้นพื้นดิน (อยู่ล่างสุด)
        self.chunk_groups_roof = {}   # ชั้นหลังคา (อยู่บนสุด)
        
        # Instruction groups for Kivy rendering
        self.ground_group = InstructionGroup()
        self.bg_group = InstructionGroup()
        self.fg_group = InstructionGroup()
        self.roof_group = InstructionGroup()
        
        # 1. Load data
        if not self._load_map_file(filename):
            return
            
        # 2. Setup resources
        self.load_tilesets()
        
        # 3. Generate geometry
        self._build_meshes()
        
    def _load_map_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.map_data = json.load(f)
            self.width = self.map_data.get('width', 0)
            self.height = self.map_data.get('height', 0)
            self.tile_w = self.map_data.get('tilewidth', 16)
            self.tile_h = self.map_data.get('tileheight', 16)
            return True
        except Exception as e:
            print(f"Failed to load map {filename}: {e}")
            return False

    # --- Tileset Loading ---

    def load_tilesets(self):
        """Parse all tilesets defined in the map and prepare textures/hitboxes."""
        for ts_info in self.map_data.get('tilesets', []):
            firstgid = ts_info.get('firstgid', 1)
            source = ts_info.get('source')
            if not source: continue
                
            tsx_path = self._resolve_path(source, '.tsx')
            if not tsx_path: continue
                
            try:
                self._parse_tsx(tsx_path, firstgid)
            except Exception as e:
                print(f"Error loading tileset {tsx_path}: {e}")

    def _resolve_path(self, filename, sub_dir=None):
        """Find a file in map_dir, optional sub_dir, or via recursive search."""
        base = os.path.basename(filename)
        paths_to_check = [os.path.join(self.map_dir, base)]
        if sub_dir:
            paths_to_check.insert(0, os.path.join(self.map_dir, sub_dir, base))
            
        for p in paths_to_check:
            if os.path.exists(p): return p
            
        # Recursive fallback
        for root, _, files in os.walk(self.map_dir):
            if base in files: return os.path.join(root, base)
        return None

    def _parse_tsx(self, tsx_path, firstgid):
        tree = ET.parse(tsx_path)
        root = tree.getroot()
        name = root.get('name', '')
        
        img_el = root.find('image')
        if img_el is None: return
            
        img_path = self._resolve_path(img_el.get('source'), 'prop')
        if not img_path: return

        # Load Texture
        cimg = CoreImage(img_path)
        self.core_images.append(cimg)
        tex = cimg.texture
        tex.mag_filter = tex.min_filter = 'nearest'
        
        # Tileset properties
        tw = int(root.get('tilewidth', self.tile_w))
        th = int(root.get('tileheight', self.tile_h))
        cols = int(root.get('columns', 1))
        count = int(root.get('tilecount', 0))
        margin = int(root.get('margin', 0))
        spacing = int(root.get('spacing', 0))

        self.setup_well(name, firstgid, cols, count)
        
        pad_x, pad_y = self._get_uv_padding(tex)
        
        for i in range(count):
            gid = firstgid + i
            col, row = i % cols, i // cols
            tx, ty = margin + col*(tw+spacing), margin + row*(th+spacing)
            
            # Tiled (Y-down) -> Kivy (Y-up)
            inv_y = cimg.height - ty - th
            region = tex.get_region(tx, inv_y, tw, th)
            
            u0, v0 = region.tex_coords[0], region.tex_coords[1]
            u1, v1 = region.tex_coords[4], region.tex_coords[5]
            
            self.textures[gid] = (tex, (u0+pad_x, v0+pad_y, u1-pad_x, v1-pad_y), tw, th, tx, inv_y)

        # Parse custom hitboxes
        for tile in root.findall('tile'):
            gid = firstgid + int(tile.get('id'))
            objgrp = tile.find('objectgroup')
            if objgrp is not None:
                boxes = []
                for obj in objgrp.findall('object'):
                    ox, oy = float(obj.get('x', 0)), float(obj.get('y', 0))
                    poly, ell = obj.find('polygon'), obj.find('ellipse')
                    
                    if poly is not None:
                        pts = [tuple(map(float, p.split(','))) for p in poly.get('points', '').split()]
                        if pts:
                            x_pts, y_pts = [p[0] for p in pts], [p[1] for p in pts]
                            boxes.append((ox+min(x_pts), oy+min(y_pts), max(x_pts)-min(x_pts), max(y_pts)-min(y_pts)))
                    else:
                        boxes.append((ox, oy, float(obj.get('width', 0)), float(obj.get('height', 0))))
                if boxes: self.tile_hitboxes[gid] = boxes

    def _get_uv_padding(self, tex):
        return 0.1 / tex.width, 0.1 / tex.height

    def setup_well(self, tsx_name, firstgid, columns, tilecount):
        if "well" in tsx_name.lower():
            # แถวแรก (บนสุด/หลังบ่อ) -> Roof (บังหัวเมื่ออยู่หลังบ่อ) และไม่มี Hitbox
            self.well_roof_gids.update(range(firstgid, firstgid + columns))
            
            # บล็อกที่เหลือทั้งหมด (ตั้งแต่แถว 2 จนถึงแถวสุดท้าย) -> ให้ดัก Hitbox (Solid)
            self.well_solid_gids.update(range(firstgid + columns, firstgid + tilecount))
            
            # แถวสุดท้าย (หน้าบ่อ) -> Foreground (วาดทับหน้าเท้า) และมี Hitbox (เพราะรวมอยู่ใน solid_gids แล้ว)
            self.well_fg_gids.update(range(firstgid + tilecount - columns, firstgid + tilecount))

    # --- Mesh Building ---

    def _build_meshes(self):
        """Construct chunked meshes for the entire map."""
        self.bg_group.clear()
        self.fg_group.clear()
        self.ground_group.clear()
        self.solid_rects = []
        
        chunk_size_pixels = TILE_SIZE * 16
        scale = TILE_SIZE / self.tile_w
        
        # Accumulators for all chunks
        chunk_meshes_bg, chunk_meshes_fg, chunk_meshes_ground, chunk_meshes_roof = {}, {}, {}, {}

        for layer in self.map_data.get('layers', []):
            if not layer.get('visible', True): continue
            
            layer_type = layer.get('type')
            name = layer.get('name', '').strip().lower()
            
            # Logic classifications
            # ใช้ (kw,) หรือ [kw] เพื่อป้องกันการไล่ตรวจทีละตัวอักษร
            # ตรวจสอบว่าเป็นชั้นหลังคา (สูงที่สุด) หรือไม่
            is_roof = any(kw in name for kw in ("หลังคา", "roof", "หลังคา2 ชั้น", "funiture3", "furniture3"))
            
            # กฎพิเศษสำหรับ home.tmj: ให้เลเยอร์ "เหนือ" อยู่ชั้นหน้าสุด (High Z)
            map_basename = os.path.basename(self.filename).lower()
            if map_basename == "home.tmj" and "เหนือ" in name:
                is_roof = True
            
            # ตรวจสอบว่าเป็นชั้นหน้าสุด (Foreground) หรือไม่
            is_fg = any(kw in name for kw in ("foreground", "fg")) and not is_roof
            
            # กฎพิเศษสำหรับ home.tmj: ให้ผนังบ้านอยู่ชั้นหน้าสุด (High Z) ตามคำขอ
            if "home.tmj" in self.filename.lower() and "ผนังบ้านบัง" in name:
                is_fg = True
                
            # กฎพิเศษสำหรับ beyond.tmj: ให้ขยะอยู่ชั้นหน้าสุด (High Z)
            if "beyond.tmj" in self.filename.lower() and "ขยะ" in name:
                is_fg = True
                
            # กฎพิกัดบ่อน้ำ (User Request): well2 = พื้น, well1 = บ่อ
            if "well2" in name:
                is_ground = True
                is_fg = False
                is_well = False
            elif "well1" in name:
                is_well = True
                is_ground = False
                is_fg = False
            else:
                is_ground = any(kw in name for kw in ("พื้น", "ground", "floor", "floor layer", "bottom", "ดิน")) and not is_fg and not is_roof
                is_well = "well" in name
            
            # Special Rule for underground.tmj: "ผนัง" and "ของ" must be solid (Hitbox)
            if "underground.tmj" in self.filename.lower() and ("ผนัง" in name or "ของ" in name):
                is_solid = True
                is_ground = False
            else:
                # Normal solid logic
                is_solid = not is_ground and (
                    any(kw in name for kw in ("ผนัง", "ผนังบ้าน", "กองขยะ", "กำแพง", "ขยะ", "wall", "solid", "obstacle", "trash", "chair", "table", "unfloor", "wall layer")) or
                    name.lower() in ("funiture", "funiture2", "furniture", "props", "ผนัง")
                ) and not any(kw in name for kw in ("resources", "floor"))
            
            opacity = layer.get('opacity', 1.0)

            # 1. Parse layer raw tile data into instances (gid, x, y, w, h)
            instances = self._get_layer_instances(layer, scale)
            if not instances: continue

            # 2. Process each tile instance
            l_meshes_bg, l_meshes_fg, l_meshes_ground, l_meshes_roof = {}, {}, {}, {}
            for gid_full, x, y, cw, ch in instances:
                self._process_tile(
                    gid_full, x, y, cw, ch, scale, chunk_size_pixels,
                    is_solid, is_fg, is_well, name, l_meshes_bg, l_meshes_fg, l_meshes_ground, is_ground, is_roof, l_meshes_roof
                )
            
            # 3. Add layer meshes to global chunk data
            self._merge_layer_to_global(l_meshes_bg, chunk_meshes_bg, opacity)
            self._merge_layer_to_global(l_meshes_fg, chunk_meshes_fg, opacity)
            self._merge_layer_to_global(l_meshes_ground, chunk_meshes_ground, opacity)
            self._merge_layer_to_global(l_meshes_roof, chunk_meshes_roof, opacity)

        # 4. Finalize Kivy groups
        self.chunk_groups_bg = self._create_mesh_groups(chunk_meshes_bg)
        self.chunk_groups_fg = self._create_mesh_groups(chunk_meshes_fg)
        self.chunk_groups_ground = self._create_mesh_groups(chunk_meshes_ground)
        self.chunk_groups_roof = self._create_mesh_groups(chunk_meshes_roof)

    def _get_layer_instances(self, layer, scale):
        instances = []
        l_type = layer.get('type')
        
        if l_type == 'tilelayer':
            tiles = self._decode_tilelayer(layer)
            w, h = layer.get('width', self.width), layer.get('height', self.height)
            # Use self.height (map height) for inversion to stay consistent across all layers
            map_h_px = self.height * self.tile_h
            for i, gid in enumerate(tiles):
                if gid == 0: continue
                col, row = i % w, i // w
                x = col * self.tile_w * scale
                # Reverting to correct Kivy y-up: total_map_height - (row + 1) * tile_height
                # This ensures Row 99 is at y=0 and Row 0 is at y=1584 (for 100-tile map)
                y = (map_h_px - (row + 1) * self.tile_h) * scale
                instances.append((gid, x, y, None, None))
                
        elif l_type == 'objectgroup':
            objs = layer.get('objects', [])
            # Tiled default draworder is "topdown" (sorted by Y)
            if layer.get('draworder', 'topdown') == 'topdown':
                objs = sorted(objs, key=lambda o: float(o.get('y', 0)))
                
            for obj in objs:
                gid = obj.get('gid', 0)
                px, py = float(obj.get('x', 0)), float(obj.get('y', 0))
                pw, ph = float(obj.get('width', self.tile_w)), float(obj.get('height', self.tile_h))
                
                x = px * scale
                # GID-based objects (bottom-left) vs Shapes (top-left)
                if gid != 0:
                    y = (self.height * self.tile_h - py) * scale
                else:
                    # For shapes (GID=0), Tiled y is top. Bottom y = H - (y + h)
                    y = (self.height * self.tile_h - (py + ph)) * scale
                instances.append((gid, x, y, pw * scale, ph * scale))
                
        return instances

    def _decode_tilelayer(self, layer):
        data = layer.get('data')
        encoding = layer.get('encoding')
        if encoding != 'base64': return data if isinstance(data, list) else []
        
        decoded = base64.b64decode(data)
        comp = layer.get('compression')
        if comp == 'zlib': decoded = zlib.decompress(decoded)
        elif comp == 'gzip': 
            import gzip
            decoded = gzip.decompress(decoded)
            
        w, h = layer.get('width', self.width), layer.get('height', self.height)
        return struct.unpack(f"<{w*h}I", decoded)

    def _process_tile(self, gid_full, x, y, cw, ch, scale, chunk_size_pixels, is_solid, is_fg, is_well, name, l_bg, l_fg, l_ground, is_ground, is_roof, l_roof):
        if gid_full == 0:
            if is_solid:
                # Shape without Tile (Collision Box)
                self.solid_rects.append([x, y, cw, ch])
            return

        gid = gid_full & ~ALL_FLAGS
        t_info = self.textures.get(gid)
        if not t_info: return
        
        tex, base_uvs, tsw, tsh, tx, ty_inv = t_info
        cx, cy = int(x // chunk_size_pixels), int(y // chunk_size_pixels)
        
        obj_px_w = int(cw / scale) if cw is not None else tsw
        obj_px_h = int(ch / scale) if ch is not None else tsh
        w, h = obj_px_w * scale, obj_px_h * scale

        # Special Case: Well (Split into BG/Bottom and Roof/Top)
        if is_well and (gid in self.well_roof_gids or gid in self.well_fg_gids or gid in self.well_solid_gids) and cw is not None:
            self._handle_well_split(x, y, w, h, obj_px_w, obj_px_h, scale, tx, ty_inv, tsh, t_info, cx, cy, l_bg, l_fg, l_roof)
            return

        # Collision Logic
        if is_solid:
            # Pass tileset dimensions (tsw, tsh) to scale custom hitboxes correctly
            self._add_to_solid_rects(gid, x, y, w, h, scale, name, tsw, tsh)
        elif is_well and gid in self.well_solid_gids:
            self.solid_rects.append([x, y, w, h])

        # UV & Geometry Calculation
        # Always use the base tile's UVs. Scaling is handled by the Mesh vertices (w, h).
        # This prevents "extracting" the wrong area from the texture atlas.
        uvs = self._get_final_uvs(gid_full, t_info)
        verts = [x, y, uvs[0], uvs[1], x+w, y, uvs[2], uvs[3], x+w, y+h, uvs[4], uvs[5], x, y+h, uvs[6], uvs[7]]
        
        # Decide Target Mesh (Roof vs FG vs BG vs Ground)
        if is_roof or gid in self.well_roof_gids:
            target_l = l_roof
        elif is_fg or gid in self.well_fg_gids:
            target_l = l_fg
        elif is_ground:
            target_l = l_ground
        else:
            target_l = l_bg
            
        self._add_to_mesh_data(target_l, cx, cy, tex, verts)

    def _handle_well_split(self, x, y, w, h, opw, oph, scale, tx, ty_i, tsw_h, t_info, cx, cy, l_bg, l_fg, l_roof):
        tex = t_info[0]
        pad_x, pad_y = self._get_uv_padding(tex)
        
        # Bottom (BG + Solid) - เหลือส่วนล่างไว้ 
        # th_px_h = 16 (1 block) ส่วนที่บังหัว/ตัว
        bh_px_h = max(0, int(oph - 16)) 
        bh_h = bh_px_h * scale
        bh_inv_y = ty_i + tsw_h - bh_px_h
        reg_b = tex.get_region(tx, bh_inv_y, opw, bh_px_h)
        bu0, bv0 = reg_b.tex_coords[0]+pad_x, reg_b.tex_coords[1]+pad_y
        bu1, bv1 = reg_b.tex_coords[4]-pad_x, reg_b.tex_coords[5]-pad_y
        
        b_verts = [x, y, bu0, bv0, x+w, y, bu1, bv0, x+w, y+bh_h, bu1, bv1, x, y+bh_h, bu0, bv1]
        self._add_to_mesh_data(l_bg, cx, cy, tex, b_verts)
        
        hp = 4 * scale
        self.solid_rects.append([x + hp, y, w - (hp * 2), bh_h])

        # Top (FG)
        th_px_h = oph - bh_px_h
        th_h, th_y = th_px_h * scale, y + bh_h
        th_inv_y = bh_inv_y - th_px_h
        reg_t = tex.get_region(tx, th_inv_y, opw, th_px_h)
        tu0, tv0 = reg_t.tex_coords[0]+pad_x, reg_t.tex_coords[1]+pad_y
        tu1, tv1 = reg_t.tex_coords[4]-pad_x, reg_t.tex_coords[5]-pad_y
        
        t_verts = [x, th_y, tu0, tv0, x+w, th_y, tu1, tv0, x+w, th_y+th_h, tu1, tv1, x, th_y+th_h, tu0, tv1]
        self._add_to_mesh_data(l_roof, cx, cy, tex, t_verts)

    def _get_final_uvs(self, gid_full, t_info):
        # Always use the tile's own base UVs from the tileset
        u0, v0, u1, v1 = t_info[1]

        # Apply Flips
        fh, fv, fd = bool(gid_full & FLIPPED_HORIZONTALLY_FLAG), bool(gid_full & FLIPPED_VERTICALLY_FLAG), bool(gid_full & FLIPPED_DIAGONALLY_FLAG)
        if fh: u0, u1 = u1, u0
        if fv: v0, v1 = v1, v0
        return [u1, v0, u1, v1, u0, v1, u0, v0] if fd else [u0, v0, u1, v0, u1, v1, u0, v1]

    def _add_to_solid_rects(self, gid, x, y, w, h, scale, name, tsw=None, tsh=None):
        """Unified hitbox generation. x,y is the Kivy bottom-left of the tile/object."""
        if gid in self.tile_hitboxes:
            # Calculate object-to-tile ratio for scaling the hitboxes
            # w and h are already world coordinates; (tsw * scale) is world size of one tile
            ratio_x = (w / (tsw * scale)) if tsw else 1.0
            ratio_y = (h / (tsh * scale)) if tsh else 1.0
            
            for hx, hy, hw, hh in self.tile_hitboxes[gid]:
                # Scaled relative coordinates (inside the object bounds)
                shx = hx * ratio_x * scale
                shy = hy * ratio_y * scale
                shw = hw * ratio_x * scale
                shh = hh * ratio_y * scale
                
                # Conversion: Tiled (y-down) -> Kivy (y-up relative to item bottom)
                # k_ry = Object Height - (Box Top Y + Box Height)
                k_ry = h - (shy + shh)
                self.solid_rects.append([x + shx, y + k_ry, shw, shh])
        else:
            # Fallback for generic solids
            self.solid_rects.append([x, y, w, h])

    # --- Mesh Management & Rendering ---

    def _add_to_mesh_data(self, m_dict, cx, cy, tex, verts):
        chunk = m_dict.setdefault((cx, cy), {}).setdefault(tex, {'vertices': [], 'indices': []})
        off = len(chunk['vertices']) // 4
        chunk['vertices'].extend(verts)
        chunk['indices'].extend([off, off+1, off+2, off+2, off+3, off])

    def _merge_layer_to_global(self, layer_chunk_meshes, global_chunk_data, opacity):
        for coord, tex_dict in layer_chunk_meshes.items():
            global_chunk_data.setdefault(coord, []).append((opacity, tex_dict))

    def _create_mesh_groups(self, chunk_data):
        groups = {}
        for coord, layers in chunk_data.items():
            grp = InstructionGroup()
            for op, tex_dict in layers:
                grp.add(Color(1, 1, 1, op))
                for tex, mesh in tex_dict.items():
                    grp.add(Mesh(vertices=mesh['vertices'], indices=mesh['indices'], 
                                fmt=[(b'vPosition', 2, 'float'), (b'vTexCoords0', 2, 'float')],
                                texture=tex, mode='triangles'))
            groups[coord] = grp
        return groups

    def draw_background(self, canvas): canvas.add(self.bg_group)
    def draw_foreground(self, canvas): canvas.add(self.fg_group)
    def draw_ground(self, canvas): canvas.add(self.ground_group)
    def draw_roof(self, canvas): canvas.add(self.roof_group)

    def update_chunks(self, cam_x, cam_y):
        ws = TILE_SIZE * 16
        # Optimization: ลดรัศมีการค้นหาจาก 1000px เหลือ 450px (เหมาะสมกับกล้อง 320x240)
        radius = 450
        nx = set()
        for cx in range(int((cam_x-radius)//ws), int((cam_x+radius)//ws)+1):
            for cy in range(int((cam_y-radius)//ws), int((cam_y+radius)//ws)+1):
                nx.add((cx, cy))
                
        # Detach
        for c in self.visible_chunks - nx:
            if c in self.chunk_groups_bg: self.bg_group.remove(self.chunk_groups_bg[c])
            if c in self.chunk_groups_fg: self.fg_group.remove(self.chunk_groups_fg[c])
            if c in self.chunk_groups_ground: self.ground_group.remove(self.chunk_groups_ground[c])
            if c in self.chunk_groups_roof: self.roof_group.remove(self.chunk_groups_roof[c])
        # Attach
        for c in nx - self.visible_chunks:
            if c in self.chunk_groups_bg: self.bg_group.add(self.chunk_groups_bg[c])
            if c in self.chunk_groups_fg: self.fg_group.add(self.chunk_groups_fg[c])
            if c in self.chunk_groups_ground: self.ground_group.add(self.chunk_groups_ground[c])
            if c in self.chunk_groups_roof: self.roof_group.add(self.chunk_groups_roof[c])
        self.visible_chunks = nx
