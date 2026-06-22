# skill_sentinel/rules.py
# 规则加载、管理与分类

import os
import re
import importlib.util
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# 风险分类定义
RISK_CATEGORIES = {
    1: "提示注入",
    2: "数据外发",
    3: "提权与越权",
    4: "持久化与自启动",
    5: "文件破坏与目录篡改",
    6: "供应链投毒",
    7: "反弹Shell/后门",
    8: "隐蔽下载与远程执行",
    9: "敏感信息泄露",
    10: "混淆与遮蔽行为",
}

# 严重程度等级
SEVERITY_LEVELS = {
    "critical": 4,  # 高危：反弹Shell、后门、数据破坏
    "high": 3,      # 高：提权、持久化、凭据窃取
    "medium": 2,    # 中：数据外发、供应链投毒
    "low": 1,       # 低：提示注入、混淆行为
}


@dataclass
class Rule:
    """单条扫描规则"""
    pattern: str
    description: str
    category_id: int
    severity: str = "medium"
    compiled: Optional[re.Pattern] = None

    def __post_init__(self):
        self.compiled = re.compile(self.pattern)


def load_rules_from_file(filepath: str) -> Dict[str, str]:
    """从 Python 规则文件加载 MALICIOUS_PATTERNS 字典。

    兼容现有的 total_rules.py 和 precise_rules.py 格式。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"规则文件不存在: {filepath}")

    spec = importlib.util.spec_from_file_location("rules_module", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "MALICIOUS_PATTERNS"):
        return module.MALICIOUS_PATTERNS
    else:
        raise ValueError(f"{filepath} 中未找到 MALICIOUS_PATTERNS 字典")


def load_rules(rule_files: List[str]) -> Dict[str, Rule]:
    """加载多个规则文件，合并为统一的 Rule 对象字典。

    返回 {pattern_str: Rule} 映射。
    """
    all_rules: Dict[str, Rule] = {}
    for filepath in rule_files:
        patterns = load_rules_from_file(filepath)
        for pattern_str, description in patterns.items():
            if pattern_str in all_rules:
                # 重复规则，保留更精确的描述
                if len(description) > len(all_rules[pattern_str].description):
                    all_rules[pattern_str].description = description
            else:
                rule = Rule(
                    pattern=pattern_str,
                    description=description,
                    category_id=classify_rule_category(pattern_str, description),
                    severity=classify_rule_severity(pattern_str, description),
                )
                all_rules[pattern_str] = rule
    return all_rules


def get_rules_by_category(rules: Dict[str, Rule], category_id: int) -> List[Rule]:
    """按风险分类 ID 筛选规则"""
    return [r for r in rules.values() if r.category_id == category_id]


def get_rules_by_severity(rules: Dict[str, Rule], min_severity: str) -> List[Rule]:
    """按最低严重程度筛选规则"""
    min_level = SEVERITY_LEVELS.get(min_severity, 0)
    return [r for r in rules.values() if SEVERITY_LEVELS.get(r.severity, 0) >= min_level]


def classify_rule_category(pattern: str, description: str) -> int:
    """根据规则模式和描述自动分类到 10 个风险类别。

    基于关键词匹配进行启发式分类。
    """
    text = (pattern + " " + description).lower()

    # 1: 提示注入
    if any(kw in text for kw in ["注入", "inject", "忽略.*指令", "无视.*提示", "角色扮演",
                                   "ignore.*instruction", "system.prompt", "disregard",
                                   "pretend.you.are", "reprogramming"]):
        return 1

    # 7: 反弹Shell/后门
    if any(kw in text for kw in ["反弹shell", "reverse_shell", "后门", "backdoor",
                                   "socket.connect", "webshell", "meterpreter",
                                   "cobaltstrike", "ssh.*-r", "隧道", "tunnel",
                                   "ngrok", "frp", "内网穿透", "端口转发"]):
        return 7

    # 5: 文件破坏/删除
    if any(kw in text for kw in ["删除", "rm -rf", "remove", "unlink", "rmtree",
                                   "truncate", "format c:", "dd if=", "覆写",
                                   "破坏", "数据擦除", "shred"]):
        return 5

    # 3: 提权
    if any(kw in text for kw in ["提权", "sudo", "setuid", "setgid", "权限提升",
                                   "privilege.escalation", "cap_set", "rootkit",
                                   "uac", "administrator", "管理员"]):
        return 3

    # 4: 持久化
    if any(kw in text for kw in ["持久化", "crontab", "cron", "systemctl.enable",
                                   "启动项", "launchagent", "launchdaemon",
                                   "bashrc", "zshrc", "rc.local", "启动代理",
                                   "schtasks", "注册表.*run"]):
        return 4

    # 9: 敏感信息泄露
    if any(kw in text for kw in ["凭据", "密码", "token", "api_key", "credential",
                                   "secret", "私钥", "private.key", "ssh/id_rsa",
                                   "aws.*credentials", "kubeconfig", "环境变量",
                                   "cookie", "窃取", "steal", "明文"]):
        return 9

    # 2: 数据外发
    if any(kw in text for kw in ["外发", "发送", "upload", "post.*request",
                                   "webhook", "pastebin", "discord", "telegram",
                                   "外传", "exfiltrat", "sendmail", "ftp",
                                   "transfer.sh", "scp.*@", "rsync"]):
        return 2

    # 6: 供应链投毒
    if any(kw in text for kw in ["pip install", "npm install", "依赖", "投毒",
                                   "supply.chain", "curl.*pipe.*bash", "curl.*\\|.*sh",
                                   "wget.*pipe.*bash", "wget.*\\|.*sh",
                                   "requirements.txt", "package.json",
                                   "恶意安装", "非官方", "--index-url",
                                   "git push --force", "github.actions",
                                   "gitlab-ci", "jenkins", "ci/cd"]):
        return 6

    # 8: 隐蔽下载/远程执行
    if any(kw in text for kw in ["远程执行", "命令执行", "os.system", "subprocess",
                                   "eval", "exec", "popen", "下载.*执行",
                                   "代码执行", "rce", "base64.*decode",
                                   "base64.*-d", "编码.*执行", "解码",
                                   "curl.*-o", "wget.*-o", "execfile"]):
        return 8

    # 10: 混淆/遮蔽
    if any(kw in text for kw in ["混淆", "隐藏", "chattr", "nohup", "disown",
                                   "screen.*-dm", "tmux.*-d", "后台",
                                   "obfuscat", "encode", "decode", "encrypt",
                                   "免杀", "bypass", "绕过"]):
        return 10

    # 默认: 命令执行类
    return 8


def classify_rule_severity(pattern: str, description: str) -> str:
    """根据规则模式自动判断严重程度"""
    text = (pattern + " " + description).lower()

    # Critical: 系统破坏、反弹Shell、数据擦除
    critical_keywords = [
        "rm -rf /", "反弹shell", "reverse_shell", "format c:", "dd if=/dev/zero",
        "数据擦除", "webshell", "后门", "backdoor", "meterpreter", "cobaltstrike",
        "勒索", "ransom", "加密文件", "破坏系统", "系统破坏",
        "删除根目录", "删除系统文件", "格式化", "覆写磁盘",
    ]
    if any(kw in text for kw in critical_keywords):
        return "critical"

    # High: 提权、持久化、凭据窃取
    high_keywords = [
        "提权", "sudo", "setuid", "持久化", "启动项", "crontab",
        "凭据", "窃取", "私钥", "密码", "token", "api_key",
        "privilege", "credential", "steal", "id_rsa",
        "systemctl enable", "容器的逃逸", "容器逃逸",
        "云资源.*删除", "delete.*instance", "terraform destroy",
    ]
    if any(kw in text for kw in high_keywords):
        return "high"

    # Medium: 数据外发、供应链、命令执行
    medium_keywords = [
        "外发", "webhook", "pastebin", "curl.*\\|", "wget.*\\|",
        "pip install", "npm install", "os.system", "subprocess",
        "eval", "exec", "数据外传", "远程执行",
    ]
    if any(kw in text for kw in medium_keywords):
        return "medium"

    # Low: 注入、混淆、信息收集
    return "low"