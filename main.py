import os
import re
import yaml
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import MessageChain

@register("manage_signin", "songwz", "签到配置与日志推送", "1.1.0", "管理签到配置并实时推送日志")
class ManageSigninPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_dir = "/bbs_config/"
        self.log_dir = "/bbs_logs/"  # 新增的日志映射目录
        self.base_file = "config-robots.yaml"
        
        # --- 日志推送相关的状态记录 ---
        self.push_target = None       # 存储要把消息推送到哪个群（目标对象）
        self.last_log_file = ""       # 记录当前正在读取的日志文件名
        self.last_position = 0        # 记录上次读取到了文件的第几个字节 (指针)
        
        # 启动后台轮询任务
        self.task = asyncio.create_task(self._watch_logs())
        print("✅ 签到管理与日志推送插件已加载!")

    # ==========================
    # 基础指令部分
    # ==========================
    @filter.command("签到列表")
    async def list_configs(self, event: AstrMessageEvent):
        result = self._list_configs()
        yield event.plain_result(result)

    @filter.command("添加签到")
    async def add_config(self, event: AstrMessageEvent, cookie: str = ""):
        if not cookie:
            yield event.plain_result("❌ 用法: /添加签到 <cookie>\ncookie 不能为空")
            return
        result = self._add_config(cookie)
        yield event.plain_result(result)

    @filter.command("删除签到")
    async def delete_config(self, event: AstrMessageEvent, num: int):
        result = self._delete_config(num)
        yield event.plain_result(result)

    # ==========================
    # 新增：绑定推送群聊指令
    # ==========================
    @filter.command("绑定推送")
    async def bind_push(self, event: AstrMessageEvent):
        """在这个群里发这句指令，机器人就会把这个群记下来"""
        self.push_target = event.message_obj.sender
        yield event.plain_result("✅ 绑定成功！\nMihoyoBBSTools 的签到日志更新后，将自动推送到本群。\n(⚠️注意：如果机器人重启，需要重新发一次 /绑定推送)")

    # ==========================
    # 后台日志轮询机制
    # ==========================
    async def _watch_logs(self):
        """每隔60秒在后台默默检查一次日志文件"""
        while True:
            await asyncio.sleep(60)
            
            # 如果还没绑定群，就不费劲去读日志了
            if not self.push_target:
                continue
                
            try:
                await self._check_and_push()
            except Exception as e:
                print(f"日志监控出现异常: {e}")

    async def _check_and_push(self):
        if not os.path.exists(self.log_dir):
            return
            
        # 找到目录下的所有 .log 文件
        files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
        if not files:
            return
            
        # 按文件的最后修改时间排序，拿到最新发生变化的那个日志文件
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
        latest_file = files[0]
        file_path = os.path.join(self.log_dir, latest_file)
        
        # 如果生成了新的日志文件（比如过零点换了新的一天），就把指针归零
        if self.last_log_file != latest_file:
            self.last_log_file = latest_file
            self.last_position = 0
            
        current_size = os.path.getsize(file_path)
        
        # 文件变大了，说明有新日志写入！
        if current_size > self.last_position:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)  # 直接跳到上次读完的位置
                new_lines = f.read().strip()
                self.last_position = f.tell()  # 更新指针位置
                
            if new_lines:
                # 清理掉日志里可能带有的终端颜色代码 (ANSI 字符)，防止在 QQ 里乱码
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_text = ansi_escape.sub('', new_lines)
                
                # 做个字数限制，防止日志突然大爆发刷屏
                if len(clean_text) > 1500:
                    clean_text = clean_text[:1500] + "\n...[日志过长，已截断]"
                
                # 组装消息并发到群里
                msg = f"📢 [签到日志更新]\n{clean_text}"
                await self.context.send_message(self.push_target, MessageChain().message(msg))
                
        # 兜底：如果文件大小反而变小了（可能被系统清理或者覆盖了），重置指针
        elif current_size < self.last_position:
            self.last_position = 0

    # ==========================
    # 以下是原有的文件读写逻辑
    # ==========================
    def _list_configs(self) -> str:
        try:
            if not os.path.exists(self.config_dir):
                return f"❌ 目录不存在: {self.config_dir}"
            files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
            if not files: return "📭 当前没有签到配置文件"
            files.sort()
            result = "📋 当前签到配置文件列表:\n"
            for f in files:
                try:
                    with open(os.path.join(self.config_dir, f), 'r', encoding='utf-8') as file:
                        cookie = yaml.safe_load(file).get('account', {}).get('cookie', '')
                        result += f"  - {f}\n    cookie: {cookie[:30]}...\n"
                except Exception as e:
                    result += f"  - {f} (⚠️ 读取失败)\n"
            return result
        except Exception as e: return f"❌ 读取失败: {str(e)}"
    
    def _add_config(self, cookie: str) -> str:
        try:
            if not os.path.exists(self.config_dir): return f"❌ 目录不存在"
            files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
            nums = [int(re.search(r"config-robots(\d+)\.yaml", f).group(1)) for f in files if re.search(r"config-robots(\d+)\.yaml", f)]
            next_num = max(nums) + 1 if nums else 1
            
            with open(os.path.join(self.config_dir, self.base_file), 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'account' not in config: config['account'] = {}
            config['account']['cookie'] = cookie
            
            new_file = f"config-robots{next_num}.yaml"
            with open(os.path.join(self.config_dir, new_file), 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            return f"✅ 已添加签到配置: {new_file}\nCookie: {cookie[:50]}..."
        except Exception as e: return f"❌ 添加失败: {str(e)}"
    
    def _delete_config(self, num: int) -> str:
        try:
            if num <= 0: return "❌ 编号必须大于 0"
            target_file = f"config-robots{num}.yaml"
            target_path = os.path.join(self.config_dir, target_file)
            if not os.path.exists(target_path): return f"❌ {target_file} 不存在"
            if target_file == self.base_file: return f"❌ 不能删除主模板"
            os.remove(target_path)
            return f"✅ 已删除: {target_file}"
        except Exception as e: return f"❌ 删除失败: {str(e)}"
