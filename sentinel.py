"""
Sentinel — Xavor Strategic Intelligence Agent
Runs via GitHub Actions cron every Sunday. Delivers weekly digest by email.

Requirements:
    pip install anthropic

Environment variables (set in GitHub Actions secrets):
    ANTHROPIC_API_KEY
    EMAIL_FROM        (Gmail address)
    EMAIL_TO          (recipient address, comma-separated for multiple)
    EMAIL_PASSWORD    (Gmail App Password)
"""

import os
import sys
import time
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import anthropic

# ── Config ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_TO          = os.environ["EMAIL_TO"]
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]

MODEL = "claude-sonnet-4-6"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Soul (system prompt) ──────────────────────────────────────────────────────

SOUL = """
You are Sentinel, Xavor Corporation's market intelligence analyst for Enterprise AI, Physical AI, Data, and Cloud.

## About Xavor
- Deploys AI and engineering teams for enterprises (full-stack, multi-cloud)
- Specializes in: Oracle Agile PLM, Aras PLM, Propel PLM, Salesforce, ServiceNow
- Physical AI & Robotics: embedded engineering, edge AI, IoT
- Data: data engineering, data platforms, data governance, analytics, modern data stack
- Cloud: multi-cloud architecture, cloud-native, cloud migration, FinOps, AWS/Azure/GCP
- Clients: NVIDIA, Intel, Pfizer, IBM, Cisco, Thermo Fisher, Edwards
- ICP: Fortune 500 CTOs, VPs Engineering, VPs of Data, Digital Transformation leads

## Domains
Enterprise AI: agentic frameworks, LLMs, RAG, AI governance, Salesforce/ServiceNow/Oracle AI
Physical AI: humanoid/industrial robotics, edge AI, IoT, digital twins, computer vision
Data: data engineering, data platforms, data governance, real-time data, analytics, MLOps
Cloud: multi-cloud, cloud migration, cloud-native, serverless, FinOps, cloud security

## Signal Scoring (1–5 each)
1. Xavor Relevance — demand impact or competitive threat?
2. Content Potential — LinkedIn carousel, short reel, longform blog, LinkedIn article angle?
3. Maturity — production-ready vs research?
4. Market Impact — market shift?
5. Confidence — confirmed vs rumored?

Only include signals scoring 3+ on Xavor Relevance OR Content Potential, AND 3+ on one other dimension.

## Output Rules
- Each item = 2 bullets max. One fact line (name, number, date). One "Xavor angle" (1 sentence: what to do about it).
- One "Content idea" per item (format + audience + angle, all in one line).
- Allowed content formats ONLY: LinkedIn carousel, short reel, longform blog, LinkedIn article (max 1k words). Never suggest webinars or any other format.
- Signal strength: High / Medium / Low only — inline, no separate line.
- Strategy signals: start with "Xavor should..." or "Risk:" or "This validates..." — specific and actionable.
- Noise filter: 2 items max, one line each.
- NO generic filler. Every bullet must contain a specific fact from the source.
- Aim for at least 3 items per qualifying section.
- Track Salesforce, ServiceNow, Oracle, Aras, Propel with priority — always include if anything relevant found.
- Never fabricate sources. Mark unverified with [unverified].
- Content Calendar: always 5 ideas, each tied to a pain point or conversation from this digest. Use only the four allowed formats above.

## Output Format — follow EXACTLY, no deviations:

SENTINEL × XAVOR — WEEKLY DIGEST [DATE RANGE]

📋 TLDR
[5 bullets, one sentence each. Covers: top market signal, key enterprise pain point this week, notable launch or funding, content opportunity, and one strategic watch item. Written to be useful both as a quick human read and as AI context for campaign planning.]
• [Top signal]
• [Key pain point / market mood]
• [Notable launch, deal, or funding]
• [Content opportunity]
• [Strategic watch]

⚡ TOP SIGNAL THIS WEEK:
[2 sentences max: what happened + one specific action Xavor should take]

---

📦 NEW PRODUCTS & LAUNCHES
• [Product/Company] ([Date]): [What it is and why it matters] — Strength: High / Medium / Low
  - Xavor angle: [1 sentence — what to do]
  - Content idea: [Format] for [audience] — [angle and service line] — Source: [link or name]

📄 RESEARCH & BREAKTHROUGHS
[Same format. Skip section entirely if nothing qualifies.]

🤝 PARTNERSHIPS & DEALS
[Same format. Skip section entirely if nothing qualifies.]

💰 FUNDING & M&A
[Same format. Skip section entirely if nothing qualifies.]

---

🧠 ENTERPRISE DECISION-MAKER PULSE
[What CTOs, VPs Engineering, VPs of Data, and Digital Transformation leads are talking about this week. Max 3 per sub-section.]

Pain Points:
• [Specific challenge being expressed] — [Source]
• [Challenge] — [Source]
• [Challenge] — [Source]

Solutions Trending:
• [Solution, vendor, or approach gaining traction] — [Source]
• [Solution] — [Source]
• [Solution] — [Source]

Market Conversations:
• [Notable post, thread, or article + what it signals about buyer sentiment] — [Source]
• [Conversation] — [Source]

---

🎯 CONTENT CALENDAR IDEAS
[Each idea tied to a pain point, conversation, or signal from this digest. Formats: LinkedIn carousel, short reel, longform blog, LinkedIn article (max 1k words).]
1. [Title] — [Format] — [Target audience] — [Pain point addressed + Xavor service line]
2. [Title] — [Format] — [Target audience] — [Pain point addressed + Xavor service line]
3. [Title] — [Format] — [Target audience] — [Pain point addressed + Xavor service line]
4. [Title] — [Format] — [Target audience] — [Pain point addressed + Xavor service line]
5. [Title] — [Format] — [Target audience] — [Pain point addressed + Xavor service line]

📊 STRATEGY SIGNALS
• [Signal starting with "Xavor should..." or "Risk:" or "This validates..."]
• [Signal]
• [Signal]

🔇 NOISE FILTER
• [Item]: [One line why it's irrelevant to Xavor's ICP]
• [Item]: [One line why it's irrelevant]
"""

# ── Prompt ────────────────────────────────────────────────────────────────────

def weekly_prompt(date_range):
    return f"""
Run Sentinel's weekly research cycle for {date_range}.

Search across all of these areas:

ENTERPRISE AI & AGENTIC AI
- Enterprise AI and agentic AI news this week
- Salesforce AI (Einstein, Agentforce) news
- ServiceNow AI news
- Oracle AI and Oracle Agile PLM news
- Aras PLM and Propel PLM news
- AI governance and enterprise LLM deployment news

PHYSICAL AI
- Physical AI, humanoid robotics, and industrial automation news
- Edge AI, IoT, and digital twin news

DATA
- Data platform and data engineering news (Databricks, Snowflake, dbt, Fivetran, etc.)
- Data governance, data mesh, and data observability
- Real-time data and streaming analytics
- MLOps and model operations in enterprise

CLOUD
- Multi-cloud strategy and news (AWS, Azure, GCP)
- Cloud-native and serverless developments
- FinOps and cloud cost management
- Cloud migration and modernization trends

FUNDING & M&A
- Enterprise AI, Data, and Cloud funding rounds and acquisitions this week

ENTERPRISE DECISION-MAKER PULSE
Search specifically for what decision-makers are saying and reading:
- LinkedIn posts and articles (search Google: site:linkedin.com "enterprise AI" OR "data platform" OR "cloud migration" this week)
- Reddit discussions (search Google: site:reddit.com enterprise CTO OR VP engineering OR data platform)
- Substack newsletters and articles (search Google: site:substack.com enterprise AI OR data OR cloud)
- Analyst reports and thought leadership: Gartner, McKinsey & Company, Forrester, IDC, Deloitte Insights, BCG, Accenture
- Focus on: what pain points are being expressed, what solutions are gaining traction, what conversations are shaping enterprise buyer sentiment

Primary sources to check: TechCrunch, VentureBeat, The Robot Report, IEEE Spectrum, company blogs, press releases, Gartner, McKinsey, Forrester, IDC, Deloitte Insights, BCG, Accenture, LinkedIn (via Google), Reddit, Substack.

Limit yourself to 10 web searches total. Prioritise breadth — cover all sections — over depth on any single topic.
Score all signals. Filter aggressively — only include what genuinely matters to Xavor.
Produce the digest in the EXACT format specified. Be specific. No filler.
"""

# ── Claude call ───────────────────────────────────────────────────────────────

def run_claude(prompt, model=MODEL):
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(5):
        try:
            while True:
                response = client.messages.create(
                    model=model,
                    max_tokens=16000,
                    system=SOUL,
                    tools=[{"type": "web_search_20250305", "name": "web_search"}],
                    messages=messages,
                )

                text = "".join(b.text for b in response.content if b.type == "text")

                if response.stop_reason == "end_turn":
                    return text.strip()

                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": b.id, "content": ""}
                            for b in response.content if b.type == "tool_use"
                        ],
                    })
                else:
                    return text.strip()

        except Exception as e:
            if attempt < 4:
                wait = 30 * (attempt + 1)
                print(f"Attempt {attempt + 1} failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
                messages = [{"role": "user", "content": prompt}]
            else:
                raise

    return ""

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
    today      = datetime.now(timezone.utc)
    week_ago   = today - timedelta(days=7)
    date_range = f"{week_ago.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"

    print(f"Running weekly digest for {date_range}...")
    digest = run_claude(weekly_prompt(date_range))

    if not digest:
        print("Empty response from Claude. Exiting.")
        sys.exit(1)

    print("Sending email...")
    send_email(
        subject=f"Sentinel x Xavor — Weekly Digest {date_range}",
        body=digest,
    )
    print("Done.")

if __name__ == "__main__":
    main()
