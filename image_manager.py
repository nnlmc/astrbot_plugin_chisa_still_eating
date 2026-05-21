import os
import re
import random

class ImageManager:
    def __init__(self):
        # 物理存储根目录
        self.data_dir = os.path.join("data", "plugin_data", "astrbot_plugin_chisa_still_eating")
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.egg_dir = os.path.join(self.plugin_dir, "Still_eating_meme")
        
        # 物理分类目录结构
        self.categories = ["food", "drink", "darkfood"]
        self.worlds = ["world1", "world2", "world3", "world4", "common"]
        self.moods = ["think", "like", "speechless", "scared"]
        
        self._ensure_infrastructure()

    def _ensure_infrastructure(self):
        """确保所有目录结构已就位"""
        for cat in self.categories:
            for w in self.worlds:
                os.makedirs(os.path.join(self.data_dir, cat, w), exist_ok=True)
        # 表情包目录统一规范化
        for w in self.worlds:
            for mood in self.moods:
                os.makedirs(os.path.join(self.data_dir, "memes", w, mood), exist_ok=True)
        # 【新增】厨师图鉴专属物理目录
        os.makedirs(os.path.join(self.data_dir, "chefs"), exist_ok=True)
        
        for char in ["千咲", "派蒙", "达妮娅"]:
            os.makedirs(os.path.join(self.egg_dir, char), exist_ok=True)

    def parse_filename(self, filename: str):
        """解析文件名，提取厨师和食物名。支持 jpg, png, webp, gif 等"""
        pattern = re.compile(r"^(?:【(.*?)】)?(.*?)(?:_\d+)?\.(?:jpg|jpeg|png|gif|webp|bmp)$", re.I)
        match = pattern.match(filename)
        if match:
            return match.group(1), match.group(2).strip()
        return None, os.path.splitext(filename)[0]

    def scan_all_items(self, config_global: dict, wv_settings: dict, category: str):
        pool = []
        # 定义类别映射与对应的硬标签
        cat_map = {"food": ("food", "特产食物"), "drink": ("drink", "特产饮品"), "dark": ("darkfood", "黑暗料理")}
        folder_name, food_type = cat_map.get(category, ("food", "特产食物"))

        # 1. 扫描纯净的 NAS 物理目录 (唯一图源)
        for w in self.worlds:
            target_dir = os.path.join(self.data_dir, folder_name, w)
            if not os.path.exists(target_dir): continue
            for file in os.listdir(target_dir):
                if file.startswith(".") or not file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                    continue
                file_path = os.path.join(target_dir, file)
                chef, food_name = self.parse_filename(file)
                pool.append({
                    "raw_name": food_name, "food": food_name, "chef": chef or "none",
                    "wv": w, "food_type": food_type, "has_image": True, "path": file_path
                })

        # (注：WebUI 托管目录 files/ 的扫描逻辑已彻底移除，纯净运行)

        # 2. 混合 WebUI 纯文字池
        for w_key, conf in wv_settings.items():
            text_key_map = {"food": "7.文字食物", "drink": "8.文字饮品", "dark": "9.文字黑暗料理"}
            t_key = text_key_map.get(category, "7.文字食物")
            for text_item in conf.get(t_key, []):
                if text_item and not any(p["food"] == text_item and p["wv"] == w_key for p in pool):
                    pool.append({
                        "raw_name": text_item, "food": text_item, "chef": "none",
                        "wv": w_key, "food_type": food_type, "has_image": False, "path": None
                    })
        return pool

    def get_chef_image(self, chef_name: str):
        """【新增】扫描 chefs/ 目录，动态提取厨师立绘，优先返回动图"""
        if not chef_name or chef_name == "none":
            return None
            
        chef_dir = os.path.join(self.data_dir, "chefs")
        if not os.path.exists(chef_dir):
            return None
            
        matched_files = []
        for file in os.listdir(chef_dir):
            if file.startswith(".") or not file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                continue
                
            # 利用已有的解析器，兼容 "弗洛洛.webp", "弗洛洛_1.gif" 等格式
            parsed_chef, parsed_name = self.parse_filename(file)
            
            # 只要文件名主体等于厨师名，或者文件名直接以厨师名开头，即视为命中
            if parsed_name == chef_name or parsed_chef == chef_name or file.startswith(chef_name):
                matched_files.append(os.path.join(chef_dir, file))
                
        if matched_files:
            # 彩蛋：如果配置了多种图片，优先寻找 GIF 发送，增强表现力
            gifs = [f for f in matched_files if f.lower().endswith('.gif')]
            if gifs:
                return random.choice(gifs)
            return random.choice(matched_files)
            
        return None

    def get_bot_meme(self, world_key: str, mood: str):
        target_dir = os.path.join(self.data_dir, "memes", world_key, mood)
        if os.path.exists(target_dir):
            files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))]
            if files: return os.path.join(target_dir, random.choice(files))
        return None

    def get_egg_meme(self, char_name: str):
        char_dir = os.path.join(self.egg_dir, char_name)
        if os.path.exists(char_dir):
            files = [f for f in os.listdir(char_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))]
            if files: return os.path.join(char_dir, random.choice(files))
        return None