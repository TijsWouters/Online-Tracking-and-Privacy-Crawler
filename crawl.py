import csv
from random import random
import re
from time import sleep, time
from playwright.sync_api import sync_playwright
from sys import argv
import json
from publicsuffix2 import get_sld
from urllib.parse import urlparse

BLOCKED_CATEGORIES = ["Advertising", "Analytics", "Social", "FingerprintingInvasive", "FingerprintingGeneral"]
with open('services.json', 'r') as f:
    SERVICES = json.load(f)

ACCEPT_WORDS = ["akkoord", "accept", "i accept all", "i accept", "akzeptieren", "agree", "accepter", "accetta", "accetta e chiudi", "accetta e continua", "i agree", "accepter et continuer", "accepter les cookies", "accept all", "yes, i agree", "alle akzeptieren", "allow all", "yes, i accept", "accetta tutti i cookie", "accept, i am 24+"]
REJECT_WORDS = ["alles weigeren", "alles afwijzen", "reject all", "alle ablehnen", "reject", "refuse all", "deny", "rifiuta", "rifiuta tutto", "deny all", "reject all purposes", "essential cookies only", "i reject all (except strictly necessary)", "no, i do not accept", "continua senza accettare", "i do not agree"]
SETTING_WORDS = ["instellen", "settings", "stel voorkeuren in", "einstellungen", "preferenze", "set preferences", "cookie settings", "cookie preferences", "einstellungen oder ablehnen", "personalizza", "view options", "manage preferences", "show purposes", "manage choices", "see purposes and manage privacy choices", "customize settings", "manage", "manage settings", "manage cookies"]

def get_sld_from_url(url):
    return get_sld(urlparse(url).netloc)

def read_sites_csv(file_path):
    sites = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sites.append(row)
    return sites

def find_candidates(scope, keywords):
    accept_regex = re.compile(rf"^(?:{'|'.join(map(re.escape, keywords))})$", re.I)
    candidates = []
    try:
        buttons = scope.query_selector_all("button")
        buttons = [btn for btn in buttons if accept_regex.search(btn.inner_text().strip())]
        links = scope.query_selector_all("a")
        links = [link for link in links if accept_regex.search(link.inner_text().strip())]
        candidates.extend(buttons)
        candidates.extend(links)
    except Exception:
        pass

    return candidates

def find_and_click(scope, keywords):
    elements = find_candidates(scope, keywords)
    for element in elements:
        if not element.is_visible():
            continue
        try:
            element.scroll_into_view_if_needed()
            element.click(timeout=3000)
            return True
        except Exception:
            print(f"Failed to click button on {scope.url} with text: {element.inner_text()}")
    return False

def keywords_click(page, keywords):
    try:
        buttons = page.query_selector_all("button")
        links = page.query_selector_all("a")
        if find_and_click(buttons + links, page.url, keywords):
            return
    except Exception:
        # If querying the main page fails for some reason, continue to frames
        pass

    # Then try each iframe/frame (skip main frame when present to avoid duplicate work)
    try:
        main_frame = page.main_frame()
    except Exception:
        main_frame = None

    for frame in page.frames:
        try:
            if main_frame is not None and frame == main_frame:
                continue
            # Query buttons and links inside the frame
            frame_buttons = frame.query_selector_all("button")
            frame_links = frame.query_selector_all("a")
            frame_url = getattr(frame, 'url', page.url)
            if find_and_click(frame_buttons + frame_links, frame_url, keywords):
                return
        except Exception:
            # Accessing cross-origin frame contents or detached frames may raise; skip
            continue

    print(f"No cookie accept button found on {page.url}")

def accept_cookies(page):
    keywords_click(page, ACCEPT_WORDS)

def open_cookie_settings(page):
    keywords_click(page, SETTING_WORDS)

def reject_cookies(page):
    keywords_click(page, REJECT_WORDS)


def scroll_down_in_steps(page):
    at_bottom = False
    page_height = page.evaluate("""() => {
        const el = document.scrollingElement || document.documentElement;
        return el.scrollHeight;
    }""")
    while not at_bottom:
        page.evaluate(
            "window.scrollBy(0,%d)" % (10 + int(page_height/10 * random()))
        )
        at_bottom = page.evaluate("""() => {
            const el = document.scrollingElement || document.documentElement;
            return el.scrollTop + el.clientHeight >= el.scrollHeight - 50;
        }""")
        sleep(0.5 + random())


def format_seconds(seconds: float) -> str:
    """Format seconds into H:MM:SS or M:SS for printing."""
    try:
        seconds = int(round(seconds))
    except Exception:
        return "unknown"
    if seconds < 0:
        seconds = 0
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

def crawl_site(page, site, mode):
    url = site['domain']
    page.goto(f"https://{url}")
    sleep(10)
    page.screenshot(path=f"screenshots_{mode}/{site['domain']}_before.png")#, full_page=True)
    if mode == "accept" or mode == "block":
        accept_cookies(page)
    elif mode == "reject":
        open_cookie_settings(page)
        sleep(2)
        reject_cookies(page)
    sleep(5)
    page.screenshot(path=f"screenshots_{mode}/{site['domain']}_after.png")#, full_page=True)
    scroll_down_in_steps(page)
    sleep(5)

def check_route_block(route, blocked_requests):
    for category in BLOCKED_CATEGORIES:
        if category in SERVICES["categories"]:
            for entity in SERVICES["categories"][category]:
                for entity_name in entity:
                    for url in entity[entity_name]:
                        for domain in entity[entity_name][url]:
                            if domain == get_sld_from_url(route.request.url):
                                blocked_requests.append({
                                    "domain": domain,
                                    "blocked_url": route.request.url,
                                    "category": category,
                                    "entity": entity_name
                                })
                                return route.abort()
    route.continue_()


if __name__ == "__main__":
    if len(argv) != 5:
        print("Usage: python crawl.py -m <mode> -l <list_file>")
        exit(1)

    mode, list_file = None, None

    if (argv[1] == '-m'):
        mode = argv[2]
    if (argv[3] == '-l'):
        list_file = argv[4]

    if not mode in ["accept", "block", "reject"] or not list_file:
        print("Usage: python crawl.py -m <accept|block|reject> -l <list_file>")
        exit(1)
    
    sites = read_sites_csv(list_file)
    
    blocked_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        total = len(sites)
        run_start = time()
        for idx, site in enumerate(sites, start=1):
            site_start = time()
            print()
            context = browser.new_context(record_har_path=f"har_logs_{mode}/{site['domain']}.har", record_video_dir=f"videos_{mode}/{site['domain']}")
            page = context.new_page()
            if mode == "block":
                page.route('**/*', lambda route: check_route_block(route, blocked_requests))
            try:
                crawl_site(page, site, mode)
            except Exception as e:
                print(f"Error crawling {site['domain']}: {e}")
            finally:
                elapsed = time() - site_start
                avg = (time() - run_start) / idx if idx > 0 else elapsed
                remaining = total - idx
                eta = avg * remaining
                print(f"({idx}/{total}) {site['domain']} crawled in {elapsed:.1f}s — ETA {format_seconds(eta)}")
            page.close()
            context.close()

        browser.close()
    
    if mode == "block":
        with open('blocked_requests_results.json', 'w') as f:
            json.dump(blocked_requests, f, indent=4)
