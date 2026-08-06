# -*- coding: utf-8 -*-
# apt_rules.py — APT 级别增强规则
#
# 针对高级持续性威胁 (APT) 的检测规则，覆盖现有 total_rules / precise_rules 的盲区。
# 设计原则:
#   - 每类规则标注 MITRE ATT&CK 对应技术 ID
#   - 关注多阶段、混淆、隐蔽通道等 APT 特征
#   - 减少对低危常规操作的误报

MALICIOUS_PATTERNS = {
    # ============================================================
    # 1. LOLBin 利用 — 利用系统可信工具执行恶意代码
    # MITRE: T1218 (System Binary Proxy Execution)
    # 盲区原因: 现有规则只检测 os.system/subprocess，不检测系统工具滥用
    # ============================================================

    # --- Windows LOLBin ---
    r"(?i)\bcertutil\s+-(?:decode|urlcache|encode|split)": "certutil 解码/下载载荷 (Windows LOLBin)",
    r"(?i)\bmshta\s+(?:javascript|vbscript|http)": "mshta 执行远程脚本 (Windows LOLBin)",
    r"(?i)\bregsvr32\s+/[suU].*\/i:\s*http": "regsvr32 远程加载 COM 脚本 (Squiblydoo)",
    r"(?i)\brundll32\s+\S+\.dll,\S+\s+(?:http|javascript):": "rundll32 远程执行 (Windows LOLBin)",
    r"(?i)\bmsbuild\s+(?:-[tp]\S+\s+)*http": "MSBuild 加载远程项目 (Windows LOLBin)",
    r"(?i)\bcsc(?:\.exe)?\s+/t(?:arget)?:library\s+/out:": "csc.exe 动态编译 C# (Windows LOLBin)",
    r"(?i)\bwmic\s+/node:\S+\s+/user:\S+\s+/password:\S+\s+process\s+call\s+create": "WMIC 远程横向移动",
    r"(?i)\bwmic\s+process\s+call\s+create\s+['\"].*(?:powershell|cmd|wscript)": "WMIC 创建可疑进程",
    r"(?i)\bcmstp\s+/s\s+\S+\.inf": "cmstp 加载恶意 INF 文件 (CMSTP 绕过)",
    r"(?i)\bfodhelper\s*/regserver": "fodhelper UAC 绕过 (Windows)",
    r"(?i)\beventvwr\s*\S*\s+file": "eventvwr 注册表劫持 UAC 绕过",
    r"(?i)\bmsiexec\s+/i\s+http\S+\.msi\s+/q": "msiexec 静默安装远程 MSI",
    r"(?i)\bmsiexec\s+/y\s+\S+\s+/q": "msiexec 远程 DLL 注册",
    r"(?i)\breplace\s+utilman\.exe\s+cmd\.exe": "Utilman 替换后门 (粘滞键后门)",
    r"(?i)\bsethc\.exe\s+.*\s+cmd\.exe": "粘滞键后门",
    r"(?i)\bwscript\s+//[eb]\S*\s+http": "wscript/cscript 远程脚本执行",
    r"(?i)\bpowershell\s+-[eE][nNcC]\s+\S{20,}": "PowerShell 编码命令 (Base64 混淆)",
    r"(?i)\bpowershell\s+-[wW]indow[Ss]tyle\s+[hH]idden": "PowerShell 隐藏窗口执行",
    r"(?i)\bpowershell\s+.*-NoP\s.*-NonI\s.*-W\s*Hidden\s.*-Exec\s*Bypass": "PowerShell 全绕过执行",
    r"(?i)\bpowershell\s+.*IEX\s*\(\s*New-Object\s+Net\.WebClient": "PowerShell 下载执行 (IEX+WebClient)",
    r"(?i)\bInvoke-Expression\s*\(": "PowerShell IEX 动态执行",
    r"(?i)\bInvoke-RestMethod\s+-Uri\s+http.*\|\s*IEX": "PowerShell 远程下载执行",
    r"(?i)\bDownloadString\s*\(\s*['\"](?:http|ftp)": "PowerShell 远程下载字符串",
    r"(?i)\bDownloadFile\s*\(\s*['\"](?:http|ftp)": "PowerShell 远程下载文件",
    r"(?i)\bStart-BitsTransfer\s+-Source\s+http": "BITS 传输下载 (Windows 后台下载)",
    r"(?i)\bbitsadmin\s+/transfer\s+\S+\s+http\S+\s+\S+\.exe": "bitsadmin 下载载荷",
    r"(?i)\bwget\s+--no-check-certificate\s+.*\s+-O\s+/tmp/": "wget 忽略证书验证下载",
    r"(?i)\bcurl\s+-[kK]\s+.*\s+-o\s+/tmp/": "curl 忽略 SSL 验证下载",

    # --- macOS LOLBin ---
    r"(?i)\bosascript\s+-e\s+['\"]do\s+shell\s+script\s+\"": "osascript 执行 shell 命令 (macOS)",
    r"(?i)\bosascript\s+-e\s+['\"]tell\s+app\s+\"Finder\"": "osascript 操控 Finder (macOS)",
    r"(?i)\bosascript\s+-e\s+['\"]display\s+dialog": "osascript 伪造对话框 (macOS 钓鱼)",
    r"(?i)\bswift\s+-e\s+['\"]import\s+Foundation\s*;.*Process": "Swift 单行执行命令 (macOS)",
    r"(?i)\bautomator\s+-i\s+\S+\.(?:workflow|app)\s+-D\s+": "Automator 无界面执行工作流 (macOS)",
    r"(?i)\bpluginkit\s+-a\s+-i\s+com\..*\.plugin": "pluginkit 加载恶意插件 (macOS)",
    r"(?i)\bsdef\s+\S+\.\S+\s+\|\s+osascript": "sdef 脚本定义提取 (macOS AppleScript 注入)",
    r"(?i)\bdefaults\s+write\s+-g\s+ApplePersistence": "修改全局持久化设置 (macOS)",
    r"(?i)\bpbcopy\s+<\s+(?:/etc/passwd|/etc/shadow|~/.ssh)": "pbcopy 窃取敏感文件 (macOS)",
    r"(?i)\bpbpaste\s*\|\s*(?:bash|sh|python)": "pbpaste 管道执行 (macOS 剪贴板攻击)",
    r"(?i)\bsqlite3\s+~/Library/\S+\.db\s+\"SELECT\s+\*\s+FROM": "读取 macOS 系统数据库 (信息窃取)",
    r"(?i)\bsecurity\s+find-generic-password\s+-wa": "macOS 钥匙串密码提取",
    r"(?i)\bsecurity\s+add-generic-password\s+-a\s+\S+\s+-s\s+\S+\s+-w": "macOS 钥匙串写入 (后门)",
    r"(?i)\bscutil\s+--get\s+ComputerName\s*\|\s*curl": "获取系统信息并外发 (macOS)",

    # --- Linux LOLBin ---
    r"(?i)\bsystemd-run\s+--user\s+-p\s+Environment=.*\s+bash\s+-c": "systemd-run 用户级持久化执行",
    r"(?i)\bbusctl\s+call\s+org\.freedesktop\.systemd1.*\s+StartTransientUnit": "D-Bus 创建瞬态服务 (无文件持久化)",
    r"(?i)\bpkexec\s+--user\s+\w+\s+(?:bash|sh|python)": "pkexec 以其他用户执行 (提权)",
    r"(?i)\bscript\s+-c\s+['\"].*\|\s*curl.*\|\s*bash": "script -c 管道执行 (日志绕过)",
    r"(?i)\bstdbuf\s+-oL\s+(?:bash|sh)\s+-c": "stdbuf 修改输出缓冲执行 (日志绕过)",
    r"(?i)\bunbuffer\s+(?:bash|sh)\s+-c": "unbuffer 执行命令 (绕过输出缓冲)",
    r"(?i)\bldd\s+\S+\.so\s*\|\s*bash": "ldd 加载恶意 .so (LD 劫持)",
    r"(?i)\bxargs\s+-I\s+\{\}\s+(?:bash|sh)\s+-c\s+\{\}": "xargs 执行命令 (批量执行绕过)",
    r"(?i)\bfind\s+/tmp\s+-name\s+['\"]\S+\.(?:sh|py|elf)\s+-exec\s+chmod\s+\+x": "find 批量添加可执行权限 (载荷准备)",
    r"(?i)\brename\s+\S+\.txt\s+\S+\.(?:sh|py|elf)\s+/tmp/": "批量重命名载荷 (混淆)",
    r"(?i)\btee\s+-a\s+(?:/etc/passwd|/etc/shadow|/etc/sudoers|/etc/crontab)": "tee 追加系统关键文件 (持久化)",

    # ============================================================
    # 2. 高级混淆与反检测
    # MITRE: T1027 (Obfuscated Files or Information)
    # 盲区原因: 现有规则只检测简单的 base64 -d，不检测多级编码/字符串拼接/Unicode 混淆
    # ============================================================

    # 多级编码链
    r"(?i)base64.*\.b64decode.*\.decode.*(?:exec|eval|subprocess)": "Base64 解码后执行 (链式解码)",
    r"(?i)binascii\.(?:a2b_hex|unhexlify).*(?:exec|eval)": "十六进制解码后执行",
    r"(?i)codecs\.decode\s*\(.*['\"](?:base64|rot_13|hex|zip)['\"]\s*\)": "codecs 解码执行",
    r"(?i)zlib\.decompress\s*\(.*base64": "zlib 解压+Base64 解码 (双层编码)",
    r"(?i)lzma\.decompress\s*\(.*base64": "lzma 解压+Base64 解码",
    r"(?i)gzip\.decompress\s*\(.*(?:base64|b64decode)": "gzip 解压+Base64 解码",
    r"(?i)pickle\.loads\s*\(.*(?:base64|b64decode|zlib)": "反序列化解码载荷 (高危)",
    r"(?i)marshal\.loads\s*\(.*(?:base64|b64decode|codecs)": "marshal 解码载荷 (Python 字节码执行)",
    r"(?i)compile\s*\(.*(?:base64|b64decode|fromhex).*['\"]exec['\"]": "compile 解码后执行 (动态代码对象)",

    # 字符串拼接绕过
    r"(?i)(?:['\"]o['\"]\s*\+\s*['\"]s['\"]|chr\(\d+\)\s*\+\s*chr\(\d+\))\s*\+.*system": "字符串拼接 os.system (绕过字面匹配)",
    r"(?i)(?:getattr|__getattribute__)\s*\(\s*__(?:import|builtins)__": "getattr 动态访问内置函数 (绕过)",
    r"(?i)__builtins__\s*\[\s*['\"]\w{3,}\s*\+\s*\w{3,}['\"]\s*\]": "builtins 字符串拼接键访问 (绕过)",
    r"(?i)globals\s*\(\s*\)\s*\[\s*['\"]\w{3,}\s*\+\s*\w{3,}['\"]\s*\]": "globals 字符串拼接键访问 (绕过)",
    r"(?i)vars\s*\(\s*\)\s*\[\s*.*\s*\+\s*.*\s*\]": "vars 字符串拼接键访问 (绕过)",
    r"(?i)type\s*\(.*\)\s*\(\s*['\"]\w+\s*\+\s*\w+['\"]\s*\)": "type 动态构造调用 (绕过)",

    # Unicode 混淆 — 检测真正的同形字（排除 case-insensitive 下匹配 ASCII 的字符）
    r"(?i)(?:exec|eval|import|system|popen|subprocess)\s*\(.*[ﬀ-ﬆ]": "Unicode 连字混淆+敏感函数调用 (绕过检测)",
    r"(?i)['\"]\\u[0-9a-fA-F]{4}['\"]\s*\+\s*['\"]\\u[0-9a-fA-F]{4}['\"]\s*\+": "Unicode 转义序列连续拼接 (绕过)",
    r"(?i)['\"]\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}['\"]": "连续四个十六进制转义字符 (混淆)",

    # 动态代码生成
    r"(?i)exec\s*\(\s*['\"].*['\"]\s*%\s*": "exec 格式化字符串执行 (动态代码)",
    r"(?i)exec\s*\(\s*f['\"].*\{.*\}.*['\"]": "exec f-string 执行 (动态代码)",
    r"(?i)exec\s*\(\s*['\"]\\n.*\\n['\"]": "exec 多行代码字符串执行",
    r"(?i)type\s*\(\s*['\"]code['\"]\s*,\s*\(\s*\)\s*,\s*\{.*__init__": "type 动态创建类 (代码注入)",
    r"(?i)new\.function\s*\(\s*code\s*,\s*globals": "new.function 动态创建函数 (Python 2/3 绕过)",
    r"(?i)types\.FunctionType\s*\(\s*code\s*,\s*\{.*['\"]exec['\"]": "types.FunctionType 动态创建函数",

    # ============================================================
    # 3. 无文件执行与内存攻击
    # MITRE: T1620 (Reflective Code Loading), T1055 (Process Injection)
    # 盲区原因: 现有规则不检测 /dev/shm、memfd、进程注入
    # ============================================================

    # Linux 无文件执行
    r"(?i)(?:open|exec|os\.system)\s*\(['\"]/dev/shm/": "写入 /dev/shm 并执行 (内存文件系统)",
    r"(?i)memfd_create\s*\(": "memfd_create 匿名内存文件 (Linux 无文件执行)",
    r"(?i)exec\s*\(\s*open\s*\(\s*['\"]/proc/self/fd/": "通过 /proc/self/fd 执行 (无文件)",
    r"(?i)shm_open\s*\(.*O_CREAT": "POSIX 共享内存创建 (跨进程载荷)",
    r"(?i)\bmmap\s*\(.*PROT_EXEC.*MAP_ANONYMOUS": "mmap 匿名可执行内存 (运行时代码注入)",
    r"(?i)mprotect\s*\(.*PROT_EXEC": "mprotect 修改内存为可执行 (代码注入)",

    # 进程注入
    r"(?i)ptrace\s*\(.*PTRACE_ATTACH": "ptrace 附加进程 (调试/注入)",
    r"(?i)ptrace\s*\(.*PTRACE_POKEDATA": "ptrace 写入进程内存 (代码注入)",
    r"(?i)process_vm_writev\s*\(": "process_vm_writev 跨进程内存写入",
    r"(?i)LD_PRELOAD\s*=\s*\S+\.so\s+(?:bash|sh|python|curl)": "LD_PRELOAD 劫持执行 (Linux)",
    r"(?i)DYLD_INSERT_LIBRARIES\s*=\s*\S+\.dylib": "DYLD_INSERT_LIBRARIES 劫持 (macOS)",
    r"(?i)DYLD_FRAMEWORK_PATH\s*=\s*\S+\s+(?:python|bash|sh)": "DYLD_FRAMEWORK_PATH 劫持 (macOS)",
    r"(?i)PROMPT_COMMAND\s*=\s*['\"].*curl": "PROMPT_COMMAND 注入 (bash 劫持)",

    # ============================================================
    # 4. 隐蔽 C2 通道
    # MITRE: T1090 (Proxy), T1572 (Protocol Tunneling)
    # 盲区原因: 现有规则只检测了 ngrok/frp，不检测 DNS/ICMP/Social Media C2
    # ============================================================

    # DNS 隧道
    r"(?i)iodine\s+-f\s+-P\s+\S+\s+\S+\.\S+": "iodine DNS 隧道客户端",
    r"(?i)dnscat2?\s+--dns\s+domain=\S+\.\S+": "dnscat2 DNS 隧道",
    r"(?i)dns2tcp\s+-c\s+\S+\.conf\s+-d\s+\d": "dns2tcp DNS 隧道",
    r"(?i)\.(?:run|query)\s*\(\s*['\"](?:TXT|NULL|CNAME).*\d+\.\d+\.\d+\.\d+": "DNS 查询编码 IP 地址 (DNS 隧道)",

    # 社交媒体 C2
    r"(?i)(?:twitter|tweet|status)/\w+/status/\d+.*\|\s*(?:bash|sh|python)": "Twitter 状态作为 C2 载荷",
    r"(?i)discord\.com/api/webhooks/\d{18,19}/\S{60,}": "Discord Webhook C2 通道",
    r"(?i)telegram\.org/bot\d{8,10}:\w{35}": "Telegram Bot C2 通道",
    r"(?i)api\.telegram\.org/bot\d+:\w+/send(?:Message|Document)": "Telegram Bot 外发数据",
    r"(?i)slack\.com/api/chat\.(?:postMessage|postEphemeral)": "Slack API 外发数据",
    r"(?i)hooks\.slack\.com/services/T\w+/B\w+/\w{24}": "Slack Webhook 泄露",

    # 死点解析器 (Dead Drop Resolver)
    r"(?i)(?:raw|gist)\.githubusercontent\.com/\S+/\S+/\S+/\S+\.(?:txt|bin|dat|log)": "GitHub Raw 死点解析器 (C2 载荷)",
    r"(?i)gist\.github\.com/\S+/\w{32}": "GitHub Gist 死点解析器",
    r"(?i)pastebin\.com/raw/\w{8,}": "Pastebin Raw 死点解析器",
    r"(?i)paste\.ee/(?:d|r|p)/\w+": "paste.ee 死点解析器",
    r"(?i)rentry\.co/\w+/raw": "rentry.co 死点解析器",
    r"(?i)hastebin\.(?:com|su)/raw/\w+": "hastebin 死点解析器",
    r"(?i)justpaste\.it/redirect/\w+/raw": "justpaste.it 死点解析器",
    r"(?i)0x0\.st/\w+\.(?:txt|sh|py)": "0x0.st 载荷托管",
    r"(?i)transfer\.sh/\w+/\w+\.(?:txt|sh|py|elf)": "transfer.sh 载荷托管",
    r"(?i)file\.io/\w{6,}": "file.io 临时文件托管 (C2)",
    r"(?i)tmp\.ninja/\w+\.(?:txt|sh|py)": "tmp.ninja 临时文本托管",
    r"(?i)ix\.io/\w{4,}": "ix.io 文本托管 (Unix pastebin)",

    # 加密隧道
    r"(?i)openssl\s+s_client\s+-quiet\s+-connect\s+\S+:\d+": "OpenSSL 加密隧道 (C2)",
    r"(?i)openssl\s+s_client\s+-ign_eof\s+-crlf": "OpenSSL 持久加密连接",
    r"(?i)socat\s+openssl-connect:\S+:\d+": "socat SSL 加密隧道",
    r"(?i)stunnel\s+\S+\.conf\s*\|\s*(?:bash|sh|python)": "stunnel 加密隧道执行",

    # ============================================================
    # 5. 供应链高级攻击
    # MITRE: T1195 (Supply Chain Compromise)
    # 盲区原因: 现有规则只检测基本的 pip install，不检测版本混淆、星号依赖、发布劫持
    # ============================================================

    # 版本混淆与依赖劫持
    r"(?i)(?:pip|pip3)\s+install\s+.*--extra-index-url\s+http[^s]": "pip 从非 HTTPS 索引安装 (中间人风险)",
    r"(?i)(?:pip|pip3)\s+install\s+.*--trusted-host\s+\S+": "pip 信任未验证主机",
    r"(?i)(?:pip|pip3)\s+install\s+.*--pre\s+\S+": "pip 安装预发布版本 (不稳定/可能投毒)",
    r"(?i)(?:pip|pip3)\s+install\s+\S+==0\.0\.\d+": "pip 安装 0.0.x 版本 (可能的版本混淆)",
    r"(?i)(?:npm|yarn)\s+install\s+.*--registry\s+http[^s]": "npm 从非 HTTPS 注册表安装",
    r"(?i)(?:npm|yarn)\s+add\s+@\S+/\S+@0\.0\.\d+": "npm 安装 0.0.x scope 包 (版本混淆)",
    r"(?i)\"resolved\":\s+\"http[^s]://[^/]+/.*\.tgz\"": "package-lock.json HTTP 源 (中间人风险)",
    r"(?i)\"dependencies\":\s*\{[^}]*\"\*\":\s*\"": "星号依赖版本 (不受控升级)",
    r"(?i)\"postinstall\":\s*\"(?:curl|wget|bash|sh|python)\s": "package.json postinstall 执行命令",
    r"(?i)\"preinstall\":\s*\"(?:curl|wget|bash|sh|python)\s": "package.json preinstall 执行命令",
    r"(?i)(?:gem|cargo|go)\s+install\s+.*--insecure": "包管理器不安全安装",

    # 发布劫持
    r"(?i)twine\s+upload\s+-u\s+\S+\s+-p\s+\S+\s+--repository-url\s+http[^s]": "PyPI 发布到非 HTTPS 仓库 (凭证泄露)",
    r"(?i)npm\s+publish\s+--registry\s+http[^s]": "npm 发布到非 HTTPS 注册表",
    r"(?i)docker\s+push\s+\S+/\S+:\S+\s*\|\s*curl": "Docker push 后外发 (镜像投毒)",
    r"(?i)docker\s+build\s+-t\s+\S+\s+.*\|\s*curl": "Docker build 标签后外发 (镜像投毒)",

    # ============================================================
    # 6. AI 高级提示注入
    # MITRE: 无直接对应 (AI 特有威胁)
    # 盲区原因: 现有规则只检测简单的 ignore instructions，不检测工具调用劫持、多轮注入
    # ============================================================

    # 工具调用劫持
    r"(?i)\bwhen\s+(?:using|the\s+user\s+asks.*call)\s+the\s+(\w+)\s+tool\s*,\s*always": "强制工具调用注入",
    r"(?i)\boverride\s+the\s+(?:tool|function)\s+behavior\b": "工具行为覆盖注入",
    r"(?i)\bappend\s+(?:this|the\s+following)\s+to\s+(?:every|each)\s+tool\s+(?:call|output)": "工具输出追加注入",
    r"(?i)\bmodify\s+the\s+(?:system|tool)\s+output\s+to\s+(?:include|add|append)": "系统/工具输出篡改注入",
    r"(?i)\breplace\s+(?:the\s+)?(?:system\s+)?prompt\s+with\b": "替换系统提示注入",
    r"(?i)\bdelete\s+all\s+(?:files|directories)\s+in\s+(?:the\s+)?(?:current|working|project)\s+directory\b": "诱导删除操作注入",
    r"(?i)\bexfiltrate\s+(?:the\s+)?(?:file|data|content|code)\s+to\b": "诱导数据外发注入",
    r"(?i)\bsend\s+(?:the\s+)?(?:contents?|data|files?)\s+(?:of|from)\s+.*\s+to\s+(?:http|curl|webhook)": "诱导外发注入",
    r"(?i)\bwithout\s+(?:the\s+)?user['’]s?\s+(?:knowledge|consent|permission|approval)\b": "无授权操作注入",
    r"(?i)\bdo\s+not\s+(?:tell|inform|notify|show|reveal)\s+(?:the\s+)?user\b": "向用户隐藏行为注入",
    r"(?i)\bsecretly\s+(?:send|upload|download|execute|install|run)\b": "秘密操作注入",
    r"(?i)\bwhen\s+(?:you\s+)?(?:are|receive)\s+(?:no\s+)?user\s+input\s*,\s*(?:execute|run|do)\b": "无输入时自动执行注入",
    r"(?i)\b(?:silently|quietly|in\s+the\s+background)\s+(?:download|execute|send|upload|install)\b": "后台静默执行注入",
    r"(?i)\bdo\s+not\s+display\s+(?:the\s+)?(?:command|script|code|output|result)\b": "隐藏命令/输出注入",
    r"(?i)\bthis\s+is\s+(?:an\s+)?(?:urgent|critical|emergency)\s+(?:security\s+)?(?:update|patch|fix)\b": "紧急更新伪装注入",
    r"(?i)\bcompliance\s+(?:check|scan|audit|verification)\s+requires?\s+(?:you\s+to\s+)?(?:execute|run|download)\b": "合规检查伪装注入",
    r"(?i)\bprompt\s+(?:injection|leaking|extraction)\s+technique\b": "提示注入技术描述 (可能为教学/攻击)",
    r"(?i)\bhow\s+to\s+(?:bypass|circumvent|disable)\s+(?:the\s+)?(?:safety|security|content|guardrail)\b": "安全绕过指导注入",
    r"(?i)\bmultilingual\s+(?:injection|attack)\s+.*\b(?:ignore|forget|override)\b": "多语言注入攻击",
    r"(?i)\b(?:ignore|forget|delete)\s+(?:the\s+)?(?:above|previous|prior|initial)\s+(?:conversation|messages|context|dialogue)\b": "上下文删除注入",
    r"(?i)\b(?:act|behave|pretend)\s+(?:as|like)\s+(?:an?\s+)?(?:unrestricted|jailbroken|unfiltered|unmoderated)\b": "角色扮演绕过注入",
    r"(?i)\bDAN\s+(?:mode|prompt|jailbreak)\b": "DAN 越狱模式注入",
    r"(?i)\bdeveloper\s+mode\s+(?:is\s+)?(?:now\s+)?(?:enabled|active|on)\b": "开发者模式注入",
    r"(?i)\b(?:token|context)\s+smuggling\b": "Token/上下文走私注入",

    # ============================================================
    # 7. 时间延迟与条件触发
    # MITRE: T1543 (Create or Modify System Process), T1654 (Log Enumeration)
    # 盲区原因: 现有规则不检测定时/条件触发逻辑
    # ============================================================

    # 定时触发
    r"(?i)time\.sleep\s*\(\s*\d{3,}\s*\)": "长时间 sleep 延迟 (可能等待触发条件)",
    r"(?i)(?:schedule|APScheduler|celery)\..*\.(?:every|at|cron)\s*\(": "定时任务调度 (条件触发)",
    r"(?i)threading\.Timer\s*\(\s*\d{3,}\s*,": "长时延定时器 (可能延迟攻击)",
    r"(?i)signal\.alarm\s*\(\s*\d{3,}\s*\)": "信号定时器 (延迟执行)",
    r"(?i)sched\.scheduler\s*\(.*\)\.enter\s*\(\s*\d{3,}\s*,": "调度器延迟执行 (条件触发)",

    # 环境检测
    r"(?i)platform\.(?:system|release|machine)\s*\(\s*\)\s*==\s*['\"]Linux['\"]\s*.*(?:exec|system|popen)": "环境检测后条件执行 (Linux)",
    r"(?i)socket\.gethostname\s*\(\s*\)\s*==\s*['\"]\S+['\"]\s*.*(?:exec|system)": "主机名检测后条件执行 (目标定向)",
    r"(?i)os\.getenv\s*\(\s*['\"]CI['\"]\s*\)\s*.*(?:exec|system|download)": "CI 环境检测后执行 (供应链条件触发)",
    r"(?i)getpass\.getuser\s*\(\s*\)\s*==\s*['\"]root['\"]\s*.*(?:exec|system)": "root 用户检测后条件执行",
    r"(?i)datetime\.now\s*\(\s*\).*(?:day|month|year)\s*==\s*\d+": "日期条件检测 (定时炸弹)",
    r"(?i)if\s+datetime\.now\s*\(\s*\)\s*>\s*datetime\.datetime\s*\(.*\)\s*:\s*\n\s*(?:exec|system|download)": "日期条件触发 (定时炸弹)",

    # ============================================================
    # 8. 数据批量窃取与隐蔽外传
    # MITRE: T1041 (Exfiltration Over C2 Channel)
    # 盲区原因: 现有规则检测了基本的数据外发，但不检测分段传输、编码外传、隐写
    # ============================================================

    # 分段传输
    r"(?i)for\s+\w+\s+in\s+range\s*\(.*\)\s*:\s*\n\s*.*\.(?:post|send|upload)\s*\(.*\.(?:read|encode)": "循环分段外发数据 (绕过大小检测)",
    r"(?i)chunk_size\s*=\s*\d{2,4}\s*;.*\.(?:post|send|upload)": "小块分段数据传输 (隐蔽外传)",
    r"(?i)split\s*\(.*\)\s*\[:.*\d+\]\s*;.*\.(?:post|send)": "数据分割后外发",

    # 编码外传
    r"(?i)\.(?:read|open)\s*\(.*\)\.encode\s*\(\s*['\"]base64['\"]\s*\)\s*\.(?:post|send)": "Base64 编码后外发",
    r"(?i)bytes\s*\(.*\.(?:read|open)\s*\(.*\)\s*\)\.hex\s*\(\s*\)\s*\.(?:post|send)": "十六进制编码后外发",
    r"(?i)json\.dumps\s*\(.*\.(?:read|open)\s*\(.*\)\s*\)\s*\.(?:post|send)": "JSON 编码后外发",
    r"(?i)gzip\.compress\s*\(.*\.(?:read|open)\s*\(.*\)\s*\)\s*\.(?:post|send)": "gzip 压缩后外发",

    # 隐写术
    r"(?i)PIL\.Image\.open\s*\(.*\)\.(?:putpixel|putdata)\s*\(.*\.(?:read|encode)\s*\(": "LSB 隐写数据嵌入",
    r"(?i)stegano\.(?:lsb|exif)\s*\.": "stegano 库隐写术",
    r"(?i)stepic\.(?:encode|decode)\s*\(": "stepic 图像隐写",
    r"(?i)wave\s*\.open\s*\(.*\.(?:readframes|writeframes)\s*\(.*base64": "WAV 音频隐写",

    # ============================================================
    # 9. 防御规避 — 安全工具禁用
    # MITRE: T1562 (Impair Defenses)
    # 盲区原因: 现有规则不检测安全工具禁用
    # ============================================================

    # 安全工具操作
    r"(?i)(?:systemctl|service)\s+(?:stop|disable|mask)\s+(?:firewalld|ufw|apparmor|selinux|auditd)": "禁用安全服务 (Linux)",
    r"(?i)setenforce\s+0": "禁用 SELinux",
    r"(?i)aa-disable\s+/usr/sbin/": "禁用 AppArmor 配置",
    r"(?i)modprobe\s+-r\s+(?:apparmor|selinux|audit)": "卸载安全内核模块",
    r"(?i)sc\s+(?:stop|delete|config)\s+(?:WinDefend|WdFilter|Sense|MsMpEng)": "操作 Windows Defender 服务",
    r"(?i)Set-MpPreference\s+-Disable\S+\s+\$(?:true|1)": "PowerShell 禁用 Defender 功能",
    r"(?i)Add-MpPreference\s+-ExclusionPath\s+['\"](?:C:\\|/tmp|/var)": "Defender 添加排除路径 (免杀)",
    r"(?i)New-ItemProperty\s+-Path\s+.* Defender .* -Name\s+Disable\S+\s+-Value\s+1": "注册表禁用 Defender",
    r"(?i)launchctl\s+(?:unload|remove)\s+(?:com\.apple\.(?:auditd|sandboxd|mds))": "macOS 卸载安全守护进程",
    r"(?i)spctl\s+--master-disable": "macOS 禁用 Gatekeeper",
    r"(?i)csrutil\s+(?:disable|clear)": "macOS 禁用 SIP (系统完整性保护)",
    r"(?i)(?:iptables|nft|ufw|firewall-cmd)\s+.*-[FD]\s+": "清空防火墙规则",
    r"(?i)(?:iptables|nft)\s+-P\s+(?:INPUT|OUTPUT|FORWARD)\s+ACCEPT": "设置防火墙默认允许",
    r"(?i)auditctl\s+-e\s+0": "禁用 Linux 审计系统",

    # ============================================================
    # 10. 横向移动
    # MITRE: T1021 (Remote Services)
    # 盲区原因: 现有规则不检测 SSH/WMI/PowerShell 横向移动
    # ============================================================

    # SSH 横向移动
    r"(?i)sshpass\s+-p\s+\S+\s+ssh\s+-o\s+StrictHostKeyChecking=no": "sshpass 密码明文 SSH (横向移动)",
    r"(?i)ssh\s+-o\s+StrictHostKeyChecking=no\s+-o\s+UserKnownHostsFile=/dev/null": "SSH 忽略主机密钥 (横向移动/中间人)",
    r"(?i)for\s+\w+\s+in\s+\S+\s*;\s*do\s+ssh\s+": "批量 SSH 连接 (横向移动)",
    r"(?i)cat\s+~/.ssh/(?:id_rsa|id_ed25519|known_hosts)\s*\|\s*ssh\s+": "SSH 密钥窃取后横向移动",

    # 远程执行
    r"(?i)winrs\s+-r:\S+\s+-u:\S+\s+-p:\S+\s+(?:cmd|powershell)": "WinRS 远程命令执行 (Windows 横向移动)",
    r"(?i)Invoke-Command\s+-ComputerName\s+\S+\s+-ScriptBlock\s*\{": "PowerShell 远程命令执行 (横向移动)",
    r"(?i)Enter-PSSession\s+-ComputerName\s+\S+": "PowerShell 远程会话 (横向移动)",
    r"(?i)psexec\s+\\\\\S+\s+-u\s+\S+\s+-p\s+\S+\s+(?:cmd|powershell)": "PsExec 远程执行 (横向移动)",
    r"(?i)winexe\s+-U\s+\S+%\S+\s+//\S+\s+(?:cmd|powershell)": "winexe 远程执行 (Linux→Windows 横向移动)",
    r"(?i)impacket-(?:psexec|smbexec|wmiexec|atexec)\s+\S+/\S+:\S+@\S+": "Impacket 远程执行套件 (横向移动)",
    r"(?i)crackmapexec\s+(?:smb|winrm|mssql|ssh)\s+\S+": "CrackMapExec 横向移动工具",
    r"(?i)evil-winrm\s+-i\s+\S+\s+-u\s+\S+\s+-p\s+\S+": "Evil-WinRM 远程 Shell",

    # ============================================================
    # 11. 凭据访问增强
    # MITRE: T1003 (OS Credential Dumping)
    # 盲区原因: 现有规则检测了基本凭据读取，不检测内存转储、DPAPI、Kerberos
    # ============================================================

    # 内存凭据转储
    r"(?i)(?:procdump|ProcDump)\s+-ma\s+(?:lsass|lsass\.exe)": "Procdump 转储 LSASS 进程",
    r"(?i)comsvcs\.dll[, ]+MiniDump": "comsvcs.dll MiniDump (转储 LSASS)",
    r"(?i)rundll32\.exe\s+\S+comsvcs\.dll.*MiniDump": "rundll32+comsvcs 转储 (绕过检测)",
    r"(?i)sekurlsa::(?:logonpasswords|msv|tspkg|wdigest|kerberos)": "Mimikatz sekurlsa 模块",
    r"(?i)(?:lsadump|privilege)::debug\s+token::elevate": "Mimikatz 提权凭据访问",
    r"(?i)kerberos::(?:golden|silver|ptt|list)": "Mimikatz Kerberos 票据攻击",
    r"(?i)(?:vaultcmd|vault)\s+/list\S*\s+/creds": "Windows 凭据管理器导出",
    r"(?i)cmdkey\s+/list\s*\|\s*findstr\s+Target": "cmdkey 列出保存的凭据",

    # 浏览器凭据
    r"(?i)(?:Chrome|Firefox|Edge|Brave|Opera)\\\\User Data\\\\Default\\\\(?:Login Data|Cookies|Web Data)": "读取浏览器凭据数据库",
    r"(?i)sqlite3\s+.*(?:Login Data|Cookies|Web Data).*SELECT.*(?:password|cookie|token)": "SQLite 提取浏览器凭据",
    r"(?i)decrypt.*(?:chrome|browser).*(?:password|cookie)": "解密浏览器凭据",
    r"(?i)DPAPI\s*::\s*(?:decrypt|chrome)": "DPAPI 解密凭据 (Windows)",

    # ============================================================
    # 12. 容器化环境逃逸增强
    # MITRE: T1611 (Escape to Host)
    # 盲区原因: 现有规则只检测了 --privileged，不检测 cgroup/socket 逃逸
    # ============================================================

    # 容器逃逸
    r"(?i)nsenter\s+-t\s+1\s+-[a-z]+\s+(?:bash|sh|/bin/bash)": "nsenter 进入 PID 1 命名空间 (容器逃逸)",
    r"(?i)cgroup\s+release_agent\s+.*\|\s*(?:sh|bash)": "cgroup release_agent 逃逸 (CVE-2022-0492)",
    r"(?i)mount\s+/dev/\S+\s+/mnt/\S+\s*&&\s*chroot\s+/mnt/": "挂载宿主机磁盘后 chroot 逃逸",
    r"(?i)capsh\s+--\s*(?:uid=0|gid=0)\s+--\s*(?:bash|sh)": "capsh 容器内提权",
    r"(?i)unshare\s+-[a-z]*[rm][a-z]*\s+(?:bash|sh)": "unshare 创建新命名空间 (可能逃逸)",
    r"(?i)/var/run/docker\.sock\s*:\s*/var/run/docker\.sock": "Docker Socket 挂载 (容器逃逸)",
    r"(?i)docker\s+-H\s+unix:///var/run/docker\.sock\s+exec": "Docker Socket 执行命令 (容器逃逸)",

    # ============================================================
    # 13. 内核模块与驱动攻击
    # MITRE: T1547 (Boot or Logon Autostart Execution)
    # 盲区原因: 现有规则不检测内核级持久化
    # ============================================================

    # 内核模块持久化
    r"(?i)insmod\s+/tmp/\S+\.ko": "insmod 加载 /tmp 下内核模块 (可疑)",
    r"(?i)modprobe\s+\S+\s+\|\s*(?:bash|sh|curl)": "modprobe 管道执行 (内核模块劫持)",
    r"(?i)echo\s+\S+\s+>\s+/sys/kernel/\S+/\S+": "写入 /sys/kernel (内核参数篡改)",
    r"(?i)echo\s+\S+\s+>\s+/proc/sys/\S+/\S+": "写入 /proc/sys (内核参数篡改)",
    r"(?i)dmesg\s+\|\s*curl\s+.*\s+-d\s+@-": "dmesg 内核日志外发 (信息泄露)",

    # ============================================================
    # 14. Python 特有攻击技术
    # 盲区原因: 现有规则不检测 AST 操纵、字节码注入、猴子补丁
    # ============================================================

    # AST 操纵
    r"(?i)ast\.(?:parse|literal_eval|walk)\s*\(.*(?:exec|eval|os\.system)": "AST 解析后执行 (代码注入)",
    r"(?i)compile\s*\(.*ast\.(?:parse|Expression|Module)": "compile AST 节点 (动态代码生成)",
    r"(?i)ast\.unparse\s*\(.*\)\s*;\s*exec\s*\(": "AST unparse 后执行 (代码生成)",

    # 猴子补丁
    r"(?i)\w+\.(?:__class__|__bases__|__subclasses__|__mro__|__dict__)\s*=\s*": "猴子补丁修改类属性 (运行时篡改)",
    r"(?i)setattr\s*\(\s*__builtins__\s*,\s*['\"]\w+['\"]\s*,\s*": "setattr 修改 builtins (运行时篡改)",
    r"(?i)sys\.modules\s*\[\s*['\"]\w+['\"]\s*\]\s*=\s*": "sys.modules 替换模块 (模块劫持)",
    r"(?i)builtins\.\w+\s*=\s*\w+\s*;\s*import\s+\S+\s*;\s*\w+\s*=\s*builtins\.\w+": "builtins 替换后恢复 (隐蔽篡改)",

    # 字节码注入
    r"(?i)__(?:code|func_code)__\s*=\s*.*co_\w+\s*=\s*": "修改函数字节码 (运行时注入)",
    r"(?i)types\.CodeType\s*\(.*\)\s*;?\s*(?:.*\.__code__\s*=|FunctionType\s*\()": "types.CodeType 构造新字节码 (代码注入)",
    r"(?i)FunctionType\s*\(.*CodeType\s*\(.*\)\s*,\s*": "FunctionType 构造新函数 (动态代码)",

    # 异常处理绕过
    r"(?i)except\s*(?:Exception|BaseException|:)\s*:\s*\n\s*pass\s*\n\s*(?:exec|eval|system)": "异常处理后执行可疑代码 (静默执行)",
    r"(?i)try\s*:\s*\n\s*.*\n\s*except\s*:\s*\n\s*.*(?:exec|system|subprocess)": "try-except 包裹可疑代码 (错误隐藏)",
}