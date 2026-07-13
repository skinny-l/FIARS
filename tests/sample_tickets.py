"""Real sample tickets used to verify the parser (no server needed)."""

HDD_TICKET = """工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
硬盘VR状态/Disk Virtual Return Status：forced_non_return强制不返还
Priority：normal
可以直接维修
server_model：S520-B3 server_product：S68M1-I9DD3B-L-WW
服务器SN/Server SN：21C938088
机柜位置/Location：MYJHBGDS_B4_DH1B-B-10
起始U位/ unit_no: 40
server_po：
server_ip：fdbd:dc53:15:830::25
服务器资产编号/asset_no:2024-is-srv-1688446
部件位置/part_position:22
背板号/backplane_number:0
服务器厂商/manufacturer:Inspur
部件厂商/part_manufacturer:Seagate
固件版本/firmware_version:SC03
部件SN/part_sn:WVT0VMT9
部件容量/part_size:20TB
部件类型/part_type:HDD
部件PN/part_pn:ST20000NM007D
fault_log_dir:None
故障明细/Fault_Detail:HDD: 0 < (BadSectorCount) < Min & (IOErrorWeek) > Min
故障设备/fault_part：sdw
故障类型/fault_type:Disk
故障描述/Fault Description:IOErrorWeekCount: (678) > 50 and HDDReallocatedSectors: 0 < (32) <= 200
30天内重复报修次数/fault_30day_rt：0
manufacturer_id：530666

From <https://stms.ieisystem.com/beijian/PkgController/showGcsPkgTodoInfo.htm?id=2014119&taskId=8d543b39-6886-11f1-a513-6c92bf668245>
"""

HDD_TICKET_NUMBER = "SHGD0002014119"

# Dispatch/assignment table sample — one row, matching HDD_TICKET's server SN.
# Note the dispatch ticket number ("...9999") deliberately differs from
# HDD_TICKET_NUMBER above, to prove the merge overrides the manually-typed
# ticket number rather than just filling in when blank.
DISPATCH_ROW_HDD = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
2/7/2026
SHGD0002019999
SHSJ0004150001
21C938088
MYJHBGDS_B4_DH1B-B-10-40
Hard drive
V0232PY0000000ZY
V0233JP0000000ZY
Q
QC5476M6D
Fahrul Deliver onsite"""

# Real dispatch table sample: one ticket number covering two parts on the
# same server (Motherboard + Memory), used to test category disambiguation.
DISPATCH_TABLE_TWO_PARTS = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
2/7/2026
SHGD0002025775
SHSJ0004155107
21D738325
MYJHBBDC02_B1_G1-V-14-13
Motherboard - high risk have bent pins
YZMB-02666-106
YZMB-02666-106 borrow
Q
QC6468D7-SG
Fahrul Deliver onsite
2/7/2026
SHGD0002025775
SHSJ0004155107
21D738325
MYJHBBDC02_B1_G1-V-14-13
Memory
V0040NM0000000ZY
V0040NM0000000ZY
Q
QC6468D7-SG
Fahrul Deliver onsite"""

# Real-world case: ONE fault-description block (one job) but the dispatch
# table carries two rows for the same ticket/server SN — Memory and
# Motherboard both replaced under one ticket. Used to verify that both
# parts land in a single report instead of one PN being dropped, and
# instead of the ticket being split into two separate block reports.
MB_TICKET = """工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
Priority：normal
server_model：S520-B3 server_product：SA5280LM6D
服务器SN/Server SN：21B916171
机柜位置/Location：MYJHBGDS_B2_DH1A-H-10
起始U位/ unit_no: 33
服务器厂商/manufacturer:Inspur
部件厂商/part_manufacturer:Inspur
部件类型/part_type:Motherboard
故障明细/Fault_Detail:Memory CE (Count) > Max (Kernel)
故障类型/fault_type:Memory
故障描述/Fault Description:Memory CE (Count) > Max (Kernel)
30天内重复报修次数/fault_30day_rt：0
"""

MB_TICKET_NUMBER = "SHGD0002032731"

DISPATCH_TABLE_MB_PLUS_MEMORY = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
10/7/2026
SHGD0002032731
SHSJ0004170384
21B916171
MYJHBGDS_B2_DH1A-H-10-33
Memory
V0040E20000000ZY
V0040E20000000ZY
I
SA5280LM6D
Haikal | Xianyao | Zul Deliver onsite
10/7/2026
SHGD0002032731
SHSJ0004170384
21B916171
MYJHBGDS_B2_DH1A-H-10-33
Motherboard
YZMB-03296-10F
YZMB-03296-10F
I
SA5280LM6D
Haikal | Xianyao | Zul Deliver onsite"""

# Real-world case: TWO 工单标签/tags fault blocks under one ticket — same
# server SN, two distinct GPU Xid events (Xid 95 uncontained ECC, and a
# separate remapped-rows event) — but only ONE dispatch-table row for that
# server SN (the GPU itself was only dispatched once). Used to verify the
# two blocks combine into a single note (shared header, one Remark) with
# each block keeping its own Details line and its own part data, instead
# of rendering as two fully separate reports.
GPU_TWO_BLOCK_TICKET = """工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
Priority：normal
server_model：NF5468M6 server_product：G26S2-I8CD4-WW
服务器SN/Server SN：2KB900226
机柜位置/Location：MYJHBGDS_B2_DH2A-A-04
起始U位/ unit_no: 11
服务器厂商/manufacturer:Inspur
部件位置/part_position:37:00
故障明细/Fault_Detail:xid 95 Uncontained ECC error occurred
故障类型/fault_type:GPU
故障描述/Fault Description:diff:371;NVRM: Xid (PCI:0000:37:00): 95, pid=5171, Uncontained: FBHUB. RST: Yes, D-RST: No
30天内重复报修次数/fault_30day_rt：0
工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
Priority：normal
server_model：NF5468M6 server_product：G26S2-I8CD4-WW
服务器SN/Server SN：2KB900226
机柜位置/Location：MYJHBGDS_B2_DH2A-A-04
起始U位/ unit_no: 11
服务器厂商/manufacturer:Inspur
部件位置/part_position:0000:37:00.0
部件厂商/part_manufacturer:Nvidia
部件SN/part_sn:1323622028016
部件PN/part_pn:900-21001-0020-100
故障明细/Fault_Detail:Remapped Rows pending With Volatile DRAM Uncorrectable > 0
故障类型/fault_type:GPU
故障描述/Fault Description:RemappedRows Pending:Yes,Volatile DRAMUncorrectable:2, need to reset GPU or server.
30天内重复报修次数/fault_30day_rt：0
"""

GPU_TICKET_NUMBER = "SHGD0002034312"

DISPATCH_ROW_GPU_SINGLE = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
12/7/2026
SHGD0002034312
SHSJ0004173985
2KB900226
MYJHBGDS_B2_DH2A-A-04-11
GPU A100 PCIE - SPEX2026071100090
0000:37:00.0 SN: 1323622028016
run FD and collect logs update in sheet first
A
NF5468M6
Hafidz"""

# Real-world bug case: TWO separate 工单标签/tags fault blocks, both
# physically RAM (two DIMMs, two slots), same ticket/server SN — but the
# dispatch table collapses both into a single "Memory x2" row (one PN for
# both units) alongside separate Motherboard and NIC rows for parts that
# have no fault-description block of their own. Regression for a bug where
# the second RAM block, finding no same-category row left (the "x2" row
# had been treated as exhausted after the first match), fell back to the
# Motherboard row — mixing RAM's own Model/SN/MPN with Motherboard's PN
# under an incorrectly-titled "Old Motherboard" block.
RAM_X2_BLOCK_1 = """工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
Priority：normal
server_model：S520-B3 server_product：QC6468D7-SG
服务器SN/Server SN：21D720120
机柜位置/Location：MYJHBGDS_F2_DHGA-A-21
起始U位/ unit_no: 17
服务器厂商/manufacturer:Inspur
部件位置/part_position:P1_C3_D0
部件厂商/part_manufacturer:Micron
部件SN/part_sn:802C0F24444BC656AC
部件容量/part_size:64GB
部件类型/part_type:RAM
部件PN/part_pn:MTC40F2046S1RC56BD1
fault_log_dir:None
故障明细/Fault_Detail:Memory CE
故障类型/fault_type:Memory
故障描述/Fault Description:Memory CE (Count) > Max (Kernel)
30天内重复报修次数/fault_30day_rt：0
"""

RAM_X2_BLOCK_2 = """工单标签/tags：
60天内重复报修次数/fault_60day_rt：0
主机业务属性/idc_kind：核心机房
Priority：normal
server_model：S520-B3 server_product：QC6468D7-SG
服务器SN/Server SN：21D720120
机柜位置/Location：MYJHBGDS_F2_DHGA-A-21
起始U位/ unit_no: 17
服务器厂商/manufacturer:Inspur
部件位置/part_position:P1_C5_D0
部件厂商/part_manufacturer:Micron
部件SN/part_sn:802C0F24444BC654AE
部件容量/part_size:64GB
部件类型/part_type:RAM
部件PN/part_pn:MTC40F2046S1RC56BD1
fault_log_dir:None
故障明细/Fault_Detail:Memory CE
故障类型/fault_type:Memory
故障描述/Fault Description:Memory CE (Count) > Max (Kernel)
30天内重复报修次数/fault_30day_rt：0
"""

RAM_X2_TICKET = RAM_X2_BLOCK_1 + RAM_X2_BLOCK_2
RAM_X2_TICKET_NUMBER = "SHGD0002034569"

DISPATCH_TABLE_RAM_X2_PLUS_MB_NIC = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
13/7/2026
SHGD0002034569
SHSJ0004174583
21D720120
MYJHBGDS_F2_DHGA-A-21-17
Memory x2
V0040J30000000ZY
V0040J30000000ZY
Q
QC6468D7-SG
Aziz | Isq Deliver onsite
13/7/2026
SHGD0002034569
SHSJ0004174583
21D720120
MYJHBGDS_F2_DHGA-A-21-17
Motherboard - high risk have bent pins
YZMB-02666-106
YZMB-02666-106 borrow
Q
QC6468D7-SG
Aziz | Isq Deliver onsite
13/7/2026
SHGD0002034569
SHSJ0004174583
21D720120
MYJHBGDS_F2_DHGA-A-21-17
NIC
V0220A90000004ZY
V0220A90000004ZY
Q
QC6468D7-SG
Aziz | Isq Deliver onsite"""
