import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime
from core.utils import colored


def parse_nmap_xml(xml_input):
    if isinstance(xml_input, str) and (xml_input.startswith("<?xml") or xml_input.startswith("<nmaprun")):
        try:
            root = ET.fromstring(xml_input)
        except ET.ParseError as e:
            print(colored(f"  [!] XML parse error: {e}", "31"))
            return None
    elif os.path.exists(xml_input):
        try:
            tree = ET.parse(xml_input)
            root = tree.getroot()
        except ET.ParseError as e:
            print(colored(f"  [!] XML parse error: {e}", "31"))
            return None
    else:
        print(colored(f"  [!] File not found: {xml_input}", "31"))
        return None

    scan_info = {
        "scanner": root.get("scanner", "nmap"),
        "version": root.get("version", ""),
        "start_time": root.get("start", ""),
        "args": root.get("args", ""),
        "targets": [],
        "total_hosts": 0,
        "total_open_ports": 0,
    }

    for host in root.findall("host"):
        host_info = {"ip": "", "hostname": "", "status": "", "os": "", "ports": [], "scripts": []}

        status_el = host.find("status")
        if status_el is not None:
            host_info["status"] = status_el.get("state", "unknown")

        for addr in host.findall("address"):
            if addr.get("addrtype") == "ipv4":
                host_info["ip"] = addr.get("addr", "")
            elif addr.get("addrtype") == "ipv6":
                host_info["ip"] = host_info["ip"] or addr.get("addr", "")

        hostnames = host.find("hostnames")
        if hostnames is not None:
            hname = hostnames.find("hostname")
            if hname is not None:
                host_info["hostname"] = hname.get("name", "")

        os_elements = host.findall("os/osmatch")
        if os_elements:
            host_info["os"] = os_elements[0].get("name", "")

        ports_el = host.find("ports")
        if ports_el is not None:
            for port in ports_el.findall("port"):
                port_info = {
                    "port": int(port.get("portid", 0)),
                    "protocol": port.get("protocol", "tcp"),
                    "state": port.find("state").get("state", "unknown") if port.find("state") is not None else "unknown",
                    "service": "",
                    "version": "",
                    "product": "",
                    "scripts": [],
                }
                svc = port.find("service")
                if svc is not None:
                    port_info["service"] = svc.get("name", "")
                    port_info["product"] = svc.get("product", "")
                    port_info["version"] = svc.get("version", "")

                for script in port.findall("script"):
                    port_info["scripts"].append({
                        "id": script.get("id", ""),
                        "output": script.get("output", ""),
                    })

                host_info["ports"].append(port_info)
                if port_info["state"] == "open":
                    scan_info["total_open_ports"] += 1

        host_scripts = host.find("hostscript")
        if host_scripts is not None:
            for script in host_scripts.findall("script"):
                host_info["scripts"].append({
                    "id": script.get("id", ""),
                    "output": script.get("output", ""),
                })

        scan_info["targets"].append(host_info)
        scan_info["total_hosts"] += 1

    return scan_info


def format_nmap_results(data):
    if not data or "targets" not in data:
        return "No data to display."

    lines = []
    lines.append("=" * 55)
    lines.append(f"Nmap Scan Report  |  Scanner: {data.get('scanner', 'nmap')}")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Hosts: {data['total_hosts']}  |  Open Ports: {data['total_open_ports']}")
    lines.append("=" * 55)

    for host in data["targets"]:
        lines.append(f"\nHost: {host['ip']} ({host.get('hostname', 'N/A')})")
        lines.append(f"Status: {host['status']}")
        if host.get("os"):
            lines.append(f"OS: {host['os']}")
        if host.get("ports"):
            lines.append(f"{'PORT':<8} {'STATE':<8} {'SERVICE':<12} {'VERSION'}")
            lines.append("-" * 55)
            for p in host["ports"]:
                if p["state"] == "open":
                    ver = f"{p['product']} {p['version']}".strip()
                    lines.append(f"{p['port']}/{p['protocol']:<4} {p['state']:<8} {p['service']:<12} {ver}")
        if host.get("scripts"):
            for s in host["scripts"]:
                lines.append(f"  Script: {s['id']} -> {s['output'][:120]}")

    return "\n".join(lines)


def run_nmap_parser(filepath):
    data = parse_nmap_xml(filepath)
    if data:
        output = format_nmap_results(data)
        print(colored(output, "37"))
        save_path = os.path.join("reports", f"nmap_parsed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs("reports", exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
        print(colored(f"\n[+] Parsed data saved: {save_path}", "32"))
        return data
    return None
