# Whisperer

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey?logo=windows) ![Anthropic](https://img.shields.io/badge/AI-Claude%204.5-9146FF?logo=anthropic) ![Whisper](https://img.shields.io/badge/STT-Whisper-FF6F00) ![Last Commit](https://img.shields.io/github/last-commit/NOLOGOSE/Whisperer) ![Stars](https://img.shields.io/github/stars/NOLOGOSE/Whisperer?style=social)

**Voice input that understands what you mean, not just what you say.**

Hold a key → speak → release → text appears wherever your cursor is.  
Unlike plain dictation, Whisperer reads the intent embedded in your speech and acts on it.

---

## What makes it different

Most voice-input tools convert speech to text verbatim. Whisperer goes one step further: it detects editing and writing instructions spoken alongside your content, and executes them.

| You say | You get |
|---------|---------|
| 我叫 Hans，帮我翻译成英文 | `My name is Hans.` |
| 告诉客户产品延迟一周，写邮件 | A complete professional email body |
| Reply to the supplier saying we accept their offer, keep it formal | A polished acceptance email |
| This acoustic panel helps reduce echo — write Amazon bullet points | Compliant English listing bullets |
| 帮我回复说今天太忙改明天吧 | A natural, ready-to-send chat message |

---

## Requirements

- Windows 10 or 11
- Python **3.12** (not 3.13 or 3.14 — some wheels are missing for newer versions)
- A working microphone
- An [Anthropic API key](https://console.anthropic.com/)

---

## Installation

Open **PowerShell** and run these commands in order.

### 1. Disable the Microsoft Store Python alias

Windows ships a fake `python.exe` that opens the Store. Disable it:

```
Settings → Apps → Advanced app settings → App execution aliases
→ toggle OFF "python.exe" and "python3.exe"
```

### 2. Install Python 3.12

Download the installer from https://www.python.org/downloads/release/python-3120/  
During install, check **"Add Python to PATH"**.

Verify in PowerShell:
```powershell
python --version   # should print Python 3.12.x
```

### 3. Allow PowerShell scripts

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Get the project

```powershell
git clone https://github.com/NOLOGOSE/Whisperer.git
cd Whisperer
```

Or download the ZIP and extract it, then `cd` into the folder.

### 5. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Your prompt should now start with `(venv)`.

### 6. Install dependencies

```powershell
pip install -r requirements.txt
```

### 7. ⚠️ Remove hf-xet immediately

`hf-xet` is sometimes pulled in as a transitive dependency and **causes a crash on Windows** (access violation when Whisper loads). Remove it before doing anything else:

```powershell
pip uninstall hf-xet -y
```

It's safe to run even if it wasn't installed — it will just say "not installed".

### 8. Configure

```powershell
copy .env.example .env
notepad .env
```

Fill in at minimum your `ANTHROPIC_API_KEY`. Save and close.

### 9. Run

```powershell
python voice_input.py
```

The first run downloads the Whisper model (~460 MB for `small`). Subsequent starts are instant.

---

## Configuration

All options live in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `WHISPER_MODEL` | `small` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` | Claude model. Haiku is fastest and cheapest. |
| `HOTKEY` | `caps lock` | Push-to-talk key. Supports single keys and combos (see below). |

### Hotkey examples

```
HOTKEY=caps lock          # default — works well on laptops
HOTKEY=right ctrl
HOTKEY=f9
HOTKEY=ctrl+alt+space     # combo key
HOTKEY=ctrl+shift+`
```

**Do not use `ctrl+v`** — the program uses that key internally to paste.

---

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Hold `HOTKEY` | Record |
| Release `HOTKEY` | Stop and process |
| `Ctrl+Alt+1` | Switch to **chat** mode |
| `Ctrl+Alt+2` | Switch to **email** mode |
| `Ctrl+Alt+3` | Switch to **listing** mode |
| `Esc` | Exit |

---

## Modes

Switch modes with `Ctrl+Alt+1/2/3` at any time. The current mode is shown in the console.

### Chat (default) — `Ctrl+Alt+1`

Everyday messaging and chat input. Handles three kinds of input:

- **Content + instruction** — executes the instruction on your words  
  *"帮我翻译成英文：我明天不能来" → `I won't be able to make it tomorrow.`*
- **Intent + writing instruction** — drafts a complete message from your brief  
  *"告诉他我同意，但需要多两天" → natural, ready-to-send reply*
- **Pure dictation** — cleans up punctuation and typos, keeps your voice

### Email — `Ctrl+Alt+2`

Professional email writing.

- Give bullet-point instructions → get a complete, polished email body
- Dictate a rough draft → get clean, formal prose
- Translation instructions are executed literally

*Example: "通知供应商我们推迟三周发货，原因是港口拥堵，保持礼貌专业"*  
→ Full supplier email body, ready to paste into your mail client.

### Listing (Amazon) — `Ctrl+Alt+3`

Amazon product listing copywriting in English. Compliant with Amazon's guidelines — avoids unverifiable claims, uses safe phrasing like "helps reduce", "designed for", "suitable for".

*Example: "这是一款隔音泡棉，主要卖点是吸音好、安装简单、颜色好看，写 bullet points"*  
→ 5 compliant English bullet points.

---

## Console output

```
正在加载 Whisper 模型 (small)，首次运行会自动下载...
✓ Whisper 模型已就绪
✓ Claude 客户端已就绪

✓ 就绪。按住 [CAPS LOCK] 说话，Esc 退出。
✓ 当前模式：chat

🎙️  录音中... 停止
📝 [zh] 我叫 Hans，帮我翻译成英文  (1.2s)
🤖 [chat] My name is Hans.  (0.8s)
```

---

## Auto-start on login

1. Press `Win+R`, type `shell:startup`, press Enter.
2. Create a shortcut to `start.bat` in the folder that opens.

The tool will launch silently (no console window) every time you log in.  
To check if it's running: open Task Manager and look for `pythonw.exe`.

---

## Troubleshooting

### PowerShell shows "python is not recognized" or opens the Microsoft Store

Go to **Settings → Apps → Advanced app settings → App execution aliases** and toggle off both `python.exe` and `python3.exe`.

### `Activate.ps1` is blocked by execution policy

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### The program starts then immediately exits / Whisper crashes silently

Almost certainly caused by `hf-xet`. Run:

```powershell
.\venv\Scripts\Activate.ps1
pip uninstall hf-xet -y
python voice_input.py
```

### Laptop function keys (F9 etc.) don't work as hotkey

Most laptops require pressing `Fn+F9` to send the F9 keycode. Either hold `Fn` while using the hotkey, change it in BIOS to "F-key mode", or use a different key like `caps lock` or `right ctrl`.

### API error: "insufficient_quota" or "invalid_api_key"

Check your key and account balance at https://console.anthropic.com/

### Ctrl+V doesn't work as HOTKEY

The program uses `Ctrl+V` internally to paste results. Choose any other key.

### Nothing is pasted / paste goes to wrong window

The paste fires immediately after Claude responds. Make sure your target text field is still focused when you start speaking. For longer Claude responses (email drafting), you may need to click back into the field before releasing the key.

### Microphone not detected

Run `python -c "import sounddevice; print(sounddevice.query_devices())"` to list available devices. If your mic is not the default, you may need to set it as the default in Windows Sound settings.

---

## Roadmap

- System tray icon with mode indicator
- Audio feedback (beep on start/stop)
- Streaming transcription for long recordings
- Configurable output device per mode
- Linux / macOS support

---

## License

MIT — see [LICENSE](LICENSE).
