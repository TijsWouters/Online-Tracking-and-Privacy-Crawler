This project implements a web crawler using **Playwright** to measure online tracking behavior for 40 news websites under three different crawl modes(see below).
It collects HAR files, screenshots, videos, and performs a comprehensive privacy&tracking analysis.

## Getting Started

### 1.Install dependencies
Make sure you have installed all necessary packages in `requirements.txt` and Playwright browsers.
```
pip install -r requirements.txt
```

### 2.Run the crawler
In the crawler directory, run: 
```
python crawl.py -m <accept | block | reject> -l <list_file> 
```
This executes one of the three crawl modes and produces the corresponding results.

### 3. Output
The crawler generates:
- har_logs_\<mode\> — HAR network logs
- screenshots_\<mode\> — screenshots before/after cookie action
- videos_\<mode\> — visit recordings
- blocked_requests_results.json - blocked requests (block mode only)

### 4. Analyze the data
Use the notebook located in `analysis/analysis.ipynb`
to run all analyses and generate tables and figures.

## Crawl Modes
**Crawl-Accept**
- Accept all cookies and data processing

**Crawl-Reject**
- Reject non-essential cookies and data processing

**Crawl-Block**
- Accept all cookies and data processing
- Block requests to domains categorized as:
    - Advertising
    - Analytics
    - Social 
    - FingerprintingInvasive 
    - FingerprintingGeneral 
    
    as defined in Disconnect’s blocklist  




