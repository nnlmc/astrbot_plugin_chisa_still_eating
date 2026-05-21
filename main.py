import random
import re
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from .image_manager import ImageManager
from .food_data import FoodDataManager
from .rate_limiter import RateLimiter
from .responder import Responder

@register("astrbot_plugin_chisa_still_eating", "Rua432", "2.1.1_Beta", "跨次元美食与情绪沉浸系统")
class FlavorFusionUltimate(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.image_mgr = ImageManager()
        self.data_mgr = FoodDataManager(config)
        self.limiter = RateLimiter()
        self.responder = Responder()
        self._refresh_world_cache()
        self._rebuild_alias_map()

        eat_keywords = self.config.get("trigger_eat", ["吃什么", "吃啥", "吃点儿啥"])
        drink_keywords = self.config.get("trigger_drink", ["喝什么", "喝啥", "喝点儿啥"])
        dark_keywords = self.config.get("trigger_dark", ["来点黑暗料理", "黑暗料理"])
        common_eat_keywords = self.config.get("trigger_common_eat", ["来点现实的食物", "来点三次元食物"])
        common_drink_keywords = self.config.get("trigger_common_drink", ["来点现实的饮品", "来点三次元饮品"])
        
        if not isinstance(eat_keywords, list): eat_keywords = [eat_keywords]
        if not isinstance(drink_keywords, list): drink_keywords = [drink_keywords]
        if not isinstance(dark_keywords, list): dark_keywords = [dark_keywords]
        if not isinstance(common_eat_keywords, list): common_eat_keywords = [common_eat_keywords]
        if not isinstance(common_drink_keywords, list): common_drink_keywords = [common_drink_keywords]
        
        self.eat_pattern = re.compile("|".join([re.escape(str(k)) for k in eat_keywords if k]))
        self.drink_pattern = re.compile("|".join([re.escape(str(k)) for k in drink_keywords if k]))
        self.dark_pattern = re.compile("|".join([re.escape(str(k)) for k in dark_keywords if k]))
        self.common_eat_pattern = re.compile("|".join([re.escape(str(k)) for k in common_eat_keywords if k]))
        self.common_drink_pattern = re.compile("|".join([re.escape(str(k)) for k in common_drink_keywords if k]))

    def _refresh_world_cache(self):
        raw_settings = {
            "world1": self.config.get("world1", {}),
            "world2": self.config.get("world2", {}),
            "world3": self.config.get("world3", {}),
            "world4": self.config.get("world4", {})
        }
        self.wv_settings = {}
        for wk, v in raw_settings.items():
            if isinstance(v, dict) and "default" in v:
                self.wv_settings[wk] = v["default"]
            else:
                self.wv_settings[wk] = v

    def _rebuild_alias_map(self):
        self.alias_map = {}
        for i in range(1, 5):
            w_key = f"world{i}"
            aliases = self.config.get(f"{w_key}_aliases", [])
            inner_conf = self.wv_settings.get(w_key, {})
            inner_aliases = inner_conf.get("2.世界别称", [])
            
            combined = set([str(a).strip() for a in (aliases + inner_aliases) if a])
            for alias in combined:
                self.alias_map[alias] = w_key

    def _resolve_active_key(self) -> str:
        selection = self.config.get("active_world", "世界1(鸣潮)")
        if "世界1" in selection: return "world1"
        if "世界2" in selection: return "world2"
        if "世界3" in selection: return "world3"
        if "世界4" in selection: return "world4"
        return "world1"

    @filter.event_message_type(EventMessageType.ALL)
    async def global_message_interceptor(self, event: AstrMessageEvent, *args, **kwargs):
        msg_text = event.message_str
        if not msg_text: return
        msg_text = msg_text.strip()
        
        # ==========================================
        # 💡 新增：帮助菜单拦截 (必须放在最前面防误触)
        # ==========================================
        if msg_text in ["千小妹还在吃帮助", "千咲吃什么帮助", "干饭帮助", "美食帮助"]:
            help_text = (
                "🍱 【千小妹还在吃 v2.1_Beta】干饭指南\n\n"
                "🍔 基础点餐：\n"
                "· 吃什么 / 喝什么 (全宇宙随机摇号)\n"
                "· 来点现实的食物 / 来点现实的饮品 (绝对锁定三次元外卖)\n\n"
                "✨ 异界特产：\n"
                "· 鸣潮特产 / 原神特产 (指定世界点餐)\n"
                "· 来点黑暗料理 (作死专用，请自备复活药)\n\n"
                "💡 提示：点菜太快的话，可是会被干饭人无情截胡的哦！"
            )
            yield event.make_result().message(help_text)
            event.stop_event()
            return
        # ==========================================

        self._refresh_world_cache()
        self._rebuild_alias_map() 
        
        category = None
        forced_world = None

        # 优先级判定：专属指令 > 别名 > 通用指令
        if self.dark_pattern.search(msg_text): 
            category = "dark"
        elif self.common_eat_pattern.search(msg_text):
            category = "food"
            forced_world = "common"
        elif self.common_drink_pattern.search(msg_text):
            category = "drink"
            forced_world = "common"
        elif self.drink_pattern.search(msg_text): 
            category = "drink"
        elif self.eat_pattern.search(msg_text): 
            category = "food"

        # 如果没有触发专属的三次元强制锁定，再进行世界观嗅探
        if not forced_world:
            for alias, w_key in self.alias_map.items():
                if category and alias in msg_text:
                    forced_world = w_key
                    break
                if not category and (f"{alias}特产" in msg_text or f"{alias}吃" in msg_text):
                    category = "food"
                    forced_world = w_key
                    break

        if not category:
            return 
            
        async for res in self.execute_flow(event, category, forced_world):
            yield res

    async def execute_flow(self, event: AstrMessageEvent, category: str, forced_world: str = None):
        event.should_call_llm(True)
        uid = event.get_sender_id()
        group_id = event.message_obj.group_id or uid
        
        # 确定主导人设的世界观（绝对不能因为点的是现实食物，导游就丢了人设！）
        if forced_world and forced_world != "common":
            active_key = forced_world
        else:
            active_key = self._resolve_active_key()
            
        active_conf = self.wv_settings.get(active_key, {})
            
        bot_pool = active_conf.get("3.自称池", [])
        bot_host = random.choice(bot_pool if bot_pool else ["推荐官"])
        world_host = active_conf.get("1.世界名称", "") or f"世界{active_key[-1]}"

        # 1. 🚨 拦截乱入引擎
        if self.limiter.is_spaming(uid, self.config.get("spam_threshold", 3)):
            if random.randint(1, 100) <= self.config.get("interception_egg_chance", 50):
                egg_role = self.config.get("active_egg_role", "千咲")
                inter_text = f"【拦截警报】你点得太快啦！{egg_role}怕你撑着，已经先你一步把厨房吃空了！"
                meme_file = self.image_mgr.get_egg_meme(egg_role)
            else:
                inter_pool = active_conf.get("6.打断句式", [])
                inter_text = random.choice(inter_pool if inter_pool else [f"{bot_host}觉得你点得太频繁了。"]).format(bot=bot_host)
                meme_file = self.image_mgr.get_bot_meme(active_key, "speechless")
                
            chain = event.make_result().message(inter_text)
            if meme_file: chain.file_image(meme_file)
            yield chain
            event.stop_event()
            return

        # 2. 🔁 摆烂复读判定
        cd_seconds = self.config.get("repeat_cooldown", 60)
        if not self.limiter.is_repeat_in_cooldown(group_id, cd_seconds) and (random.randint(1, 100) <= self.config.get("repeat_prob", 10)):
            self.limiter.record_repeat_trigger(group_id)
            
            fallback_pool = self.config.get("repeat_templates", [])
            if not fallback_pool: 
                fallback_pool = ["是啊，吃什么"]
                
            text = random.choice(fallback_pool).format(bot=bot_host)
            chain = event.make_result().message(text)
            
            meme_file = self.image_mgr.get_bot_meme(active_key, "think")
            if meme_file: chain.file_image(meme_file)
            
            yield chain
            event.stop_event()
            return

        # 3. 🥘 数据抽签
        pool = self.image_mgr.scan_all_items(self.config, self.wv_settings, category)
        
        # 动态将三次元“纯文字卡池”注入主卡池
        common_texts = []
        if category == "food":
            common_texts = self.config.get("common_food_text", [])
        elif category == "drink":
            common_texts = self.config.get("common_drink_text", [])
            
        for text_item in common_texts:
            item_name = str(text_item).strip()
            if item_name:
                pool.append({
                    "wv": "common", 
                    "food": item_name, 
                    "raw_name": item_name,
                    "chef": "none", 
                    "has_image": False,
                    "path": None
                })
        
        if forced_world:
            strict_pool = [item for item in pool if item["wv"] == forced_world]
            if strict_pool:
                pool = strict_pool

        picked = self.data_mgr.filter_and_pick(group_id, pool, active_key)
        
        if not picked:
            yield event.make_result().message(f"【卡池告急】未找到任何可用的食物/饮品数据！请检查文件夹或配置。")
            event.stop_event()
            return

        food_name = picked["food"]
        chef_name = picked["chef"]
        origin_key = picked["wv"]
        
        # 4. 🧩 特制料理拼装器
        if chef_name != "none":
            full_food_desc = f"由【{chef_name}】特制的{food_name}"
        else:
            full_food_desc = food_name

        final_text = ""
        mood = "like"
        use_ai = False

        # 5. AI 拟人接驳
        if self.config.get("enable_ai", False) and random.randint(1, 100) <= self.config.get("ai_probability", 5):
            is_crossover = (origin_key != "common" and origin_key != active_key)
            ai_text = await self.responder.generate_response(
                self.context, event, bot_host, world_host, food_name, category, chef_name, is_crossover
            )
            if ai_text:
                final_text = ai_text
                use_ai = True
                mood = "scared" if category == "dark" else "like"

        # 6. 传统叙事模板组装 (严格分层路由防越界)
        if not use_ai:
            fmt_args = {
                "bot": bot_host, "bot_a": bot_host, "food": food_name, 
                "chef": chef_name, "full_food_desc": full_food_desc,
                "world_a": world_host
            }
            is_crossover = (origin_key != "common" and origin_key != active_key)
            
            if category == "dark":
                pool_text = self.config.get("dark_templates", [])
                final_text = random.choice(pool_text if pool_text else ["危险的{full_food_desc}！"]).format(**fmt_args)
                mood = "scared"
            elif is_crossover:
                cross_conf = self.wv_settings.get(origin_key, {})
                fmt_args["world_b"] = cross_conf.get("1.世界名称", "异世界") 
                bot_b_pool = cross_conf.get("3.自称池", ["异界人"])
                fmt_args["bot_b"] = random.choice(bot_b_pool if bot_b_pool else ["异界人"])
                pool_text = self.config.get("crossover_templates", [])
                final_text = random.choice(pool_text if pool_text else ["{bot_a}遇到了{bot_b}，一起吃了{full_food_desc}"]).format(**fmt_args)
            elif chef_name != "none":
                pool_text = active_conf.get("5.厨师句式", [])
                final_text = random.choice(pool_text if pool_text else ["【{chef}】特制了{food}"]).format(**fmt_args)
            elif origin_key == "common":
                # 【防串线核心】：现实食物绝对不走世界观专属句式，强制路由至 generic 兜底池
                pool_text = self.config.get("generic_templates", [])
                final_text = random.choice(pool_text if pool_text else ["铛铛！为你抽中了美味的{food}！"]).format(**fmt_args)
            else:
                # 只有 origin_key == active_key，才会走本地特色句式
                pool_text = active_conf.get("4.专属句式", []) + self.config.get("generic_templates", [])
                final_text = random.choice(pool_text if pool_text else ["推荐{food}"]).format(**fmt_args)

        # 7. 📸 动态图配装引擎 
        img_to_send = picked.get("path") if picked.get("has_image") else None
        meme_to_send = None
        
        if random.randint(1, 100) <= self.config.get("egg_prob", 10):
            egg_char = self.config.get("egg_character", "千咲")
            meme_to_send = self.image_mgr.get_egg_meme(egg_char)
            if meme_to_send:
                final_text += self.data_mgr.fetch_egg_text(egg_char)
        else:
            if chef_name != "none" and random.randint(1, 100) <= self.config.get("chef_meme_prob", 50):
                meme_to_send = self.image_mgr.get_chef_image(chef_name)
            elif random.randint(1, 100) <= self.config.get("global_meme_prob", 30):
                meme_to_send = self.image_mgr.get_bot_meme(active_key, mood)

        # 8. 🚀 最终顺序落盘包
        result = event.make_result().message(final_text)
        if img_to_send: result.file_image(img_to_send)
        if meme_to_send: result.file_image(meme_to_send)
            
        yield result
        event.stop_event()
