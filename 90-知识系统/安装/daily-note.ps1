$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$python = 'C:\Users\stove\AppData\Local\Programs\Python\Python312\python.exe'
$kb = 'D:\notes\90-知识系统\脚本\kb.py'
$log = "$env:USERPROFILE\.codex\kb-daily.log"
& $python $kb daily 2>&1 | Out-File -FilePath $log -Append -Encoding utf8