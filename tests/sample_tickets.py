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
