"""
load_gpu_faults.py — GPU fault codes for SA5212D6/SA5326D6.
Source: Vendor GPU troubleshooting documentation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db
from fiars.config import load_config

ENTRIES = [
    {"category":"GPU","error_code":"GPU_PCIe_UCE",
     "fault_description":"PCIe UCE (Uncorrectable Error) on GPU — GPU unresponsive, OS may crash or reboot",
     "affected_parts":"Retimer card, OCP riser cable, GPU",
     "root_cause":"Faulty Retimer card or OCP riser cable, poor signal integrity between GPU and motherboard",
     "solution":"1. Collect one-key logs. 2. Check Retimer card and OCP riser cable connections. 3. Replace Retimer card or OCP riser cable if faulty. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Card_Dropout",
     "fault_description":"GPU card dropout — GPU becomes unresponsive, OS fails to recognize GPU, Xid errors",
     "affected_parts":"GPU, OCP riser cable",
     "root_cause":"Poor connection between GPU and OCP riser, faulty GPU, BIOS/BMC firmware issue",
     "solution":"1. Collect one-key logs. 2. Reseat GPU and OCP riser cable. 3. Check firmware versions. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Signal_Monitoring_Fault",
     "fault_description":"GPU signal monitoring line fault — GPU slot not recognized in OS",
     "affected_parts":"OCP riser cable, GPU",
     "root_cause":"Misconnection or fault in OCP riser cable, BIOS version issue",
     "solution":"1. Collect one-key logs. 2. Check OCP riser cable connections. 3. Replace OCP riser cable if misconnected. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_CTO",
     "fault_description":"GPU CTO (Correctable Transaction Error) — GPU performance issues",
     "affected_parts":"GPU, OCP riser cable",
     "root_cause":"Faulty GPU or poor signal integrity between GPU and motherboard",
     "solution":"1. Collect one-key logs. 2. Reseat GPU and OCP riser cable. 3. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Slot_Anomaly",
     "fault_description":"GPU slot information anomaly — GPU slot not recognized in OS",
     "affected_parts":"OCP riser cable, GPU",
     "root_cause":"Misconnection or fault in OCP riser cable",
     "solution":"1. Collect one-key logs. 2. Check OCP riser cable connections. 3. Replace OCP riser cable if misconnected. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Power_Supply_Fault",
     "fault_description":"GPU power supply fault — GPU fails to power on",
     "affected_parts":"GPU power supply, GPU",
     "root_cause":"Faulty GPU power supply or poor power connection",
     "solution":"1. Collect one-key logs. 2. Check GPU power supply connections. 3. Replace GPU power supply if faulty. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_VBIOS_Fault",
     "fault_description":"GPU BIOS (VBIOS) fault — GPU fails to initialize, corrupted firmware",
     "affected_parts":"GPU",
     "root_cause":"Faulty or corrupted GPU BIOS/VBIOS",
     "solution":"1. Collect one-key logs. 2. Flash GPU BIOS using provided tools. 3. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Fan_Fault",
     "fault_description":"GPU fan fault — GPU fan failure detected",
     "affected_parts":"GPU fan, GPU",
     "root_cause":"Faulty GPU fan or poor fan connection",
     "solution":"1. Collect one-key logs. 2. Check GPU fan connections. 3. Replace GPU fan if faulty. 4. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Driver_Fault",
     "fault_description":"GPU driver fault — GPU driver fails to load, incompatible driver version",
     "affected_parts":"GPU",
     "root_cause":"Faulty or incompatible GPU driver",
     "solution":"1. Collect one-key logs. 2. Reinstall or update GPU driver. 3. If issue persists, replace GPU.",
     "source":"SA5212D6 GPU Reference [5,10]"},

    {"category":"GPU","error_code":"GPU_Xid_79_Fallen_Off_Bus",
     "fault_description":"GPU Xid 79 — GPU has fallen off the bus, NVRM Xid error",
     "affected_parts":"GPU, OCP riser cable, Retimer card, Motherboard",
     "root_cause":"GPU communication failure — faulty GPU, OCP riser cable, retimer card, or PCIe slot issue",
     "solution":"1. Collect one-key logs (SOLHostCapture). 2. Reseat GPU and OCP riser cable. 3. Check retimer card. 4. Test GPU in different slot if possible. 5. If issue persists, replace GPU. 6. If issue follows slot, replace motherboard.",
     "source":"SA5212D6 GPU Reference [5,10]"},
]


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)
    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='GPU_Xid_79_Fallen_Off_Bus'").fetchone()
    con.close()
    if has:
        print("GPU fault codes already loaded. Skipping.")
        return
    for e in ENTRIES:
        db.add_knowledge(path, e)
    print(f"Loaded {len(ENTRIES)} GPU fault codes.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
