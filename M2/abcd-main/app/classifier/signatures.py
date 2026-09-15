import re
from typing import List, Dict, Any, Pattern

# Stage 1 - Cheap Deterministic Format Signatures
JSON_PREFIX: Pattern[str] = re.compile(r"^\s*[\{\[]")
SYSLOG_PRI: Pattern[str] = re.compile(r"^\s*<(\d{1,3})>")
SYSLOG_BSD: Pattern[str] = re.compile(
    r"^\s*(?:<\d{1,3}>)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:[0-9]|[0-9][0-9])\s+(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
)
SYSLOG_ISO: Pattern[str] = re.compile(
    r"^\s*(?:<\d{1,3}>)?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
)
CEF_SIGNATURE: Pattern[str] = re.compile(r"(?:^|\s)CEF:(\d+)\|")
LEEF_SIGNATURE: Pattern[str] = re.compile(r"(?:^|\s)LEEF:(1\.0|2\.0)\|")
XML_PREFIX: Pattern[str] = re.compile(
    r"^\s*<\?xml|^\s*<[a-zA-Z0-9_\-]+(?:\s+[^>]+)?>.*</[a-zA-Z0-9_\-]+>"
)
KEY_VALUE_PATTERN: Pattern[str] = re.compile(
    r'(?:[a-zA-Z0-9_\.\-]+=(?:"[^"]*"|\'[^\']*\'|[^\s]+))'
)

# Stage 2 - Source/Vendor Signatures
VENDOR_SIGNATURES: List[Dict[str, Any]] = [
    {
        "vendor": "Cisco",
        "product": "ASA",
        "patterns": [
            re.compile(r"%ASA-\d+-\d+:"),
            re.compile(r"%FTD-\d+-\d+:"),
            re.compile(r"%PIX-\d+-\d+:"),
        ],
        "keywords": [
            "Built inbound TCP connection",
            "Built outbound TCP connection",
            "Teardown TCP connection",
            "Deny ip src",
            "Deny tcp src",
            "cisco-asa",
        ],
    },
    {
        "vendor": "Fortinet",
        "product": "FortiGate",
        "patterns": [
            re.compile(r'devname="?[A-Za-z0-9_\-]+"'),
            re.compile(r'devid="?FG[A-Za-z0-9]+"'),
            re.compile(r"ftg_"),
        ],
        "keywords": ["fortigate", "type=traffic", "type=utm", "type=event", "logid="],
    },
    {
        "vendor": "Palo Alto",
        "product": "PAN-OS",
        "patterns": [
            re.compile(
                r",1,\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2},[0-9A-Fa-f]+,(TRAFFIC|THREAT|SYSTEM|CONFIG),"
            ),
            re.compile(r"PAN-OS"),
        ],
        "keywords": ["paloalto", "PAN-OS", "TRAFFIC", "THREAT", "pan_syslog"],
    },
    {
        "vendor": "Linux",
        "product": "Syslog",
        "patterns": [
            re.compile(r"\b(sshd|sudo|systemd|cron|kernel|authpriv|pam_unix)\[?\d*\]?:")
        ],
        "keywords": [
            "Accepted password for",
            "Failed password for",
            "session opened for user",
            "COMMAND=/bin",
        ],
    },
    {
        "vendor": "Windows",
        "product": "EventLog",
        "patterns": [re.compile(r"\bEventID[=:]\s*\d+"), re.compile(r"<Event xmlns=")],
        "keywords": [
            "Microsoft-Windows-Security-Auditing",
            "EventID",
            "Security-Auditing",
        ],
    },
    {
        "vendor": "AWS",
        "product": "CloudTrail",
        "patterns": [
            re.compile(r'"eventVersion":\s*"1\.\d+"'),
            re.compile(r'"awsRegion":'),
        ],
        "keywords": ["eventSource", "awsRegion", "userIdentity"],
    },
]
