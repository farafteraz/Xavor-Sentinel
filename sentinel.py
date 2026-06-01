"""
Sentinel — Xavor Strategic Intelligence Agent
Runs via GitHub Actions cron. Delivers digest by email.

Requirements:
    pip install openai tavily-python requests beautifulsoup4

Environment variables (set in GitHub Actions secrets):
    NVIDIA_API_KEY
    TAVILY_API_KEY
    EMAIL_FROM        (Gmail address)
    EMAIL_TO          (recipient address, comma-separated for multiple)
    EMAIL_PASSWORD    (Gmail App Password)
"""

import os
import sys
import time
import argparse
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from tavily import TavilyClient

# ── Config ────────────────────────────────────────────────────────────────────

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
EMAIL_FROM     = os.environ["EMAIL_FROM"]
EMAIL_TO       = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

PRIMARY_MODEL = "meta/llama-3.3-70b-instruct"

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# ── Soul (system prompt) ──────────────────────────────────────────────────────

SOUL = """
You are Sentinel, Xavor Corporation's market intelligence analyst for Enterprise AI and Physical AI.

## About Xavor
- Deploys AI and engineering teams for enterprises (full-stack, multi-cloud)
- Specializes in: Oracle Agile PLM, Aras PLM, Propel PLM, Salesforce, ServiceNow
- Physical AI & Robotics: embedded engineering, edge AI, IoT
- Clients: NVIDIA, Intel, Pfizer, IBM, Cisco, Thermo Fisher, Edwards
- ICP: Fortune 500 CTOs, VPs Engineering, Digital Transformation leads

## Domains
Enterprise AI: agentic frameworks, LLMs, RAG, AI governance, Salesforce/ServiceNow/Oracle AI
Physical AI: humanoid/industrial robotics, edge AI, IoT, digital twins, computer vision

## Signal Scoring (1–5 each)
1. Xavor Relevance — demand impact or competitive threat?
2. Content Potential — blog, LinkedIn, webinar angle?
3. Maturity — production-ready vs research?
4. Market Impact — market shift?
5. Confidence — confirmed vs rumored?

Only include signals scoring 3+ on Xavor Relevance OR Content Potential, AND 3+ on one other dimension.

## Output Rules
- Be concise. Each item = 2-4 bullet points max. No paragraphs.
- One "Xavor angle" per item (1 sentence).
- One "Content idea" per item (1 sentence).
- Signal strength: High / Medium / Low only.
- Strategy signals: start with "Xavor should..." or "Risk:" or "This validates..."
- Noise filter: 2 items max, one line each.
- NO padding. NO intros. NO conclusions. If a week is quiet, say so briefly.
- Track Salesforce, ServiceNow, Oracle, Aras, Propel with priority.
- Never fabricate sources. Mark unverified with [unverified].

## Output Format — follow EXACTLY, no deviations:

SENTINEL × XAVOR — WEEKLY DIGEST [DATE RANGE]

⚡ TOP SIGNAL THIS WEEK:
[2-3 sentences max: what happened, why it matters to Xavor, one action]

---

📦 NEW PRODUCTS & LAUNCHES
• [Product/Company] ([Date]): [One line description]
  - Xavor angle: [1 sentence]
  - Content idea: [1 sentence]
  - Source: [link or publication name]
  - Strength: High / Medium / Low

📄 RESEARCH & BREAKTHROUGHS
[Same format. Skip section entirely if nothing qualifies.]

🤝 PARTNERSHIPS & DEALS
[Same format. Skip section entirely if nothing qualifies.]

💰 FUNDING & M&A
[Same format. Skip section entirely if nothing qualifies.]

---

🎯 CONTENT CALENDAR IDEAS
1. [Title] — [Format] — [1 sentence on angle and service line]
2. [Title] — [Format] — [1 sentence on angle and service line]
3. [Title] — [Format] — [1 sentence on angle and service line]

📊 STRATEGY SIGNALS
• [Signal starting with "Xavor should..." or "Risk:" or "This validates..."]
• [Signal]
• [Signal]

🔇 NOISE FILTER
• [Item]: [One line why it's irrelevant to Xavor's ICP]
• [Item]: [One line why it's irrelevant]
"""

# ── Web search ────────────────────────────────────────────────────────────────

WEEKLY_QUERIES = [
    "enterprise AI news this week",
    "physical AI robotics news this week",
    "Salesforce AI news this week",
    "ServiceNow AI news this week",
    "agentic AI enterprise this week",
    "Aras PLM OR Oracle AI news 2026",
    "edge AI IoT news this week",
    "humanoid robotics industrial news this week",
]

MIDWEEK_QUERIES = [
    "Salesforce OR ServiceNow OR Oracle major launch announcement",
    "enterprise AI funding round 50 million 2026",
    "physical AI robotics major partnership deal",
]


def fetch_article(url, char_limit=3000):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:char_limit]
    except Exception:
        return None


def gather_search_results(queries, max_results=5):
    all_results = []
    seen_urls = set()

    for query in queries:
        try:
            response = tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=False,
            )
            for r in response.get("results", []):
                url = r["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                full_text = fetch_article(url)
                body = full_text if full_text else r["content"][:500]

                all_results.append(
                    f"[{r.get('published_date', 'n/d')}] {r['title']}\n"
                    f"URL: {url}\n"
                    f"Content: {body}"
                )
                time.sleep(0.5)
        except Exception as e:
            print(f"Search failed for '{query}': {e}")
        time.sleep(0.3)

    return "\n\n---\n\n".join(all_results)


# ── LLM call ──────────────────────────────────────────────────────────────────

def run_llm(system, user_prompt, model=PRIMARY_MODEL):
    for attempt in range(5):
        try:
            response = nvidia_client.chat.completions.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 4:
                wait = 30 * (attempt + 1)
                print(f"Request failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# ── Prompts ───────────────────────────────────────────────────────────────────

def weekly_prompt(date_range, search_results):
    return f"""
Run Sentinel's weekly research cycle for {date_range}.

Below are live search results gathered from the web. Use ONLY these as your sources.
Do not fabricate any news items not present here. Mark anything uncertain as [unverified].

--- SEARCH RESULTS START ---
{search_results}
--- SEARCH RESULTS END ---

Score signals. Filter aggressively — only include what genuinely matters to Xavor.
Produce the digest in the EXACT format specified in your instructions. Be brief. No filler.
"""


def midweek_prompt(date_range, search_results):
    return f"""
Run Sentinel's mid-week scan for {date_range}.

Below are live search results. Use ONLY these as your sources.

--- SEARCH RESULTS START ---
{search_results}
--- SEARCH RESULTS END ---

Look only for HIGH signals (4+ on Xavor Relevance AND Market Impact):
- Major launches from Salesforce, ServiceNow, Oracle, Aras, Propel
- Funding rounds >$50M in Enterprise AI or Physical AI
- Major partnerships in Xavor's ecosystem

If something qualifies, write a short alert (max 150 words) using this format:
⚡ SENTINEL ALERT — [DATE]
[Headline]. [Xavor angle in 1 sentence]. [Recommended action in 1 sentence].

Then list any other qualifying signals in the standard bullet format.

If nothing qualifies, respond with exactly: NO_ALERT
"""


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(subject, body):
    recipients = [r.strip() for r in EMAIL_TO.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(recipients)

    html = f"""
    <html><body style="font-family: sans-serif; max-width: 700px; margin: auto; padding: 20px;">
    <pre style="white-space: pre-wrap; font-family: sans-serif; font-size: 14px; line-height: 1.6;">{body}</pre>
    </body></html>
    """

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())

    print(f"Email sent to: {', '.join(recipients)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sentinel - Xavor Research Agent")
    parser.add_argument(
        "mode",
        choices=["weekly", "midweek"],
        help="Run mode: 'weekly' for Sunday digest, 'midweek' for Wednesday scan",
    )
    args = parser.parse_args()

    today      = datetime.now(timezone.utc)
    week_ago   = today - timedelta(days=7)
    date_range = f"{week_ago.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"

    if args.mode == "weekly":
        print(f"Running weekly digest for {date_range}...")
        print("Gathering search results...")
        search_results = gather_search_results(WEEKLY_QUERIES)
        print(f"Collected {len(search_results.splitlines())} lines of search data. Running LLM...")
        digest = run_llm(SOUL, weekly_prompt(date_range, search_results))
        print("Sending email...")
        send_email(
            subject=f"Sentinel x Xavor - Weekly Digest {date_range}",
            body=digest,
        )
        print("Done.")

    elif args.mode == "midweek":
        print(f"Running mid-week scan for {date_range}...")
        print("Gathering search results...")
        search_results = gather_search_results(MIDWEEK_QUERIES)
        print("Running LLM...")
        result = run_llm(SOUL, midweek_prompt(date_range, search_results))
        if result.strip() == "NO_ALERT":
            print("No high-priority signals found. No email sent.")
            sys.exit(0)
        print("Sending alert email...")
        send_email(
            subject=f"Sentinel Alert - {date_range}",
            body=result,
        )
        print("Alert sent.")


if __name__ == "__main__":
    main()
