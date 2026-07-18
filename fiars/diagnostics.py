"""
diagnostics.py — Diagnostic commands and on-site reference by fault category.

Returns category-specific CLI commands, log collection steps, and
verification procedures an engineer needs on-site.
"""
from __future__ import annotations

COMMANDS: dict[str, list[dict[str, str]]] = {
    "Storage": [
        {"cmd": "smartctl -a /dev/sdX", "desc": "Full SMART data for the drive"},
        {"cmd": "nvme smart-log /dev/nvmeXn1", "desc": "NVMe health and error log"},
        {"cmd": "lsblk", "desc": "Disk layout and mount points"},
        {"cmd": "ipmitool sel list | grep -i disk", "desc": "BMC events related to disk"},
        {"cmd": "storcli /c0 show", "desc": "RAID controller status (if applicable)"},
        {"cmd": "dmesg | grep -i 'error\\|fault\\|nvme'", "desc": "Kernel disk error messages"},
    ],
    "Memory": [
        {"cmd": "dmidecode -t memory", "desc": "DIMM layout, slots, sizes, and speeds"},
        {"cmd": "ipmitool sel list | grep -i memory", "desc": "BMC memory error events"},
        {"cmd": "edac-util -s", "desc": "ECC correctable/uncorrectable error summary"},
        {"cmd": "mcelog --client", "desc": "Machine check exception log"},
        {"cmd": "grep -i 'edac\\|mce\\|memory' /var/log/messages", "desc": "OS memory error log"},
    ],
    "CPU": [
        {"cmd": "lscpu", "desc": "CPU model, cores, sockets, and features"},
        {"cmd": "ipmitool sel list | grep -i cpu", "desc": "BMC CPU error events"},
        {"cmd": "mcelog --client", "desc": "Machine check exception details"},
        {"cmd": "dmesg | grep -i 'mce\\|ierr\\|caterr'", "desc": "Kernel CPU error messages"},
        {"cmd": "sensors", "desc": "CPU temperature readings (lm-sensors)"},
    ],
    "GPU": [
        {"cmd": "nvidia-smi", "desc": "GPU status, temperature, utilization, and errors"},
        {"cmd": "nvidia-smi -q", "desc": "Detailed GPU diagnostics (all fields)"},
        {"cmd": "dmesg | grep -i 'xid\\|nvidia\\|gpu'", "desc": "GPU/Xid kernel errors"},
        {"cmd": "lspci | grep -i 'vga\\|3d\\|display'", "desc": "Detect GPU in PCIe slots"},
        {"cmd": "nvidia-smi --query-gpu=gpu_bus_id,name,temperature.gpu --format=csv", "desc": "GPU bus ID and temp (quick check)"},
    ],
    "Power": [
        {"cmd": "ipmitool sensor list", "desc": "All sensor readings (voltages, temps, fans)"},
        {"cmd": "ipmitool power status", "desc": "Current power state"},
        {"cmd": "ipmitool sel list | grep -i power", "desc": "BMC power-related events"},
        {"cmd": "ipmitool chassis status", "desc": "Chassis power and fault indicators"},
    ],
    "Thermal": [
        {"cmd": "ipmitool sensor list | grep -i fan", "desc": "Fan speed readings"},
        {"cmd": "ipmitool sensor list | grep -i temp", "desc": "Temperature readings"},
        {"cmd": "ipmitool sel list | grep -i 'fan\\|temp\\|thermal'", "desc": "BMC thermal events"},
        {"cmd": "sensors", "desc": "OS-level temperature sensors (lm-sensors)"},
    ],
    "BIOS": [
        {"cmd": "dmidecode -t bios", "desc": "BIOS vendor, version, and release date"},
        {"cmd": "dmidecode -t system", "desc": "System manufacturer and model info"},
        {"cmd": "ipmitool sel list", "desc": "Full BMC system event log"},
    ],
    "Firmware": [
        {"cmd": "ipmitool mc info", "desc": "BMC firmware version and manufacturer"},
        {"cmd": "ipmitool sel list", "desc": "Full system event log"},
        {"cmd": "ipmitool user list", "desc": "BMC user accounts"},
        {"cmd": "ipmitool lan print", "desc": "BMC network configuration"},
    ],
    "BMC": [
        {"cmd": "ipmitool mc info", "desc": "BMC firmware version"},
        {"cmd": "ipmitool sel list", "desc": "Full system event log"},
        {"cmd": "ipmitool user list", "desc": "BMC user accounts (check for issues)"},
        {"cmd": "ipmitool lan print", "desc": "BMC network settings"},
        {"cmd": "ipmitool mc reset cold", "desc": "Cold reset BMC (use with caution)"},
    ],
    "Network": [
        {"cmd": "lspci | grep -i 'net\\|ethernet'", "desc": "Detect network adapters"},
        {"cmd": "ip link show", "desc": "All network interfaces and status"},
        {"cmd": "ethtool ethX", "desc": "Link speed, duplex, and driver info"},
        {"cmd": "dmesg | grep -i 'eth\\|nic\\|link'", "desc": "Kernel network messages"},
    ],
    "Board": [
        {"cmd": "dmidecode -t baseboard", "desc": "Motherboard model and serial"},
        {"cmd": "ipmitool sel list", "desc": "Full BMC event log"},
        {"cmd": "ipmitool sensor list", "desc": "All sensor readings"},
        {"cmd": "lspci", "desc": "All PCIe devices detected"},
    ],
    "System": [
        {"cmd": "ipmitool sel list", "desc": "Full BMC event log"},
        {"cmd": "dmesg | tail -50", "desc": "Recent kernel messages"},
        {"cmd": "journalctl -b -p err", "desc": "Errors since last boot"},
        {"cmd": "uptime", "desc": "System uptime and load"},
    ],
}

# Common commands that apply to ALL categories
COMMON = [
    {"cmd": "ipmitool sel list", "desc": "Full BMC system event log (always collect)"},
]

# Log collection paths
LOG_PATHS = {
    "sel_log": "onekeylog/log/selelist.csv",
    "audit_log": "onekeylog/log/audit.log",
    "idl_log": "onekeylog/log/idl.log",
    "system_err": "onekeylog/log/err.log",
    "system_crit": "onekeylog/log/crit.log",
    "debug_log": "onekeylog/log/inspur_debug.log",
    "psu_history": "onekeylog/log/psuFaultHistory.log",
    "raid_log": "onekeylog/log/raid%d.log",
    "sol_log": "onekeylog/sollog/solHostCaptured.log",
    "bmc_uart": "onekeylog/sollog/BMCUart.log",
    "netcard_log": "onekeylog/sollog/NetCard.log",
    "ierr_capture": "onekeylog/log/CaptureScreen/IERR/IERR_Capture.jpeg",
    "mce_capture": "onekeylog/log/CaptureScreen/MCERR/MCE_Error2_Capture1.jpeg",
    "dmesg": "onekeylog/log/dmesg",
    "bmc_sel": "onekeylog/log/BMC1/SEL.dat",
    "error_report": "onekeylog/log/ErrorAnalyReport.json",
    "reg_raw": "onekeylog/log/RegRawData.json",
    "cpld_info": "onekeylog/runningdata/cpldinfo.log",
    "runtime_data": "onekeylog/runningdata/rundatainfo.log",
    "fan_info": "onekeylog/runningdata/faninfo.log",
    "component_info": "onekeylog/component/component.log",
    "config": "onekeylog/configuration/config.log",
    "bios_settings": "onekeylog/configuration/conf/redfish/bios/bios_current_settings.json",
}

# Category-specific key logs to collect
_CATEGORY_LOGS = {
    "Storage": ["sel_log", "dmesg", "error_report", "sol_log"],
    "Memory": ["sel_log", "dmesg", "error_report", "mce_capture", "reg_raw"],
    "CPU": ["sel_log", "dmesg", "ierr_capture", "mce_capture", "error_report", "reg_raw"],
    "GPU": ["sel_log", "sol_log", "dmesg", "error_report"],
    "Power": ["sel_log", "psu_history", "runtime_data"],
    "Thermal": ["sel_log", "fan_info", "runtime_data"],
    "BIOS": ["sel_log", "bios_settings", "config"],
    "Firmware": ["sel_log", "bmc_sel", "config", "component_info"],
    "BMC": ["sel_log", "bmc_sel", "bmc_uart", "debug_log", "config"],
    "Network": ["sel_log", "netcard_log", "sol_log", "component_info"],
}


def get_diagnostics(category: str) -> dict:
    """Return diagnostic commands, log paths, and collection steps for a fault category."""
    cat = category if category in COMMANDS else "System"
    cat_cmds = COMMANDS.get(cat, COMMANDS["System"])
    cat_cmd_set = {c["cmd"] for c in cat_cmds}
    common_cmds = [c for c in COMMON if c["cmd"] not in cat_cmd_set]
    cmds = common_cmds + cat_cmds
    key_logs = _CATEGORY_LOGS.get(cat, ["sel_log", "dmesg", "error_report"])
    log_list = [{"name": k, "path": LOG_PATHS.get(k, "")} for k in key_logs if k in LOG_PATHS]

    return {
        "category": cat,
        "commands": cmds,
        "key_logs": log_list,
        "log_collection": [
            "Collect one-key logs BEFORE any changes",
            "Key logs for this fault type:",
        ] + [f"  {l['name']}: {l['path']}" for l in log_list[:5]],
    }
