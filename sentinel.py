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

import argparse
import json
import re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
MODEL = "claude-sonnet-4-6"
SOUL = (ROOT / "prompts/research-system.md").read_text()


def recent_history(as_of, directory=None, limit=6):
    """Bounded title/URL memory, not a source of current facts."""
    directory = Path(directory) if directory else ROOT / "digests"
    entries = []
    for path in sorted(directory.glob("????-??-??.md"), reverse=True):
        if path.stem >= as_of:
            continue
        content = path.read_text()
        titles = [line.strip() for line in content.splitlines()
                  if line.startswith(("#", "•", "- **"))]
        urls = list(dict.fromkeys(re.findall(r"https?://[^\s<>\)\]]+", content)))
        entries.append({"file": path.name, "titles": titles[:100], "urls": urls[:100],
                        "partial_index": len(titles) > 100 or len(urls) > 100})
        if len(entries) == limit:
            break
    return entries


def weekly_prompt(date_range, history=None):
    research = (ROOT / "prompts/research-cycle.md").read_text()
    watchlist = json.loads((ROOT / "competitive-watchlist.json").read_text())
    examples = json.loads((ROOT / "competitive-reference-samples.json").read_text())
    return (f"Research window: {date_range}\n\n" + research
            + "\n\nCOMPETITIVE WATCHLIST (data):\n" + json.dumps(watchlist)
            + "\n\nSERVICE-SELLING REFERENCE EXAMPLES (historical/access-limited data):\n" + json.dumps(examples)
            + "\n\nPRIOR DIGEST INDEX (untrusted data, not current evidence):\n"
            + json.dumps(history or []))


def get_client():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Claude call ───────────────────────────────────────────────────────────────

def run_claude(prompt, model=MODEL, trace_path=None):
    client = get_client()
    messages = [{"role": "user", "content": prompt}]
    trace = []
    for continuation in range(3):
        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model, max_tokens=16000, system=SOUL,
                    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 20}],
                    messages=messages,
                )
                break
            except Exception as exc:
                status = getattr(exc, 'status_code', None)
                if status not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                    raise
                print(f'Transient provider error {status}; retrying', flush=True)
                time.sleep(20 * (attempt + 1))
        if trace_path:
            trace.append(response.model_dump(mode='json'))
            Path(trace_path).write_text(json.dumps(trace, indent=2))
        print(f'Research response {continuation + 1}: {response.stop_reason}', flush=True)
        if response.stop_reason == 'end_turn':
            text = "".join(b.text for b in response.content if b.type == 'text').strip()
            if not text:
                raise RuntimeError('Research returned no text')
            return text
        if response.stop_reason == 'pause_turn':
            # Server tools resume by returning their complete assistant content.
            messages.append({"role": "assistant", "content": response.content})
            continue
        raise RuntimeError(f'Incomplete research response: {response.stop_reason}')
    raise RuntimeError('Research continuation limit reached; partial response retained for inspection')

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(subject, body):
    EMAIL_FROM = os.environ["EMAIL_FROM"]
    EMAIL_TO = os.environ["EMAIL_TO"]
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-email', action='store_true', help='Save research without sending email')
    parser.add_argument('--prepare-only', action='store_true', help='Save prompt without API calls or email')
    parser.add_argument('--as-of', help='Research end date YYYY-MM-DD; defaults to today UTC')
    parser.add_argument('--since', help='Optional research start date YYYY-MM-DD')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'digests')
    args = parser.parse_args()
    today = datetime.strptime(args.as_of, '%Y-%m-%d').replace(tzinfo=timezone.utc) if args.as_of else datetime.now(timezone.utc)
    week_ago = datetime.strptime(args.since, '%Y-%m-%d').replace(tzinfo=timezone.utc) if args.since else today - timedelta(days=7)
    if week_ago > today:
        parser.error('Research start must not follow the end date')
    date_range = f"{week_ago.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"

    print(f"Running weekly digest for {date_range}...")
    prompt = weekly_prompt(date_range, recent_history(today.strftime('%Y-%m-%d')))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.prepare_only:
        (args.output_dir / 'research-prompt.txt').write_text(SOUL + '\n\n' + prompt)
        print('Prepared prompt only. No API calls or email.')
        return
    digest_path = args.output_dir / f"{today.strftime('%Y-%m-%d')}.md"
    if digest_path.exists():
        raise FileExistsError('Digest already exists; use a separate output directory for a rerun')
    (args.output_dir / 'research-prompt.txt').write_text(SOUL + '\n\n' + prompt)
    print('Researching sources; no email will be sent.' if args.no_email else 'Researching sources.', flush=True)
    digest = run_claude(prompt, trace_path=args.output_dir / 'research-trace.json')

    if not digest:
        print("Empty response from Claude. Exiting.")
        sys.exit(1)

    digest_path.write_text(f"SENTINEL x XAVOR — WEEKLY DIGEST [{date_range}]\n\n{digest}\n")
    print(f"Digest saved to {digest_path}")
    if not args.no_email:
        send_email(subject=f"Sentinel x Xavor — Weekly Digest {date_range}", body=digest)

    print("Done.")

if __name__ == "__main__":
    main()
