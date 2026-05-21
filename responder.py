import logging
import random

class Responder:
    """高阶AI拟人化沉浸回复接入总线：调用当前机器人绑定的LLM进行灵魂级人设对白"""
    def __init__(self):
        self.logger = logging.getLogger("astrbot")

    async def generate_response(self, context, bot_name: str, world_name: str, food_name: str, category: str, chef_name: str, is_crossover: bool) -> str:
        # 精细化物品描述
        cat_desc = "特产饮品" if category == "drink" else "危险的黑暗料理" if category == "dark" else "特产美食"
        
        # 针对大乱斗或特制，给 LLM 下达精准的情境提示
        context_desc = f"这是一份属于你们本世界的{cat_desc}。"
        if is_crossover:
            context_desc = f"这是一份来自其他世界的异界{cat_desc}，由于时空波动你和玩家在跨次元乱斗中偶然得到了它。"
        elif chef_name != "none":
            context_desc = f"这是一份由特定角色【{chef_name}】精心下厨为你和玩家特制的{cat_desc}。"

        # 【新增核心逻辑】针对动词和情绪的强制补丁
        action_hint = "邀请对方一起品尝。"
        if category == "drink":
            action_hint = "⚠️注意：这是一种饮品！台词中必须使用“喝”、“干杯”、“品尝”等词汇，绝对不能出现“吃”这个字眼。"
        elif category == "dark":
            action_hint = "⚠️注意：这是极其可怕的黑暗料理！你的语气必须表现出惊恐、嫌弃、警惕，或者是准备开溜的状态，疯狂劝阻玩家尝试。"

        prompt = (
            f"你现在正在严格扮演一个名为【{bot_name}】的角色，你来自【{world_name}】世界。你的性格、说话口吻、标志性人设必须完全契合原作。\n"
            f"现在，请你用符合你人设的生动语气，向玩家（漂泊者/旅行者/开拓者/群友）介绍或呈现：【{food_name}】。\n"
            f"当前的对话背景情境：{context_desc}\n"
            f"{action_hint}\n"
            f"请展开一段极具沉浸感、高还原度的短文本角色对白。字数必须严格控制在 60 字以内。\n"
            f"⚠️绝对死命令：直接输出你的角色对白台词内容即可！不要夹带任何括号、动作描写旁白、系统提示、或者现代网络的废话。"
        )

        try:
            # 动态向上寻找并适配 AstrBot 的大模型服务核心
            if hasattr(context, "get_llm_service"):
                llm_service = context.get_llm_service()
                if llm_service:
                    # 动态适配 text_chat 或 generate_text 异步方法
                    if hasattr(llm_service, "text_chat"):
                        response = await llm_service.text_chat(prompt)
                        if response and response.strip():
                            return response.strip()
                    elif hasattr(llm_service, "generate_text"):
                        response = await llm_service.generate_text(prompt)
                        if response and response.strip():
                            return response.strip()
            return ""
        except Exception as e:
            self.logger.error(f"[FlavorFusion AI] 大模型沉浸回复总线调用失败: {str(e)}")
            return ""