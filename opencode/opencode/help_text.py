HELP = """Pony CLI（opencode-cli 包，命令 pony）

环境变量
  PONY_LOCAL_ONLY_ROOT  本地缓存/构建根（默认 D:\\Pony\\local-only）
  OPENCODE_DATA_DIR     数据根（默认 local-only/opencode/data）
  OPENCODE_DB           直接指定 opencode.db 完整路径
  OPENCODE_RECORD_DIR    路径操作 JSON 记录目录（默认 Pony 工作区根 D:\\Pony）
  PONY_GIT_REPO         pony git 默认仓库 URL
  PONY_SOFTWARE         与 -y 联用：跳过「发起软件」询问时写入记录的 software 字段

命令
  pony git [--repo URL] [--root 路径] [-y]
                                在 Pony 根目录下清理并重建「Pony_Cursor_repo」，再浅克隆 GitHub
                                （默认根 D:\\Pony，目标 D:\\Pony\\Pony_Cursor_repo）
  pony game                     启动「星屑回避」（pygame，入口 game\\main.py）
  pony help                     本说明
  pony list                     直接多选已归档会话（需 questionary）
  pony list --name 片段         先按标题缩小范围
  pony list --note 说明         非交互：对当前匹配结果全部恢复
  pony list [-y]                -y 跳过「最终确认」

  pony rollback --list          列出 backups 下各次备份
  pony rollback 说明 [-y]       按说明匹配 manifest 并取消归档

  pony rm json --dry-run        仅预览：将删除的无效 JSON（backups）
  pony rm json [-y]             删除 backups 下无效 JSON
  pony rm pick                  多选 backups 下 .json
  pony rm pick --all [-y]       另含 OPENCODE_RECORD_DIR 下 record_*.json

重要操作前会询问「发起软件」与「确定执行」；加 -y 跳过最终确认。
每次成功执行 list / rollback / rm / git 会追加路径操作记录。

可选依赖: pip install questionary
"""
