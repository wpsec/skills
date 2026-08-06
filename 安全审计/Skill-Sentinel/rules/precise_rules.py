# -*- coding: utf-8 -*-
# Precise_rules.py
# 场景模式规则：仅检测可能导致实际破坏、后门、数据丢失、权限提升、持久化等的高危操作
# 适用于任何类型的Skill（包括渗透测试、自动化、学术研究等），排除正常的无害操作

MALICIOUS_PATTERNS = {
    # ========== 1. 数据库破坏/数据篡改（渗透测试Skill绝对禁止） ==========
    r"(?i)\bDROP\s+TABLE\b": "删除表 (DROP TABLE) - 破坏数据",
    r"(?i)\bDROP\s+DATABASE\b": "删除数据库 (DROP DATABASE) - 破坏数据",
    r"(?i)\bTRUNCATE\s+TABLE\b": "清空表 (TRUNCATE) - 数据丢失",
    r"(?i)\bDELETE\s+FROM\s+\S+\s+WHERE\s+1=1\b": "无条件删除数据 - 数据丢失",
    r"(?i)\bUPDATE\s+\S+\s+SET\s+\S+\s+WHERE\s+1=1\b": "无条件更新数据 - 数据篡改",
    r"(?i)\bINTO\s+OUTFILE\b": "写入文件到服务器 - Webshell植入",
    r"(?i)\bxp_cmdshell\b": "执行系统命令 (MSSQL) - 命令执行",
    r"(?i)\bexec\s+master\.\.xp_": "扩展存储过程 - 高危",
    r"(?i)\bCREATE\s+USER\b": "创建数据库用户 - 后门账户",
    r"(?i)\bALTER\s+USER\b": "修改数据库用户 - 权限篡改",
    r"(?i)\bGRANT\s+ALL\s+PRIVILEGES\b": "授予所有权限 - 提权",
    r"(?i)\bmysql\.udf\.\w+": "MySQL UDF提权",
    r"(?i)\bredis-cli\s+FLUSHALL\b": "Redis清空全部数据 - 数据丢失",
    r"(?i)\bredis-cli\s+CONFIG\s+SET\s+dir\b": "Redis写文件后门",
    r"(?i)\bmongodrop\s+--drop\b": "MongoDB删除数据库",

    # ========== 2. 文件破坏/覆写/删除（针对用户系统） ==========
    r"(?i)\brm\s+-rf\s+/": "删除根目录 - 系统破坏",
    r"(?i)\bdd\s+of=/dev/sda": "覆写磁盘 - 数据销毁",
    r"(?i)\bformat\s+C:": "格式化C盘 - 系统破坏",
    r"(?i)\bdel\s+/[FSQ]?\s+[\\/]Windows": "删除Windows系统文件",
    r"(?i)\bshutil\.rmtree\s*\(['\"]/(?:home|root|etc|var|usr)": "递归删除关键目录",
    r"(?i)\bos\.remove\s*\(['\"]/etc/passwd['\"]": "删除系统认证文件",
    r"(?i)\bpathlib\.Path\.unlink\s*\(['\"]/etc/shadow['\"]": "删除密码文件",
    r"(?i)\btruncate\s+-s\s+0\s+/var/log/": "清空日志文件 - 痕迹清除",
    r"(?i)\bchmod\s+777\s+/etc/sudoers": "sudoers文件提权",
    r"(?i)\bchown\s+-R\s+\w+:\w+\s+/": "递归更改根目录所有者 - 权限失控",

    # ========== 3. 反弹Shell / 后门植入 / 远程控制 ==========
    r"(?i)\bsocket\.connect\s*\(.*\)\s*;?\s*os\.dup2": "反弹Shell (socket+dup2)",
    r"(?i)\breverse_shell": "反弹Shell字符串",
    r"(?i)\bimport\s+pty;.*spawn": "PTY反弹Shell",
    r"(?i)\bnc\s+-e\s+/bin/sh": "Netcat反弹Shell",
    r"(?i)\bbash\s+-i\s+>&\s+/dev/tcp/": "Bash TCP反弹Shell",
    r"(?i)\bpython\s+-c\s+['\"]import\s+os,pty,socket.*connect": "Python反弹Shell",
    r"(?i)\bperl\s+-e\s+['\"]use\s+Socket;": "Perl反弹Shell",
    r"(?i)\bruby\s+-rsocket\s+-e\s+['\"]": "Ruby反弹Shell",
    r"(?i)\bmsfvenom\s+-p\s+windows/meterpreter": "生成Metasploit后门",
    r"(?i)\bempire\s+launcher": "Empire后门",
    r"(?i)\bcobaltstrike\s+beacon": "CobaltStrike Beacon",
    r"(?i)\bwebshell\s+upload": "上传Webshell",
    r"(?i)\b<?php\s+@eval\($_POST": "PHP一句话木马",
    r"(?i)\b<%@\s+Page\s+Language=\"C#\"\s+Debug=\"true\"": "ASPX Webshell",
    r"(?i)\bssh\s+-R\s+\d+:\d+\.\d+\.\d+\.\d+:\d+": "SSH远程端口转发 - 隧道后门",
    r"(?i)\bssh\s+-L\s+\d+:\d+\.\d+\.\d+\.\d+:\d+": "SSH本地端口转发 - 穿透防火墙",
    r"(?i)\bssh\s+-D\s+\d+": "SSH动态隧道 - SOCKS代理后门",
    r"(?i)\bngrok\s+tcp\s+\d+": "ngrok TCP隧道暴露内网",
    r"(?i)\bfrp\s+client": "FRP内网穿透客户端",
    r"(?i)\bcloudflared\s+tunnel": "Cloudflare Tunnel后门",

    # ========== 4. 持久化与自启动（在用户系统留下后门） ==========
    r"(?i)\bcrontab\s+-e\s+.*\n.*\*.*\*.*\*.*\*.*\*.*\|\s*wget": "crontab定时下载后门",
    r"(?i)\b@reboot\s+.*python\s+-c\s+['\"]": "cron@reboot持久化",
    r"(?i)\bsystemctl\s+enable\s+.*\.service": "启用systemd服务持久化",
    r"(?i)\bHKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run": "Windows注册表启动项持久化",
    r"(?i)\bHKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run": "系统级注册表启动项",
    r"(?i)\bschtasks\s+/create\s+/sc\s+onlogon": "Windows计划任务持久化",
    r"(?i)\blaunchctl\s+load\s+-w\s+~/Library/LaunchAgents/": "macOS LaunchAgent持久化",
    r"(?i)\becho\s+.*\s*>>\s+~/.bashrc": "修改bashrc持久化",
    r"(?i)\becho\s+.*\s*>>\s+~/.zshrc": "修改zshrc持久化",
    r"(?i)\becho\s+.*\s*>>\s+/etc/rc\.local": "修改rc.local持久化",
    r"(?i)\bchattr\s+\+i\s+/etc/crontab": "设置crontab不可变 - 防删除后门",

    # ========== 5. 权限提升（从普通用户提权到root/管理员） ==========
    r"(?i)\bsudo\s+su\s+-": "sudo切换root用户 - 提权",
    r"(?i)\bsudo\s+-u\s+root\s+": "以root执行命令",
    r"(?i)\bsetuid\s*\(": "设置setuid位 - 提权",
    r"(?i)\bsetgid\s*\(": "设置setgid位 - 提权",
    r"(?i)\bcap_set_proc": "设置Linux capabilities提权",
    r"(?i)\binsmod\s+rootkit": "加载内核rootkit",
    r"(?i)\bdkms\s+install\s+--force": "安装恶意内核模块",
    r"(?i)(?:exploit|poc|exploitdb|msf|metasploit|payload|shellcode).*\bCVE-\d{4}-\d{4,}|\bCVE-\d{4}-\d{4,}.*(?:exploit|poc|payload|shellcode|反弹|reverse)": "CVE漏洞利用 (含利用代码)",
    r"(?i)\bSUID\s+shell": "SUID提权shell",
    r"(?i)\bbypass\s+UAC": "绕过UAC (Windows提权)",
    r"(?i)\bpowershell\s+-ExecutionPolicy\s+Bypass": "PowerShell绕过执行策略",

    # ========== 6. 凭据窃取与信息外发（导致用户/目标凭据泄露） ==========
    r"(?i)\bopen\s*\(['\"]/etc/shadow['\"]\)": "读取密码哈希 - 凭据窃取",
    r"(?i)\bopen\s*\(['\"]~/.ssh/id_rsa['\"]\)": "读取SSH私钥 - 身份窃取",
    r"(?i)\bopen\s*\(['\"]~/.aws/credentials['\"]\)": "读取AWS凭证 - 云后门",
    r"(?i)\bopen\s*\(['\"]~/.kube/config['\"]\)": "读取kubeconfig - 集群接管",
    r"(?i)\bopen\s*\(['\"].*\.env['\"]\)": "读取环境变量文件 - 密钥泄露",
    r"(?i)\bos\.environ\[\s*['\"](?:SECRET|KEY|TOKEN|PASSWORD)": "读取敏感环境变量",
    r"(?i)(?:import|from|require|install|pip|npm|exec|eval|system|popen|subprocess|write|open).*keylogger|keylogger.*(?:import|exec|eval|system|popen|subprocess|write|open)": "键盘记录器代码 (非文档引用)",
    r"(?i)\bclipboard\s+read": "读取剪贴板 - 凭证窃取",
    r"(?i)\bgetpass\.getpass\s*\(.*\)\s*;\s*requests\.post": "窃取输入密码并外发",
    r"(?i)\btelegram\.Bot\.send_message\s*\(.*password": "通过Telegram外发密码",
    r"(?i)\bwebhook\.post\s*\(.*cookie": "通过webhook外发Cookie",
    r"(?i)\brequests\.post\s*\(['\"](?:https?://[^'\"]*hook[^'\"]*|https?://[^'\"]*pastebin[^'\"]*)": "外发数据到webhook/pastebin",

    # ========== 7. 破坏性命令执行（对目标系统） ==========
    r"(?i)\bkill\s+-9\s+\d+": "强制结束进程 - DoS",
    r"(?i)\bpkill\s+-f\s+[^&]": "批量杀死进程",
    r"(?i)\bshutdown\s+now": "立即关机 - 服务中断",
    r"(?i)\breboot\s+now": "重启系统 - 服务中断",
    r"(?i)\binit\s+0": "关机 (SysV init)",
    r"(?i)\bpoweroff": "关机",
    r"(?i)\broute\s+del\s+default": "删除默认路由 - 网络中断",
    r"(?i)\biptables\s+-P\s+INPUT\s+DROP": "防火墙阻断所有入站流量",
    r"(?i)\biptables\s+-F": "清空防火墙规则",
    r"(?i)\bip\s+link\s+set\s+eth0\s+down": "禁用网卡 - 网络中断",
    r"(?i)\bifconfig\s+eth0\s+down": "禁用网卡",
    r"(?i)\bdd\s+if=/dev/zero\s+of=/dev/sda": "数据擦除 - 破坏系统",
    r"(?i)\brm\s+-rf\s+/\s*--no-preserve-root": "强制删除根目录",

    # ========== 8. 容器逃逸 / 特权操作 ==========
    r"(?i)\bdocker\s+run\s+--privileged": "运行特权容器 - 逃逸风险",
    r"(?i)\bdocker\s+exec\s+-it\s+\S+\s+bash": "容器内执行bash - 逃逸入口",
    r"(?i)\bkubectl\s+exec\s+--\s+/bin/sh": "Pod内命令执行",
    r"(?i)\bkubectl\s+delete\s+(?:pod|deployment|service)": "删除K8s资源 - 服务中断",
    r"(?i)\bnsenter\s+-t\s+1\s+-m\s+-u\s+-i\s+-n": "进入PID 1命名空间 - 容器逃逸",
    r"(?i)\bmount\s+--bind\s+/host\s+/": "绑定宿主机根目录 - 逃逸",
    r"(?i)\bchroot\s+/host": "chroot到宿主机 - 逃逸",

    # ========== 9. 云资源破坏 ==========
    r"(?i)\baws\s+s3\s+rm\s+--recursive": "递归删除S3存储桶 - 数据丢失",
    r"(?i)\baws\s+ec2\s+terminate-instances": "终止EC2实例 - 服务中断",
    r"(?i)\baws\s+rds\s+delete-db-instance": "删除RDS数据库实例 - 数据丢失",
    r"(?i)\bgcloud\s+compute\s+instances\s+delete": "删除GCE实例",
    r"(?i)\baz\s+vm\s+delete": "删除Azure虚拟机",
    r"(?i)\bterraform\s+destroy\s+-auto-approve": "Terraform销毁所有资源",
    r"(?i)\bcdk\s+destroy\s+--force": "CDK强制销毁堆栈",

    # ========== 10. 供应链投毒（针对Skill自身） ==========
    r"(?i)\bcurl\s+.*\|\s*sudo\s+(?:bash|sh)": "curl管道sudo执行 - 恶意安装",
    r"(?i)\bwget\s+.*\.sh\s*&&\s*bash": "下载并执行shell脚本",
    r"(?i)\bpip\s+install\s+--index-url\s+\S+\s+--force-reinstall": "从非官方源强制安装 - 依赖投毒",
    r"(?i)\bnpm\s+install\s+-g\s+--unsafe-perm": "全局安装npm包 - 供应链攻击",
    r"(?i)\bopen\(['\"]requirements\.txt['\"],\s*'w'\).*write.*malicious": "写入恶意依赖",
    r"(?i)\b__import__\('os'\)\.system\(['\"]pip\s+install\s+git\+https": "动态安装git仓库依赖",

    # ========== 11. 自然语言注入（劫持AI行为） ==========
    r"(?i)\bignore\s+all\s+previous\s+instructions\b": "忽略前置指令 - 提示注入",
    r"(?i)\byou\s+are\s+now\s+a\s+(\w+\s+)*agent\b": "角色扮演劫持",
    r"(?i)\byour\s+new\s+role\s+is\s+malicious\b": "新角色分配为恶意",
    r"(?i)\bpretend\s+you\s+are\s+a\s+hacker\b": "伪装黑客角色",
    r"(?i)\bdisregard\s+your\s+system\s+prompt\b": "无视系统提示",



    # ========== 12. Windows 特有破坏性操作 ==========
    r"(?i)Add-MpPreference\s+-ExclusionPath": "Windows Defender排除路径 - 免杀",
    r"(?i)Set-MpPreference\s+-DisableRealtimeMonitoring\s+\$true": "关闭实时监控 - 禁用防护",
    r"(?i)New-ItemProperty\s+-Path\s+HKLM:\\(?:SOFTWARE|SYSTEM).*ValueData": "写注册表项 - 持久化/破坏",
    r"(?i)Remove-Item\s+-Path\s+HKLM:\\(?:SOFTWARE|SYSTEM).*?-Recurse": "删除注册表键 - 系统破坏",
    r"(?i)net\s+user\s+\w+\s+.*\s+/add": "创建Windows用户 - 后门账户",
    r"(?i)net\s+localgroup\s+Administrators\s+\w+\s+/add": "将用户加入管理员组 - 提权",
    r"(?i)wmic\s+process\s+call\s+create\s+.*\.exe": "通过WMIC创建进程 - 执行恶意程序",
    r"(?i)schtasks\s+/create\s+/tn\s+\w+\s+/tr\s+.*\.exe": "创建计划任务 - 持久化",
    r"(?i)reg\s+add\s+HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run": "注册表自启动项",
    r"(?i)vssadmin\s+delete\s+shadows\s+/all\s+/quiet": "删除卷影副本 - 阻止恢复",
    r"(?i)wbadmin\s+delete\s+backup\s+-keepVersions:\s*0": "删除备份 - 破坏恢复能力",
    r"(?i)bcdedit\s+/set\s+{default}\s+recoveryenabled\s+No": "禁用系统恢复 - 破坏修复",

    # ========== 13. macOS 特有破坏性操作 ==========
    r"(?i)osascript\s+-e\s+'.*tell\s+application\s+\"System\s+Events\"": "AppleScript提权/执行命令",
    r"(?i)defaults\s+write\s+/Library/LaunchDaemons/": "写入LaunchDaemon - 持久化",
    r"(?i)launchctl\s+load\s+-w\s+/Library/LaunchDaemons/.*\.plist": "加载系统级守护进程",
    r"(?i)tmutil\s+delete\s+-d\s+/Volumes/*\.backupdb": "删除Time Machine备份",
    r"(?i)spctl\s+--master-disable": "禁用Gatekeeper - 允许任意应用运行",
    r"(?i)csrutil\s+disable": "禁用SIP系统完整性保护 - 高危",
    r"(?i)kextload\s+-b\s+com\..*\.kext": "加载内核扩展 - 可能为rootkit",

    # ========== 14. 数据库隐蔽后门与破坏 ==========
    r"(?i)CREATE\s+TRIGGER\s+.*\s+AFTER\s+INSERT\s+ON\s+.*\s+BEGIN\s+EXEC\s+xp_cmdshell": "触发器执行命令 - 后门",
    r"(?i)CREATE\s+PROCEDURE\s+.*\s+AS\s+EXEC\s+xp_cmdshell": "存储过程后门",
    r"(?i)ALTER\s+DATABASE\s+.*\s+SET\s+RECOVERY\s+SIMPLE": "修改数据库恢复模式 - 阻止日志恢复",
    r"(?i)DBCC\s+SHRINKFILE\s+\(.*,\s+TRUNCATEONLY\)": "收缩数据库文件 - 可能破坏数据",
    r"(?i)EXEC\s+master\.\.sp_addlinkedserver": "添加链接服务器 - 横向移动",
    r"(?i)CREATE\s+OR\s+REPLACE\s+DIRECTORY\s+.*\s+AS\s+'.*'": "Oracle目录对象 - 文件读写",
    r"(?i)SELECT\s+pg_export_setting\s*\(": "PostgreSQL导出配置 - 信息泄露",
    r"(?i)SELECT\s+pg_read_file\s*\(": "PostgreSQL读取任意文件 - 信息窃取",
    r"(?i)SELECT\s+pg_write_file\s*\(": "PostgreSQL写入文件 - Webshell",
    r"(?i)COPY\s+.*\s+TO\s+PROGRAM\s+':.*'": "PostgreSQL COPY TO PROGRAM - 命令执行",

    # ========== 15. 云权限篡改与资源接管 ==========
    r"(?i)aws\s+iam\s+attach-user-policy\s+--policy-arn\s+arn:aws:iam::aws:policy/AdministratorAccess": "授予用户管理员权限 - 权限提升",
    r"(?i)aws\s+iam\s+create-access-key\s+--user-name": "创建新AccessKey - 后门凭证",
    r"(?i)aws\s+iam\s+update-login-profile\s+--password": "修改用户密码 - 账户接管",
    r"(?i)gcloud\s+iam\s+service-accounts\s+keys\s+create": "创建GCP服务账号密钥 - 后门",
    r"(?i)az\s+role\s+assignment\s+create\s+--role\s+Owner": "授予Azure Owner角色 - 提权",
    r"(?i)az\s+ad\s+app\s+credential\s+reset\s+--id": "重置Azure AD应用凭证 - 后门",
    r"(?i)helm\s+install\s+--set\s+privileged=true": "Helm安装特权Chart - 容器逃逸",

    # ========== 16. AI 自身环境干扰 / 模型投毒 ==========
    r"(?i)os\.environ\[\s*['\"]OPENAI_API_KEY['\"]\s*\]\s*=\s*['\"].*": "修改OpenAI API密钥 - 重定向请求",
    r"(?i)os\.environ\[\s*['\"]ANTHROPIC_API_KEY['\"]\s*\]\s*=\s*['\"].*": "修改Anthropic API密钥",
    r"(?i)~/.anthropic/skills/.*\.md.*write": "写入Skill目录 - 植入恶意Skill",
    r"(?i)~/.config/claude/skills/.*\.json.*write": "修改Claude配置文件",
    r"(?i)CODE_INJECTION\s*=\s*True": "禁用代码注入保护 - 高危",
    r"(?i)sys\.path\.insert\s*\(\s*0,\s*.*\)\s*;.*import": "修改Python路径劫持导入 - 库投毒",
    r"(?i)__import__\('builtins'\)\.exec\s*\(": "绕过内置函数限制执行代码",

    # ========== 17. CI/CD 管道篡改（针对开发环境） ==========
    r"(?i)sed\s+-i\s+.*\.gitlab-ci\.yml": "篡改GitLab CI配置",
    r"(?i)echo\s+.*\s+>>\s+\.github/workflows/.*\.ya?ml": "追加恶意步骤到GitHub Actions",
    r"(?i)jenkins-cli\s+groovy\s+.*\bSystem\.exit": "Jenkins Groovy脚本执行 - 破坏",
    r"(?i)curl\s+-X\s+POST\s+.*/job/.*/build": "触发Jenkins构建 - 可能执行恶意流水线",
    r"(?i)git\s+push\s+--force\s+.*\s+main": "强制推送覆盖主分支 - 代码丢失",
    r"(?i)git\s+reset\s+--hard\s+HEAD~1\s*;.*git\s+push\s+--force": "回退并强制推送 - 删除提交历史",

    # ========== 18. 网络破坏（阻断/劫持流量） ==========
    r"(?i)iptables\s+-I\s+INPUT\s+-p\s+tcp\s+--dport\s+22\s+-j\s+DROP": "阻断SSH端口 - 远程锁死",
    r"(?i)iptables\s+-I\s+OUTPUT\s+-d\s+8\.8\.8\.8\s+-j\s+DROP": "阻断DNS解析 - 网络故障",
    r"(?i)nft\s+add\s+rule\s+ip\s+filter\s+INPUT\s+drop": "nftables阻断所有入站",
    r"(?i)route\s+add\s+0\.0\.0\.0\s+gw\s+1\.2\.3\.4": "修改默认网关 - 流量劫持",
    r"(?i)arp\s+-s\s+.*\s+.*\s+-i\s+eth0": "静态ARP绑定 - 可能ARP欺骗",
    r"(?i)tc\s+qdisc\s+add\s+.*\s+netem\s+loss\s+100%": "模拟100%丢包 - 拒绝服务",

    # ========== 19. 加密勒索/文件锁定 ==========
    r"(?i)encrypt\s+files\s+with\s+AES\s+.*\s+\.encrypted": "加密文件 - 勒索行为",
    r"(?i)bitcoin\s+address\s+1\w{25,34}": "比特币地址 - 勒索赎金",
    r"(?i)ransom\s+note\s+readme\.txt": "勒索信文件名",
    r"(?i)\.locked\s+extension": "锁定文件扩展名 - 勒索",
    r"(?i)send\s+bitcoin\s+to\s+this\s+address": "要求支付比特币",
    r"(?i)gpg\s+--symmetric\s+--passphrase\s+.*\s+--batch\s+.*\.\*": "GPG对称加密文件 - 可能勒索",

    # ========== 20. 额外隐蔽执行/反检测技巧 ==========
    r"(?i)base64\s+-d\s+.*\|\s*bash": "base64解码后执行bash - 混淆",
    r"(?i)echo\s+.*\|\s*base64\s+-d\s*\|\s*bash": "echo base64管道执行",
    r"(?i)python\s+-c\s+['\"]import\s+urllib;.*\.decode\('base64'\)": "Python base64解码执行",
    r"(?i)perl\s+-M\s+MIME::Base64\s+-e\s+.*decode_base64": "Perl base64解码执行",
    r"(?i)openssl\s+enc\s+-d\s+-aes-256-cbc\s+-in\s+.*\s+-out\s+.*\s+-pass\s+pass:": "解密隐藏payload",
    r"(?i)xxd\s+-r\s+-p\s+.*\s+\|\s+bash": "十六进制解码执行",
    r"(?i)(?:curl|wget)\s+-q\s+-O-\s+.*\|\s+sh": "静默下载执行",
    r"(?i)(?:curl|wget)\s+--silent\s+.*\|\s+bash": "静默管道执行",
    r"(?i)tmux\s+new-session\s+-d\s+-s\s+\w+\s+.*\s+&&\s+disown": "后台隐藏会话",
    r"(?i)nohup\s+.*\s+>/dev/null\s+2>&1\s+&": "后台静默执行并丢弃输出",
    r"(?i)screen\s+-dmS\s+\w+\s+.*\s+&&\s+exit": "screen后台会话后退出",


    # ========== 21. 进程注入 / 内存执行 ==========
    r"(?i)VirtualAllocEx\s*\(": "分配远程进程内存 - 进程注入",
    r"(?i)WriteProcessMemory\s*\(": "写入远程进程内存 - 进程注入",
    r"(?i)CreateRemoteThread\s*\(": "创建远程线程 - 进程注入",
    r"(?i)QueueUserAPC\s*\(": "APC注入 - 进程注入",
    r"(?i)SetThreadContext\s*\(": "设置线程上下文 - 进程劫持",
    r"(?i)ntdll\.RtlCreateUserThread": "RtlCreateUserThread - 进程注入",
    r"(?i)ReflectiveLoader": "反射式DLL加载 - 内存执行",
    r"(?i)memfd_create\s*\(": "匿名内存文件执行 - Linux无文件执行",
    r"(?i)execve\s*\(\s*['\"]/proc/self/fd/": "通过文件描述符执行 - 无文件执行",

    # ========== 22. 凭据转储 / 内存提取 ==========
    r"(?i)mimikatz\s+\"privilege::debug\"": "Mimikatz提权 - 凭据窃取",
    r"(?i)sekurlsa::logonpasswords": "Mimikatz导出登录密码",
    r"(?i)lsass\.dmp": "转储lsass进程 - 凭据窃取",
    r"(?i)procdump\s+-ma\s+lsass\.exe": "Procdump转储lsass",
    r"(?i)comsvcs\.dll\s+MiniDump": "通过comsvcs转储lsass",
    r"(?i)Get-Helper\s+Get-LsaLogonSession": "PowerShell获取LSA登录会话",
    r"(?i)mimikatz.*dpapi::cache": "Mimikatz DPAPI解密",
    r"(?i)vaultcmd\s+/listcreds:": "Windows凭据管理器导出",

    # ========== 23. 网络嗅探 / 流量拦截 ==========
    r"(?i)tcpdump\s+-i\s+\w+\s+-w\s+.*\.pcap": "抓包保存 - 流量窃听",
    r"(?i)tshark\s+-i\s+\w+\s+-T\s+fields": "Wireshark命令行抓包",
    r"(?i)scapy\.sniff\s*\(": "Scapy嗅探",
    r"(?i)pyshark\.LiveCapture\s*\(": "PyShark实时抓包",
    r"(?i)mitmproxy\s+-s\s+.*\.py": "mitmproxy脚本劫持流量",
    r"(?i)mitmdump\s+-s\s+.*\.py": "mitmdump脚本劫持",
    r"(?i)bettercap\s+-eval\s+.*net.sniff": "Bettercap嗅探",
    r"(?i)ethtool\s+-K\s+\w+\s+rx\s+off": "关闭网卡RX校验 - 可能流量嗅探",

    # ========== 24. 隐蔽隧道 / 绕过防火墙 ==========
    r"(?i)dns2tcp\s+-c\s+.*\.conf": "DNS隧道客户端",
    r"(?i)iodine\s+-f\s+-P\s+\w+\s+\w+\.\w+": "碘DNS隧道",
    r"(?i)dnscat2\s+--dns\s+domain=\w+\.\w+": "dnscat2 DNS隧道",
    r"(?i)icmptunnel\s+--server": "ICMP隧道",
    r"(?i)ptunnel\s+-p\s+\d+\.\d+\.\d+\.\d+": "ICMP隧道 (ptunnel)",
    r"(?i)http-tunnel\s+--server": "HTTP隧道",
    r"(?i)websocket\s+.*proxy": "WebSocket代理 - 绕过防火墙",
    r"(?i)stunnel\s+.*\.conf": "SSL隧道封装",
    r"(?i)proxychains\s+.*\s+\d+\.\d+\.\d+\.\d+": "Proxychains代理链",

    # ========== 25. Linux能力滥用 / 权限维持 ==========
    r"(?i)setcap\s+cap_net_raw\+ep\s+/usr/bin/python": "赋予Python嗅探能力",
    r"(?i)setcap\s+cap_dac_override\+ep\s+/bin/bash": "能力覆盖DAC - 文件读写绕过",
    r"(?i)setcap\s+cap_sys_ptrace\+ep": "进程跟踪能力 - 可注入",
    r"(?i)getcap\s+-r\s+/": "递归查看能力 - 信息收集",
    r"(?i)capsh\s+--print": "能力打印 - 信息收集",

    # ========== 26. 针对AI模型/数据的篡改 ==========
    r"(?i)model\.weights.*\.pth.*write": "写入PyTorch权重文件 - 模型篡改",
    r"(?i)\.h5.*\bmodel\b.*save": "保存模型 - 可能替换",
    r"(?i)chroma\.add\s+.*\s+metadata": "Chroma向量数据库添加 - 可能投毒",
    r"(?i)pinecone\.upsert\s*\(": "Pinecone向量写入 - 投毒",
    r"(?i)qdrant\.upsert\s*\(": "Qdrant向量写入",
    r"(?i)weaviate\.data_object\.create": "Weaviate对象创建",
    r"(?i)llm\.generate\s+.*\s+prompt\s*=\s*.*DROP\s+TABLE": "LLM生成破坏性SQL - 间接SQL注入",
    r"(?i)langchain\.run\s+.*\s+execute\s+.*DROP": "LangChain执行删除操作",

    # ========== 27. 外泄数据到匿名文件分享服务 ==========
    r"(?i)curl\s+--upload-file\s+.*\s+https?://(?:transfer\.sh|0x0\.st|file\.io)": "上传到匿名分享服务",
    r"(?i)wget\s+--post-file\s+.*\s+https?://(?:pastebin\.com|rentry\.co)": "上传到pastebin类服务",
    r"(?i)requests\.put\s*\(\s*['\"](?:https?://(?:tmp\.ninja|send\.vis\.ee))": "PUT到临时文件服务",
    r"(?i)scp\s+.*\s+.*@\d+\.\d+\.\d+\.\d+:.*": "SCP外发文件",
    r"(?i)rsync\s+-avz\s+.*\s+\d+\.\d+\.\d+\.\d+::": "rsync外发",

    # ========== 28. 清除日志 / 反取证 ==========
    r"(?i)rm\s+-rf\s+/var/log/": "删除系统日志",
    r"(?i)find\s+/var/log/\s+-name\s+\"*.log\"\s+-delete": "批量删除日志",
    r"(?i)history\s+-c": "清空shell历史",
    r"(?i)cat\s+/dev/null\s+>\s+~/.bash_history": "清空bash历史",
    r"(?i)shred\s+-zu\s+.*\.log": "覆写并删除日志",
    r"(?i)wevtutil\s+cl\s+\w+": "清除Windows事件日志",
    r"(?i)Clear-EventLog\s+-Log\s+\w+": "PowerShell清除事件日志",
    r"(?i)Remove-Item\s+.*\.evtx\s+-Force": "删除evtx日志文件",
    r"(?i)auditctl\s+-e\s+0": "禁用Linux审计系统",
    r"(?i)systemd\-journald\-remote\s+--flush": "清空journal日志",

    # ========== 29. 虚拟机逃逸（针对虚拟化环境） ==========
    r"(?i)VMware\s+Tools\s+.*\bCVE-\d{4}-\d{4}\b": "VMware逃逸漏洞利用",
    r"(?i)VirtualBox\s+.*\bCVE-\d{4}-\d{4}\b": "VirtualBox逃逸",
    r"(?i)qemu-kvm\s+.*\bdevice\s+vfio-pci": "QEMU PCI设备穿透 - 可能逃逸",
    r"(?i)echo\s+.*\s+>/sys/kernel/debug/x86/": "写入内核调试接口 - 高危",
    r"(?i)modprobe\s+vmw_balloon": "加载VMware内存气球驱动 - 可能不稳定",

    # ========== 30. 篡改开发工具配置（供应链持久化） ==========
    r"(?i)git\s+config\s+--global\s+url\.\"http://.*\.insteadOf\s+https://github\.com": "Git URL重定向 - 供应链劫持",
    r"(?i)git\s+remote\s+add\s+origin\s+.*@.*\.com:.*/.*\.git": "添加恶意远程仓库",
    r"(?i)sed\s+-i\s+.*\s+package\.json.*\s+\"postinstall\":\s+\".*\"": "npm postinstall脚本篡改",
    r"(?i)sed\s+-i\s+.*\s+package-lock\.json.*\s+\"resolved\":\s+\"http": "修改package-lock.json下载源",
    r"(?i)echo\s+.*\s+>>\s+\.npmrc": "追加npm配置 - 注册表劫持",
    r"(?i)echo\s+.*\s+>>\s+\.pypirc": "追加PyPI配置 - 上传劫持",
    r"(?i)sed\s+-i\s+.*\s+Dockerfile.*\s+RUN\s+curl": "Dockerfile插入恶意RUN",
    r"(?i)sed\s+-i\s+.*\s+Makefile.*\s+curl.*\|.*sh": "Makefile插入恶意命令",



    # ========== 31. 数据库脱裤（批量导出/全量查询） ==========
    r"(?i)SELECT\s+\*\s+FROM\s+\S+\s+(?:WHERE\s+1=1\s+)?(?:;|$)(?!\s+LIMIT)": "全表查询无LIMIT - 可能脱裤",
    r"(?i)SELECT\s+\*\s+FROM\s+\S+\s+(?:WHERE\s+1=1\s+)?\s*;.*SELECT\s+\*\s+FROM": "多表全量查询 - 逐表脱裤",
    r"(?i)mysqldump\s+-u\s+\S+\s+-p\S*\s+--all-databases": "MySQL全库导出 - 脱裤",
    r"(?i)mysqldump\s+-u\s+\S+\s+-p\S*\s+--databases\s+\S+": "MySQL指定库导出 - 脱裤",
    r"(?i)pg_dump\s+-U\s+\S+\s+-d\s+\S+\s+-F\s+c\s+-f\s+.*\.dump": "PostgreSQL导出 - 脱裤",
    r"(?i)pg_dumpall\s+-U\s+\S+": "PostgreSQL全库导出",
    r"(?i)mongoexport\s+--db\s+\S+\s+--collection\s+\S+\s+--out\s+.*\.json": "MongoDB导出集合 - 脱裤",
    r"(?i)mongodump\s+--db\s+\S+\s+--out\s+": "MongoDB全库备份 - 脱裤",
    r"(?i)sqlite3\s+\S+\.db\s+\.dump": "SQLite导出全部数据 - 脱裤",
    r"(?i)redis-cli\s+--scan\s+--pattern\s+\*\s*\|\s*xargs\s+redis-cli\s+get": "Redis遍历所有键值 - 脱裤",
    r"(?i)redis-cli\s+KEYS\s+\*\s*\|\s*xargs\s+redis-cli\s+MGET": "Redis批量获取所有key - 脱裤",
    r"(?i)INTO\s+OUTFILE\s+'.*\.(?:csv|sql|txt)'": "MySQL导出到文件 - 数据提取",
    r"(?i)COPY\s+.*\s+TO\s+'(?:/tmp|/var/www|C:\\).*\.(?:csv|sql|txt)'": "PostgreSQL COPY导出文件",
    r"(?i)SELECT\s+\*\s+FROM\s+\S+\s+LIMIT\s+\d{4,}": "LIMIT数量极大(≥1000) - 批量导出",
    r"(?i)SELECT\s+\*\s+FROM\s+\S+\s+WHERE\s+id\s+>=\s*0\s+AND\s+id\s+<=\s*\d{5,}": "范围查询覆盖大量行 - 批量导出",
    r"(?i)SELECT\s+\*\s+FROM\s+\S+\s+WHERE\s+1=1\s+UNION\s+SELECT\s+.*\s+FROM\s+\S+": "UNION注入批量提取数据",
    r"(?i)SELECT\s+GROUP_CONCAT\(.*\)\s+FROM\s+\S+": "MySQL GROUP_CONCAT批量拼接 - 一次性提取多行",
    r"(?i)FOR\s+EACH\s+ROW\s+BEGIN\s+INSERT\s+INTO\s+backup_table": "触发器批量复制数据 - 隐蔽脱裤",
    r"(?i)CREATE\s+TABLE\s+backup_.*\s+AS\s+SELECT\s+\*\s+FROM": "创建备份表复制全部数据",
    r"(?i)SELECT\s+\*\s+FROM\s+.*\s+INTO\s+@\w+": "变量批量接收数据 - 内存脱裤",
    r"(?i)\bhttp(?:s?)://.*/api/.*\?(?:page|offset|start)=\d+(?:&limit=)?\d{4,}": "API接口请求大量分页数据(limit≥1000) - 批量导出",
    r"(?i)\bhttp(?:s?)://.*/api/.*\?(?:page|offset|start)=(\d+)&(?:limit=\1\s*&?)*page=\d+": "API自动翻页循环 - 遍历所有数据",
    r"(?i)while\s+True:\s+requests\.get\(.*page=": "循环拉取所有分页数据 - 脱裤",
    r"(?i)for\s+page\s+in\s+range\(1,\s+\d+\)": "循环遍历多页拉取数据",


}




