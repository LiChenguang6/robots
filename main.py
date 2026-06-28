import os
import re
import yaml
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import MessageChain

@register("manage_signin", "songwz", "签到配置与日志推送", "1.3.0", "管理签到配置并实时推送日志(行数追踪版)")
class ManageSigninPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_dir = "/bbs_config/"
        self.log_dir = "/bbs_logs/"
        self.base_file = "config-robots.yaml"
        
        self.push_target = None
        self.last_log_file = ""
        self.last_line_count = 0  # 记录已读取的行数
        
        self.task = asyncio.create_task(self._watch_logs())
        print("✅ 签到管理与日志推送插件 (V1.3) 已加载!")

    # ==========================
    # 基础指令：配置管理
    # ==========================
    @filter.command("签到列表")
    async def list_configs(self, event: AstrMessageEvent):
        yield event.plain_result(self._list_configs())

    @filter.command("添加签到")
    async def add_config(self, event: AstrMessageEvent):
        """使用正则提取指令后的完整字符串，支持带换行/分号/空格的复杂 Cookie"""
        raw_msg = event.message_str.strip()
        # 匹配指令后的所有内容
        match = re.search(r'(?:/添加签到|添加签到)\s+(.*)', raw_msg, re.DOTALL)
        
        if not match:
            yield event.plain_result("❌ 用法: /添加签到 <cookie>\nCookie 不能为空")
            return
            
        cookie = match.group(1).strip().replace('"', '').replace("'", "")
        
        if not cookie:
            yield event.plain_result("❌ 提取到的 Cookie 为空，请检查输入格式")
            return
            
        yield event.plain_result(self._add_config(cookie))

    @filter.command("删除签到")
    async def delete_config(self, event: AstrMessageEvent, num: int):
        yield event.plain_result(self._delete_config(num))

    # ==========================
    # 进阶指令：日志推送与查询
    # ==========================
    @filter.command("绑定推送")
    async def bind_push(self, event: AstrMessageEvent):
        self.push_target = event.message_obj.sender
        try:
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
                latest_file = files[0]
                self.last_log_file = latest_file
                with open(os.path.join(self.log_dir, latest_file), 'r', encoding='utf-8', errors='ignore') as f:
                    self.last_line_count = len(f.readlines())
        except Exception:
            pass
        yield event.plain_result("✅ 绑定成功！\nMihoyoBBSTools 日志有更新时将自动推送至本群。")

    @filter.command("最新日志")
    async def get_latest_log(self, event: AstrMessageEvent, n: int = 30):
        try:
            if not os.path.exists(self.log_dir):
                yield event.plain_result(f"❌ 日志目录不存在")
                return
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if not files:
                yield event.plain_result("📭 暂无日志")
                return
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
            with open(os.path.join(self.log_dir, files[0]), 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                clean_text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', "".join(lines[-n:]))
            yield event.plain_result(f"📄 最新 {n} 行日志:\n{clean_text}")
        except Exception as e:
            yield event.plain_result(f"❌ 读取失败: {str(e)}")

    async def _watch_logs(self):
        while True:
            await asyncio.sleep(60)
            if self.push_target:
                try: await self._check_and_push()
                except Exception: pass

    async def _check_and_push(self):
        if not os.path.exists(self.log_dir): return
        files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
        if not files: return
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
        latest_file = files[0]
        file_path = os.path.join(self.log_dir, latest_file)
        
        if self.last_log_file != latest_file:
            self.last_log_file = latest_file
            self.last_line_count = 0
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if len(lines) > self.last_line_count:
            new_lines = "".join(lines[self.last_line_count:]).strip()
            self.last_line_count = len(lines)
            if new_lines:
                clean_text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', new_lines)
                await self.context.send_message(self.push_target, MessageChain().message(f"📢 [新动态]\n{clean_text[:1500]}"))
        elif len(lines) < self.last_line_count:
            self.last_line_count = 0

    # 配置读写逻辑保持不变
    def _list_configs(self) -> str:
        try:
            if not os.path.exists(self.config_dir): return "❌ 目录不存在"
            files = sorted([f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")])
            result = "📋 配置文件列表:\n"
            for f in files:
                with open(os.path.join(self.config_dir, f), 'r', encoding='utf-8') as file:
                    cookie = yaml.safe_load(file).get('account', {}).get('cookie', '')
                    result += f" - {f}: {cookie[:20]}...\n"
            return result
        except Exception as e: return f"❌ 读取失败: {e}"
    
    def _add_config(self, cookie: str) -> str:
        try:
            files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
            nums = [int(re.search(r"(\d+)", f).group(1)) for f in files if re.search(r"(\d+)", f)]
            next_num = max(nums) + 1 if nums else 1
            with open(os.path.join(self.config_dir, self.base_file), 'r', encoding='utf-8') as f: config = yaml.safe_load(f)
            config['account'] = {'cookie': cookie}
            new_file = f"config-robots{next_num}.yaml"
            with open(os.path.join(self.config_dir, new_file), 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            return f"✅ 已添加: {new_file}"
        except Exception as e: return f"❌ 添加失败: {e}"
    
    def _delete_config(self, num: int) -> str:
        try:
            target = f"config-robots{num}.yaml"
            if not os.path.exists(os.path.join(self.config_dir, target)): return f"❌ {target} 不存在"
            os.remove(os.path.join(self.config_dir, target))
            return f"✅ 已删除: {target}"
        except Exception as e: return f"❌ 删除失败: {e}"
