# Sharing the trading desk with your brother

Two ways. Pick one.

## A. On his own computer (most private, simplest)
Send him the zip. He unzips it and double-clicks `run_windows.bat` (or `run_mac.command`).
`START_HERE.txt` tells him everything. Nothing leaves his computer.

## B. As a link (he opens it in any browser, even on a phone)
The free option is Streamlit Community Cloud. It is not deployed for you: you do these steps once.

1. **GitHub:** make a free account. Create a **private** repository and upload the unzipped project.
   (`.gitignore` already keeps `.env`, `*.db` and `feedback.csv` out. Check that none of them were uploaded.)
2. **Streamlit Community Cloud:** go to share.streamlit.io, sign in with GitHub, choose *Create app*,
   pick the repository, branch `main`, and set the main file to `Trading_Desk.py`.
3. **Secrets:** in the app's *Advanced settings*, in the Secrets box, paste:
   ```
   hosted = "1"
   password = "a-long-password-only-you-and-your-brother-know"
   ```
   `hosted` makes every visitor's journal live only in their own browser session (nothing is written to
   a file that other visitors could see). `password` puts a password screen in front of every page.
4. **Privacy:** an app made from a private repository is private, and viewers you invite by email
   sign in first. Only one private app is allowed at a time on the free plan. If the repository is
   public the app is public, so keep the password on.
5. **Share:** send the link, and send the password in a separate message.
6. **Updating:** change the files in GitHub and the app updates itself.

### Rules for a hosted copy
- Never put a broker password, OTP, API key or API secret anywhere: not in Secrets, not in the app.
  The app does not need them.
- Do not upload real trade files to an app that is not password protected.
- In hosted mode the journal is forgotten when the tab closes. The Journal page has a *Backup* tab to
  download and reload it, and the Feedback page can be copied or downloaded.
- Free hosted apps go to sleep when unused and wake up slowly. That is normal.

### Running it hosted on your own computer (to test the password screen)
```
ALGOBOT_HOSTED=1 ALGOBOT_PASSWORD=test streamlit run Trading_Desk.py      # Mac and Linux
set ALGOBOT_HOSTED=1 && set ALGOBOT_PASSWORD=test && streamlit run Trading_Desk.py      # Windows
```
