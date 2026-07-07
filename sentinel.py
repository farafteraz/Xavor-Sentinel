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
- Each item = 3–5 bullets with specific facts: names, numbers, dates, percentages, quoted language. No paraphrased generalities.
- One "Xavor angle" per item: 2 sentences — what it means for Xavor, and what to do about it.
- One "Content idea" per item: full title + format + audience + pain point addressed, all in one line.
- Allowed content formats ONLY: LinkedIn carousel, short reel, longform blog, LinkedIn article (max 1k words). Never suggest webinars or any other format.
- Signal strength: High / Medium / Low — on its own line.
- Strategy signals: start with "Xavor should..." or "Risk:" or "This validates..." — specific, with numbers or timelines where available.
- Noise filter: 2 items max, one line each.
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
• [Product/Company] ([Date]): [What it is]
  - [Specific fact, stat, or detail]
  - [Specific fact, stat, or detail]
  - Xavor angle: [2 sentences — what it means + what to do]
  - Content idea: "[Title]" — [Format] — [Audience] — [Pain point + service line]
  - Source: [link or publication]
  - Strength: High / Medium / Low

📄 RESEARCH & BREAKTHROUGHS
[Same format as above. Skip section entirely if nothing qualifies.]

🤝 PARTNERSHIPS & DEALS
[Same format as above. Skip section entirely if nothing qualifies.]

💰 FUNDING & M&A
[Same format as above. Skip section entirely if nothing qualifies.]

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

## Source Quality Filter
Prefer: named research reports (with sample size, date, or methodology), official company newsrooms and press releases, trade press with original reporting, analyst firms (Gartner, Forrester, IDC, McKinsey, Deloitte, BCG, Accenture), and practitioner-authored content with specific data or experience.
Exclude: AI hype articles without original data, clickbait headlines, influencer hot takes without sourcing, anonymous opinion pieces, and content that states a trend without citing who found it, when, or how.

## Search Strategy
Do not default to broad "[topic] news this week" queries — these surface the same top results every week. Instead, vary your approach:
- Named announcements: "[company] announcement" OR "[product] launch" OR "[product] GA" {date_range}
- Research hunting: "[topic] survey 2026" OR "[topic] report 2026" OR "[topic] study 2026"
- Deals and moves: "[company] acquisition" OR "[company] partnership" OR "[company] integration" {date_range}
- Niche trade press and analyst content beyond the top search results
- Site-specific: site:substack.com [topic], site:linkedin.com/pulse [topic], site:reddit.com [topic]
- Regulatory and compliance: specific laws, deadlines, enforcement actions, governance mandates
- Follow threads: if a finding is interesting, search deeper on that specific story rather than moving to the next broad topic

## Domains

ENTERPRISE AI & AGENTIC AI
- Specific product releases or GA announcements: Salesforce Agentforce, ServiceNow AI Platform, Oracle AI, agentic frameworks and tools
- Named research reports on enterprise AI adoption, agent deployment, or governance — look for ones with survey data and named methodology
- Aras PLM, Propel PLM — releases, customer wins, analyst mentions, competitive moves
- AI governance: regulatory deadlines (EU AI Act, US state laws), compliance frameworks, enterprise policy tooling
- Build-vs-buy debates, platform comparison discussions, or implementation post-mortems from practitioners

PHYSICAL AI
- Named deployment contracts or partnerships (binding agreements, RaaS deals, pilot-to-production announcements)
- Specific hardware or platform launches in humanoid/industrial robotics
- Edge AI integration announcements with named vendors or verticals
- Digital twin deployments with named companies, use cases, or outcomes

DATA
- Specific platform releases with named features: Databricks, Snowflake, dbt, Fivetran, Starburst, Monte Carlo, etc.
- Data governance: Unity Catalog, data mesh, observability tooling — named product updates
- M&A in the modern data stack — deal size, acquirer, stated rationale
- MLOps and LLMOps: named tooling updates, agent lifecycle management, evaluation frameworks

CLOUD
- Named cloud architecture decisions, migrations, or multi-cloud strategy announcements
- FinOps: AI cost management, token spend tracking, GPU cost attribution, named tooling
- AWS, Azure, GCP — specific service launches or pricing changes relevant to enterprise AI
- Cloud security and governance developments with named frameworks or incidents

FUNDING & M&A
- Deals with dollar amounts, named acquirer, named target, stated strategic rationale
- Physical AI and robotics investment rounds

ENTERPRISE DECISION-MAKER PULSE
Hunt for what practitioners and leaders are actually writing and discussing — not what vendors say they care about:
- LinkedIn: site:linkedin.com/pulse "[pain point]" 2026 — look for posts from named CTO, VP, or CDO roles
- Substack: site:substack.com "enterprise AI" OR "data engineering" OR "cloud architecture" 2026
- Reddit: site:reddit.com "enterprise" AND ("AI agents" OR "data platform" OR "PLM" OR "cloud costs")
- Analyst reports: search by report name or topic — "Gartner magic quadrant 2026" OR "Forrester wave 2026" OR "IDC report enterprise AI"
- Focus on: specific pain points with quoted or cited language, named solutions gaining traction, active debates and decisions enterprise buyers are navigating

## Sources
Company newsrooms, press releases, TechCrunch, VentureBeat, The Robot Report, IEEE Spectrum, Futurum, SiliconANGLE, Constellation Research, Gartner, McKinsey, Forrester, IDC, Deloitte Insights, BCG, Accenture, FinOps Foundation, LinkedIn (via Google), Reddit, Substack.

Score all signals. Filter aggressively — only include what genuinely matters to Xavor.
Every item in the digest must cite a specific fact, statistic, named product, named company, or dated event — no paraphrased generalities.
Produce the digest in the EXACT format specified.
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

    # Persist the digest so the monthly Content Engine can pick it up.
    os.makedirs("digests", exist_ok=True)
    digest_path = f"digests/{today.strftime('%Y-%m-%d')}.md"
    with open(digest_path, "w") as f:
        f.write(f"SENTINEL x XAVOR — WEEKLY DIGEST [{date_range}]\n\n{digest}\n")
    print(f"Digest saved to {digest_path}")

    print("Done.")

if __name__ == "__main__":
    main()
