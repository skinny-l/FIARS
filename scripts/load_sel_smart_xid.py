"""
load_sel_smart_xid.py — BMC SEL codes, SMART attributes, Xid codes,
additional CPU faults, and one-key log reference for SA5212D6.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

ENTRIES = [
    # ── Additional CPU faults ────────────────────────────────────────────
    {"category":"CPU","error_code":"CPU_Threshold",
     "fault_description":"CPU threshold fault",
     "affected_parts":"CPU","root_cause":"BIOS version issue",
     "solution":"1. Check BIOS version; if lower than BIOS_01.01.01.05.01, upgrade BIOS and BMC. 2. Check and reapply thermal paste. 3. If issue persists after BIOS upgrade, perform Linpack stress testing and cross-testing to determine if hardware issue.",
     "source":"SA5212D6 CPU"},
    {"category":"CPU","error_code":"MCE_Generic",
     "fault_description":"Machine Check Exception (MCE) — CPU MCE error",
     "affected_parts":"CPU","root_cause":"BIOS version issue or system kernel issue",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. If problem persists, check OS kernel for compatibility issues. 3. Perform cross-testing to identify hardware faults.",
     "source":"SA5212D6 CPU"},
    {"category":"CPU","error_code":"P0_Card_Err",
     "fault_description":"GPU card error related to CPU link",
     "affected_parts":"CPU, GPU","root_cause":"BIOS version issue or riser cable connection issue",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. Inspect riser cable connections and reseat if needed. 3. Replace faulty riser cable if issue persists.",
     "source":"SA5212D6 CPU"},
    {"category":"CPU","error_code":"P0_NIC_Err",
     "fault_description":"Network card error related to CPU link",
     "affected_parts":"CPU, NIC","root_cause":"BIOS version issue or GPU upstream issue",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. Check SOL logs for GPU upstream issues. 3. Replace faulty GPU or riser cable if issue persists.",
     "source":"SA5212D6 CPU"},

    # ── BMC SEL Event Codes ──────────────────────────────────────────────
    {"category":"Thermal","error_code":"SEL_0x04","fault_description":"SEL 0x04: Fan Failure","affected_parts":"Fan","solution":"Replace the failed fan.","source":"SA5212D6 BMC SEL"},
    {"category":"System","error_code":"SEL_0x05","fault_description":"SEL 0x05: Intrusion Detected","affected_parts":"Chassis","solution":"Check for physical intrusion and secure the chassis.","source":"SA5212D6 BMC SEL"},
    {"category":"CPU","error_code":"SEL_0x07","fault_description":"SEL 0x07: CPU Overtemperature","affected_parts":"CPU","solution":"Check thermal paste and CPU cooling system; replace fan or clean heatsink.","source":"SA5212D6 BMC SEL"},
    {"category":"Power","error_code":"SEL_0x08","fault_description":"SEL 0x08: Power Supply Failure","affected_parts":"PSU","solution":"Replace the faulty power supply.","source":"SA5212D6 BMC SEL"},
    {"category":"Network","error_code":"SEL_0x0B","fault_description":"SEL 0x0B: Add-in Card Failure","affected_parts":"PCIe card","solution":"Reseat the PCIe card; if issue persists, replace it.","source":"SA5212D6 BMC SEL"},
    {"category":"Memory","error_code":"SEL_0x0C","fault_description":"SEL 0x0C: Memory Failure","affected_parts":"DIMM","solution":"Replace the faulty DIMM.","source":"SA5212D6 BMC SEL"},
    {"category":"Storage","error_code":"SEL_0x0D","fault_description":"SEL 0x0D: Disk Failure","affected_parts":"Hard Drive","solution":"Replace the failed disk.","source":"SA5212D6 BMC SEL"},
    {"category":"System","error_code":"SEL_0x0E","fault_description":"SEL 0x0E: System Power Button Pressed","affected_parts":"System","solution":"No action required unless frequent unexpected shutdowns occur.","source":"SA5212D6 BMC SEL"},
    {"category":"BMC","error_code":"SEL_0x0F","fault_description":"SEL 0x0F: BMC Watchdog Timeout","affected_parts":"BMC","solution":"Reboot BMC or reset the watchdog timer.","source":"SA5212D6 BMC SEL"},
    {"category":"System","error_code":"SEL_0x10","fault_description":"SEL 0x10: System Reboot","affected_parts":"System","solution":"Investigate cause (power, OS, or hardware issue).","source":"SA5212D6 BMC SEL"},
    {"category":"BIOS","error_code":"SEL_0x11","fault_description":"SEL 0x11: Boot Error","affected_parts":"Boot device","solution":"Check boot order and ensure bootable media is connected.","source":"SA5212D6 BMC SEL"},
    {"category":"BIOS","error_code":"SEL_0x12","fault_description":"SEL 0x12: BIOS Boot Failure","affected_parts":"BIOS","solution":"Update BIOS firmware.","source":"SA5212D6 BMC SEL"},
    {"category":"System","error_code":"SEL_0x13","fault_description":"SEL 0x13: OS Status","affected_parts":"OS","solution":"Check OS logs and system health.","source":"SA5212D6 BMC SEL"},
    {"category":"BMC","error_code":"SEL_0x14","fault_description":"SEL 0x14: BMC Watchdog Reset","affected_parts":"BMC","solution":"Investigate BMC configuration and watchdog timer settings.","source":"SA5212D6 BMC SEL"},
    {"category":"Network","error_code":"SEL_0x15","fault_description":"SEL 0x15: LAN Failure","affected_parts":"Network Interface","solution":"Check LAN cable and network interface card.","source":"SA5212D6 BMC SEL"},
    {"category":"System","error_code":"SEL_0x16","fault_description":"SEL 0x16: Subsystem Failure","affected_parts":"Subsystem","solution":"Check subsystem logs for specific failure.","source":"SA5212D6 BMC SEL"},
    {"category":"BIOS","error_code":"SEL_0x17","fault_description":"SEL 0x17: BIOS Options Failure","affected_parts":"BIOS","solution":"Reconfigure BIOS options or update firmware.","source":"SA5212D6 BMC SEL"},
    {"category":"GPU","error_code":"SEL_0x18","fault_description":"SEL 0x18: GPU Failure","affected_parts":"GPU","solution":"Replace the GPU or reseat the card.","source":"SA5212D6 BMC SEL"},
    {"category":"Storage","error_code":"SEL_0x19","fault_description":"SEL 0x19: RAID Failure","affected_parts":"RAID Controller","solution":"Replace the RAID controller or rebuild array.","source":"SA5212D6 BMC SEL"},
    {"category":"Firmware","error_code":"SEL_0x1A","fault_description":"SEL 0x1A: Firmware Update Failure","affected_parts":"BMC or Component","solution":"Retry firmware update or use alternative method.","source":"SA5212D6 BMC SEL"},

    # ── SMART Attributes ─────────────────────────────────────────────────
    {"category":"Storage","error_code":"SMART_Reallocated_Sector","fault_description":"Reallocated Sector Count > 100","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Current_Pending","fault_description":"Current Pending Sector Count > 50","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Uncorrectable","fault_description":"Uncorrectable Sector Count > 0","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Power_On_Hours","fault_description":"Power-On Hours > 100,000","affected_parts":"Hard disk","solution":"Replace the disk (end of service life).","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Temperature","fault_description":"Disk Temperature > 60°C","affected_parts":"Hard disk, Cooling","solution":"Check cooling system and disk health.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Read_Error_Rate","fault_description":"Read Error Rate > 1000","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Seek_Error_Rate","fault_description":"Seek Error Rate > 1000","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},
    {"category":"Storage","error_code":"SMART_Spin_Retry","fault_description":"Spin Retry Count > 10","affected_parts":"Hard disk","solution":"Replace the disk.","source":"SA5212D6 SMART"},

    # ── Xid Error Codes ──────────────────────────────────────────────────
    {"category":"GPU","error_code":"Xid_1","fault_description":"Xid 1: GPU reset requested","affected_parts":"GPU","solution":"Reboot the system.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_2","fault_description":"Xid 2: GPU reset failed","affected_parts":"GPU","solution":"Replace the GPU.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_3","fault_description":"Xid 3: GPU watchdog timeout","affected_parts":"GPU","solution":"Reboot the system.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_4","fault_description":"Xid 4: GPU power failure","affected_parts":"GPU, Power supply","solution":"Check power supply and GPU connection.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_5","fault_description":"Xid 5: GPU temperature threshold exceeded","affected_parts":"GPU, Cooling","solution":"Check cooling system and GPU health.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_6","fault_description":"Xid 6: GPU fan failure","affected_parts":"GPU fan, GPU","solution":"Replace the GPU or reseat the fan.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_7","fault_description":"Xid 7: GPU memory error","affected_parts":"GPU","solution":"Replace the GPU.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_8","fault_description":"Xid 8: GPU driver failure","affected_parts":"GPU","solution":"Reinstall or update GPU driver.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_9","fault_description":"Xid 9: GPU PCIe link failure","affected_parts":"GPU, Riser cable","solution":"Reseat the GPU or replace the riser cable.","source":"SA5212D6 Xid"},
    {"category":"GPU","error_code":"Xid_10","fault_description":"Xid 10: GPU firmware failure","affected_parts":"GPU","solution":"Update GPU firmware.","source":"SA5212D6 Xid"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)
    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='SEL_0x04'").fetchone()
    con.close()
    if has:
        print("SEL/SMART/Xid data already loaded. Skipping.")
        return
    for e in ENTRIES:
        db.add_knowledge(path, e)
    print(f"Loaded {len(ENTRIES)} SEL/SMART/Xid/CPU entries.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
