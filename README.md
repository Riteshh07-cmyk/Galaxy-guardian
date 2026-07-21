# Galaxy Guardian – Gesture Controlled Space Shooter

**Status:** 🚧 Step 1 of build in progress (project setup + window test)

## Current folder structure

```
galaxy_guardian/
├── assets/
│   ├── player/
│   ├── enemy/
│   ├── boss/
│   ├── background/
│   ├── effects/
│   ├── sounds/
│   ├── fonts/
│   └── ui/
├── main.py
├── settings.py
├── requirements.txt
└── README.md
```

## Step 1 Setup Instructions

1. **Install Python 3.10 or 3.11** (MediaPipe does not yet support every
   version of 3.12/3.13, so stick to 3.10/3.11 to avoid install headaches).
   Check your version:
   ```
   python --version
   ```

2. **Open a terminal inside the `galaxy_guardian` folder.**

3. **Create a virtual environment** (keeps this project's packages separate
   from everything else on your machine):
   ```
   python -m venv venv
   ```

4. **Activate it:**
   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
   - Windows (cmd.exe): `venv\Scripts\activate.bat`
   - macOS / Linux: `source venv/bin/activate`

   You'll know it worked because your terminal prompt will show `(venv)`
   at the start of the line.

5. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

6. **Run the game window test:**
   ```
   python main.py
   ```

   ✅ **Expected result:** a 1280×720 dark space-colored window opens,
   titled "Galaxy Guardian", showing an FPS counter in the top-left
   that should read close to 60. Pressing `ESC` or clicking the window's
   close button should close it cleanly with no errors in the terminal.

   ❌ If it doesn't run: copy the exact error text and we'll debug it
   before moving on — don't move to Step 2 until this works.

## What's next (Step 2)

Once you confirm `main.py` runs cleanly, we'll add an animated starfield
background and the main menu skeleton.