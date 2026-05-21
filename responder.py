import logging
import random

class Responder:
    """高阶AI拟人化沉浸回复接入总线：调用当前机器人绑定的LLM进行灵魂级人设对白"""
    def __init__(self):
        self.logger = logging.getLogger("astrbot")

    async def generate_response(self, context, event, bot_name: str, world_name: str, food_name: str, category: str, chef_name: str, is_crossover: bool) -> str:
        # 精细化物品描述
        cat_desc = "饮品" if category == "drink" else "黑暗料理" if category == "dark" else "食物"
        
        # 告诉 LLM 当前的情况，但不强迫它说出来
        context_desc = f"现在你手里有一份你们世界的{cat_desc}【{food_name}】。"
        if is_crossover:
            context_desc = f"时空乱流把你卷入了异世界，你偶然得到了异世界{cat_desc}【{food_name}】。"
        elif chef_name != "none":
            context_desc = f"【{chef_name}】刚刚在厨房做好了{cat_desc}【{food_name}】，并交给了你。"

        # 针对动词和情绪的强制补丁
        action_hint = "你现在要把这个东西给玩家（漂泊者/旅行者/开拓者/群友等）。"
        if category == "drink":
            action_hint += "⚠️记住这是饮品，台词必须用“喝”、“干杯”等动词，绝不能说“吃”。"
        elif category == "dark":
            action_hint += "⚠️这是极其可怕的黑暗料理！你必须表现出极其惊恐、嫌弃或疯狂吐槽的语气，阻止对方或者想拉人垫背。"

        # 🚀 全新升级的“去NPC化”激进提示词
        prompt = (
            f"请你完全沉浸扮演【{world_name}】的【{bot_name}】。\n"
            f"当前情境：{context_desc} {action_hint}\n"
            f"⚠️为了打破死板的机械回复，制造聊天群里的惊喜感，你必须遵守以下死命令：\n"
            f"1. 【去NPC化】绝不能像系统提示音或服务员一样生硬地报菜名！严禁说“这是一份由xx特制的xx”这种刻板废话！\n"
            f"2. 【性格拉满】用极其符合你角色人设的口语、专属口癖、甚至傲娇/慵懒/贪吃/吐槽的态度来聊天！\n"
            f"3. 【字数极简】把你当做正在QQ群里水群的真实群友，台词控制在 15 到 40 字以内！越精炼自然越好。\n"
            f"4. 【格式限制】直接输出纯台词文本！严禁任何括号、旁白、动作描写（如“递给你”）、以及任何多余的系统解释！"
        )

        try:
            # === 适配 AstrBot 最新版 API 调用大模型 ===
            if hasattr(context, "get_current_chat_provider_id") and hasattr(context, "tool_loop_agent"):
                umo = event.unified_msg_origin
                prov_id = await context.get_current_chat_provider_id(umo)
                llm_resp = await context.tool_loop_agent(
                    event=event,
                    chat_provider_id=prov_id,
                    prompt=prompt
                )
                if llm_resp and hasattr(llm_resp, "completion_text"):
                    result_text = llm_resp.completion_text.strip()
                    if result_text:
                        return result_text
            
            # === 向下兼容旧版 API ===
            elif hasattr(context, "get_llm_service"):
                llm_service = context.get_llm_service()
                if llm_service:
                    if hasattr(llm_service, "text_chat"):
                        response = await llm_service.text_chat(prompt)
                        if response and response.strip():
                            return response.strip()
                    elif hasattr(llm_service, "generate_text"):
                        response = await llm_service.generate_text(prompt)
                        if response and response.strip():
                            return response.strip()
            
            self.logger.warning("[FlavorFusion AI] 未能找到兼容的 AstrBot 大模型接口或模型返回为空")
            return ""
        except Exception as e:
            self.logger.error(f"[FlavorFusion AI] 大模型沉浸回复总线调用失败: {str(e)}")
            return ""
