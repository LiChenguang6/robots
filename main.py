# main.py
import os
import re
import yaml
from typing import Tuple, Optional
from astrbot.api.all import *

class ManageSigninPlugin:
    """
    签到配置管理插件
    用于管理 MihoyoBBSTools 的 config-robots.yaml 文件
    """
    
    def __init__(self) -> None:
        self.config_dir = "/docker/MihoyoBBSTools-master/config/"
        self.base_file = "config-robots.yaml"
        print("✅ 签到管理插件已加载!")
    
    async def run(self, ame: AstrMessageEvent) -> Tuple[bool, Optional[tuple]]:
        """
        处理消息
        """
        message = ame.message_str.strip()
        
        # 指令1: 显示所有配置文件
        if message == "/签到列表" or message == "签到列表":
            result = self._list_configs()
            return True, (True, result, "签到列表")
        
        # 指令2: 添加配置文件
        elif message.startswith("/添加签到"):
            parts = message.split(maxsplit=1)
            if len(parts) < 2:
                return True, (False, "❌ 用法: /添加签到 <cookie>", "添加签到")
            cookie = parts[1].strip()
            if not cookie:
                return True, (False, "❌ cookie 不能为空", "添加签到")
            result = self._add_config(cookie)
            return True, (True, result, "添加签到")
        
        # 指令3: 删除配置文件
        elif message.startswith("/删除签到"):
            parts = message.split(maxsplit=1)
            if len(parts) < 2:
                return True, (False, "❌ 用法: /删除签到 <编号>", "删除签到")
            try:
                num = int(parts[1].strip())
            except ValueError:
                return True, (False, "❌ 编号必须是数字", "删除签到")
            result = self._delete_config(num)
            return True, (True, result, "删除签到")
        
        # 不处理其他消息
        return False, None
    
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
                match = re.search(r"config-robots(\d*)\.yaml", f)
                if match:
                    num = match.group(1)
                    nums.append(int(num) if num else 0)
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
            
            # 保护主模板文件
            if target_file == self.base_file:
                return f"❌ 不能删除主模板 {self.base_file}"
            
            os.remove(target_path)
            return f"✅ 已删除签到配置: {target_file}"
        except Exception as e:
            return f"❌ 删除失败: {str(e)}"
    
    def info(self) -> dict:
        """插件元信息"""
        return {
            "name": "签到配置管理",
            "desc": "管理 MihoyoBBSTools 的签到配置文件",
            "help": """
📌 签到配置管理插件使用说明:

1. 查看所有配置: /签到列表
   └── 显示所有 config-robots*.yaml 文件

2. 添加新配置: /添加签到 <cookie>
   └── 新建 config-robotsN.yaml (N自动递增)
   └── 只修改 cookie 字段，其他保持不变

3. 删除配置: /删除签到 <编号>
   └── 删除 config-robotsN.yaml
   └── 编号范围: 1 ~ N (不能删除主模板)

📝 示例:
  /签到列表
  /添加签到 _MHYUUID=xxx; cookie_token=xxx
  /删除签到 3
            """,
            "version": "1.0.0",
            "author": "songwz"
        }
