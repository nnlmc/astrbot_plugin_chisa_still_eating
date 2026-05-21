import time

class RateLimiter:
    def __init__(self):
        self.user_records = {}   # {uid: [timestamps]}
        self.repeat_cooldowns = {} # {group_id: float} 记录上一次发呆复读的时间戳

    def is_spaming(self, uid: str, threshold: int) -> bool:
        """滑动时间窗口保安引擎，严格限制60秒内部署的请求频次"""
        now = time.time()
        timestamps = self.user_records.setdefault(uid, [])
        timestamps[:] = [ts for ts in timestamps if now - ts < 60]
        if len(timestamps) >= threshold: 
            return True
        timestamps.append(now)
        return False

    def is_repeat_in_cooldown(self, group_id: str, cooldown_seconds: int) -> bool:
        """动态比对用户在WebUI中填写的冷静期秒数限制，防止连续摆烂复读"""
        now = time.time()
        last_time = self.repeat_cooldowns.get(group_id, 0.0)
        if now - last_time < cooldown_seconds:
            return True
        return False

    def record_repeat_trigger(self, group_id: str):
        """成功触发摆烂复读时，刷新对应群组的冷却时间戳"""
        self.repeat_cooldowns[group_id] = time.time()