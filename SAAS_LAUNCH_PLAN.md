# TradeALGO SaaS Launch Plan
> Execute this AFTER 90-day paper trading validates the strategy.

---

## Status Tracker
- [ ] Strategy validated (90-day paper trade complete)
- [ ] Deploy to Streamlit Community Cloud
- [ ] Set password in Streamlit Secrets
- [ ] Set up Razorpay Payment Link
- [ ] Add legal disclaimer to app homepage
- [ ] First paying subscriber

---

## Step 1 — Deploy (10 minutes)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub (Himanshu-PRO01)
3. Create App → repo: `TradeALGO-main` → main file: `Trading_Desk.py`
4. In **Advanced Settings → Secrets**, paste:
   ```toml
   hosted = "1"
   password = "YOUR-SUBSCRIBER-PASSWORD-HERE"
   ```
5. Deploy → share the URL with subscribers.

---

## Step 2 — Collect Payment (No Code Needed)
**Option A: UPI (instant, free)**
- Share your UPI ID (Google Pay / PhonePe / Paytm)
- Confirm payment screenshot → send password over WhatsApp

**Option B: Razorpay Payment Link (professional)**
1. Create free account at [razorpay.com](https://razorpay.com)
2. Dashboard → Payment Links → Create Link
3. Set amount (Rs 199 / Rs 599 / Rs 4999)
4. Share the link on Instagram / Telegram / WhatsApp
5. On payment → manually send password (automate when 50+ subscribers)

---

## Step 3 — Pricing Tiers
| Plan | Price | Access |
|:---|:---|:---|
| Weekly Pass | Rs 199 | 7 days |
| Monthly | Rs 599 | 30 days |
| Annual Pro | Rs 4,999 | 365 days + WhatsApp support |

---

## Step 4 — Legal Disclaimer (paste on homepage / landing page)
> "TradeALGO is algorithmic software for self-directed traders. It does not
> provide investment advice, recommendations, or guaranteed returns. All trading
> involves risk. The developer is not a SEBI-registered analyst."

---

## SEBI License (Do Later — After Graduation)
- **Exam**: NISM Series XV (Research Analyst), Rs 1,500 fee, 60% pass mark
- **Capital Required**: Rs 1 Lakh net worth (CA certificate)
- **Application**: siportal.sebi.gov.in, fee Rs 5,000 total
- **Track record ready**: audit_logs/SEBI_TRACK_RECORD_REPORT.md (auto-built by daemon)

---

## Notes
- Do NOT need a new website — Streamlit app IS the product
- Do NOT need user login/account system — one shared password per tier
- Do NOT build payment automation until 50+ subscribers
- Everything needed is already in this repo
