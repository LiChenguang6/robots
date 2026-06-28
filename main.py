import os
import re
import yaml
import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import MessageChain

@register("manage_signin", "songwz", "签到配置与日志推送", "1.2.0", "管理签到配置并实时推送日志")
class ManageSigninPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_dir = "/bbs_config/"
        self.log_dir = "/bbs_logs/"
        self.base_file = "config-robots.yaml"
        
        self.push_target = None
        self.last_log_file = ""
        self.last_position = 0
        
        self.task = asyncio.create_task(self._watch_logs())
        print("✅ 签到管理与日志推送插件 (V1.2) 已加载!")

    # ==========================
    # 基础指令：配置管理
    # ==========================
    @filter.command("签到列表")
    async def list_configs(self, event: AstrMessageEvent):
        yield event.plain_result(self._list_configs())

    @filter.command("添加签到")
    async def add_config(self, event: AstrMessageEvent, cookie: str = ""):
        if not cookie:
            yield event.plain_result("❌ 用法: /添加签到 <cookie>\ncookie 不能为空")
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
        """绑定当前群聊，接收自动更新的日志"""
        self.push_target = event.message_obj.sender
        # 绑定时顺便把当前日志大小记录下来，防止一绑定就把老日志全发出来刷屏
        try:
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
                latest_file = files[0]
                self.last_log_file = latest_file
                self.last_position = os.path.getsize(os.path.join(self.log_dir, latest_file))
        except Exception:
            pass
            
        yield event.plain_result("✅ 绑定成功！\nMihoyoBBSTools 生成新日志后将自动推送至本群。\n(⚠️ 重启机器人需重新绑定)")

    @filter.command("最新日志")
    async def get_latest_log(self, event: AstrMessageEvent):
        """手动获取当前最新的几十行日志"""
        try:
            if not os.path.exists(self.log_dir):
                yield event.plain_result(f"❌ 日志目录不存在: {self.log_dir}")
                return
                
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            if not files:
                yield event.plain_result("📭 暂无 .log 日志文件")
                return
                
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
            latest_file = files[0]
            file_path = os.path.join(self.log_dir, latest_file)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # 取最后 30 行，防止文字过长发不出
                tail_lines = "".join(lines[-30:])
                
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_text = ansi_escape.sub('', tail_lines)
            
            yield event.plain_result(f"📄 {latest_file} 最新日志:\n{clean_text}")
        except Exception as e:
            yield event.plain_result(f"❌ 读取日志失败: {str(e)}")

    # ==========================
    # 后台日志轮询机制
    # ==========================
    async def _watch_logs(self):
        while True:
            await asyncio.sleep(60)
            if not self.push_target:
                continue
            try:
                await self._check_and_push()
            except Exception as e:
                print(f"日志监控异常: {e}")

    async def _check_and_push(self):
        if not os.path.exists(self.log_dir):
            return
        files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
        if not files:
            return
            
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_dir, x)), reverse=True)
        latest_file = files[0]
        file_path = os.path.join(self.log_dir, latest_file)
        
        if self.last_log_file != latest_file:
            self.last_log_file = latest_file
            self.last_position = 0
            
        current_size = os.path.getsize(file_path)
        
        if current_size > self.last_position:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_lines = f.read().strip()
                self.last_position = f.tell()
                
            if new_lines:
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_text = ansi_escape.sub('', new_lines)
                
                if len(clean_text) > 1500:
                    clean_text = clean_text[:1500] + "\n...[日志过长，已截断]"
                
                msg = f"📢 [新签到动态]\n{clean_text}"
                await self.context.send_message(self.push_target, MessageChain().message(msg))
                
        elif current_size < self.last_position:
            self.last_position = 0

    # ==========================
    # 原有的配置读写逻辑保持不变
    # ==========================
    def _list_configs(self) -> str:
        try:
            if not os.path.exists(self.config_dir): return f"❌ 目录不存在: {self.config_dir}"
            files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
            if not files: return "📭 当前没有签到配置文件"
            files.sort()
            result = "📋 当前签到配置文件列表:\n"
            for f in files:
                try:
                    with open(os.path.join(self.config_dir, f), 'r', encoding='utf-8') as file:
                        cookie = yaml.safe_load(file).get('account', {}).get('cookie', '')
                        result += f"  - {f}\n    cookie: {cookie[:30]}...\n"
                except Exception:
                    result += f"  - {f} (⚠️ 读取失败)\n"
            return result
        except Exception as e: return f"❌ 读取失败: {str(e)}"
    
    def _add_config(self, cookie: str) -> str:
        try:
            if not os.path.exists(self.config_dir): return f"❌ 目录不存在"
            files = [f for f in os.listdir(self.config_dir) if f.startswith("config-robots") and f.endswith(".yaml")]
            nums = [int(re.search(r"config-robots(\d+)\.yaml", f).group(1)) for f in files if re.search(r"config-robots(\d+)\.yaml", f)]
            next_num = max(nums) + 1 if nums else 1
            with open(os.path.join(self.config_dir, self.base_file), 'r', encoding='utf-8') as f: config = yaml.safe_load(f)
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
