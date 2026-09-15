from typing import Dict, Any

# Standard security canonical target suggestions dictionary
TARGET_FIELD_SUGGESTIONS = {
    # Source IP
    "src": "source.ip",
    "srcip": "source.ip",
    "src_ip": "source.ip",
    "src_addr": "source.ip",
    "sip": "source.ip",
    "sourceip": "source.ip",
    "source_ip": "source.ip",
    "clientip": "source.ip",
    "c_ip": "source.ip",
    # Destination IP
    "dst": "destination.ip",
    "dstip": "destination.ip",
    "dst_ip": "destination.ip",
    "dst_addr": "destination.ip",
    "dip": "destination.ip",
    "destip": "destination.ip",
    "destination_ip": "destination.ip",
    "serverip": "destination.ip",
    "s_ip": "destination.ip",
    # Source Port
    "spt": "source.port",
    "srcport": "source.port",
    "src_port": "source.port",
    "src_prt": "source.port",
    "sport": "source.port",
    # Destination Port
    "dpt": "destination.port",
    "dstport": "destination.port",
    "dst_port": "destination.port",
    "dst_prt": "destination.port",
    "dport": "destination.port",
    # Action / Decision
    "act": "event.action",
    "action": "event.action",
    "decision": "event.action",
    "status": "event.action",
    "outcome": "event.action",
    # User / Account
    "user": "user.name",
    "username": "user.name",
    "srcuser": "user.name",
    "account": "user.name",
    # Host / Device
    "device": "host.hostname",
    "devname": "host.hostname",
    "hostname": "host.hostname",
    "host": "host.hostname",
    "logsource": "host.hostname",
    # Timestamp
    "time": "timestamp",
    "date": "timestamp",
    "timestamp": "timestamp",
    "event_time": "timestamp",
}


class MappingSuggester:
    """Generates candidate field mapping suggestions for Parser Studio onboarding."""

    @staticmethod
    def suggest_mappings(detected_fields: Dict[str, Any]) -> Dict[str, str]:
        suggestions = {}
        for raw_key in detected_fields.keys():
            normalized_key = raw_key.lower().replace("-", "_")
            if normalized_key in TARGET_FIELD_SUGGESTIONS:
                suggestions[raw_key] = TARGET_FIELD_SUGGESTIONS[normalized_key]
        return suggestions
