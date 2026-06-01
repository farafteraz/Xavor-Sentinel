"""
Sentinel — Xavor Strategic Intelligence Agent
Runs via GitHub Actions cron. Delivers digest by email.

Requirements:
    pip install google-genai

Environment variables (set in GitHub Actions secrets):
    GEMINI_API_KEY
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

from google import genai
from google.genai import types

# ── Config ────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
EMAIL_FROM     = os.environ["EMAIL_FROM"]
EMAIL_TO       = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

PRIMARY_MODEL = "gemini-2.0-flash"

client = genai.Client(api_key=GEMINI_API_KEY)

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
- Each item = 3-5 bullet points. Be specific — include names, numbers, dates from the source.
- One "Xavor angle" per item (2 sentences: what it means + what to do).
- One "Content idea" per item (1 sentence, include the format and target audience).
- Signal strength: High / Medium / Low only.
- Strategy signals: start with "Xavor should..." or "Risk:" or "This validates..." — be specific and actionable.
- Noise filter: 2 items max, one line each.
- NO generic filler. Every bullet must contain a specific fact from the source material.
- Aim for at least 3 items per qualifying section.
- Track Salesforce, ServiceNow, Oracle, Aras, Propel with priority — always include if anything relevant found.
- Never fabricate sources. Mark unverified with [unverified].
- Content Calendar: always 5 ideas, each with a target audience.

## Output Format — follow EXACTLY, no deviations:

SENTINEL × XAVOR — WEEKLY DIGEST [DATE RANGE]

⚡ TOP SIGNAL THIS WEEK:
[2-3 sentences max: what happened, why it matters to Xavor, one action]

---

📦 NEW PRODUCTS & LAUNCHES
• [Product/Company] ([Date]): [One line description]
  - Xavor angle: [2 sentences]
  - Content idea: [1 sentence with format and audience]
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
1. [Title] — [Format] — [Target audience] — [1 sentence on angle and service line]
2. [Title] — [Format] — [Target audience] — [1 sentence on angle and service line]
3. [Title] — [Format] — [Target audience] — [1 sentence on angle and service line]
4. [Title] — [Format] — [Target audience] — [1 sentence on angle and service line]
5. [Title] — [Format] — [Target audience] — [1 sentence on angle and service line]

📊 STRATEGY SIGNALS
• [Signal starting with "Xavor should..." or "Risk:" or "This validates..."]
• [Signal]
• [Signal]

🔇 NOISE FILTER
• [Item]: [One line why it's irrelevant to Xavor's ICP]
• [Item]: [One line why it's irrelevant]
"""

# ── Prompts ───────────────────────────────────────────────────────────────────

def weekly_prompt(date_range):
    return f"""
Run Sentinel's weekly research cycle for {date_range}.

Search for:
- Enterprise AI and agentic AI news this week
- Physical AI, humanoid robotics, and industrial automation news this week
- Salesforce AI (Einstein, Agentforce) news this week
- ServiceNow AI news this week
- Oracle AI and Oracle Agile PLM news this week
- Aras PLM and Propel PLM news this week
- Edge AI, IoT, and digital twin news this week
- Major enterprise AI funding rounds and M&A this week
- AI governance and enterprise LLM deployment news this week

Check: TechCrunch, VentureBeat, The Robot Report, IEEE Spectrum, company blogs, press releases.

Score signals. Filter aggressively — only include what genuinely matters to Xavor.
Produce the digest in the EXACT format specified. Be specific. No filler.
"""

def midweek_prompt(date_range):
    return f"""
Run Sentinel's mid-week scan for {date_range}.

Search only for HIGH signals (4+ on Xavor Relevance AND Market Impact):
- Major launches from Salesforce, ServiceNow, Oracle, Aras, Propel
- Funding rounds >$50M in Enterprise AI or Physical AI
- Major partnerships in Xavor's ecosystem

If something qualifies, write a short alert (max 150 words) using this format:
⚡ SENTINEL ALERT — [DATE]
[Headline]. [Xavor angle in 1 sentence]. [Recommended action in 1 sentence].

Then list any other qualifying signals in the standard bullet format.

If nothing qualifies, respond with exactly: NO_ALERT
"""

# ── Gemini call ───────────────────────────────────────────────────────────────

def run_gemini(prompt, model=PRIMARY_MODEL):
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SOUL,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    max_output_tokens=8192,
                    temperature=0.3,
                ),
            )
            return response.text.strip()
        except Exception as e:
            if attempt < 4:
                wait = 30 * (attempt + 1)
                print(f"Request failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

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
        digest = run_gemini(weekly_prompt(date_range))
        print("Sending email...")
        send_email(
            subject=f"Sentinel x Xavor - Weekly Digest {date_range}",
            body=digest,
        )
        print("Done.")

    elif args.mode == "midweek":
        print(f"Running mid-week scan for {date_range}...")
        result = run_gemini(midweek_prompt(date_range))
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
