from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

# ──────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────

HORIZONTAL = "#ef5b25"   # orange
OTHER      = "#10a4da"   # cyan
VERSION    = "1.0.0"
API_ENDPOINT = "https://www.postman.com/_api/ws/proxy"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Content-Type": "application/json",
}
OUTPUT_FILE = Path("scan.txt")
console = Console()

# ──────────────────────────────────────────────────────────────────────────
# NETWORK LAYER WITH RETRIES
# ──────────────────────────────────────────────────────────────────────────

_session: Optional[requests.Session] = None

def _get_session() -> requests.Session:
    """Singleton *requests.Session* with automatic retries."""
    global _session  # noqa: PLW0603
    if _session is None:
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        _session = requests.Session()
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


def safe_request(method: str, url: str, **kwargs) -> Optional[requests.Response]:
    kwargs.setdefault("timeout", 30)
    try:
        resp = _get_session().request(method, url, **kwargs)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as exc:  # noqa: BLE001
        console.log(f"[red]⚠️  {method.upper()} {url} → {exc}[/]")
        return None

# ──────────────────────────────────────────────────────────────────────────
# RENDERING HELPERS
# ──────────────────────────────────────────────────────────────────────────

def _print_logo() -> None:
    ascii_logo = Text(
        """
                     __                        _            
    ____  ____  _____/ /_____ ___  ____ _____  (_)___ ______
   / __ \ __ \ ___/ __/ __ `__ \/ __ `/ __ \/ / __ `/ ___/
  / /_/ / /_/ (__  ) /_/ / / / / /_/ / / / / / / /_/ / /__  
 / .___/\____/____/\__/ /_/ /_/  \__,_/_/ /_/_/\__,_/\___/  
/_/                                                         
        """,
        style="bold",
    )
    console.print(Panel.fit(ascii_logo, border_style=HORIZONTAL, subtitle=f"v{VERSION}", subtitle_align="right"))


def _progress(desc: str, total: int | None = None) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[bold]{desc}[/]"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )

# ──────────────────────────────────────────────────────────────────────────
# FILE UTILITIES
# ──────────────────────────────────────────────────────────────────────────

def write_report(*lines: str) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("a", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")


def _json(resp: Optional[requests.Response]) -> Dict[str, Any]:
    return resp.json() if resp else {}

# ──────────────────────────────────────────────────────────────────────────
# DOMAIN LOGIC
# ──────────────────────────────────────────────────────────────────────────

def initial_search(query: str) -> tuple[list[str], list[str]]:
    payload: Dict[str, Any] = {
        "service": "search",
        "method": "POST",
        "path": "/search-all",
        "body": {
            "queryIndices": [
                "collaboration.workspace",
                "runtime.collection",
                "runtime.request",
                "adp.api",
                "flow.flow",
                "apinetwork.team",
            ],
            "queryText": query,
            "size": 25,
            "from": 0,
            "requestOrigin": "srp",
            "mergeEntities": True,
            "nonNestedRequests": True,
        },
    }
    workspaces: list[str] = []
    teams: list[str] = []

    with _progress("Reconnaissance", total=3) as prog:
        t = prog.add_task("search", total=3)
        for _ in range(3):
            resp = safe_request("POST", API_ENDPOINT, headers=HEADERS, json=payload)
            payload["body"]["from"] += 25
            for item in _json(resp).get("data", []):
                doc = item["document"]
                tpe = doc.get("documentType")
                if tpe == "request":
                    ph = doc.get("publisherHandle")
                    if ph and doc.get("workspaces"):
                        slug = doc["workspaces"][0].get("slug")
                        if slug:
                            workspaces.append(f"https://www.postman.com/{ph}/workspace/{slug}/")
                elif tpe == "team":
                    teams.append(f"https://www.postman.com/{doc['publicHandle']}")
                elif tpe == "workspace":
                    workspaces.append(f"https://www.postman.com/{doc['publisherHandle']}/workspace/{doc['slug']}")
            prog.advance(t)

    workspaces = list({u for u in workspaces if "/workspace/" in u and "//" not in u.replace("https://", "")})
    teams = list(set(teams))
    write_report("Workspaces:", *workspaces, "", "Teams:", *teams, "")
    return workspaces, teams


def discover_elements(workspaces: list[str]) -> tuple[int, int, list[str]]:
    coll_cnt = 0
    env_cnt = 0
    coll_urls: list[str] = []

    with _progress("Découverte", total=len(workspaces)) as prog:
        t = prog.add_task("discover", total=len(workspaces))
        for ws in workspaces:
            m_pub = re.search(r"https://www.postman.com/([^/]+)/", ws)
            m_slug = re.search(r"/workspace/([^/]+)/?$", ws)
            if not (m_pub and m_slug):
                prog.advance(t)
                continue
            pub, slug = m_pub.group(1), m_slug.group(1)
            wid_resp = safe_request("POST", API_ENDPOINT, headers=HEADERS, json={
                "service": "workspaces", "method": "GET", "path": f"/workspaces?handle={pub}&slug={slug}",
            })
            wid_data = _json(wid_resp).get("data", [])
            if not wid_data:
                prog.advance(t)
                continue
            wid = wid_data[0]["id"]
            el_resp = safe_request("POST", API_ENDPOINT, headers=HEADERS, json={
                "service": "workspaces", "method": "GET", "path": f"/workspaces/{wid}?include=elements",
            })
            el = _json(el_resp).get("data", {}).get("elements", {})
            env_ids = el.get("environments", [])
            col_ids = el.get("collections", [])

            env_cnt += len(env_ids)
            for cid in col_ids:
                coll_cnt += 1
                url = f"{ws}collection/{cid}"
                coll_urls.append(url)
                write_report(f"Collection {url}")
            for eid in env_ids:
                write_report(f"Environnement {eid}")
            prog.advance(t)
    return coll_cnt, env_cnt, coll_urls


def scan_collections(urls: list[str]) -> tuple[int, list[Any], list[Any], list[Any]]:
    req_total = 0
    auths: list[Any] = []
    headers_found: list[Any] = []
    bodies_found: list[Any] = []
    placeholder = re.compile(r"^\{\{.*\}\}$")

    def dedupe(lst: List[Any]) -> List[Any]:
        seen: set[str] = set()
        out: list[Any] = []
        for el in lst:
            s = json.dumps(el, sort_keys=True)
            if s not in seen:
                seen.add(s)
                out.append(el)
        return out

    console.print("\n[bold]Analyse des collections…[/]")
    with _progress("Analyse", total=len(urls)) as prog:
        t = prog.add_task("analyse", total=len(urls))
        for curl in urls:
            cid = curl.rstrip("/").split("/")[-1]
            c_resp = safe_request("GET", f"https://www.postman.com/_api/collection/{cid}", headers=HEADERS)
            c_data = _json(c_resp).get("data")
            if not c_data:
                prog.advance(t)
                continue
            owner = c_data["owner"]
            order: List[str] = list(c_data["order"])

            def expand(fid: str):
                f_resp = safe_request("GET", f"https://www.postman.com/_api/folder/{owner}-{fid}", headers=HEADERS)
                f_data = _json(f_resp).get("data", {})
                order.extend(f_data.get("order", []))
                for sub in f_data.get("folders_order", []):
                    expand(sub)

            for fid in c_data.get("folders_order", []):
                expand(fid)

            req_total += len(order)
            for rid in order:
                r_resp = safe_request("GET", f"https://www.postman.com/_api/request/{owner}-{rid}", headers=HEADERS)
                r_data = _json(r_resp).get("data")
                if not r_data:
                    continue
                if r_data.get("auth"):
                    auths.append(r_data["auth"])
                for h in r_data.get("headerData", []):
                    if h["key"] not in {"Content-Type", "Accept", "x-api-error-detail", "x-api-appid"} and h["value"] and not placeholder.match(h["value"]):
                        headers_found.append(h)

                def hunt(x: Any):
                    if isinstance(x, dict):
                        for k, v in x.items():
                            if k.lower() in {"voucher","username","password","email","token","accesskey","creditcard","phone","address","mobilephone","cellphone","code","authorization_code","client_id","client_secret","name","apikey","customer_email","api_key","api_secret","apisecret","hash","paypal_token","identity","phonehome","phoneoffice","phonemobile","consumer_key","consumer_secret","access_token"}:
                                bodies_found.append(v)
                            else:
                                hunt(v)
                    elif isinstance(x, list):
                        for i in x:
                            hunt(i)
                mode = r_data.get("dataMode")
                if mode == "raw" and (raw := r_data.get("rawModeData")):
                    try:
                        hunt(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
                elif mode == "params":
                    for p in r_data.get("data", []):
                        if p["key"] in {"voucher","username","password","email","token","accesskey","creditcard","phone","address","mobilephone","cellphone","code","authorization_code","client_id","client_secret","name","apikey","customer_email","api_key","api_secret","apisecret","hash","paypal_token","identity","phonehome","phoneoffice","phonemobile","consumer_key","consumer_secret","access_token"}:
                            bodies_found.append(p["value"])
            prog.advance(t)

    return req_total, dedupe(auths), dedupe(headers_found), dedupe(bodies_found)

# ──────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Postman OSINT scanner (Rich + retries)")
    parser.add_argument("query", help="Target name, e.g. tesla")
    args = parser.parse_args()

    OUTPUT_FILE.write_text(f"Rapport du scan de {args.query}\n\n", encoding="utf-8")

    _print_logo()
    console.rule(style=OTHER)

    workspaces, teams = initial_search(args.query)
    console.print(f"[bold red]{len(workspaces)} Workspaces trouvés[/]  |  [bold blue]{len(teams)} Teams trouvées[/]")

    coll_cnt, env_cnt, coll_urls = discover_elements(workspaces)
    console.print(f"\n[bold green]{coll_cnt} Collections[/] – [bold green]{env_cnt} Environnements[/]")

    if not coll_urls:
        console.print("Aucune collection à analyser.", style="yellow")
        return

    req_total, auths, headers, bodies = scan_collections(coll_urls)
    console.print(
        f"\n[bold green]{req_total} requêtes analysées[/] – "
        f"[bold red]{len(auths)} auths[/], "
        f"[bold red]{len(headers)} headers[/], "
        f"[bold red]{len(bodies)} bodies[/] détectés"
    )

    write_report(
        "Auths:", json.dumps(auths, indent=2),
        "", "Headers:", json.dumps(headers, indent=2),
        "", "Bodies:", json.dumps(bodies, indent=2)
    )


if __name__ == "__main__":
    main()
