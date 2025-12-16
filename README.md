Here is the updated **README.md**. It has been rewritten to emphasize the convenience of `main.py` while keeping the critical instructions about the Edge Driver version.

---

# Bing Search Automation for Microsoft RewardsA robust
all-in-one Python automation tool designed to perform daily Bing searches on **PC** and **Mobile** modes automatically. This project helps automate the process of earning Microsoft Rewards points by simulating human-like browsing behavior.

With the new `main.py`, you can complete both desktop and mobile search quotas in a single run.

## 🚀 Features
* **One-Click Automation:** Runs both PC and Mobile search tasks sequentially via `main.py`.
* **Real-time Trending Keywords:** Automatically fetches current trending topics from **Bing News** and **Baidu Hot Search** to ensure search queries look natural (no repeated static words).
* **Smart Fallback:** If network scraping fails, it automatically switches to a robust internal keyword list.
* **Human Simulation:** Includes random intervals (5-10s), page scrolling, and mouse simulated movements to avoid bot detection.
* **Stability:** Optimized with "Eager" loading strategies and timeout protection to prevent hanging on slow-loading pages.

## 🛠️ Prerequisites
* **Python 3.x** installed on your system.
* **Microsoft Edge** browser installed.

## 📥 Installation & Setup###1. Clone or Download this repositoryDownload the source code to a local folder.

### 2. Install DependenciesOpen your terminal/command prompt and run:

```bash
pip install selenium
```

### 3. Download the Matching Edge Driver (⚠️ CRITICAL)
**This is the most important step.** You must download the `msedgedriver` that **exactly matches** your current Microsoft Edge browser version.

1. Open Microsoft Edge.
2. Go to `Settings` -> `About Microsoft Edge` (or type `edge://settings/help` in the address bar).
3. Note the **Version number** (e.g., `131.0.2903.99`).
4. Visit the [Microsoft Edge Driver Official Download Page](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/).
5. Find the version that matches yours and download the **x64** (for Windows 64-bit) zip file.
6. Unzip the file and place `msedgedriver.exe` into the `edgedriver_win64/` folder in this project directory.

> **Note:** If your Edge browser updates automatically in the future, you may need to download the new driver version again if the script stops working.

## 📂 Project StructureEnsure your folder looks like this:

```text
├── edgedriver_win64/
│   └── msedgedriver.exe    <-- Your downloaded driver goes here
├── main.py                 <-- The main entry point
├── pc.py                   <-- Module for PC searches
├── mobile.py               <-- Module for Mobile searches
└── README.md

```

## 🏃‍♂️ UsageYou only need to run one file. The script will first execute the PC searches, then automatically switch to Mobile emulation.

### Run the full automation:
```bash
python main.py
```

*(Optional)* If you want to run them individually:

* PC only: `python pc.py`
* Mobile only: `python mobile.py`

## 📝 How it Works1. **PC Phase:** The script launches Edge on desktop mode, scrapes 30 real-time keywords, and performs the searches with random scrolling and pauses.
2. **Mobile Phase:** Once PC searches are done, it relaunches Edge in "iPhone X" emulation mode and repeats the process for mobile points.
3. **Completion:** The browser closes automatically after all tasks are finished.

## ⚠️ DisclaimerThis script is for educational purposes only. Using automation tools to earn Microsoft Rewards points may violate Microsoft's Terms of Service. Use this tool at your own risk. The author is not responsible for any banned accounts.