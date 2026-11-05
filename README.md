# ⚡ SOUMOJIT Hark Account Creator & Profile Manager

Automated Hark account creation and multi-profile manager tool built with CustomTkinter and Chrome DevTools Protocol (CDP).

---

## 🚀 Features
- **Strict Step-by-Step Automation:**
  - Automated dot-trick email submission on Hark.
  - Automatic 18+ Birthday Verification (`Oct 17, 1995`).
  - Incremental Atomic Mail Magic Link scraper (`/message/93` ➔ `94` ➔ `95`).
- **Clean 3-Window Layout:**
  - **Top Window:** Master Atomic Mail window.
  - **Bottom Left Window:** Hark Account 1.
  - **Bottom Right Window:** Hark Account 2.
- **Chrome Profile Isolation:**
  - Separate cookies, local storage, and sessions for every generated account.
  - Zero cross-profile data leakage.
- **Export & Management:**
  - One-click CSV export.
  - Live status tracking (Open, Successful, Failed, Pending).
  - Retry failed accounts with one click.

---

## 💻 How to Run

### Method 1: Portable Standalone Executable (No Python Required)
1. Download or copy `SOUMOJIT_Hark_Tool.exe`.
2. Double-click `SOUMOJIT_Hark_Tool.exe` to launch.
3. Done! The tool will create necessary folders automatically.

### Method 2: Run from Python Source
1. Ensure Python 3.10+ and Google Chrome are installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
   *(Or double-click `run_app.bat`)*

---

## ⚙️ Requirements
- Windows 10 / 11
- Google Chrome Browser

