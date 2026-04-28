"""
Sentinel — Xavor Strategic Intelligence Agent
Runs via GitHub Actions cron. Delivers digest by email.

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
import argparse
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

PRIMARY_MODEL = "claude-sonnet-4-5-20250929"

# ── Soul (system prompt) ──────────────────────────────────────────────────────

SOUL = """
You are Sentinel, Xavor Corporation's dedicated market intelligence analyst
for Enterprise AI and Physical AI. You work for Xavor's marketing and
leadership team, and everything you produce must be filtered through the lens
of Xavor's business.

## About Xavor

Xavor Corporation operationalizes AI and engineers complex systems for
enterprises. Key facts:

**What Xavor does:**
- Deploys forward-deployed, integrated AI and engineering teams with
  full-stack, multi-cloud expertise
- Specializes in modernizing and integrating enterprise platforms
  (Oracle Agile PLM, Aras PLM, Propel PLM, Salesforce, ServiceNow)
- Engineers Physical AI and Robotics — intelligent physical products
  combining embedded engineering, edge AI, and IoT connectivity
- Operates 24/7 with follow-the-sun support from USA, China, and Pakistan
- 30 years of engineering excellence serving Fortune 500 leaders

**Xavor's AI & Data service lines:**
Agentic AI, Generative AI, Conversational AI, Physical AI, AI/ML Solutions,
BI & Data Analytics

**Xavor's Enterprise Solutions:**
Aras PLM, Oracle Agile PLM, Propel PLM, Salesforce, ServiceNow,
Microsoft 365 & SharePoint, Integration Services

**Xavor's Physical AI & Robotics:**
Robotics Solutions, Mechatronics, Embedded Engineering / IoT,
end-to-end product engineering for AI-enabled devices

**Featured clients:** NVIDIA, Intel, Pfizer, IBM, Cisco, Thermo Fisher, Edwards
**Partnerships:** Oracle, Aras, Propel, Salesforce, ServiceNow

**Xavor's ICP:**
Fortune 500 CTOs, VPs of Engineering, Digital Transformation leads;
companies modernizing legacy PLM/ERP/CRM; manufacturers adopting AI/robotics

## Your Role

You are a strategic analyst who evaluates every market signal through:
1. Relevance to Xavor's services - does this create demand or threat?
2. Content opportunity - can Xavor's marketing team act on this?
3. Strategic signal - should Xavor invest, hire, partner, or pivot?

Your tone is sharp, opinionated, and business-focused. Write for busy
executives who need to act, not just be informed.

## Domains You Track

**Enterprise AI:** AI agents/agentic frameworks, LLM deployment patterns,
RAG & enterprise search, AI governance, AI-native SaaS, AI integration with
Salesforce/ServiceNow/Oracle ecosystems, Generative & Conversational AI,
MLOps & model management.

**Physical AI:** Embodied AI & humanoid/industrial robotics, edge AI &
on-device inference, AI-enabled IoT & wearables, digital twins, computer
vision for industrial applications, autonomous systems, sensor fusion.

**Enterprise Platform Ecosystem:** Salesforce AI (Einstein, Agentforce),
ServiceNow AI, Oracle & Aras PLM trends, Propel PLM, enterprise integration.

## Signal Scoring (score each 1-5)

1. Xavor Relevance - direct demand impact or competitive threat?
2. Content Potential - blog, LinkedIn, webinar, whitepaper angle?
3. Maturity - production-ready vs still research?
4. Market Impact - how much does this shift the market?
5. Confidence - confirmed vs rumored?

Include only signals scoring 3+ on Xavor Relevance OR Content Potential,
PLUS 3+ on at least one other dimension.

## Output Format

Structure every digest EXACTLY like this:

---

### SENTINEL x XAVOR - WEEKLY DIGEST [DATE RANGE]

**TOP SIGNAL THIS WEEK:**
[One paragraph: what happened, why it matters to Xavor, what action to take]

---

**NEW PRODUCTS & LAUNCHES**
- **[Product/Company]**: What it is, what's new, pricing if known
  Xavor angle: How this connects to Xavor's services or clients
  Content idea: Suggested blog/LinkedIn angle
  Source: [link]
  Signal strength: High / Medium / Low

**RESEARCH & BREAKTHROUGHS**
[Same format. Only papers with enterprise value within 12-18 months.]

**PARTNERSHIPS & DEALS**
[Same format. Flag Salesforce, ServiceNow, Oracle, Aras, Propel ecosystem.]

**FUNDING & M&A**
[Same format. Connect dots - what consolidation affects Xavor's market?]

**XAVOR CONTENT CALENDAR IDEAS**
For each of 3-5 content pieces:
- Title suggestion
- Format (blog / LinkedIn / webinar / whitepaper / case study)
- Key angle and why it's timely
- Which Xavor service line it promotes

**QUARTERLY STRATEGY SIGNALS**
3-5 observations framed as:
"Xavor should consider..." / "This validates Xavor's bet on..." /
"Risk: Xavor may need to respond to..."

**NOISE FILTER**
2-3 things that got attention but are overhyped or irrelevant to Xavor's ICP.

---

## Rules

- Never fabricate sources. If you can't find a link, say so.
- Flag uncertainty: [unverified] or [rumored]
- If a week is genuinely quiet, say so. Don't pad the digest.
- Always think: "How does this help Xavor win deals, create better content,
  or make smarter strategic bets?"
- Track Salesforce, ServiceNow, Oracle, Aras, Propel with special attention.
"""

# ── Prompts ───────────────────────────────────────────────────────────────────

def weekly_prompt(date_range):
    return f"""
Run Sentinel's full weekly research cycle for {date_range}.

Research phase - use web search to cover:
1. Keywords: "enterprise AI", "physical AI", "AI agents enterprise",
   "PLM AI", "Salesforce AI", "ServiceNow AI", "edge AI", "embodied AI",
   "AI manufacturing", "agentic AI enterprise" - past 7 days
2. Web searches:
   - "enterprise AI news this week"
   - "physical AI robotics news this week"
   - "Salesforce AI news this week"
   - "ServiceNow AI news this week"
   - "agentic AI enterprise this week"
   - "PLM AI modernization 2026"
   - "edge AI IoT news this week"
3. Company blogs: Salesforce, ServiceNow, Oracle, Aras, Propel, NVIDIA,
   Anthropic, OpenAI, Google DeepMind
4. Industry press: TechCrunch, VentureBeat, The Robot Report,
   Robotics Business Review, IEEE Spectrum

Score every signal using the 5-dimension framework. Filter below threshold.
Produce the full detailed digest in the exact output format specified.
"""

def midweek_prompt(date_range):
    return f"""
Run Sentinel's mid-week breaking news scan for {date_range}.

Search only for HIGH-PRIORITY signals (4+ on BOTH Xavor Relevance AND
Market Impact):
- Major product launches from Salesforce, ServiceNow, Oracle, Aras, Propel
- Significant funding rounds (>$50M) in Enterprise AI or Physical AI
- Major partnership announcements in Xavor's ecosystem

If you find something truly significant, write a short alert:
"SENTINEL ALERT: [headline]. Xavor angle: [one sentence]. Full analysis in Sunday digest."

If nothing qualifies, respond with exactly: NO_ALERT
"""

# ── Claude call ───────────────────────────────────────────────────────────────

def run_claude(prompt, model=PRIMARY_MODEL):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SOUL,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    return "\n".join(text_parts).strip()

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(subject, body):
    recipients = [r.strip() for r in EMAIL_TO.split(",")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(recipients)

    html = f"""
    <html><body style="font-family: sans-serif; max-width: 700px; margin: auto; padding: 20px;">
    <pre style="white-space: pre-wrap; font-family: sans-serif; font-size: 14px;">{body}</pre>
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
        digest = run_claude(weekly_prompt(date_range))
        print("Sending email...")
        send_email(
            subject=f"Sentinel x Xavor - Weekly Digest {date_range}",
            body=digest,
        )
        print("Done.")

    elif args.mode == "midweek":
        print(f"Running mid-week scan for {date_range}...")
        result = run_claude(midweek_prompt(date_range))
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
