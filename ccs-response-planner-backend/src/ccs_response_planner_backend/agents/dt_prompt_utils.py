"""
Helpers for generating dynamic digital-twin prompt sections
from a DT configuration dict.
"""
from typing import Any


def format_container_list(config: dict[str, Any]) -> str:
    """
    Build a comma-separated list of non-attacker container IDs.

    :param config: the digital twin configuration dict
    :return: e.g. ``"i1_gateway, i1_firewall, i1_log_collector, ..."``
    """
    hosts = config.get("hosts", [])
    ids = [
        h["id"] for h in hosts
        if "attacker" not in h.get("id", "")
    ]
    return ", ".join(ids)


def _zone_label(
    ip_addresses: dict[str, str],
    networks: list[dict[str, Any]],
) -> str:
    """
    Derive a human-readable zone label from a host's IPs.

    :param ip_addresses: mapping of network-id to IP
    :param networks: the config networks list
    :return: a zone label string
    """
    net_map = {
        n["id"]: n.get("name", n["id"])
        for n in networks
    }
    zones = list(ip_addresses.keys())
    if len(zones) > 2:
        return "all zones"
    return ", ".join(net_map.get(z, z) for z in zones)


def format_container_table(
    config: dict[str, Any],
) -> str:
    """
    Build a Markdown table of non-attacker containers.

    Columns: Container, Zone, IP address, Role.

    :param config: the digital twin configuration dict
    :return: a Markdown table string
    """
    networks = config.get("networks", [])
    hosts = config.get("hosts", [])
    lines = [
        "| Container     | Zone       "
        "| IP address  | Role"
        "                                    |",
        "|---------------|------------"
        "|-------------|---------"
        "--------------------------------|",
    ]
    for h in hosts:
        if "attacker" in h.get("id", ""):
            continue
        cid = h["id"]
        zone = _zone_label(
            h.get("ip_addresses", {}), networks,
        )
        ips = ", ".join(h.get("ip_addresses", {}).values())
        role = h.get("description", "")
        lines.append(
            f"| {cid:<13} | {zone:<10} "
            f"| {ips:<11} | {role:<39} |"
        )
    return "\n".join(lines)


def format_network_connectivity(
    config: dict[str, Any],
) -> str:
    """
    Build a human-readable network adjacency description.

    Excludes links involving the attacker. Groups server-to-
    server links into a concise summary.

    :param config: the digital twin configuration dict
    :return: a connectivity description string
    """
    links = config.get("links", [])
    hosts_map: dict[str, dict[str, Any]] = {
        h["id"]: h for h in config.get("hosts", [])
    }

    server_links: list[tuple[str, str]] = []
    infra_links: list[tuple[str, str]] = []
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if "attacker" in src or "attacker" in tgt:
            continue
        src_name = hosts_map.get(
            src, {},
        ).get("name", src)
        tgt_name = hosts_map.get(
            tgt, {},
        ).get("name", tgt)
        if "server" in src.lower() and "server" in tgt.lower():
            server_links.append((src_name, tgt_name))
        else:
            infra_links.append((src_name, tgt_name))

    parts: list[str] = []
    if infra_links:
        infra_desc = ", ".join(
            f"{a}\u2013{b}" for a, b in infra_links
        )
        parts.append(
            f"Infrastructure chain: {infra_desc}."
        )
    if server_links:
        link_desc = ", ".join(
            f"{a}\u2013{b}" for a, b in server_links
        )
        parts.append(
            "Server-to-server adjacency links "
            "(bidirectional, routed through the network "
            f"infrastructure): {link_desc}. "
            "All other server-to-server connections "
            "are blocked."
        )
    return " ".join(parts) if parts else "N/A"
