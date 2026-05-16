HELP = """Pony CLI（opencode-cli 包，命令 pony）

环境变量
  OPENCODE_DATA_DIR    数据根目录（默认 用户\\.local\\share\\opencode）
  OPENCODE_DB          直接指定 opencode.db 完整路径（优先于 DATA_DIR）
  OPENCODE_RECORD_DIR  路径操作 JSON 记录目录（默认 D:\\Pony）；追加写入「路径操作记录.json」（JSON 数组，每条 7 键，与模板一致）
  PONY_SOFTWARE         与 -y 联用：跳过「发起软件」询问时写入记录的 software 字段（可选）

命令
  pony git [--repo URL] [--root 路径] [-y]
                                在 Pony 根目录下清理并重建「Pony_Cursor_repo」，再浅克隆 GitHub 仓库到该
                                文件夹内（默认根: OPENCODE_RECORD_DIR，未设时为 D:\\Pony；完整路径示例
                                D:\\Pony\\Pony_Cursor_repo；默认仓库: PONY_GIT_REPO 或
                                https://github.com/Sam780214/Pony_Cursor.git）
  pony game                     启动「星屑回避」（pygame，入口 game\\main.py）
  pony help                     本说明
  pony list                     直接多选已归档会话（需 questionary，不先整表刷屏）
  pony list --name 片段         先按标题缩小范围
  pony list --note 说明         非交互：对当前匹配结果全部恢复；仍会在执行前确认（可用 -y 跳过）
  pony list [-y]                -y / --yes 跳过「最终确认」（仍会写路径操作记录）

  pony rollback --list          列出 backups 下各次备份
  pony rollback 说明 [-y]       按说明匹配 manifest 并取消归档；-y 跳过确认

  pony rm json --dry-run        仅预览：将删除的无效 JSON（backups）
  pony rm json [-y]            删除 backups 下无效 JSON；-y 跳过确认
  pony rm pick                  多选：backups 下全部 .json（正常+损坏）均可删
  pony rm pick --all [-y]       另含 OPENCODE_RECORD_DIR 下 record_*.json（路径操作记录）；-y 跳过删除前确认

重要操作前会：① 询问「发起软件」（cmd / PowerShell / pwsh / wt / 其他）；② 再询问「确定执行」。
加 -y / --yes 时跳过第②步；第①步可用环境变量 PONY_SOFTWARE 指定，否则记为「未指定(-y)」。
每次成功执行 list / rollback / rm / git 会向「路径操作记录.json」追加一条记录（仅含：时间、发起路径、目标路径、名称、简称、发起软件、ID）；manifest 仍会含 initiator_software（list 时）。

可选依赖: pip install questionary
"""
