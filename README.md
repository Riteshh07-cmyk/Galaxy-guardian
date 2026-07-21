# 🚀 Galaxy Guardian
## Gesture Controlled Space Shooter Game

> A futuristic AI-powered space shooter controlled using real-time hand gestures.

Galaxy Guardian is a computer vision-based arcade game where players control a spaceship using hand movements detected through a webcam.

Built using **Python, Pygame, OpenCV, MediaPipe, and NumPy**, this project combines Artificial Intelligence, Game Development, and Human-Computer Interaction.

---

# 🎮 Features

## ✋ AI Gesture Control
- Real-time hand tracking using MediaPipe
- Webcam-based control system
- Gesture recognition
- Controller-free gameplay experience

## 🚀 Game Features
- Player spaceship
- Enemy spacecrafts
- Shooting mechanics
- Collision detection
- Health system
- Score tracking
- Boss battles
- Power-ups

## 🌌 Visual Effects
- Animated space background
- Starfield effect
- Explosion animations
- Particle effects
- Smooth 60 FPS gameplay

## 🔊 Audio System
- Background music
- Shooting sounds
- Explosion effects
- UI sounds

---

# 🧠 How It Works

Galaxy Guardian uses computer vision to convert your hand movements into game controls.

```
Webcam
   |
   ↓
OpenCV Frame Processing
   |
   ↓
MediaPipe Hand Detection
   |
   ↓
Gesture Recognition
   |
   ↓
Player Movement / Actions
   |
   ↓
Pygame Game Engine
```

---

# 🛠️ Technologies Used

| Technology | Usage |
|------------|-------|
| Python | Core programming language |
| Pygame | Game development framework |
| OpenCV | Webcam and image processing |
| MediaPipe | Hand tracking AI |
| NumPy | Mathematical calculations |

---

# 📂 Project Structure

```
galaxy_guardian/

│
├── assets/
│   │
│   ├── player/
│   │   └── spaceship images
│   │
│   ├── enemy/
│   │   └── enemy sprites
│   │
│   ├── boss/
│   │   └── boss images
│   │
│   ├── background/
│   │   └── space backgrounds
│   │
│   ├── effects/
│   │   └── explosions and particles
│   │
│   ├── sounds/
│   │   └── music and effects
│   │
│   ├── fonts/
│   │
│   └── ui/
│       └── buttons and interface
│
├── main.py
├── settings.py
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

## Requirements

Recommended Python version:

```
Python 3.10 or Python 3.11
```

MediaPipe compatibility is better with Python 3.10/3.11.

---

## 1. Clone Repository

```bash
git clone https://github.com/yourusername/galaxy_guardian.git
```

Move into project folder:

```bash
cd galaxy_guardian
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

---

## 3. Activate Virtual Environment

### Windows PowerShell

```bash
venv\Scripts\Activate.ps1
```

### Windows CMD

```bash
venv\Scripts\activate.bat
```

### Linux / macOS

```bash
source venv/bin/activate
```

After activation:

```
(venv)
```

will appear in your terminal.

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Run The Game

Start Galaxy Guardian:

```bash
python main.py
```

Expected result:

✅ 1280×720 game window opens  
✅ Title: "Galaxy Guardian"  
✅ FPS counter visible  
✅ Smooth gameplay at around 60 FPS  

Exit:

```
ESC
```

or close the game window.

---

# 🎮 Controls

| Action | Input |
|--------|-------|
| Move Spaceship | Hand Movement |
| Shoot | Hand Gesture |
| Pause | ESC |
| Exit | Close Window |

---

# 🖐️ Gesture System

The game detects hand landmarks using MediaPipe.

Process:

1. Webcam captures your hand
2. OpenCV processes frames
3. MediaPipe identifies hand points
4. Gesture algorithm calculates movement
5. Commands are sent to the game

---

# 🗺️ Development Roadmap

## ✅ Step 1: Project Setup

Completed:

- Project structure created
- Virtual environment setup
- Pygame window created
- FPS system added


---

## 🚧 Step 2: Game Foundation

Upcoming:

- [ ] Animated starfield background
- [ ] Main menu
- [ ] Player spaceship
- [ ] Movement system


---

## 🔥 Step 3: Gesture Integration

Upcoming:

- [ ] Webcam integration
- [ ] MediaPipe setup
- [ ] Hand landmark detection
- [ ] Gesture controls


---

## 👾 Step 4: Combat System

Upcoming:

- [ ] Enemy spawning
- [ ] Shooting system
- [ ] Bullet collision
- [ ] Score system
- [ ] Health bar


---

## 👑 Step 5: Advanced Features

Upcoming:

- [ ] Boss fights
- [ ] Multiple levels
- [ ] Power-ups
- [ ] Leaderboard
- [ ] Advanced AI enemies


---

# 📸 Screenshots

Screenshots will be added after major milestones.

Example:

```
screenshots/

├── main_menu.png
├── gameplay.png
└── boss_fight.png
```

---

# 🤝 Contributing

Contributions and suggestions are welcome.

Steps:

```bash
git checkout -b feature-name
```

Make changes and commit:

```bash
git add .
git commit -m "Added new feature"
```

Push:

```bash
git push origin feature-name
```

Create a Pull Request.

---

# 👨‍💻 Developer

## Ritesh Mulik

Computer Engineering Student

Interested in:

- 💻 Software Development
- 🤖 Artificial Intelligence
- 🎮 Game Development
- 👁️ Computer Vision


---

# ⭐ Support

If you like this project:

⭐ Star the repository  
🍴 Fork the project  
🚀 Share your feedback


---

# 📜 License

This project is created for educational and experimental purposes.
