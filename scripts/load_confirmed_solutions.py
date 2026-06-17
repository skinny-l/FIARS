"""
load_confirmed_solutions.py — Load verified fault solutions into the knowledge base.
Source: Vendor documentation (categorized confirmed solutions).

    python scripts/load_confirmed_solutions.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

SOLUTIONS = [
    # ── Fan ─────────────────────────────────────────────────────────────
    {"category": "Fan", "error_code": "BAC0203",
     "fault_description": "Fan speed abnormal (BAC0203+ fan speed 80% abnormal, PIA_PIA-SETUP-CHECK_Fan speed_ratio outside 0.6-1.8 range)",
     "affected_parts": "Fan module",
     "root_cause": "Mechanical failure in fan module or incorrect speed ratio reporting",
     "solution": "Check fan speed using ipmitool sensor list or BMC Web GUI. Replace fan module and cross-validate to confirm mechanical failure.",
     "source": "Vendor KB [6]"},

    {"category": "Fan", "error_code": "Fan_Speed_Ratio_Mismatch",
     "fault_description": "Fan speed ratio outside acceptable range (0.6 to 1.8)",
     "affected_parts": "Fan module, BMC firmware",
     "root_cause": "Bin file mismatch or topology mismatch on production line machines",
     "solution": "Refresh the bin file if error reported 100% on production line machines. Ensure bin file and topology match.",
     "source": "Vendor KB [6]"},

    # ── PSU ─────────────────────────────────────────────────────────────
    {"category": "PSU", "error_code": "PSU_Status_Abnormal",
     "fault_description": "PSU status not monitored or shows abnormal behavior",
     "affected_parts": "Power Supply Unit",
     "root_cause": "PSU hardware failure or monitoring fault",
     "solution": "Check PSU status through BIOS POST error detection and system health LED. Replace PSU if necessary.",
     "source": "Vendor KB [1]"},

    # ── Motherboard ─────────────────────────────────────────────────────
    {"category": "Motherboard", "error_code": "Power_On_Failure",
     "fault_description": "System fails to power on — fans do not spin, LEDs not lit",
     "affected_parts": "Motherboard, Power supply",
     "root_cause": "Motherboard power supply system damage, expansion slot issues, short circuits, or damaged BIOS",
     "solution": "Confirm power supply has current input. Check for motherboard power supply system damage, expansion slot issues, short circuits, or damaged BIOS.",
     "source": "Vendor KB [5]"},

    {"category": "Motherboard", "error_code": "No_Display",
     "fault_description": "No display shown after power-on",
     "affected_parts": "Motherboard",
     "root_cause": "Motherboard component fault",
     "solution": "Check motherboard components for faults. Replace motherboard if necessary.",
     "source": "Vendor KB [5]"},

    # ── CPU ─────────────────────────────────────────────────────────────
    {"category": "CPU", "error_code": "IERR/MCE",
     "fault_description": "Uncorrectable machine check exception (MCE) or IERR reported during boot",
     "affected_parts": "CPU",
     "root_cause": "CPU hardware fault causing uncorrectable errors",
     "solution": "Analyze logs (bmcblackinfo, bmcloginfo, logoemlog, extlog, crashdump json BAFI_crashdump_xxxxxxx.json) to identify faulty CPU. If one CPU reports error, focus on that CPU. If multiple CPUs report, identify first CPU based on TSC time. Replace faulty CPU.",
     "source": "Vendor KB [8]"},

    {"category": "CPU", "error_code": "UPI_Bandwidth_Reduction",
     "fault_description": "UPI bandwidth reduction error reported during boot",
     "affected_parts": "CPU0, CPU1, Motherboard",
     "root_cause": "Foreign objects or bad pins on CPU socket, or motherboard fault",
     "solution": "Reinstall CPU0 and CPU1, check for foreign objects or bad pins. If error persists, cross-verify with other normal machines to determine if motherboard is faulty.",
     "source": "Vendor KB [8]"},

    # ── Memory ──────────────────────────────────────────────────────────
    {"category": "Memory", "error_code": "ECC_Error",
     "fault_description": "Correctable ECC errors reported in SEL logs",
     "affected_parts": "Memory/DIMM",
     "root_cause": "Faulty DIMM producing correctable errors",
     "solution": "Replace memory at the specified location (e.g. P1_C1_D0). Clear log and retest.",
     "source": "Vendor KB [9]"},

    {"category": "Memory", "error_code": "Memory_MCE",
     "fault_description": "Memory MCE errors reported in SEL or IDL logs",
     "affected_parts": "Memory/DIMM",
     "root_cause": "DIMM hardware fault causing machine check exceptions",
     "solution": "Use xeon_ce_decoder_0_3_beta tool to confirm exact memory location. Replace faulty memory.",
     "source": "Vendor KB [9]"},

    {"category": "Memory", "error_code": "Memory_Dropped",
     "fault_description": "Memory dropped or disabled, number of memory mismatched",
     "affected_parts": "Memory/DIMM, CPU",
     "root_cause": "Faulty DIMM or CPU socket issue causing memory detection failure",
     "solution": "Cross-verify memory to determine if issue follows memory or CPU. Replace faulty memory or CPU.",
     "source": "Vendor KB [9]"},

    # ── Hard Disk / NVMe ────────────────────────────────────────────────
    {"category": "Storage", "error_code": "NVMe_Bandwidth_Reduction",
     "fault_description": "NVMe SSD bandwidth reduced from X4 to X2",
     "affected_parts": "NVMe SSD, Backplane, Cable",
     "root_cause": "Poor connection at disk, backplane, or cable",
     "solution": "Reseat disk, backplane, and cable. Clear log and retest.",
     "source": "Vendor KB [10]"},

    {"category": "Storage", "error_code": "SMART_Error",
     "fault_description": "SMART error reported by hard disk",
     "affected_parts": "Hard disk / SSD",
     "root_cause": "Disk media or firmware failure",
     "solution": "Replace the disk. Use offline refreshed stock SSDs after firmware update.",
     "source": "Vendor KB [10]"},

    # ── Battery ─────────────────────────────────────────────────────────
    {"category": "Battery", "error_code": "P3V_BAT_Low",
     "fault_description": "P3V_BAT voltage lower than 2.70 Volts",
     "affected_parts": "CMOS Battery",
     "root_cause": "Low battery voltage or false alarm from BMC firmware",
     "solution": "Measure battery voltage, confirm > 2.7V. Update BMC to version 3.15 or higher to address low battery false alarms.",
     "source": "Vendor KB [7]"},

    # ── BIOS ────────────────────────────────────────────────────────────
    {"category": "BIOS", "error_code": "BIOS_Password_Lock",
     "fault_description": "BIOS password is set and cannot be cleared",
     "affected_parts": "BIOS, Motherboard jumper",
     "root_cause": "BIOS password configured and not documented",
     "solution": "Clear password via BIOS setup menu. Alternatively, clear BIOS password jumper on motherboard.",
     "source": "Vendor KB [4]"},

    # ── System Firmware ─────────────────────────────────────────────────
    {"category": "Firmware", "error_code": "POST_Error",
     "fault_description": "System firmware error reported during POST",
     "affected_parts": "CPU, System firmware",
     "root_cause": "CPU seating issue or outdated system firmware",
     "solution": "Reinstall or adjust CPU. Check for system firmware updates.",
     "source": "Vendor KB [6]"},

    # ── Storage (MDisk) ─────────────────────────────────────────────────
    {"category": "Storage", "error_code": "Unmanaged_MDisks",
     "fault_description": "MDisks are unmanaged and not assigned to a storage pool",
     "affected_parts": "MDisks, Storage pool",
     "root_cause": "MDisks not detected or not assigned after configuration change",
     "solution": "Use detectmdisk command to manually scan Fibre Channel network for unmanaged MDisks. Use lsmdiskcandidate to list unmanaged MDisks.",
     "source": "Vendor KB [11]"},

    {"category": "Storage", "error_code": "MDisk_Extent_Unknown",
     "fault_description": "Volume copies using extents on MDisks but location unclear",
     "affected_parts": "MDisks, Volumes",
     "root_cause": "Extent allocation information not visible in standard view",
     "solution": "Use lsmdiskextent command to display extent location between MDisks and volumes.",
     "source": "Vendor KB [12]"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    # Check if already loaded
    existing = db.count_knowledge(path)
    if existing > 0:
        con = db.connect(path)
        has_ecc = con.execute("SELECT 1 FROM knowledge WHERE error_code='ECC_Error'").fetchone()
        con.close()
        if has_ecc:
            print(f"Confirmed solutions already loaded ({existing} entries). Skipping.")
            return

    loaded = 0
    for s in SOLUTIONS:
        db.add_knowledge(path, s)
        loaded += 1

    print(f"Loaded {loaded} confirmed solutions into knowledge base.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
