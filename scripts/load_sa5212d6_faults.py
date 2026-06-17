"""
load_sa5212d6_faults.py — SA5212D6/SA5326D6 specific fault codes.
Adds SMART errors, BMC-specific issues, GPU/PCIe/BIOS faults.
Deduplicates against existing knowledge entries.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

ENTRIES = [
    # ── SMART Error Codes ────────────────────────────────────────────────
    {"category":"Storage","error_code":"SMART_197",
     "fault_description":"SMART 197 Current_Pending_Sector: sectors waiting to be reallocated",
     "affected_parts":"Hard disk / SSD",
     "root_cause":"Disk media degradation, pending sector reallocation",
     "solution":"Replace the drive immediately. Backup data if possible before replacement.",
     "source":"SA5212D6 SMART Reference"},

    {"category":"Storage","error_code":"SMART_198",
     "fault_description":"SMART 198 Offline_Uncorrectable: sectors that could not be corrected",
     "affected_parts":"Hard disk / SSD",
     "root_cause":"Permanent media failure, uncorrectable sectors",
     "solution":"Replace the drive immediately. Data on affected sectors may be lost.",
     "source":"SA5212D6 SMART Reference"},

    {"category":"Storage","error_code":"SMART_5",
     "fault_description":"SMART 5 Reallocated_Sector_Ct: number of reallocated sectors increasing",
     "affected_parts":"Hard disk / SSD",
     "root_cause":"Disk media wear, sectors being remapped to spare area",
     "solution":"Monitor the drive. If reallocated count keeps increasing, replace the drive proactively.",
     "source":"SA5212D6 SMART Reference"},

    {"category":"Storage","error_code":"SMART_199",
     "fault_description":"SMART 199 UDMA_CRC_Error_Count: data transfer errors between drive and controller",
     "affected_parts":"Hard disk, Cable, Backplane",
     "root_cause":"Cable issue, backplane issue, or drive controller fault",
     "solution":"1. Check cables and connections. 2. Reseat drive and cables. 3. If errors persist, replace the drive.",
     "source":"SA5212D6 SMART Reference"},

    {"category":"Storage","error_code":"SMART_187",
     "fault_description":"SMART 187 Reported_Uncorrect: uncorrectable errors during data transfer",
     "affected_parts":"Hard disk / SSD",
     "root_cause":"Drive media or controller failure",
     "solution":"Replace the drive immediately.",
     "source":"SA5212D6 SMART Reference"},

    # ── BMC-Specific Faults ──────────────────────────────────────────────
    {"category":"BMC","error_code":"BMC_User_Addition_Issue",
     "fault_description":"BMC sensor anomalies after adding a BMC user",
     "affected_parts":"BMC module",
     "root_cause":"BMC configuration issue triggered by user account changes",
     "solution":"1. Review BMC configuration. 2. Remove or reconfigure the added BMC user. 3. If issue persists, replace BMC module.",
     "source":"SA5212D6 BMC Reference [4]"},

    {"category":"BMC","error_code":"BMC_Drive_Fault_After_FW",
     "fault_description":"BMC frequently reports Drive Fault after upgrading Intel NVMe firmware",
     "affected_parts":"BMC module, NVMe drive",
     "root_cause":"BMC version incompatibility with updated NVMe firmware",
     "solution":"1. Check BMC version. 2. Upgrade BMC firmware to compatible version. 3. If issue persists, replace BMC module.",
     "source":"SA5212D6 BMC Reference [4]"},

    # ── GPU / PCIe / Network ─────────────────────────────────────────────
    {"category":"GPU","error_code":"GPU_High_Temperature",
     "fault_description":"GPU high temperature, OS logs show GPU slot information anomalies",
     "affected_parts":"GPU, OCP riser cable, Motherboard",
     "root_cause":"OCP riser cable misconnection causing improper GPU cooling or signaling",
     "solution":"1. Check OCP riser cable connections. 2. Replace OCP riser cable if misconnected. 3. If issue persists, replace motherboard.",
     "source":"SA5212D6 Network Reference [5]"},

    {"category":"Network","error_code":"OCP_Riser_Cable_Misconnection",
     "fault_description":"OCP riser cable misconnection causing GPU high temperature or PCIe anomalies",
     "affected_parts":"OCP riser cable, Motherboard",
     "root_cause":"Incorrect OCP riser cable installation",
     "solution":"1. Check OCP riser cable connections. 2. Replace cable if misconnected. 3. If issue persists, replace motherboard.",
     "source":"SA5212D6 Network Reference [5]"},

    {"category":"Network","error_code":"PCIe_Bandwidth_Reduction_V02207R",
     "fault_description":"PCIe bandwidth reduction on PCIe network card (V02207R000000000)",
     "affected_parts":"PCIe network card, Motherboard",
     "root_cause":"Design issue with specific PCIe network card model",
     "solution":"1. Check PCIe network card connections. 2. Replace the PCIe network card. 3. If issue persists, replace motherboard.",
     "source":"SA5212D6 Network Reference [5]"},

    # ── BIOS / CPU Threshold ─────────────────────────────────────────────
    {"category":"BIOS","error_code":"BIOS_Version_Low_CPU_Throttle",
     "fault_description":"CPU threshold throttling caused by BIOS version below BIOS_01.01.01.05.01",
     "affected_parts":"BIOS, CPU, Motherboard",
     "root_cause":"Outdated BIOS version causing incorrect CPU thermal thresholds",
     "solution":"1. Check BIOS version. 2. Upgrade BIOS to BIOS_01.01.01.05.01. 3. Upgrade BMC firmware. 4. Apply thermal paste if necessary. 5. Perform Linpack stress testing. 6. If issue persists, replace motherboard or CPU.",
     "source":"SA5212D6 BIOS Reference [16]"},

    {"category":"CPU","error_code":"CPU_Threshold_Throttling",
     "fault_description":"CPU threshold throttling detected in BMC and OS logs",
     "affected_parts":"CPU, BIOS, BMC",
     "root_cause":"Thermal management issue, often caused by outdated BIOS or cooling failure",
     "solution":"1. Check BIOS version, upgrade to BIOS_01.01.01.05.01. 2. Upgrade BMC firmware. 3. Apply thermal paste. 4. Perform Linpack stress testing. 5. Replace mainboard or CPU if issue persists.",
     "source":"SA5212D6 CPU Reference [16]"},

    # ── Memory SEL Events ────────────────────────────────────────────────
    {"category":"Memory","error_code":"Memory_Threshold_Exceeded",
     "fault_description":"Memory error threshold exceeded — SEL event indicating excessive memory errors",
     "affected_parts":"DIMM, Motherboard",
     "root_cause":"DIMM degradation causing error count to exceed monitoring threshold",
     "solution":"1. Identify affected memory slot from BMC logs. 2. Replace the memory in the specific slot. 3. Clear log and retest. 4. If issue persists, replace motherboard.",
     "source":"SA5212D6 SEL Reference"},

    # ── Storage Backplane ────────────────────────────────────────────────
    {"category":"Storage","error_code":"P12V_NVME_FAULT_Detailed",
     "fault_description":"P12V_NVME power fault — abnormal power to NVMe storage rail",
     "affected_parts":"Motherboard, Hard disk backplane",
     "root_cause":"Power supply fault on the 12V NVMe rail",
     "solution":"1. Collect one-key logs. 2. Power off server and disconnect power cord. 3. Power on and check if normal. 4. If fault persists, replace motherboard or hard disk backplane.",
     "source":"SA5212D6 Storage Reference [1,5,9]"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='SMART_197'").fetchone()
    con.close()
    if has:
        print("SA5212D6 fault codes already loaded. Skipping.")
        return

    for e in ENTRIES:
        db.add_knowledge(path, e)
    print(f"Loaded {len(ENTRIES)} SA5212D6-specific fault codes.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
