# 🌙 Baby Sleep Content Agent — FREE STACK
### mybelovedsleep.com · Cost: $0.00/month

Scrapes viral baby sleep content every Monday at 6am SGT, generates
adapted content, and updates your dashboard. Runs 100% free.

---

## Free stack breakdown

| Component | Tool | Cost |
|---|---|---|
| Instagram scraping | Playwright (public pages) | Free |
| TikTok scraping | Playwright (public pages) | Free |
| Pinterest scraping | Playwright (public pages) | Free |
| Blog articles | Google Custom Search API | Free (100/day limit) |
| Competitor sites | Playwright | Free |
| AI content generation | Google Gemini 1.5 Flash | Free (1,500 req/day) |
| Automation scheduler | GitHub Actions | Free |
| **Total** | | **$0.00/month** |

---

## 3 API keys needed (all free, ~20 minutes setup)

### 1. Google Gemini API key (5 min)
- Go to **aistudio.google.com**
- Click **Get API key** → Create API key → copy it
- GitHub Secret name: `GEMINI_API_KEY`

### 2. Google Custom Search API key (10 min)
- Go to **console.cloud.google.com**
- Create a project → Enable **Custom Search API**
- APIs & Services → Credentials → **Create API Key** → copy it
- GitHub Secret name: `GOOGLE_API_KEY`

### 3. Google Custom Search Engine ID (5 min)
- Go to **cse.google.com/cse/create/new**
- Name it anything (e.g. "Baby Sleep Agent")
- Under "Sites to search": type `*` to search the whole web
- Click Create → Setup → **Search engine ID** → copy it
- GitHub Secret name: `GOOGLE_CSE_ID`

---

## GitHub setup (25 min total including above)

### Step 1 — GitHub account
- github.com → Sign up (free) → New repository: `baby-sleep-agent` (private)
- Upload all files using the "Upload files" button (no terminal needed)

### Step 2 — Add the 3 secrets
- Your repo → **Settings** → Secrets and variables → Actions → New secret
- Add all three: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`

### Step 3 — Test run
- **Actions** tab → Baby Sleep Content Agent → **Run workflow**
- Takes ~90 seconds. Watch it live.

### Step 4 — View dashboard
- After run: download `dashboard/report_latest.json` from your repo
- Open `dashboard/index.html` in any browser

From here it runs every **Monday 6am SGT automatically**. No further action needed.

---

## File structure

```
baby-sleep-agent-free/
├── agent.py                     ← Main runner
├── scrapers/
│   ├── instagram.py             ← Playwright: Instagram hashtags
│   ├── tiktok.py                ← Playwright: TikTok keyword search
│   ├── pinterest.py             ← Playwright: Pinterest search
│   ├── blogs.py                 ← Google Custom Search API
│   └── competitors.py           ← Playwright: competitor blog pages
├── ai/
│   ├── viral_scorer.py          ← Ranks posts by viral potential
│   ├── content_gen.py           ← Gemini: blog, carousel, reel script
│   └── gap_analysis.py          ← Gemini: competitor gap analysis
├── output/
│   └── reporter.py              ← Builds dashboard JSON
├── dashboard/
│   ├── index.html               ← Your dashboard (open this!)
│   └── report_latest.json       ← Updated every Monday
├── requirements.txt             ← Just: playwright
├── .gitignore
└── .github/workflows/
    └── weekly_agent.yml         ← Cron: Monday 6am SGT
```

---

## Notes on Playwright scraping

Playwright reads **publicly visible** pages only — the same content
any person can see by visiting instagram.com or tiktok.com in a browser.
This is within the terms of service for research and personal use.

If Instagram or TikTok change their page structure, the scrapers may
need a small update to the CSS selectors. Check the GitHub Actions log
if a run shows 0 posts from a source.

---

## Troubleshooting

**"0 posts from Instagram"** → Instagram may have updated their HTML
structure. Open an Issue in your repo with the error from the Actions log.

**"Gemini API error 429"** → You've hit the free rate limit (rare for
weekly runs). The free tier allows 1,500 requests/day — a single run
uses only 3–4 requests.

**"Google Custom Search: 403"** → Check that GOOGLE_API_KEY and
GOOGLE_CSE_ID are correctly added as GitHub Secrets (not mixed up).
