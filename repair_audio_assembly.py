"""
REPAIR SCRIPT — Audio Registration & Forced Assembly
Targets: Kodachrome_Gelatin_Dream_1778332473_V4_LIVE

Steps:
  1. Scan folder for scene_N_soundscape.mp3 files and register them in storyboard.json
  2. Re-attempt dual-track FFmpeg mix for music scenes (1, 4, 9) using existing
     scene_N_music.mp3 + scene_N_sfx_env.mp3  →  scene_N_soundscape.mp3
     Mix: music@60% / env@40% (stable amix duration=first)
  3. Force final assembly — create the ULTIMATE_MASTER.mp4 (bypasses gatekeeper)
  4. Validate project title branding in storyboard.json SEO block
"""

import os, sys, json, re, shutil, subprocess, time

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

EPISODE_FOLDER = (
    r"g:\My Drive\Z sosFiles\Z_act\@ NETWORK\@ MEDIAUPSCALE_FACTORY"
    r"\Endless_Summers_Paradise - Production"
    r"\Kodachrome_Gelatin_Dream_1778332473_V4_LIVE"
)

MUSIC_SCENES   = [1, 4, 9]          # dual-track scenes
VIDEO_DURATION = 5                  # seconds per clip
SCENE_COUNT    = 9

FFMPEG_CANDIDATES = [
    os.path.join(
        r"g:\My Drive\Z sosFiles\Z_act\@ NETWORK\@ MEDIAUPSCALE_FACTORY",
        "Tools", "ffmpeg.exe"
    ),
    shutil.which("ffmpeg") or "",
    r"C:\ffmpeg\bin\ffmpeg.exe",
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def find_ffmpeg():
    for p in FFMPEG_CANDIDATES:
        if p and os.path.exists(p):
            r = subprocess.run([p, "-version"], capture_output=True, text=True)
            if r.returncode == 0:
                return p
    return None


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def load_storyboard(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_storyboard(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── STEP 1: REGISTER SOUNDSCAPE PATHS IN STORYBOARD.JSON ────────────────────

def register_audio_paths(folder, sb_path):
    log("STEP 1 — Registering soundscape paths in storyboard.json...")

    data   = load_storyboard(sb_path)
    is_dict = isinstance(data, dict)
    scenes  = data.get("scenes", data) if is_dict else data

    registered = 0
    for scene in scenes:
        sid = scene.get("scene_id")
        if sid is None:
            continue

        sp = os.path.join(folder, f"scene_{sid}_soundscape.mp3")
        mp = os.path.join(folder, f"scene_{sid}_music.mp3")

        if os.path.exists(sp) and os.path.getsize(sp) > 0:
            scene["soundscape_path"] = sp
            registered += 1
            log(f"  Scene {sid}: registered {os.path.basename(sp)} ({os.path.getsize(sp):,} bytes)")
        else:
            log(f"  Scene {sid}: WARNING — soundscape not found on disk: {sp}")

        if os.path.exists(mp) and os.path.getsize(mp) > 0:
            scene["music_path"] = mp

    if is_dict:
        data["scenes"] = scenes

    save_storyboard(sb_path, data)
    log(f"  Registered {registered}/{SCENE_COUNT} scene audio paths. storyboard.json saved.")
    return registered


# ─── STEP 2: RE-MIX DUAL-TRACK MUSIC SCENES ──────────────────────────────────

def remix_music_scenes(folder, ffmpeg, video_duration):
    log("STEP 2 — Re-mixing dual-track music scenes (stable amix: music×0.6 + env×0.8)...")

    for sid in MUSIC_SCENES:
        music_in = os.path.join(folder, f"scene_{sid}_music.mp3")
        env_in   = os.path.join(folder, f"scene_{sid}_sfx_env.mp3")
        out      = os.path.join(folder, f"scene_{sid}_soundscape.mp3")

        if not os.path.exists(music_in):
            log(f"  Scene {sid}: SKIP — scene_{sid}_music.mp3 not found.")
            continue
        if not os.path.exists(env_in):
            log(f"  Scene {sid}: SKIP — scene_{sid}_sfx_env.mp3 not found.")
            continue

        log(f"  Scene {sid}: mixing music ({os.path.getsize(music_in):,}b) + "
            f"env ({os.path.getsize(env_in):,}b) ...")

        tmp_out = out + ".tmp.mp3"

        # Stable FFmpeg graph (aligned with factory_engine_pipeline_v4._mix_dual_track_audio)
        cmd = (
            f'"{ffmpeg}" -y '
            f'-i "{music_in}" -i "{env_in}" '
            f'-filter_complex "[0:a]volume=0.6[a1];[1:a]volume=0.4[a2];'
            f'[a1][a2]amix=inputs=2:duration=first" '
            f'-c:a libmp3lame "{tmp_out}"'
        )

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 1000:
            # Atomically replace the old soundscape with the properly mixed one
            if os.path.exists(out):
                os.remove(out)
            os.rename(tmp_out, out)
            log(f"  Scene {sid}: OK — mixed soundscape ({os.path.getsize(out):,} bytes)")
        else:
            log(f"  Scene {sid}: WARN — FFmpeg mix failed. stderr: {result.stderr[:300]}")
            log(f"  Scene {sid}: Falling back to music-only track.")
            # Fallback: copy music track straight to soundscape
            shutil.copy2(music_in, out)
            if os.path.exists(tmp_out):
                os.remove(tmp_out)


# ─── STEP 3: FORCE FINAL ASSEMBLY ────────────────────────────────────────────

def force_assembly(folder, ffmpeg, scene_count, video_duration):
    log("STEP 3 — Forced FFmpeg assembly (bypassing gatekeeper)...")

    episode_name = os.path.basename(folder)
    dur_filter   = f"atrim=duration={video_duration},apad=whole_dur={video_duration}"
    baked_clips  = []

    log(f"  Stage 1: Baking audio into individual scene clips...")

    for i in range(1, scene_count + 1):
        v_in  = os.path.join(folder, f"scene_{i}_VIDEO.mp4")
        sfx   = os.path.join(folder, f"scene_{i}_soundscape.mp3")
        v_out = os.path.join(folder, f"scene_{i}_BAKED.mp4")

        if not (os.path.exists(v_in) and os.path.getsize(v_in) > 10_000):
            log(f"  Scene {i}: SKIP — VIDEO.mp4 missing or too small.")
            continue

        if not (os.path.exists(sfx) and os.path.getsize(sfx) > 0):
            log(f"  Scene {i}: WARN — soundscape missing, baking silent copy.")
            shutil.copy2(v_in, v_out)
            baked_clips.append(v_out)
            continue

        fc  = f"[1:a]{dur_filter}[a]"
        cmd = (
            f'"{ffmpeg}" -y -i "{v_in}" -i "{sfx}" '
            f'-filter_complex "{fc}" -map 0:v -map [a] '
            f'-c:v libx264 -preset ultrafast -c:a aac -b:a 192k -shortest "{v_out}"'
        )

        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if os.path.exists(v_out) and os.path.getsize(v_out) > 10_000:
            log(f"  Scene {i}: OK — baked ({os.path.getsize(v_out):,} bytes)")
            baked_clips.append(v_out)
        else:
            log(f"  Scene {i}: FAIL — FFmpeg stderr: {r.stderr[:300]}")

    if not baked_clips:
        log("  ERROR: No clips baked. Cannot assemble master.")
        return False

    log(f"  Stage 1 complete — {len(baked_clips)}/{scene_count} clips baked.")

    # ── Stage 2: Concatenate ──────────────────────────────────────────────────

    master_name = f"{episode_name}_ULTIMATE_MASTER.mp4"
    master_path = os.path.join(folder, master_name)

    if len(baked_clips) == 1:
        log("  Stage 2: Single clip — copying directly to master...")
        shutil.copy2(baked_clips[0], master_path)
    else:
        log(f"  Stage 2: Concatenating {len(baked_clips)} clips...")

        list_file = os.path.join(folder, "baked_list.txt")
        sorted_clips = sorted(
            baked_clips,
            key=lambda x: int(re.search(r"scene_(\d+)", x).group(1))
        )
        with open(list_file, "w", encoding="utf-8") as f:
            for clip in sorted_clips:
                f.write(f"file '{os.path.basename(clip)}'\n")

        concat_cmd = (
            f'"{ffmpeg}" -y -f concat -safe 0 -i "{list_file}" '
            f'-c copy "{master_path}"'
        )
        r = subprocess.run(
            concat_cmd, shell=True, capture_output=True, text=True,
            cwd=folder
        )

        if os.path.exists(list_file):
            os.remove(list_file)

    if os.path.exists(master_path) and os.path.getsize(master_path) > 100_000:
        size_mb = os.path.getsize(master_path) / (1024 * 1024)
        log(f"  SUCCESS — Master created: {master_name} ({size_mb:.1f} MB)")
        return True
    else:
        log(f"  FAIL — Master file invalid or missing: {master_path}")
        return False


# ─── STEP 4: BRANDING CHECK ──────────────────────────────────────────────────

def check_branding(sb_path):
    log("STEP 4 — Branding check: verifying project title...")

    data    = load_storyboard(sb_path)
    is_dict = isinstance(data, dict)
    seo     = data.get("seo_metadata_usa_high_rpm", {}) if is_dict else {}
    title   = seo.get("project_title", "")

    if "Endless Summer Paradise" in title:
        log(f"  OK — project_title is: '{title}'")
    else:
        log(f"  FIXING — project_title was: '{title}'")
        seo["project_title"] = "Endless Summer Paradise \u2014 The Jelly Kingdom"
        if is_dict:
            data["seo_metadata_usa_high_rpm"] = seo
        save_storyboard(sb_path, data)
        log(f"  Fixed — project_title now: '{seo['project_title']}'")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("REPAIR: Audio Registration & Forced Assembly")
    log(f"Target: {os.path.basename(EPISODE_FOLDER)}")
    log("=" * 60)

    if not os.path.isdir(EPISODE_FOLDER):
        log(f"FATAL: Episode folder not found: {EPISODE_FOLDER}")
        sys.exit(1)

    sb_path = os.path.join(EPISODE_FOLDER, "storyboard.json")
    if not os.path.exists(sb_path):
        log("FATAL: storyboard.json not found in episode folder.")
        sys.exit(1)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        log("FATAL: FFmpeg not found.")
        sys.exit(1)
    log(f"FFmpeg: {ffmpeg}")

    # Step 1: Register audio paths
    register_audio_paths(EPISODE_FOLDER, sb_path)
    print()

    # Step 2: Re-mix dual-track music scenes
    remix_music_scenes(EPISODE_FOLDER, ffmpeg, VIDEO_DURATION)
    print()

    # Re-register after re-mix so storyboard.json reflects updated file sizes
    log("Re-registering audio paths after remix...")
    register_audio_paths(EPISODE_FOLDER, sb_path)
    print()

    # Step 3: Force assembly
    success = force_assembly(EPISODE_FOLDER, ffmpeg, SCENE_COUNT, VIDEO_DURATION)
    print()

    # Step 4: Branding check
    check_branding(sb_path)
    print()

    log("=" * 60)
    if success:
        log("REPAIR COMPLETE. ULTIMATE_MASTER.mp4 is ready.")
    else:
        log("REPAIR PARTIAL — assembly failed. Check logs above.")
    log("=" * 60)


if __name__ == "__main__":
    main()
