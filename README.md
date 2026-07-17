# Argor Cast Bar Rate Tracker

Scrapes UOB's public gold & silver rates page once an hour, records the
Argor Cast Bar "Bank Sells (SGD)" and "Bank Buys (SGD)" figures, and plots
them over time on a small website.

## How it fits together

```
.github/workflows/scrape.yml   -> runs scraper/scrape.py every hour on GitHub's servers
scraper/scrape.py              -> renders the UOB page with a headless browser,
                                   extracts the two numbers, appends them to:
docs/data/prices.json          -> the growing history file
docs/index.html                -> reads prices.json and draws the chart
                                   (this folder is what GitHub Pages publishes)
```

Because the workflow commits `docs/data/prices.json` back into the repo every
hour, and GitHub Pages serves straight from the repo, the site updates itself
automatically — no separate database or backend hosting needed, and no cost.

## One-time setup (about 10 minutes)

1. **Create a new GitHub repository** (public or private both work) and push
   this project to it:
   ```bash
   cd gold-tracker
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

2. **Allow the workflow to push commits.**
   In your repo: **Settings → Actions → General → Workflow permissions** →
   select **"Read and write permissions"** → Save.
   (Without this, the hourly job can scrape but can't save the result.)

3. **Turn on GitHub Pages.**
   In your repo: **Settings → Pages** → under "Build and deployment", set
   **Source: Deploy from a branch**, **Branch: main**, **Folder: /docs** →
   Save.
   GitHub will give you a URL like `https://<your-username>.github.io/<your-repo>/`
   — that's your live site.

4. **Kick off the first run manually** so you don't have to wait an hour:
   Repo → **Actions** tab → **"Hourly gold price scrape"** workflow →
   **Run workflow**.
   Check the run for a green checkmark, then refresh your Pages URL —
   you should see one data point on the chart. After that it updates itself
   every hour.

## Notes

- **Why a headless browser, not a simple HTTP request?** UOB's rates table
  is filled in by JavaScript after the page loads, so a plain request only
  sees an empty table. Playwright actually renders the page like a real
  browser, waits for the numbers to appear, then reads them.
- **If a scrape fails** (e.g. UOB changes their page layout), that run's
  Action will show a red ✗ in the Actions tab and the existing history is
  left untouched — nothing gets overwritten with bad data. GitHub will
  email you automatically when a scheduled workflow starts failing.
- **Changing the schedule:** edit the `cron: "0 * * * *"` line in
  `.github/workflows/scrape.yml`. That expression means "minute 0 of every
  hour." [crontab.guru](https://crontab.guru) is handy for adjusting it.
- **Cost:** this all runs on GitHub's free tier (Actions + Pages) for a
  public repo. Private repos get a generous free minutes allowance too;
  one scrape a day uses a few minutes each, well within it.
- **If UOB changes their page structure**, `scraper/scrape.py` looks for a
  table row whose text matches "argor...cast...bar" and pulls the first two
  numbers it finds in that row — this is intentionally loose so small
  wording changes won't break it, but a bigger redesign might need the
  selector logic updated.
