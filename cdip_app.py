"""
CDIP Wave Model Timelapse — Streamlit App
=========================================
Captures, stores, and animates the Scripps/CDIP Conception wave model.

Run locally:
    streamlit run cdip_app.py

Deploy free at:
    https://streamlit.io/cloud  (connect your GitHub repo)

Requirements:
    pip install streamlit requests Pillow schedule
"""

import os
import time
import threading
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw

# ── Configuration ──────────────────────────────────────────────────────────────
IMAGE_URL     = "https://cdip.ucsd.edu/recent/model_images/conception.png"
FRAMES_DIR    = Path("cdip_frames")
TARGET_FRAMES = 144       # 72 hours of data
FPS           = 15        # timelapse playback speed
INTERVAL_MIN  = 30        # capture interval (matches CDIP update cycle)
# ───────────────────────────────────────────────────────────────────────────────

FRAMES_DIR.mkdir(exist_ok=True)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CDIP Wave Timelapse",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — dark nautical theme ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&display=swap');

/* Base */
html, body, [class*="css"] {
    background-color: #080f1a;
    color: #c8d8e8;
    font-family: 'IBM Plex Mono', monospace;
}

/* Header */
.cdip-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
    border-bottom: 1px solid #1a3a5c;
    margin-bottom: 2rem;
}
.cdip-header h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.5rem;
    letter-spacing: 0.12em;
    color: #4fc3f7;
    margin: 0;
    text-shadow: 0 0 40px rgba(79,195,247,0.4);
}
.cdip-header p {
    color: #5a7a94;
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin: 0.3rem 0 0 0;
}

/* Stat cards */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
}
.stat-card {
    background: #0d1f33;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.stat-card .val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #4fc3f7;
    line-height: 1;
}
.stat-card .lbl {
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #5a7a94;
    margin-top: 0.3rem;
}

/* Section headers */
.section-label {
    font-size: 0.65rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #4fc3f7;
    border-bottom: 1px solid #1a3a5c;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

/* Status pill */
.status-active {
    display: inline-block;
    background: #0a2a1a;
    border: 1px solid #1a6640;
    color: #4caf82;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
}
.status-idle {
    display: inline-block;
    background: #1a1a0a;
    border: 1px solid #5a5a20;
    color: #a0a050;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0a1628 !important;
    border-right: 1px solid #1a3a5c;
}

/* Buttons */
.stButton > button {
    background: transparent;
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    border-radius: 4px;
    padding: 0.5rem 1.2rem;
    width: 100%;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #4fc3f7;
    color: #080f1a;
}

/* Progress bar */
.stProgress > div > div {
    background-color: #4fc3f7 !important;
}

/* Sliders */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background-color: #4fc3f7 !important;
}

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Password Protection ────────────────────────────────────────────────────────
APP_PASSWORD = "havefun"   # ← CHANGE THIS to your own password

def check_password():
    """Show a login screen and return True only if the correct password is entered."""

    # Already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    # Login page CSS
    st.markdown("""
    <style>
    .login-wrap {
        max-width: 420px;
        margin: 8rem auto 0 auto;
        background: #0d1f33;
        border: 1px solid #1a3a5c;
        border-radius: 10px;
        padding: 3rem 2.5rem;
        text-align: center;
    }
    .login-wrap h2 {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.4rem;
        color: #4fc3f7;
        letter-spacing: 0.12em;
        margin-bottom: 0.2rem;
        text-shadow: 0 0 30px rgba(79,195,247,0.4);
    }
    .login-wrap p {
        color: #5a7a94;
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-wrap">
        <h2>🌊 CDIP WAVE</h2>
        <p>Timelapse · Conception Point · CA</p>
    </div>
    """, unsafe_allow_html=True)

    # Centered password input
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", placeholder="Enter password...")
        if st.button("ENTER →", use_container_width=True):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — try again.")

    return False

# Gate the entire app behind the password check
if not check_password():
    st.stop()

# ── Helper functions ───────────────────────────────────────────────────────────

def get_frames() -> list:
    """Return sorted list of all captured frame paths."""
    return sorted(FRAMES_DIR.glob("conception_*.png"))


def parse_timestamp(path: Path) -> str:
    try:
        parts = path.stem.split("_")
        dt = datetime.strptime(parts[1] + parts[2], "%Y%m%d%H%M%S")
        return dt.strftime("%b %d %Y  %H:%M")
    except Exception:
        return path.stem


def capture_one_frame() -> tuple:
    """Download and save the current CDIP image. Returns (success, message)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = FRAMES_DIR / f"conception_{timestamp}.png"
    try:
        resp = requests.get(IMAGE_URL, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        img.save(filepath)
        return True, f"Captured → {filepath.name}"
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def build_gif(frames: list, fps: int = FPS) -> bytes:
    """Build an animated GIF from frames and return raw bytes."""
    duration_ms = int(1000 / fps)
    pil_frames  = []

    progress = st.progress(0, text="Building timelapse...")
    for i, fp in enumerate(frames):
        img  = Image.open(fp).convert("RGBA")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        label = parse_timestamp(fp)

        # Timestamp overlay — shadow + white
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            draw.text((w - 185 + dx, 8 + dy), label, fill=(0, 0, 0, 200))
        draw.text((w - 185, 8), label, fill=(255, 255, 255, 230))

        pil_frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
        progress.progress((i + 1) / len(frames), text=f"Building timelapse… {i+1}/{len(frames)}")

    buf = BytesIO()
    pil_frames[0].save(
        buf, format="GIF",
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    progress.empty()
    return buf.getvalue()


def background_capture_loop():
    """Runs in a daemon thread — captures every 30 min while app is open."""
    while st.session_state.get("capturing", False):
        capture_one_frame()
        # Sleep in 10s chunks so we can respond to stop signal quickly
        for _ in range(INTERVAL_MIN * 6):
            if not st.session_state.get("capturing", False):
                break
            time.sleep(10)


# ── Session state init ─────────────────────────────────────────────────────────
if "capturing"     not in st.session_state: st.session_state.capturing     = False
if "capture_thread" not in st.session_state: st.session_state.capture_thread = None
if "gif_bytes"     not in st.session_state: st.session_state.gif_bytes     = None
if "gif_frame_count" not in st.session_state: st.session_state.gif_frame_count = 0
if "last_capture"  not in st.session_state: st.session_state.last_capture  = "—"
if "log"           not in st.session_state: st.session_state.log           = []


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cdip-header">
    <h1>🌊 CDIP WAVE TIMELAPSE</h1>
    <p>Scripps Institution of Oceanography · Conception Point · Central California Coast</p>
</div>
""", unsafe_allow_html=True)


# ── Stat cards ────────────────────────────────────────────────────────────────
frames      = get_frames()
frame_count = len(frames)
data_hours  = frame_count * 0.5
pct_to_goal = min(frame_count / TARGET_FRAMES * 100, 100)
status_html = '<span class="status-active">● CAPTURING</span>' if st.session_state.capturing else '<span class="status-idle">○ IDLE</span>'

st.markdown(f"""
<div class="stat-grid">
    <div class="stat-card"><div class="val">{frame_count}</div><div class="lbl">Frames Captured</div></div>
    <div class="stat-card"><div class="val">{data_hours:.1f}</div><div class="lbl">Hours of Data</div></div>
    <div class="stat-card"><div class="val">{pct_to_goal:.0f}%</div><div class="lbl">To 72hr Goal</div></div>
    <div class="stat-card"><div class="val">{FPS}</div><div class="lbl">Playback FPS</div></div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar — Controls ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label">📡 Capture Control</div>', unsafe_allow_html=True)
    st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)
    st.markdown(f"<small style='color:#5a7a94'>Last capture: {st.session_state.last_capture}</small>", unsafe_allow_html=True)
    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ START", disabled=st.session_state.capturing):
            st.session_state.capturing = True
            t = threading.Thread(target=background_capture_loop, daemon=True)
            t.start()
            st.session_state.capture_thread = t
            st.session_state.log.insert(0, f"{datetime.now().strftime('%H:%M:%S')} — Capture started")
            st.rerun()

    with col2:
        if st.button("■ STOP", disabled=not st.session_state.capturing):
            st.session_state.capturing = False
            st.session_state.log.insert(0, f"{datetime.now().strftime('%H:%M:%S')} — Capture stopped")
            st.rerun()

    if st.button("📸 CAPTURE NOW"):
        with st.spinner("Fetching image..."):
            ok, msg = capture_one_frame()
        ts = datetime.now().strftime("%H:%M:%S")
        st.session_state.last_capture = datetime.now().strftime("%b %d  %H:%M")
        st.session_state.log.insert(0, f"{ts} — {msg}")
        if ok:
            st.success("Frame captured!")
        else:
            st.error(msg)
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-label">🎬 Timelapse Settings</div>', unsafe_allow_html=True)

    fps_choice    = st.slider("Playback FPS", 1, 30, FPS)
    frames_choice = st.slider("Frames to include", 10, max(TARGET_FRAMES, frame_count), min(TARGET_FRAMES, frame_count))

    st.markdown("---")
    st.markdown('<div class="section-label">ℹ️ Info</div>', unsafe_allow_html=True)
    st.markdown(f"""
<small style='color:#5a7a94; line-height:1.8'>
📍 Conception Point, CA<br>
🔄 CDIP updates every 30 min<br>
🎯 Target: 144 frames (72 hrs)<br>
⏱ At {fps_choice}fps: {frames_choice/fps_choice:.1f}s timelapse<br>
🔗 cdip.ucsd.edu
</small>
""", unsafe_allow_html=True)


# ── Main content ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🗺 Live Image", "🎬 Timelapse", "📋 Capture Log"])

# ── Tab 1: Live current image ─────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-label">Current Wave Model</div>', unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 1])
    with col_img:
        if st.button("🔄 Refresh Live Image"):
            st.rerun()
        try:
            resp = requests.get(IMAGE_URL, timeout=10)
            resp.raise_for_status()
            live_img = Image.open(BytesIO(resp.content))
            st.image(live_img, caption=f"Live — {datetime.now().strftime('%b %d %Y  %H:%M')}", use_container_width=True)
        except Exception as e:
            st.error(f"Could not load live image: {e}")

    with col_info:
        st.markdown("""
<div style='padding: 1.5rem; background: #0d1f33; border: 1px solid #1a3a5c; border-radius: 6px; font-size: 0.8rem; line-height: 2'>
<div class="section-label">How to Read This Map</div>
<b style='color:#4fc3f7'>Hs (ft)</b> — Significant wave height<br>
<b style='color:#4fc3f7'>Tp (s)</b> — Peak period in seconds<br>
<b style='color:#4fc3f7'>Dp (°)</b> — Peak direction in degrees<br>
<b style='color:#4fc3f7'>N. Pac</b> — North Pacific swell source<br>
<b style='color:#4fc3f7'>S. Pac</b> — South Pacific swell source<br><br>
<div class="section-label">Color Scale</div>
Black → Blue → Green → Yellow → Red<br>
<span style='color:#5a7a94'>0 ft &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 9+ ft</span><br><br>
<div class="section-label">Frequency Rings</div>
Inner ring (0.12 Hz) = short period swell<br>
Outer ring (0.04 Hz) = long period swell<br>
</div>
""", unsafe_allow_html=True)


# ── Tab 2: Timelapse ──────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-label">72-Hour Wave Timelapse</div>', unsafe_allow_html=True)

    if frame_count == 0:
        st.info("No frames captured yet. Use the sidebar to start capturing or grab a single frame with **CAPTURE NOW**.")
    else:
        frames_to_use = get_frames()
        if len(frames_to_use) > frames_choice:
            frames_to_use = frames_to_use[-frames_choice:]

        col_build, col_dl = st.columns([2, 1])
        with col_build:
            if st.button(f"⚙ BUILD TIMELAPSE  ({len(frames_to_use)} frames @ {fps_choice}fps)"):
                with st.spinner("Rendering GIF..."):
                    gif_data = build_gif(frames_to_use, fps_choice)
                st.session_state.gif_bytes       = gif_data
                st.session_state.gif_frame_count = len(frames_to_use)
                st.success(f"Timelapse built! {len(frames_to_use)} frames · {len(frames_to_use)/fps_choice:.1f}s · {len(gif_data)//1024} KB")

        if st.session_state.gif_bytes:
            with col_dl:
                st.download_button(
                    label="⬇ DOWNLOAD GIF",
                    data=st.session_state.gif_bytes,
                    file_name=f"cdip_timelapse_{datetime.now().strftime('%Y%m%d_%H%M')}.gif",
                    mime="image/gif",
                )

            st.markdown("")
            st.image(
                st.session_state.gif_bytes,
                caption=f"Timelapse · {st.session_state.gif_frame_count} frames · {fps_choice}fps",
                use_container_width=False,
            )

        # Frame browser
        st.markdown("---")
        st.markdown('<div class="section-label">Browse Individual Frames</div>', unsafe_allow_html=True)
        if frame_count > 0:
            all_frames = get_frames()
            frame_idx  = st.slider("Frame", 0, len(all_frames) - 1, len(all_frames) - 1)
            selected   = all_frames[frame_idx]
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.image(str(selected), caption=parse_timestamp(selected), use_container_width=True)
            with col_b:
                st.markdown(f"""
<div style='padding: 1rem; background: #0d1f33; border: 1px solid #1a3a5c; border-radius: 6px; font-size: 0.8rem; line-height:2'>
<b>Frame</b>: {frame_idx + 1} of {frame_count}<br>
<b>Timestamp</b>: {parse_timestamp(selected)}<br>
<b>File</b>: {selected.name}<br>
<b>Size</b>: {selected.stat().st_size // 1024} KB
</div>
""", unsafe_allow_html=True)


# ── Tab 3: Capture log ────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-label">Capture Activity Log</div>', unsafe_allow_html=True)

    col_prog, col_clear = st.columns([3, 1])
    with col_prog:
        st.progress(pct_to_goal / 100, text=f"{frame_count} / {TARGET_FRAMES} frames  ({pct_to_goal:.0f}% to 72-hr goal)")
    with col_clear:
        if st.button("🗑 CLEAR LOG"):
            st.session_state.log = []
            st.rerun()

    if st.session_state.log:
        log_text = "\n".join(st.session_state.log[:50])
        st.code(log_text, language=None)
    else:
        st.markdown("<small style='color:#5a7a94'>No activity yet.</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-label">Saved Frames on Disk</div>', unsafe_allow_html=True)

    if frame_count > 0:
        all_frames = get_frames()
        frame_data = [
            {
                "Filename": f.name,
                "Timestamp": parse_timestamp(f),
                "Size (KB)": f.stat().st_size // 1024,
            }
            for f in reversed(all_frames[-20:])  # show last 20
        ]
        st.dataframe(frame_data, use_container_width=True, hide_index=True)
        if frame_count > 20:
            st.caption(f"Showing 20 most recent of {frame_count} total frames.")
    else:
        st.markdown("<small style='color:#5a7a94'>No frames on disk yet.</small>", unsafe_allow_html=True)
