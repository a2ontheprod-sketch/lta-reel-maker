# LTA REEL MAKER v1.0 — Windows App + FL Studio Master Capture VST3

## What you're getting

**LTA Reel Maker** is a Windows desktop reel creator with a simple black-and-pink UI, 300 visual styles, live previews and MP4 exports. An optional **LTA Reel Capture** VST3 sits on your FL Studio Master and records the stereo master to a WAV file that the app can import.

### Currently implemented
- 300 labelled selectable visual styles, made from **25 different animation/rendering engines × 12 visual art directions**. This is 300 looks, not 300 independently coded rendering algorithms. No network or downloaded graphics needed.
- Exact note-based animations when you **import a real MIDI file**. Piano rolls, note grids, bass tracks, chord lines, falling notes and more. The app never invents exact notes from the Master audio.
- Audio-driven visualisers using measured low/mid/high energy, loudness and onset activity.
- Beat import: WAV, MP3, FLAC, M4A (via bundled FFmpeg).
- FL Studio Master VST3: captures transparent stereo 24-bit WAV in the background with a buffered writer, without applying audio effects.
- Import a screen image or recording; **Arrangement Scan** uses that image/recording as an animated backdrop. Windows screen recording uses FFmpeg desktop capture. The screen clip and Master capture must be lined up by the user; no automatic timecode sync yet.
- Search, family filtering, favourites (persisted), Surprise Me, custom producer title.
- Reel start selection and 15/30/60-second clip lengths (or remaining song duration if shorter).
- Export 1080×1920, 1080×1080 or 1920×1080 H.264/AAC MP4 with the actual beat audio synced from the source file.
- Original built-in demo WAV + MIDI so the app works before you import your own beat.

### NOT implemented yet / honest limitations
- A standard Master VST cannot see exact MIDI notes, chords, drum patterns, track names or Playlist objects from other FL Studio tracks. **Use a .mid export for accurate note animation.** A finished stereo beat can supply only estimated audio energy and transients.
- The VST3 itself captures **audio only**. The desktop app performs screen capture, rendering and export.
- No automatic note transcription or stem separation; no guaranteed kick/snare/hat isolation.
- Screen recording can be incorporated as an arrangement background, but doesn't automatically align to DAW timeline without further work.
- This source has been tested with Python GUI and MP4 exports in a Linux environment. **The Windows EXE and JUCE VST3 have NOT been compiled/tested on a Windows runner in this session.** GitHub Actions must confirm both builds. Release candidate, not a guarantee of a flawless product.

## GitHub: build online without a Windows compiler on your PC

1. Extract the downloaded `LTA_REEL_MAKER_GITHUB_SOURCE.zip`.
2. Create a new **empty** GitHub repository named `lta-reel-maker` (at https://github.com/new).
3. Upload the repository contents: the `Desktop`, `Plugin`, `tests`, `.github` folders, `requirements.txt`, `README_START_HERE.md`, and `run_windows.bat`. Commit files.
4. **Important:** GitHub's browser upload may skip the hidden `.github` folder! Check that `.github/workflows/build-windows.yml` exists in your repository.
5. If missing: GitHub **Add file → Create new file**; enter exactly `.github/workflows/build-windows.yml`; paste the contents of the included `GITHUB_WORKFLOW_COPY_PASTE.yml` and click **Commit changes**.
6. Open **Actions → Build LTA Reel Maker - App and VST3 → Run workflow**. Two jobs build independently:
   - `Build Windows Reel Maker EXE` → `LTA-Reel-Maker-Windows-App` artifact.
   - `Build FL Studio Master Capture VST3` → `LTA-Reel-Capture-Master-VST3` artifact.
7. Download and extract the two artifacts. The app artifact contains `LTA-Reel-Maker.exe` (double-click). The VST artifact contains a ZIP, which you extract to find the complete `LTA Reel Capture.vst3` folder.
8. Copy **the whole `.vst3` folder** into `C:\Program Files\Common Files\VST3` (admin permissions may be needed). In FL Studio go to **Options → Manage plugins → Find installed plugins**.

### Desktop app even if GitHub VST build fails

The independent GitHub **desktop-app** job still gives you the executable if the VST job fails. You can immediately import WAV or MP3 and MIDI and export videos. You can also run source directly on Windows: install Python 3.12, then double-click `run_windows.bat`.

## Everyday workflow

1. In FL Studio, put **LTA Reel Capture** near the **end of the Master FX chain**. Press **REC** in that plugin, play the section you want, then press **STOP**. WAVs appear in `Documents\LTA Reel Maker\Captures`.
2. Open **LTA-Reel-Maker.exe**. Click the big circle under CAPTURE to load the latest completed capture, or use **+ AUDIO** to choose any beat directly.
3. **Optional for exact note visuals:** Export a MIDI file from FL Studio (File → Export → MIDI file, when available, or use a pattern's MIDI export), click **+ MIDI**, and choose it. MIDI timing should line up with the beginning of the audio you import. If the beat was recorded starting in the middle of a song, MIDI note positions may need adjustment at source.
4. **Optional screen content:** Use **+ SCREEN** to select an FL Studio screenshot or an existing screen recording. Or click **REC SCREEN** and switch to FL Studio; click the button again to stop recording. Screen frames feed the Arrangement Scan family.
5. Browse visualisers, use favourites (small ♡ on style tiles), search, category filters or Surprise Me.
6. Use **CLIP START** for the section you want and 15s, 30s or 60s. Use Play to preview where supported.
7. Select 9:16 / 1:1 / 16:9 and click **EXPORT REEL**. Choose a destination. Your MP4 contains the original beat audio, no added interface sound effects.

## Technical design

- `Desktop/app.py`: Tkinter desktop UI with beat preview and style picker.
- `Desktop/visualisers.py`: 25 different drawing algorithms and 12 distinct art directions, available as 300 selectable looks.
- `Desktop/core.py`: FFmpeg decoding, energy analysis, MIDI parsing, screen recording, captured clips.
- `Desktop/exporter.py`: streaming H.264 MP4 exporter through FFmpeg; render frames match preview.
- `Desktop/demo.py`: makes an original test beat + corresponding MIDI.
- `Plugin/`: JUCE 8 VST3 plugin; transparently passes audio while recording WAV to Documents using a threaded disk writer.
- `.github/workflows/build-windows.yml`: builds EXE and VST3 in parallel on Windows 2022.
- `tests/`: audio/MIDI, 25 visualiser families and MP4 export tests.

## Copyright and privacy

- The app processes local media, no cloud uploads or accounts. Screen recordings may contain personal windows, so review before posting.
- Only export and post content you have the right to share.
- JUCE has its own licences; before commercial distribution of a JUCE-based VST, confirm compliance with the JUCE licence terms.

## If GitHub shows a red cross

Open the failed job, expand the first red step, and send its full error log. Don't change unrelated files. The two build jobs are independent, so you may still have a working app artifact while resolving VST compiler errors.
