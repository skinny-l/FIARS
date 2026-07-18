"""
load_server_fault_kb.py — Server Fault Knowledge Base (29 entries).
Source: Vendor server fault troubleshooting documentation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

ENTRIES = [
    # ── CPU ──────────────────────────────────────────────────────────────
    {"category":"CPU","error_code":"CPU_IERR",
     "fault_description":"Unexpected system reboot, system crash, or processor error events (IERR)",
     "affected_parts":"CPU, Motherboard",
     "root_cause":"Faulty CPU, motherboard issue, or firmware issue",
     "solution":"1. Review system and processor logs. 2. Analyze processor error records. 3. Cross-test CPU if available. 4. Replace CPU if fault follows processor. 5. Replace motherboard if issue persists.",
     "source":"Server Fault KB - CPU"},

    {"category":"CPU","error_code":"CPU_Detection_Failure",
     "fault_description":"CPU not recognized, CPU configuration error, FRB2 failure, POST failure",
     "affected_parts":"CPU, Motherboard",
     "root_cause":"Improper CPU installation, bent socket pins, unsupported CPU, or motherboard fault",
     "solution":"1. Reseat CPU. 2. Inspect CPU socket for bent pins. 3. Clear CMOS. 4. Test with known-good CPU. 5. Replace faulty component.",
     "source":"Server Fault KB - CPU"},

    {"category":"CPU","error_code":"CPU_Thermal_Event",
     "fault_description":"CPU thermal trip, CPU throttling, high temperature alerts",
     "affected_parts":"CPU, Fan, Heatsink",
     "root_cause":"Fan failure, dust buildup, poor airflow, or cooling module failure",
     "solution":"1. Verify fan operation. 2. Clean cooling components. 3. Check airflow restrictions. 4. Replace faulty fans or heatsinks. 5. Monitor operating temperature.",
     "source":"Server Fault KB - CPU"},

    {"category":"CPU","error_code":"CPU_Memory_Fault",
     "fault_description":"Memory errors linked to specific CPU, memory channel failure",
     "affected_parts":"CPU, Motherboard",
     "root_cause":"Faulty CPU memory controller or motherboard issue",
     "solution":"1. Test memory on alternate channels. 2. Swap CPU if available. 3. Replace faulty CPU. 4. Replace motherboard if required.",
     "source":"Server Fault KB - CPU"},

    # ── Memory ───────────────────────────────────────────────────────────
    {"category":"Memory","error_code":"Memory_Detection_Failure",
     "fault_description":"Memory not recognized, missing memory capacity",
     "affected_parts":"DIMM, Motherboard",
     "root_cause":"Improper installation, faulty DIMM, or faulty memory slot",
     "solution":"1. Reseat DIMM. 2. Test DIMM in another slot. 3. Replace faulty DIMM. 4. Replace motherboard if necessary.",
     "source":"Server Fault KB - Memory"},

    {"category":"Memory","error_code":"Correctable_ECC_CE",
     "fault_description":"ECC correction events, intermittent memory warnings (Correctable Error)",
     "affected_parts":"DIMM",
     "root_cause":"Aging DIMM or signal integrity issue",
     "solution":"1. Monitor error frequency. 2. Run memory diagnostics. 3. Replace DIMM if errors increase.",
     "source":"Server Fault KB - Memory"},

    {"category":"Memory","error_code":"Uncorrectable_ECC_UCE",
     "fault_description":"System crash or memory-related fault events (Uncorrectable ECC Error)",
     "affected_parts":"DIMM",
     "root_cause":"Failed memory module",
     "solution":"1. Identify affected DIMM. 2. Replace memory module. 3. Perform memory validation testing.",
     "source":"Server Fault KB - Memory"},

    {"category":"Memory","error_code":"Memory_Controller_Fault",
     "fault_description":"Multiple memory channel failures, persistent memory errors",
     "affected_parts":"CPU, Motherboard",
     "root_cause":"CPU memory controller failure or motherboard issue",
     "solution":"1. Test with known-good memory. 2. Replace CPU if memory controller is faulty. 3. Replace motherboard if required.",
     "source":"Server Fault KB - Memory"},

    # ── Storage & RAID ───────────────────────────────────────────────────
    {"category":"Storage","error_code":"RAID_Driver_Issue",
     "fault_description":"RAID controller not detected, RAID driver missing during OS installation",
     "affected_parts":"RAID Controller",
     "root_cause":"Missing or incompatible RAID driver",
     "solution":"1. Install correct RAID driver. 2. Update controller firmware. 3. Verify OS compatibility.",
     "source":"Server Fault KB - Storage"},

    {"category":"Storage","error_code":"RAID_Degraded",
     "fault_description":"RAID degraded warning, reduced redundancy",
     "affected_parts":"Hard disk, RAID array",
     "root_cause":"Failed drive in RAID array",
     "solution":"1. Identify failed disk. 2. Replace failed disk. 3. Rebuild RAID array. 4. Verify array health.",
     "source":"Server Fault KB - Storage"},

    {"category":"Storage","error_code":"Drive_Detection_Failure",
     "fault_description":"Drive not detected, missing storage device",
     "affected_parts":"Hard disk, Cable, Controller",
     "root_cause":"Loose cable, failed drive, or failed controller",
     "solution":"1. Check cabling. 2. Reseat drive. 3. Test drive in another system. 4. Replace faulty component.",
     "source":"Server Fault KB - Storage"},

    {"category":"Storage","error_code":"Drive_Failure",
     "fault_description":"Read/write errors, SMART alerts, drive inaccessible",
     "affected_parts":"Hard disk / SSD",
     "root_cause":"Mechanical failure, NAND degradation, or controller failure",
     "solution":"1. Backup data immediately. 2. Replace drive. 3. Rebuild RAID if applicable.",
     "source":"Server Fault KB - Storage"},

    {"category":"Storage","error_code":"Storage_Controller_Failure",
     "fault_description":"Multiple drives unavailable, storage subsystem failure",
     "affected_parts":"Storage controller",
     "root_cause":"Controller hardware fault or firmware corruption",
     "solution":"1. Update firmware. 2. Replace controller. 3. Validate storage functionality.",
     "source":"Server Fault KB - Storage"},

    # ── Network ──────────────────────────────────────────────────────────
    {"category":"Network","error_code":"Network_Connectivity_Failure",
     "fault_description":"Network disconnected, link down",
     "affected_parts":"Cable, NIC, Switch port",
     "root_cause":"Faulty cable, faulty port, or switch issue",
     "solution":"1. Verify cable connection. 2. Test alternate cable. 3. Test alternate switch port. 4. Replace faulty hardware.",
     "source":"Server Fault KB - Network"},

    {"category":"Network","error_code":"Network_Performance_Issue",
     "fault_description":"Slow network speed, high latency",
     "affected_parts":"Cable, NIC, Network driver",
     "root_cause":"Network congestion, faulty cable, or driver issue",
     "solution":"1. Verify link speed. 2. Update network driver. 3. Replace faulty cable. 4. Investigate network infrastructure.",
     "source":"Server Fault KB - Network"},

    {"category":"Network","error_code":"Network_Adapter_Failure",
     "fault_description":"NIC not detected, network unavailable",
     "affected_parts":"NIC",
     "root_cause":"Failed NIC or driver issue",
     "solution":"1. Update driver. 2. Reseat adapter. 3. Replace network card.",
     "source":"Server Fault KB - Network"},

    # ── Power ────────────────────────────────────────────────────────────
    {"category":"Power","error_code":"No_Power_Condition",
     "fault_description":"System does not power on",
     "affected_parts":"PSU, Power cable, Motherboard",
     "root_cause":"Failed PSU, power cable issue, or motherboard issue",
     "solution":"1. Verify power source. 2. Test alternate power cable. 3. Test alternate PSU. 4. Replace faulty component.",
     "source":"Server Fault KB - Power"},

    {"category":"Power","error_code":"PSU_Failure",
     "fault_description":"PSU alarms, redundant PSU failure",
     "affected_parts":"PSU",
     "root_cause":"PSU hardware fault",
     "solution":"1. Reseat PSU. 2. Test known-good PSU. 3. Replace failed PSU.",
     "source":"Server Fault KB - Power"},

    {"category":"Power","error_code":"Power_Overload_Event",
     "fault_description":"PSU overload alarms, unexpected shutdowns",
     "affected_parts":"PSU",
     "root_cause":"Excessive power draw or undersized PSU",
     "solution":"1. Verify power consumption. 2. Reduce load if required. 3. Install appropriate PSU.",
     "source":"Server Fault KB - Power"},

    # ── Cooling & Thermal ────────────────────────────────────────────────
    {"category":"Thermal","error_code":"Fan_Failure",
     "fault_description":"Fan stopped, fan speed warning",
     "affected_parts":"Fan module",
     "root_cause":"Fan motor failure or fan connection issue",
     "solution":"1. Verify fan operation. 2. Check fan connections. 3. Replace failed fan.",
     "source":"Server Fault KB - Cooling"},

    {"category":"Thermal","error_code":"Fan_Speed_Abnormality",
     "fault_description":"Fan speed too low or too high",
     "affected_parts":"Fan module, BIOS",
     "root_cause":"Fan fault or incorrect BIOS fan profile settings",
     "solution":"1. Verify fan profile settings. 2. Test fan operation. 3. Replace fan if necessary.",
     "source":"Server Fault KB - Cooling"},

    {"category":"Thermal","error_code":"Environmental_Temperature",
     "fault_description":"High system temperature, thermal alarms",
     "affected_parts":"Cooling system, Rack",
     "root_cause":"Poor room cooling or blocked airflow",
     "solution":"1. Improve cooling environment. 2. Verify rack airflow. 3. Remove airflow obstructions.",
     "source":"Server Fault KB - Cooling"},

    # ── BIOS / Firmware / BMC ────────────────────────────────────────────
    {"category":"BIOS","error_code":"BIOS_POST_Failure",
     "fault_description":"System fails POST, boot process stops",
     "affected_parts":"Motherboard, CPU, Memory",
     "root_cause":"Hardware failure or BIOS corruption",
     "solution":"1. Clear CMOS. 2. Test minimum hardware configuration. 3. Replace faulty hardware.",
     "source":"Server Fault KB - BIOS"},

    {"category":"BIOS","error_code":"BIOS_Config_Issue",
     "fault_description":"Incorrect BIOS settings, configuration errors",
     "affected_parts":"BIOS, CMOS battery",
     "root_cause":"Misconfiguration or CMOS reset",
     "solution":"1. Restore default settings. 2. Reconfigure BIOS. 3. Replace CMOS battery if needed.",
     "source":"Server Fault KB - BIOS"},

    {"category":"Firmware","error_code":"Firmware_Compatibility",
     "fault_description":"Hardware not recognized or unstable operation due to firmware",
     "affected_parts":"BIOS, BMC, Hardware firmware",
     "root_cause":"Outdated firmware or firmware mismatch",
     "solution":"1. Update BIOS. 2. Update BMC firmware. 3. Validate firmware compatibility.",
     "source":"Server Fault KB - Firmware"},

    {"category":"Firmware","error_code":"BMC_Communication_Failure",
     "fault_description":"BMC not responding, management connection failure",
     "affected_parts":"BMC, Motherboard, Network",
     "root_cause":"Firmware issue, network issue, or motherboard fault",
     "solution":"1. Restart BMC. 2. Verify network settings. 3. Update firmware. 4. Replace motherboard if required.",
     "source":"Server Fault KB - Firmware"},

    # ── System & Boot ────────────────────────────────────────────────────
    {"category":"System","error_code":"System_Crash_Hang",
     "fault_description":"System lockup, system hang, unexpected restart",
     "affected_parts":"CPU, Memory, Motherboard",
     "root_cause":"CPU failure, memory failure, motherboard issue, or driver issue",
     "solution":"1. Review logs. 2. Run hardware diagnostics. 3. Identify failing component. 4. Replace faulty hardware.",
     "source":"Server Fault KB - System"},

    {"category":"System","error_code":"OS_Boot_Failure",
     "fault_description":"OS fails to load, boot device error",
     "affected_parts":"Boot device, BIOS",
     "root_cause":"Failed boot device, corrupted OS, or BIOS configuration issue",
     "solution":"1. Verify boot device. 2. Check BIOS boot order. 3. Repair operating system. 4. Replace failed storage device.",
     "source":"Server Fault KB - System"},

    {"category":"System","error_code":"UEFI_GPT_Issue",
     "fault_description":"UEFI boot failure, disk size limitation issues",
     "affected_parts":"BIOS, Boot disk",
     "root_cause":"Legacy boot mode or incorrect disk format",
     "solution":"1. Enable UEFI mode. 2. Convert disk to GPT. 3. Reinstall operating system if required.",
     "source":"Server Fault KB - System"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='CPU_IERR'").fetchone()
    con.close()
    if has:
        print("Server Fault KB already loaded. Skipping.")
        return

    for e in ENTRIES:
        db.add_knowledge(path, e)
    print(f"Loaded {len(ENTRIES)} server fault KB entries.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
