# Roy G's Spirits Price Tracker

Automatically scrapes current prices from **Provi** and **Twin B2B**, updates the
`Cost Per Bottle` column in your Master Order Guide, and syncs On Hand quantities
from your Inventory Locations sheet — running every **Monday, Wednesday, and Friday**.

---

## Folder Structure

```
spirits-price-tracker/
├── .github/
│   └── workflows/
│       └── update_prices.yml     ← GitHub Actions schedule
├── scraper/
│   ├── scraper.py                ← Provi + Twin B2B scrapers
│   └── excel_updater.py          ← Excel read/write logic
├── spreadsheets/
│   └── claude_excel_sheet.xlsx   ← YOUR spreadsheet lives here
├── main.py                       ← Entry point
├── requirements.txt
└── README.md
```

---

## One-Time Setup

### 1. Create a GitHub Repository

1. Go to [github.com](https://github.com) → **New repository**
2. Name it `roys-spirits-tracker` (or anything you like)
3. Set it to **Private** (your credentials are stored as secrets, not in code)
4. Click **Create repository**

### 2. Upload This Project

Upload all files from this folder into your new repo. The easiest way:

```bash
# If you have Git installed locally
git clone https://github.com/YOUR_USERNAME/roys-spirits-tracker.git
cd roys-spirits-tracker
# Copy all files from this project into the folder
git add .
git commit -m "Initial setup"
git push
```

Or use the GitHub web UI: drag and drop files into the repo.

### 3. Put Your Spreadsheet in the Repo

Create a `spreadsheets/` folder in the repo and upload `claude_excel_sheet.xlsx` into it.

### 4. Add Your Credentials as GitHub Secrets

This keeps your username/password **out of the code** and secure.

1. In your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add each of these:

| Secret Name     | Value                          |
|-----------------|--------------------------------|
| `PROVI_EMAIL`   | Your Provi login email         |
| `PROVI_PASSWORD`| Your Provi password            |
| `TWIN_EMAIL`    | Your Twin B2B login email      |
| `TWIN_PASSWORD` | Your Twin B2B password         |

### 5. Enable Actions

- Go to your repo → **Actions** tab → click **Enable GitHub Actions** if prompted

---

## How It Works

Each Monday, Wednesday, and Friday at 8:00 AM CT, GitHub automatically:

1. Logs into **Provi** and searches for each product assigned to Provi/Specs
2. Logs into **Twin B2B** and searches for each product assigned to Twin
3. Updates the **Cost Per Bottle** column in the Master Order Guide
4. Reads quantities you entered in **Inventory Locations** and copies them to the **On Hand** column in Master Order Guide
5. Updates the **Date** field at the top
6. Saves and commits the updated spreadsheet back to the repo

---

## How to Update Your On Hand Quantities (Weekly)

In the **Inventory Locations** sheet, quantities go in **column C** (the third column of each group):

| Column A (Item Name) | Column B (blank) | Column C (Quantity) |
|----------------------|------------------|---------------------|
| Elit                 |                  | 3                   |
| Figenza              |                  | 1                   |
| Haiken               |                  | 2                   |

Repeat this pattern for each 3-column group (columns D-F, G-I, J-L, M-O).

After entering your counts, **upload the updated spreadsheet** back to the `spreadsheets/` folder in the repo (or commit it if using Git locally). The next scheduled run will pick up the new quantities.

---

## Manual Run

To trigger the scraper immediately without waiting for the schedule:

1. Go to your repo → **Actions** tab
2. Click **Spirits Price Update** in the left sidebar
3. Click **Run workflow** → **Run workflow**

---

## Downloading the Updated Spreadsheet

After each run, the updated file is committed back to the repo at:
`spreadsheets/claude_excel_sheet.xlsx`

Just navigate there in GitHub and click **Download**.

---

## Troubleshooting

**A price shows as unchanged / not updated**
- The product name in your sheet may not match what the site returns. Check the Actions log for "no price found for" warnings. You can adjust product names in the spreadsheet to match the site listing exactly.

**Login failed**
- Double-check your GitHub Secrets. Make sure there are no extra spaces in the values.

**Workflow not running**
- GitHub may pause scheduled workflows on repos with no recent activity. Just make any small commit (like editing this README) to reactivate it.
