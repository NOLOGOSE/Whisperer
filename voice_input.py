"""Voice input assistant: push-to-talk → Whisper → Claude → paste."""

import os
import sys
import time
import threading

import numpy as np
import sounddevice as sd
import pyperclip
import pyautogui
import keyboard
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WHISPER_MODEL     = os.getenv("WHISPER_MODEL", "small")
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
HOTKEY            = os.getenv("HOTKEY", "caps lock")

SAMPLE_RATE  = 16000
CHANNELS     = 1
MIN_DURATION = 0.3  # seconds; shorter clips are silently discarded

# Raw triple-quoted strings avoid any backslash-escape issues in prompts.
PROMPTS = {
    "chat": r"""你是语音输入处理助手，用户在做日常聊天输入。

判断用户输入属于哪类：

A) 完整内容 + 编辑指令（如"...翻译成英文"、"...改正式点"、"...去掉最后一句"）
   → 对已有内容执行指令，特别注意"翻译"指令必须真的翻译为目标语言

B) 表达意图 + 写作指令（如"帮我写..."、"告诉 XX..."、"回复..."、"扩写..."、"续写..."）
   → 根据用户大意，写出完整、自然、可直接发送的聊天文本

C) 纯口述内容（无任何指令）
   → 修正标点错字，保持口语化

只输出最终文本，不要解释、引号或前后缀。""",

    "email": r"""你是邮件写作助手。

判断用户输入：

A) 完整邮件内容 + 编辑指令 → 按指令处理，"翻译"必须真翻译
B) 邮件大意/要点（"帮我写邮件告诉..."、"回复客户说..."、"通知供应商..."）
   → 根据要点写出完整、得体、专业的邮件正文（不写收件人/主题）
C) 纯口述邮件内容 → 转为得体书面语

只输出邮件正文，不要解释。""",

    "listing": r"""你是亚马逊产品文案助手。

判断用户输入：

A) 完整文案 + 编辑指令 → 按指令处理
B) 产品要点（"这是一款...帮我写产品描述"、"主要卖点是...写 bullet points"）
   → 根据要点写出合规英文 Listing 文案
C) 纯口述文案 → 合规化处理

避免绝对化或不可证实用语（如"100%"、"certified"、"NRC 0.92"、"soundproof"）。
用安全表达："helps reduce"、"designed for"、"supports"、"suitable for"。

只输出最终文案。""",
}

MODE_NAMES = ["chat", "email", "listing"]
current_mode_index = 0

# ── Recording state ───────────────────────────────────────────────────────────
# recording_lock is held for the entire duration of one recording session,
# preventing re-entrant or concurrent recordings.
recording_lock  = threading.Lock()
is_recording    = False
audio_frames: list = []
recording_start = 0.0
current_stream  = None

whisper_model = None
claude_client = None


# ── Model loading ─────────────────────────────────────────────────────────────

def load_models() -> None:
    global whisper_model, claude_client

    print(f"正在加载 Whisper 模型 ({WHISPER_MODEL})，首次运行会自动下载...")
    try:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("✓ Whisper 模型已就绪")
    except Exception as exc:
        print(f"✗ Whisper 加载失败: {exc}")
        sys.exit(1)

    try:
        import anthropic
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print("✓ Claude 客户端已就绪")
    except Exception as exc:
        print(f"✗ Claude 初始化失败: {exc}")
        sys.exit(1)


# ── Recording ─────────────────────────────────────────────────────────────────

def start_recording() -> None:
    global is_recording, audio_frames, recording_start, current_stream

    if not recording_lock.acquire(blocking=False):
        return  # another session is already running

    is_recording    = True
    audio_frames    = []
    recording_start = time.time()
    print("\n🎙️  录音中...", end=" ", flush=True)

    def _cb(indata, frames, time_info, status):
        if is_recording:
            audio_frames.append(indata.copy())

    try:
        current_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=_cb,
        )
        current_stream.start()
    except Exception as exc:
        print(f"\n✗ 录音启动失败: {exc}")
        is_recording   = False
        current_stream = None
        recording_lock.release()


def stop_recording() -> None:
    global is_recording, current_stream

    if not is_recording:
        return

    is_recording = False  # signal callback to stop appending
    duration     = time.time() - recording_start
    print("停止")

    try:
        if current_stream is not None:
            current_stream.stop()   # blocks until callback finishes
            current_stream.close()
    except Exception as exc:
        print(f"✗ 停止录音失败: {exc}")
    finally:
        current_stream  = None
        frames_snapshot = list(audio_frames)
        recording_lock.release()

    if duration < MIN_DURATION or not frames_snapshot:
        return  # silently discard accidental taps

    audio = np.concatenate(frames_snapshot, axis=0).flatten()
    threading.Thread(target=process_audio, args=(audio, duration), daemon=True).start()


# ── Processing pipeline ───────────────────────────────────────────────────────

def process_audio(audio: np.ndarray, duration: float) -> None:
    # 1. Transcribe
    t0 = time.time()
    try:
        segments, info = whisper_model.transcribe(audio, beam_size=5, language=None)
        lang       = info.language
        transcript = " ".join(seg.text for seg in segments).strip()
        t_trans    = time.time() - t0
    except Exception as exc:
        print(f"✗ 转写失败: {exc}")
        return

    if not transcript:
        return  # nothing heard — silent skip

    print(f"📝 [{lang}] {transcript}  ({t_trans:.1f}s)")

    # 2. Claude post-processing
    mode   = MODE_NAMES[current_mode_index]
    prompt = PROMPTS[mode]
    t1     = time.time()
    try:
        msg    = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=prompt,
            messages=[{"role": "user", "content": transcript}],
        )
        result   = msg.content[0].text.strip()
        t_claude = time.time() - t1
    except Exception as exc:
        print(f"✗ Claude 处理失败: {exc}")
        return

    print(f"🤖 [{mode}] {result}  ({t_claude:.1f}s)")

    # 3. Write to clipboard
    try:
        pyperclip.copy(result)
    except Exception as exc:
        print(f"✗ 写入剪贴板失败: {exc}")
        return

    # 4. Simulate Ctrl+V into the currently focused window
    try:
        time.sleep(0.15)  # give clipboard time to settle
        pyautogui.hotkey("ctrl", "v")
    except Exception as exc:
        print(f"✗ 模拟粘贴失败: {exc}")


# ── Hotkey setup ──────────────────────────────────────────────────────────────

def setup_hotkeys() -> None:
    hotkey = HOTKEY.lower().strip()

    if "+" in hotkey:
        # Combo key (e.g. ctrl+alt+space): add_hotkey fires on press;
        # poll keyboard.is_pressed on the last key to detect release.
        last_key = hotkey.split("+")[-1].strip()

        def on_combo():
            start_recording()

            def _poll_release():
                time.sleep(0.05)  # brief grace period before polling
                while keyboard.is_pressed(last_key):
                    time.sleep(0.05)
                stop_recording()

            threading.Thread(target=_poll_release, daemon=True).start()

        keyboard.add_hotkey(hotkey, on_combo, suppress=False)
    else:
        # Single key (e.g. caps lock, right ctrl, f9):
        # on_press_key may fire repeatedly due to key-repeat; the lock
        # inside start_recording() makes repeated presses a no-op.
        keyboard.on_press_key(hotkey, lambda _: start_recording(), suppress=False)
        keyboard.on_release_key(hotkey, lambda _: stop_recording(), suppress=False)

    # Mode switching
    keyboard.add_hotkey("ctrl+alt+1", lambda: switch_mode(0), suppress=False)
    keyboard.add_hotkey("ctrl+alt+2", lambda: switch_mode(1), suppress=False)
    keyboard.add_hotkey("ctrl+alt+3", lambda: switch_mode(2), suppress=False)


def switch_mode(index: int) -> None:
    global current_mode_index
    current_mode_index = index
    print(f"\n✓ 当前模式：{MODE_NAMES[index]}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    load_models()
    setup_hotkeys()

    hotkey_display = HOTKEY.upper()
    print(f"\n✓ 就绪。按住 [{hotkey_display}] 说话，Esc 退出。")
    print(f"✓ 当前模式：{MODE_NAMES[current_mode_index]}")

    try:
        keyboard.wait("esc")
    except KeyboardInterrupt:
        pass

    print("\n再见！")


if __name__ == "__main__":
    main()
