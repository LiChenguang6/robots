# Redmi K50 QQ 唤醒助手 - GitHub Actions 构建

当前分支仅用于构建 Android 接收端，不改变 robots 仓库的默认分支代码。

- 触发：推送到 k50-wake-apk-build 分支，或 Actions > Build Redmi K50 Wake APK > Run workflow。
- 构建产物：工作流详情页 Artifacts 下的 K50-QQ-Wake-debug-APK.zip，解压后获得 app-debug.apk。
- 使用：在红米 K50 安装；AstrBot 插件另行部署在群晖 NAS。
- 安全：不要把 NAS 设备密钥、QQ 白名单或其他私密配置提交到公开 GitHub 仓库。
- 限制：当前是调试签名 APK，尚未验证红米 K50 实际蓝牙 HID 行为及后台存活。
- 源码：k50-wake/packed-source.b64 是 android_k50_wake 项目的 tar.xz Base64 编码归档；workflow 自动解包编译。

原始完整源码包仍可在 ChatGPT 会话中获取，之后可迁移到专用 GitHub 仓库。
