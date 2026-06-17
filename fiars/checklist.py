"""
checklist.py — Auto-generate inspection checklist from parsed ticket.

Based on the HDD_Checklist.et template. Auto-fills header info and
pre-checks relevant boxes based on fault category and repair type.
Output is HTML that prints cleanly to PDF.
"""
from __future__ import annotations
from datetime import date
from typing import Any

CHECKLIST_ITEMS = [
    # (id, section, text, auto_check_categories)
    # auto_check_categories: list of categories that auto-check this item, or ["ALL"]
    ("pre_1", "Pre-Work", "Study and understand the fault description and suggested onsite operation in portal before proceeding with the maintenance activity", ["ALL"]),
    ("pre_2", "Pre-Work", "Five elements of machine positioning: machine rack position, U position, SN, maintenance label, UID light", ["ALL"]),
    ("pre_3", "Pre-Work", "Turn on UID to confirm server to be repaired", ["ALL"]),
    ("pre_4", "Pre-Work", "Check that the server SN is consistent with the ticket", ["ALL"]),
    ("pre_5", "Pre-Work", "Double check the marks and SN before shutdown and restart after getting permission", ["ALL"]),
    ("pre_6", "Pre-Work", "Take extra cautions on window ticket. If the server doesn't shutdown during the window maintenance time, do not proceed — escalate immediately", ["ALL"]),
    ("pre_7", "Pre-Work", "Make sure the accurate fault slot information and SN (especially Bad Hard Disk SN) before replacing spare part. If onsite found unmatch error with ticket, escalate immediately", ["ALL"]),
    ("pre_8", "Pre-Work", "Take extra cautious on server status, rack status, railkit status", ["ALL"]),

    ("rep_1", "Replacement", "Before replacing spare parts, verify PN information and capacity with service manager. For different PN spare parts, confirm compatibility before replacement", ["ALL"]),
    ("rep_2", "Replacement", "Record the firmware version and FRU before performing any activities. Make sure these are flashed accordingly after service", ["Firmware", "BIOS", "BMC"]),
    ("rep_3", "Replacement", "Confirm if device is general or customized. Confirm BIOS, BMC, FRU, SAS card, network card refresh requirements, then refresh as required", ["Firmware", "BIOS", "BMC"]),
    ("rep_4", "Replacement", "Check the FW version and customized information. Ensure they are consistent with requirements after firmware refresh", ["Firmware", "BIOS", "BMC"]),
    ("rep_5", "Replacement", "For non-multibrand spare parts, the good and bad parts must be labelled with sticker", ["ALL"]),
    ("rep_6", "Replacement", "Confirm the spare part is physically good and undamaged", ["ALL"]),

    ("post_1", "Post-Work", "All parts are dismantled and reverted accordingly", ["ALL"]),
    ("post_2", "Post-Work", "Confirm all parts of the equipment are identified normally and the server indicator light is normal", ["ALL"]),
    ("post_3", "Post-Work", "Confirm that external cables (network cable, optical fiber) are installed correctly and the network cable indicator is normal", ["Network", "ALL"]),
    ("post_4", "Post-Work", "Confirm that the server is mounted properly and securely to the rail kit. If no railkit, escalate to the team", ["ALL"]),
    ("post_5", "Post-Work", "Confirm customer feedback that the server is working normal and boot to OS normally", ["ALL"]),
    ("post_6", "Post-Work", "Confirm the specification configuration provided by customer is completed", ["ALL"]),
    ("post_7", "Post-Work", "Confirm to return all non-returnable parts/access card to customer accordingly", ["ALL"]),
    ("post_8", "Post-Work", "If server was powered off during repair, collect necessary logs and keep for at least 3 months", ["ALL"]),
]

NOTES = [
    "The operation process should not violate the regulations of the hand-written \"Red line operations\".",
    "The operation process should not violate the regulations of the datacenter and customer requirements.",
    "Select \"N/A\" if the relevant operation is not performed. Fill in the reason in Remarks if \"No\" is selected.",
    "After the ticket is completed, the engineer needs to submit the PDF of the inspection checklist signed by himself or photos for centralized filing.",
]


def _should_check(item_cats: list[str], fault_category: str) -> bool:
    if "ALL" in item_cats:
        return True
    return fault_category in item_cats


def generate_checklist(job: dict[str, Any], engineer: str = "") -> str:
    """Generate HTML inspection checklist from a parsed ticket job."""
    ticket = job.get("ticket_number", "")
    sn = job.get("server_sn", "")
    location = job.get("location_full", "") or job.get("location", "")
    model = job.get("server_model", "")
    category = job.get("category", "")
    fault = job.get("fault_description", "")
    part_type = (job.get("part", {}) or {}).get("type", "")
    today = f"{date.today().day} {date.today().strftime('%B %Y')}"

    is_hotswap = part_type.upper() in ("HDD", "SSD", "NVME", "FAN", "PSU")
    power_status = "Hot-swap (no shutdown required)" if is_hotswap else "Power off required"

    rows = []
    current_section = ""
    for i, (item_id, section, text, cats) in enumerate(CHECKLIST_ITEMS):
        if section != current_section:
            current_section = section
            rows.append(f'<tr class="sec"><td colspan="5"><b>{section}</b></td></tr>')
        checked = _should_check(cats, category)
        rows.append(f'''<tr>
            <td class="n">{i+1}</td>
            <td class="desc">{text}</td>
            <td class="chk">{"☑" if checked else "☐"}</td>
            <td class="chk">☐</td>
            <td class="rem"></td>
        </tr>''')

    note_html = "".join(f"<li>{n}</li>" for n in NOTES)

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Inspection Checklist — {ticket}</title>
<style>
@media print {{ @page {{ margin: 12mm; size: A4; }} }}
body {{ font: 11px/1.4 Arial, sans-serif; color: #111; margin: 16px; }}
h1 {{ font-size: 15px; text-align: center; margin: 0 0 4px; }}
.sub {{ text-align: center; color: #555; font-size: 11px; margin-bottom: 12px; }}
.info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 20px; margin-bottom: 12px;
         background: #f5f5f5; padding: 8px 10px; border-radius: 4px; font-size: 11px; }}
.info b {{ color: #333; }}
table {{ width: 100%; border-collapse: collapse; font-size: 10.5px; margin-bottom: 12px; }}
th, td {{ border: 1px solid #999; padding: 4px 6px; }}
th {{ background: #e0e0e0; font-size: 10px; text-transform: uppercase; }}
.n {{ width: 28px; text-align: center; }}
.chk {{ width: 36px; text-align: center; font-size: 14px; }}
.rem {{ width: 100px; }}
.desc {{ font-size: 10.5px; }}
.sec td {{ background: #eef; font-size: 11px; border: none; padding: 6px 4px 2px; }}
.notes {{ font-size: 10px; color: #555; margin-top: 8px; }}
.notes li {{ margin-bottom: 2px; }}
.sig {{ margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 11px; }}
.sig div {{ border-top: 1px solid #999; padding-top: 4px; }}
.pwr {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;
         background: {"#d4edda" if is_hotswap else "#f8d7da"}; color: {"#155724" if is_hotswap else "#721c24"}; }}
</style></head><body>
<h1>Checklist for Engineer MA Service</h1>
<div class="sub">Inspection Checklist — Hardware Maintenance</div>

<div class="info">
  <div><b>Ticket No:</b> {ticket}</div>
  <div><b>Date:</b> {today}</div>
  <div><b>Server SN:</b> {sn}</div>
  <div><b>Server Model:</b> {model}</div>
  <div><b>Location:</b> {location}</div>
  <div><b>Fault Category:</b> {category}</div>
  <div><b>Part Type:</b> {part_type}</div>
  <div><b>Power Status:</b> <span class="pwr">{power_status}</span></div>
  <div><b>Fault:</b> {fault[:80]}</div>
  <div><b>Engineer:</b> {engineer}</div>
</div>

<table>
  <thead><tr><th class="n">No.</th><th>Check Item</th><th class="chk">Yes</th><th class="chk">No/NA</th><th class="rem">Remarks</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>

<ol class="notes">{"".join(f"<li>{n}</li>" for n in NOTES)}</ol>

<div class="sig">
  <div><b>Engineer Signature:</b> ____________________<br>Date: {today}</div>
  <div><b>Customer Acknowledgement:</b> ____________________<br>Date: ___________</div>
</div>
</body></html>'''
