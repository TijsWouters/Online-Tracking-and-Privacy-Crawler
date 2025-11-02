import csv
from random import random
from time import sleep
from playwright.sync_api import sync_playwright
from sys import argv
import json
from publicsuffix2 import get_sld
from urllib.parse import urlparse

BLOCKED_CATEGORIES = ["Advertising", "Analytics", "Social", "FingerprintingInvasive", "FingerprintingGeneral"]
with open('services.json', 'r') as f:
    SERVICES = json.load(f)

ACCEPT_WORDS = ["akkoord", "accept", "akzeptieren", "agree", "accepter", "accetta", "continue", "i agree", "accepter et continuer"]
REJECT_WORDS = ["alles weigeren", "alles afwijzen", "reject all", "alle ablehnen", "reject", "refuse all", "deny", "rifiuta tutto", "deny all", "reject all purposes", "essential cookies only", "i reject all (except strictly necessary)", "no, i do not accept" ]

def get_sld_from_url(url):
    return get_sld(urlparse(url).netloc)

def read_sites_csv(file_path):
    sites = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sites.append(row)
    return sites

def accept_cookies(page):
    # Helper: try to find and click an element from a list of ElementHandle objects
    def _find_and_click(elements, context_url):
        for element in elements:
            try:
                text = element.inner_text().lower().strip()
            except Exception:
                # Some element handles may be detached or inaccessible; skip them
                continue
            # Match if any accept word appears in the element text
            if any(word in text for word in ACCEPT_WORDS):
                try:
                    element.scroll_into_view_if_needed()
                    element.click()
                except Exception:
                    print(f"Failed to click cookie accept button on {context_url} with text: {text}")
                    print(Exception)
                return True
        return False

    # Try on the main page first
    try:
        buttons = page.query_selector_all("button")
        links = page.query_selector_all("a")
        if _find_and_click(buttons + links, page.url):
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
            if _find_and_click(frame_buttons + frame_links, frame_url):
                return
        except Exception:
            # Accessing cross-origin frame contents or detached frames may raise; skip
            continue

    print(f"No cookie accept button found on {page.url}")

def reject_cookies(page):


def scroll_down_in_steps(page):
    at_bottom = False
    while not at_bottom:
        page.evaluate(
            "window.scrollBy(0,%d)" % (10 + int(1000 * random()))
        )
        at_bottom = page.evaluate("""() => {
            const el = document.scrollingElement || document.documentElement;
            return el.scrollTop + el.clientHeight >= el.scrollHeight - 50;
        }""")
        sleep(0.5 + random())

def crawl_site(page, site, mode):
    url = site['domain']
    page.goto(f"https://{url}")
    sleep(10)
    page.screenshot(path=f"screenshots/{site['domain']}_before.png")
    if mode == "accept" or mode == "block":
        accept_cookies(page)
    elif mode == "reject":
        #reject_cookies(page)
        pass  # Implement reject logic
    sleep(5)
    page.screenshot(path=f"screenshots/{site['domain']}_after.png")
    scroll_down_in_steps(page)
    sleep(5)

def check_route_block(route, site, blocked_requests):
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
        for site in sites:
            context = browser.new_context(record_har_path=f"har_logs/{site['domain']}.har", record_video_dir=f"videos/{site['domain']}")
            page = context.new_page()
            if mode == "block":
                page.route('**/*', lambda route: check_route_block(route, site, blocked_requests))
            crawl_site(page, site, mode)
            page.close()
            context.close()

        browser.close()
    
    with open('blocked_requests_results.json', 'w') as f:
        json.dump(blocked_requests, f, indent=4)
