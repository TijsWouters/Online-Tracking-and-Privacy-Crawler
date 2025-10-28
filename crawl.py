import csv
from random import random
from time import sleep
from playwright.sync_api import sync_playwright
from sys import argv

ACCEPT_WORDS = ["akkoord"]


def read_sites_csv(file_path):
    sites = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sites.append(row)
    return sites

def accept_cookies(page):
    buttons = page.query_selector_all("button")
    for button in buttons:
        text = button.inner_text().lower()
        if any(word in text for word in ACCEPT_WORDS):
            button.click()
            return
    print(f"No cookie accept button found on {page.url}")

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
        print(at_bottom)
        sleep(0.5 + random())

def crawl_site(page, site, mode):
    url = site['domain']
    page.goto(f"https://{url}")
    sleep(10)
    page.screenshot(path=f"screenshots/{site['domain']}_before.png")
    if mode == "accept" or mode == "block":
        accept_cookies(page)
    elif mode == "reject":
        pass  # Implement reject logic
    sleep(5)
    page.screenshot(path=f"screenshots/{site['domain']}_after.png")
    scroll_down_in_steps(page)
    sleep(5)


if __name__ == "__main__":
    if len(argv) != 5:
        print("Usage: python crawl.py -m <mode> -l <list_file>")
        exit(1)

    mode, list_file = None, None

    if (argv[1] == '-m'):
        mode = argv[2]
    if (argv[3] == '-l'):
        list_file = argv[4]
        
    if not mode or not list_file:
        print("Usage: python crawl.py -m <mode> -l <list_file>")
        exit(1)
    
    sites = read_sites_csv(list_file)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        for site in sites:
            context = browser.new_context(record_har_path=f"har_logs/{site['domain']}.har", record_video_dir=f"videos/{site['domain']}")
            page = context.new_page()
            crawl_site(page, site, mode)
            page.close()
            context.close()

        browser.close()
        
    
        
        
   