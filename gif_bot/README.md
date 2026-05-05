# ایت گیف (گیف ساز) – GIF Editor Telegram Bot

A full-featured Telegram GIF editor bot that clones **@itgifbot**.  
Built with **aiogram 3.x** and **FFmpeg**.

---

## Project Structure

```
gif_bot/
├── main.py            # Entry point – starts the bot
├── handlers.py        # All message & callback handlers (FSM logic)
├── keyboards.py       # All InlineKeyboardMarkup builders
├── ffmpeg_utils.py    # FFmpeg filter-graph builder + async runner
├── states.py          # FSM state definitions
├── config.py          # Paths, font map, speed map, constants
├── requirements.txt
├── .env.example       # Copy to .env and set BOT_TOKEN
├── fonts/             # ← Place your .ttf font files here
│   ├── IRANSans.ttf
│   ├── aviny.ttf
│   ├── ZahraRoosta.ttf
│   └── Vazir.ttf
└── temp_gifs/         # Auto-created. Temporary download/output files.
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| FFmpeg | 5.x+ (must be in PATH) |

Install FFmpeg:
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/download.html and add to PATH

---

## Setup

### 1. Clone / unzip the project

```bash
cd gif_bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your fonts

Place the following `.ttf` files in the `fonts/` directory:
- `IRANSans.ttf`
- `aviny.ttf`
- `ZahraRoosta.ttf`
- `Vazir.ttf`

These are Persian fonts freely available online (e.g. on GitHub).

### 5. Configure the bot token

```bash
cp .env.example .env
# Edit .env and set BOT_TOKEN=<your token from @BotFather>
```

### 6. Run the bot

```bash
python main.py
```

---

## How the FFmpeg Filter Graph Is Built

The function `ffmpeg_utils.build_filter_graph(state)` dynamically assembles
the `-vf` string by appending filter tokens in this fixed order:

```
setpts → reverse → hflip → scale(wide) → hue/negate → drawtext(text) → drawtext(watermark)
```

Each token is only added when the corresponding setting is active:

| Setting | FFmpeg filter |
|---------|--------------|
| Speed x0.5 | `setpts=2.0*PTS` |
| Speed x2   | `setpts=0.5*PTS` |
| Speed x4   | `setpts=0.25*PTS` |
| Reverse    | `reverse` |
| Mirror     | `hflip` |
| Wide       | `scale=iw*3/2:ih,setsar=1` |
| B&W        | `hue=s=0` |
| Negative   | `negate` |
| Text       | `drawtext=fontfile=...:text=...:x=...:y=...` |
| Watermark  | `drawtext=text='@itgifbot':...` |

Example full filter string (text + B&W + mirror):
```
hflip,hue=s=0,drawtext=fontfile='/fonts/IRANSans.ttf':text='خنده دار بود':fontcolor=white:fontsize=h/10:borderw=3:bordercolor=black:x=(w-tw)/2:y=h-th-10,drawtext=text='@itgifbot':fontcolor=white@0.5:fontsize=h/25:borderw=1:bordercolor=black@0.5:x=5:y=h-th-5
```

The output is always an **MP4 (H.264, no audio)** sent via `send_animation()`,
which Telegram displays as a looping silent GIF bubble.

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message + reset state |
| `/gif` | (Groups) Reply to a GIF to start editing |
| `/cancel` | Cancel current operation |

---

## Usage – Private Chat

1. Send any GIF to the bot.
2. Type the text you want overlaid (or press **بدون متن 🚫** to skip).
3. Use the inline buttons to adjust:
   - **جای متن** – 3×3 position grid
   - **رنگ متن** – text color
   - **فیلتر گیف** – Normal / B&W / Negative
   - **Font** – IRANSans / aviny / ZahraRoosta / Vazir
   - **تنظیمات دیگر** – Reverse, Mirror, Speed, Wide
4. Press **🎬 ساخت گیف** to render and receive the edited GIF.

## Usage – Group Chat

1. Reply to any GIF in the group with `/gif`.
2. The bot will ask for text in the group (or you can use **بدون متن**).
3. Configure settings and press **🎬 ساخت گیف**.
