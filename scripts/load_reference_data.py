"""
load_reference_data.py — BMC SEL events, SMART thresholds, Xid errors, CPU link faults.
Source: SA5212D6/SA5326D6 vendor KB chatbot extraction.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

ENTRIES = [
    # ── CPU link faults ──────────────────────────────────────────────────
    {"category":"CPU","error_code":"CPU_Threshold",
     "fault_description":"CPU threshold fault — CPU threshold throttling detected",
     "affected_parts":"CPU",
     "root_cause":"BIOS version issue (below BIOS_01.01.01.05.01)",
     "solution":"1. Check BIOS version, if lower than BIOS_01.01.01.05.01, upgrade BIOS and BMC. 2. Check and reapply thermal paste. 3. If issue persists after upgrade, perform Linpack stress testing and cross-testing to determine hardware issue.",
     "source":"SA5212D6 CPU Reference"},

    {"category":"CPU","error_code":"CPU_MCE",
     "fault_description":"Machine Check Exception (MCE) — CPU MCE error",
     "affected_parts":"CPU",
     "root_cause":"BIOS version issue or system kernel incompatibility",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. If problem persists, check OS kernel for compatibility issues. 3. Perform cross-testing to identify hardware faults.",
     "source":"SA5212D6 CPU Reference"},

    {"category":"GPU","error_code":"P0_Card_Err",
     "fault_description":"GPU card error related to CPU link (P0_Card_Err)",
     "affected_parts":"CPU, GPU, Riser cable",
     "root_cause":"BIOS version issue or riser cable connection issue",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. Inspect riser cable connections and reseat. 3. Replace faulty riser cable if issue persists.",
     "source":"SA5212D6 CPU-GPU Reference"},

    {"category":"Network","error_code":"P0_NIC_Err",
     "fault_description":"Network card error related to CPU link (P0_NIC_Err)",
     "affected_parts":"CPU, NIC, GPU",
     "root_cause":"BIOS version issue or GPU upstream issue",
     "solution":"1. Check BIOS version and upgrade if necessary. 2. Check SOL logs for GPU upstream issues. 3. Replace faulty GPU or riser cable if issue persists.",
     "source":"SA5212D6 CPU-NIC Reference"},

    # ── BMC SEL Event Codes ──────────────────────────────────────────────
    {"category":"Thermal","error_code":"SEL_0x04",
     "fault_description":"BMC SEL 0x04: Fan Failure detected",
     "affected_parts":"Fan","root_cause":"Fan motor or connection failure",
     "solution":"Replace the failed fan.","source":"SA5212D6 SEL Reference"},

    {"category":"System","error_code":"SEL_0x05",
     "fault_description":"BMC SEL 0x05: Chassis Intrusion Detected",
     "affected_parts":"Chassis","root_cause":"Physical intrusion or open chassis",
     "solution":"Check for physical intrusion and secure the chassis.","source":"SA5212D6 SEL Reference"},

    {"category":"CPU","error_code":"SEL_0x07",
     "fault_description":"BMC SEL 0x07: CPU Overtemperature",
     "affected_parts":"CPU, Fan, Heatsink","root_cause":"Thermal paste degradation or cooling failure",
     "solution":"Check thermal paste and CPU cooling system. Replace fan or clean heatsink.","source":"SA5212D6 SEL Reference"},

    {"category":"Power","error_code":"SEL_0x08",
     "fault_description":"BMC SEL 0x08: Power Supply Failure",
     "affected_parts":"PSU","root_cause":"PSU hardware fault",
     "solution":"Replace the faulty power supply.","source":"SA5212D6 SEL Reference"},

    {"category":"Network","error_code":"SEL_0x0B",
     "fault_description":"BMC SEL 0x0B: Add-in Card (PCIe) Failure",
     "affected_parts":"PCIe card","root_cause":"PCIe card fault or poor seating",
     "solution":"Reseat the PCIe card. If issue persists, replace it.","source":"SA5212D6 SEL Reference"},

    {"category":"Memory","error_code":"SEL_0x0C",
     "fault_description":"BMC SEL 0x0C: Memory/DIMM Failure",
     "affected_parts":"DIMM","root_cause":"DIMM hardware failure",
     "solution":"Replace the faulty DIMM.","source":"SA5212D6 SEL Reference"},

    {"category":"Storage","error_code":"SEL_0x0D",
     "fault_description":"BMC SEL 0x0D: Disk Failure",
     "affected_parts":"Hard Drive","root_cause":"Disk hardware failure",
     "solution":"Replace the failed disk.","source":"SA5212D6 SEL Reference"},

    {"category":"Firmware","error_code":"SEL_0x0F",
     "fault_description":"BMC SEL 0x0F: BMC Watchdog Timeout",
     "affected_parts":"BMC","root_cause":"BMC firmware hang or misconfiguration",
     "solution":"Reboot BMC or reset the watchdog timer.","source":"SA5212D6 SEL Reference"},

    {"category":"System","error_code":"SEL_0x10",
     "fault_description":"BMC SEL 0x10: System Reboot event",
     "affected_parts":"System","root_cause":"Power, OS, or hardware issue causing reboot",
     "solution":"Investigate cause: check power events, OS logs, and hardware health.","source":"SA5212D6 SEL Reference"},

    {"category":"BIOS","error_code":"SEL_0x11",
     "fault_description":"BMC SEL 0x11: Boot Error",
     "affected_parts":"Boot device","root_cause":"Boot device missing or misconfigured",
     "solution":"Check boot order and ensure bootable media is connected.","source":"SA5212D6 SEL Reference"},

    {"category":"BIOS","error_code":"SEL_0x12",
     "fault_description":"BMC SEL 0x12: BIOS Boot Failure",
     "affected_parts":"BIOS","root_cause":"BIOS corruption or incompatibility",
     "solution":"Update BIOS firmware.","source":"SA5212D6 SEL Reference"},

    {"category":"Network","error_code":"SEL_0x15",
     "fault_description":"BMC SEL 0x15: LAN Failure",
     "affected_parts":"Network Interface, Cable","root_cause":"LAN cable or NIC fault",
     "solution":"Check LAN cable and network interface card.","source":"SA5212D6 SEL Reference"},

    {"category":"GPU","error_code":"SEL_0x18",
     "fault_description":"BMC SEL 0x18: GPU Failure",
     "affected_parts":"GPU","root_cause":"GPU hardware fault",
     "solution":"Replace the GPU or reseat the card.","source":"SA5212D6 SEL Reference"},

    {"category":"Storage","error_code":"SEL_0x19",
     "fault_description":"BMC SEL 0x19: RAID Failure",
     "affected_parts":"RAID Controller","root_cause":"RAID controller hardware fault",
     "solution":"Replace the RAID controller or rebuild array.","source":"SA5212D6 SEL Reference"},

    {"category":"Firmware","error_code":"SEL_0x1A",
     "fault_description":"BMC SEL 0x1A: Firmware Update Failure",
     "affected_parts":"BMC or Component","root_cause":"Firmware update process failure",
     "solution":"Retry firmware update or use alternative method.","source":"SA5212D6 SEL Reference"},

    # ── SMART Thresholds ─────────────────────────────────────────────────
    {"category":"Storage","error_code":"SMART_Reallocated_Gt100",
     "fault_description":"SMART Reallocated Sector Count > 100",
     "affected_parts":"Hard disk / SSD","root_cause":"Disk media degradation, sector remapping exhausting spare area",
     "solution":"Replace the disk immediately.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_Pending_Gt50",
     "fault_description":"SMART Current Pending Sector Count > 50",
     "affected_parts":"Hard disk / SSD","root_cause":"Sectors waiting reallocation, media degradation",
     "solution":"Replace the disk immediately.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_Uncorrectable_Gt0",
     "fault_description":"SMART Uncorrectable Sector Count > 0",
     "affected_parts":"Hard disk / SSD","root_cause":"Permanent media failure",
     "solution":"Replace the disk immediately.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_PowerOnHours_Gt100k",
     "fault_description":"SMART Power-On Hours > 100,000",
     "affected_parts":"Hard disk / SSD","root_cause":"Disk exceeding design life",
     "solution":"Replace the disk proactively.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_Temp_Gt60C",
     "fault_description":"SMART Temperature > 60°C",
     "affected_parts":"Hard disk, Cooling system","root_cause":"Overheating from poor airflow or cooling failure",
     "solution":"Check cooling system and disk health. Improve airflow.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_ReadError_Gt1000",
     "fault_description":"SMART Read Error Rate > 1000",
     "affected_parts":"Hard disk / SSD","root_cause":"Read head or media failure",
     "solution":"Replace the disk.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_SeekError_Gt1000",
     "fault_description":"SMART Seek Error Rate > 1000",
     "affected_parts":"Hard disk","root_cause":"Mechanical seek mechanism failure",
     "solution":"Replace the disk.","source":"SA5212D6 SMART Thresholds"},

    {"category":"Storage","error_code":"SMART_SpinRetry_Gt10",
     "fault_description":"SMART Spin Retry Count > 10",
     "affected_parts":"Hard disk","root_cause":"Disk motor or spindle issue",
     "solution":"Replace the disk.","source":"SA5212D6 SMART Thresholds"},

    # ── GPU Xid Error Codes ──────────────────────────────────────────────
    {"category":"GPU","error_code":"Xid_1",
     "fault_description":"GPU Xid 1: GPU reset requested",
     "affected_parts":"GPU","root_cause":"GPU driver or hardware triggered reset",
     "solution":"Reboot the system. If recurring, check GPU driver and firmware.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_2",
     "fault_description":"GPU Xid 2: GPU reset failed",
     "affected_parts":"GPU","root_cause":"GPU hardware failure preventing recovery",
     "solution":"Replace the GPU.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_3",
     "fault_description":"GPU Xid 3: GPU watchdog timeout",
     "affected_parts":"GPU","root_cause":"GPU hung or unresponsive",
     "solution":"Reboot the system. If recurring, replace GPU.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_4",
     "fault_description":"GPU Xid 4: GPU power failure",
     "affected_parts":"GPU, Power supply","root_cause":"Insufficient or interrupted GPU power",
     "solution":"Check power supply and GPU power connections. Replace if faulty.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_5",
     "fault_description":"GPU Xid 5: GPU temperature threshold exceeded",
     "affected_parts":"GPU, Cooling system","root_cause":"GPU overheating",
     "solution":"Check cooling system and GPU health. Clean heatsink, verify fan operation.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_6",
     "fault_description":"GPU Xid 6: GPU fan failure",
     "affected_parts":"GPU fan","root_cause":"GPU fan motor failure",
     "solution":"Replace the GPU or reseat the fan.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_7",
     "fault_description":"GPU Xid 7: GPU memory error (ECC)",
     "affected_parts":"GPU","root_cause":"GPU memory hardware failure",
     "solution":"Replace the GPU.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_8",
     "fault_description":"GPU Xid 8: GPU driver failure",
     "affected_parts":"GPU","root_cause":"GPU driver incompatibility or corruption",
     "solution":"Reinstall or update GPU driver. If persists, replace GPU.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_9",
     "fault_description":"GPU Xid 9: GPU PCIe link failure",
     "affected_parts":"GPU, Riser cable","root_cause":"PCIe link degradation or connection issue",
     "solution":"Reseat GPU or replace the riser cable.","source":"NVIDIA Xid Reference"},

    {"category":"GPU","error_code":"Xid_10",
     "fault_description":"GPU Xid 10: GPU firmware failure",
     "affected_parts":"GPU","root_cause":"GPU firmware corruption",
     "solution":"Update GPU firmware. If persists, replace GPU.","source":"NVIDIA Xid Reference"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)
    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='SEL_0x04'").fetchone()
    con.close()
    if has:
        print("Reference data already loaded. Skipping.")
        return
    for e in ENTRIES:
        db.add_knowledge(path, e)
    print(f"Loaded {len(ENTRIES)} reference entries (SEL, SMART, Xid, CPU).")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
