import os
import re
import yaml

# 明确引入 AstrBot 必需的类和装饰器，避免命名冲突
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

# 注册插件 (插件ID, 作者, 描述, 版本)
@register("manage_signin", "songwz", "签到配置管理", "1.0.0", "管理 MihoyoBBSTools 的签到配置文件")
class ManageSigninPlugin(Star):
    # 必须接收 context 并调用父类的 __init__
    def __init__(self, context: Context):
        super().__init__(context)
        # ⚠️ 修改了这里的绝对路径，适配群晖 NAS 的实际路径
        self.config_dir = "/bbs_config/"
        self.base_file = "config-robots.yaml"
        print("✅ 签到管理插件已加载!")

    # 指令1: /签到列表
    @filter.command("签到列表")
    async def list_configs(self, event: AstrMessageEvent):
        result = self._list_configs()
        yield event.plain_result(result)

    # 指令2: /添加签到 <cookie>
    @filter.command("添加签到")
    async def add_config(self, event: AstrMessageEvent, cookie: str = ""):
        if not cookie:
            yield event.plain_result("❌ 用法: /添加签到 <cookie>\ncookie 不能为空")
            return
        result = self._add_config(cookie)
        yield event.plain_result(result)

    # 指令3: /删除签到 <编号>
    @filter.command("删除签到")
    async def delete_config(self, event: AstrMessageEvent, num: int):
        result = self._delete_config(num)
        yield event.plain_result(result)

    def _list_configs(self) -> str:
        """列出所有配置文件"""
        try:
            if not os.path.exists(self.config_dir):
                return f"❌ 目录不存在: {self.config_dir}"
            
            files = [f for f in os.listdir(self.config_dir) 
                    if f.startswith("config-robots") and f.endswith(".yaml")]
            if not files:
                return "📭 当前没有签到配置文件"
            
            files.sort()
            result = "📋 当前签到配置文件列表:\n"
            for f in files:
                file_path = os.path.join(self.config_dir, f)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        config = yaml.safe_load(file)
                        cookie = config.get('account', {}).get('cookie', '')
                        cookie_preview = cookie[:30] + "..." if len(cookie) > 30 else cookie
                        result += f"  - {f}\n    cookie: {cookie_preview}\n"
                except Exception as e:
                    result += f"  - {f} (⚠️ 读取失败: {str(e)})\n"
            return result
        except Exception as e:
            return f"❌ 读取失败: {str(e)}"
    
    def _add_config(self, cookie: str) -> str:
        """添加新的配置文件"""
        try:
            if not os.path.exists(self.config_dir):
                return f"❌ 目录不存在: {self.config_dir}"
            
            # 查找最大编号
            files = [f for f in os.listdir(self.config_dir) 
                    if f.startswith("config-robots") and f.endswith(".yaml")]
            nums = []
            for f in files:
                match = re.search(r"config-robots(\d+)\.yaml", f)
                if match:
                    nums.append(int(match.group(1)))
            next_num = max(nums) + 1 if nums else 1
            
            # 读取模板文件
            template_path = os.path.join(self.config_dir, self.base_file)
            if not os.path.exists(template_path):
                return f"❌ 模板文件 {self.base_file} 不存在"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 修改 cookie
            if 'account' not in config:
                config['account'] = {}
            config['account']['cookie'] = cookie
            
            # 写入新文件
            new_file = f"config-robots{next_num}.yaml"
            new_path = os.path.join(self.config_dir, new_file)
            with open(new_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            return f"✅ 已添加签到配置: {new_file}\nCookie: {cookie[:50]}..."
        except Exception as e:
            return f"❌ 添加失败: {str(e)}"
    
    def _delete_config(self, num: int) -> str:
        """删除配置文件"""
        try:
            if num <= 0:
                return "❌ 编号必须大于 0"
            
            target_file = f"config-robots{num}.yaml"
            target_path = os.path.join(self.config_dir, target_file)
            
            if not os.path.exists(target_path):
                return f"❌ {target_file} 不存在"
            
            if target_file == self.base_file:
                return f"❌ 不能删除主模板 {self.base_file}"
            
            os.remove(target_path)
            return f"✅ 已删除签到配置: {target_file}"
        except Exception as e:
            return f"❌ 删除失败: {str(e)}"
