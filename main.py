# data/plugins/manage_signin.py
import os
import re
import yaml
from astrbot.api.all import *

@register("manage_signin", "签到管理插件", "1.0.0", "管理 MihoyoBBSTools 的账号配置")
class ManageSigninPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config_dir = "/docker/MihoyoBBSTools-master/config/"

    @command("签到列表")
    async def list_signin(self, event: AstrMessageEvent):
        files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
        if not files:
            yield event.plain_result("📭 当前没有签到配置文件")
            return
        files.sort()
        result = "📋 当前签到配置文件列表:\n" + "\n".join([f"  - {f}" for f in files])
        yield event.plain_result(result)

    @command("添加签到")
    async def add_signin(self, event: AstrMessageEvent, cookie: str):
        # 查找最大编号
        files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
        nums = []
        for f in files:
            match = re.search(r"config-robots(\d*)\.yaml", f)
            if match:
                num = match.group(1) or 0
                nums.append(int(num))
        next_num = max(nums) + 1 if nums else 1
        
        # 读取模板
        template_path = os.path.join(self.config_dir, "config-robots.yaml")
        with open(template_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 修改 cookie
        config['account']['cookie'] = cookie
        
        # 写入新文件
        new_path = os.path.join(self.config_dir, f"config-robots{next_num}.yaml")
        with open(new_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        
        yield event.plain_result(f"✅ 已添加签到配置: config-robots{next_num}.yaml")

    @command("删除签到")
    async def delete_signin(self, event: AstrMessageEvent, num: int):
        if num <= 0:
            yield event.plain_result("❌ 编号必须大于 0")
            return
        
        # 检查是否存在
        target = os.path.join(self.config_dir, f"config-robots{num}.yaml")
        if not os.path.exists(target):
            yield event.plain_result(f"❌ config-robots{num}.yaml 不存在")
            return
        
        # 禁止删除主模板
        if num == 0 or target.endswith("config-robots.yaml"):
            yield event.plain_result("❌ 不能删除主模板 config-robots.yaml")
            return
        
        os.remove(target)
        yield event.plain_result(f"✅ 已删除签到配置: config-robots{num}.yaml")
