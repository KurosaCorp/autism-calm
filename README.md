# Autism Calm

A minimalist desktop app that helps autistic people and people with ADHD
calm down and focus. Mix ambient sounds (rain, brown noise, a cat purring, a
ticking clock and more) into your own soundscape, and watch slow, glowing
lights drift through a soft tunnel.

Built with **Python + PySide6 (Qt)** for the UI and visuals (Qt's built-in
OpenGL support, no extra graphics library) and **sounddevice + soundfile +
numpy** for audio.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\download_assets.py
.venv\Scripts\python.exe main.py
```

macOS / Linux:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_assets.py
python main.py
```

## App logo

Put the logo at **`assets/logo.jpg`** (next to the `audio` folder). It
becomes the window and taskbar icon. Non-square images are centred rather than
stretched. To use another file or format (.png, .ico, .svg), change
`LOGO_PATH` in `calm/config.py`. Without a logo, the app uses the default icon.

## Using the mixer

- Every sound has its own **Play/Pause** button and **volume slider**. Mix as
  many as you like. Sound keeps playing on every tab.
- **Stop all sound** (top right) or the **Esc** key silences everything at
  once, from any tab. Use it if things become too much.
- Play, pause and volume changes fade gently instead of jumping.

## The Visuals tab

Soft, out-of-focus lights float out of a dim central glow and drift towards
you in a slow 3D tunnel, with faint light rays turning behind them, on a
pitch-black background. Colours shift slowly through soft green, calm blue,
deep purple and gentle yellow (one full cycle takes 90 seconds).

- **Speed** slider: from 0.05× (almost still) to 2×. Speed changes glide
  rather than jump.
- **Pause**: the lights slow down over a few seconds and then stop
  completely. Sound keeps playing. **Resume** starts them gently again.
- There's no flashing, strobing or sudden movement. Each light fades in from
  the distance and fades out before it gets close, and at top speed no light
  changes brightness by more than about 1% per frame.

The animation only runs while the Visuals tab is open.

## Your sounds folder

The app keeps your sound library in your personal app-data folder, not next
to the program or in Documents:

| OS | Sounds folder |
|---|---|
| Windows | `%LOCALAPPDATA%\AutismCalm\Sounds` (e.g. `C:\Users\you\AppData\Local\AutismCalm\Sounds`) |
| macOS | `~/Library/Application Support/AutismCalm/Sounds` |
| Linux | `~/.local/share/AutismCalm/Sounds` |

On first start, the app copies the starter pack into this folder. After that
the folder is yours: the app never overwrites it. If you empty it completely,
the starter pack is copied back on the next start. Logs go to the `Logs`
folder next to it.

### Adding your own sounds (no coding needed)

1. Click **Open sounds folder** in the app.
2. Drop in `.wav`, `.ogg`, `.flac`, `.mp3` or `.aiff` files. Put them in a
   sub-folder (for example `Nature/`) to group them under that heading.
3. Restart the app. Each file gets its own row, named after the file:
   `forest_birds.ogg` shows as "Forest birds".

Files that can't be read are skipped (the reason is written to the log).
To remove a sound, delete its file.

## The starter pack

`scripts/download_assets.py` downloads 15 free recordings from Wikimedia
Commons and generates 1 sound locally:

| Category | Sounds |
|---|---|
| Noise | Brown noise, Pink noise, White noise |
| Nature | Heavy rain, Light rain, Thunder, Wind, Ocean waves, Fire crackling |
| Ambient | Airplane cabin (generated), Train ride, Deep space hum, Box fan |
| Rhythmic | Cat purring, Heartbeat, Clock ticking |

- If a download fails (offline, or Wikimedia asks scripts to slow down), a
  generated stand-in is created so the app always works. Run the script again
  later to replace stand-ins with the real recordings.
- `--synth` generates every sound offline. `--force` re-downloads everything.
- curl/wget alternatives: `scripts\download_assets.ps1` (Windows) and
  `sh scripts/download_assets.sh`.
- Licenses and authors: [assets/audio/CREDITS.md](assets/audio/CREDITS.md).
  The audio isn't committed to the repo; developers download it into
  `assets/audio/`, which is the starter pack the app (and the .exe) ships with.
  When running from source, the app copies it to your sounds folder on first
  start, like the .exe does. To pick up a changed starter pack, empty your
  sounds folder.

## Building the Windows app (.exe)

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe scripts\download_assets.py
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean AutismCalm.spec
```

This produces **`dist\AutismCalm.exe`**, a single file you can share. The
recipe in [AutismCalm.spec](AutismCalm.spec):

- bundles the starter pack and `assets/logo.jpg` into the .exe (unpacked to
  `sys._MEIPASS` while it runs);
- builds without a console window (same as `--noconsole`);
- converts `logo.jpg` into a multi-size `.ico` for the .exe icon, and adds
  version info ("Autism Calm 1.0.0" in File Properties and Task Manager);
- names the Qt OpenGL modules explicitly, because the GPU renderer is loaded
  lazily. The app uses no Qt 3D modules, so none are bundled.

Without a console, errors go to `%LOCALAPPDATA%\AutismCalm\Logs\autism-calm.log`.
To check a build automatically, set `AUTISMCALM_SMOKE_TEST` to a file path.
The app then plays every sound inaudibly, opens the Visuals tab, writes a JSON
report to that path and quits.

A one-file .exe unpacks itself to a temporary folder each time it starts, so
it takes a few seconds to open. Some antivirus tools are wary of unsigned
PyInstaller apps; code-signing the .exe avoids that.

## Sensory-friendly audio processing

Every file goes through `calm/audio/loader.py` when it is first played:

- **Even loudness:** sounds are levelled to a similar volume, so 50% means
  about the same on every slider.
- **Softened sudden peaks:** unusually loud moments, like thunder cracks, are
  compressed. To turn this off, set `SOFTEN_PEAKS = False` in `calm/config.py`.
- **Gapless loops:** the end of each file is crossfaded into its start. For
  rhythmic sounds (clock, heartbeat), the loop point is lined up with the beat
  so the rhythm doesn't stumble.
- **Trimmed fades:** silence and fade-ins/fade-outs at the ends of recordings
  are removed, so there's no dip each time a sound loops.

Every setting is documented in `calm/config.py`.

## Performance

- The app starts instantly. It only reads file headers at startup, and decodes
  a sound in a background thread the first time you press Play.
- One audio stream mixes all tracks with numpy. With all 16 sounds playing,
  each audio callback took under 1.5 ms of a 25 ms budget, with no dropouts,
  and the UI stayed responsive while sounds were loading.
- Files longer than 2 minutes are trimmed to 2 minutes, and mono files stay
  mono, to keep memory use modest.
- **Visuals run on the GPU.** Each frame, the CPU only updates about 150 light
  positions with numpy (about 0.25 ms) and makes one draw call. The soft glow
  of every light is computed by an OpenGL shader. Measured with all 16 sounds
  playing: a steady 59 fps (worst frame gap 21 ms), the slowest audio callback
  1.5 ms, and no audio dropouts.
- Without usable OpenGL (some virtual machines or remote desktops), the app
  automatically switches to a CPU renderer that draws at reduced resolution
  and scales up, which suits blurry lights. It also held 59 fps with no
  dropouts. To force a renderer, set `VISUALS_RENDERER = "raster"` or
  `"opengl"` in `calm/config.py`.
- Qt has to draw on the main thread, so the visuals keep their main-thread
  work tiny instead. Audio runs on its own thread with a 0.15 s buffer, and
  Python is set to hand the audio thread control quickly (`sys.setswitchinterval`).

## Project layout

```
main.py                        entry point
calm/
  config.py                    paths and audio tuning
  theme.py                     calm dark palette + stylesheet
  icon.py                      window/taskbar icon from assets/logo.jpg
  user_data.py                 first-run sound library copy, log file
  app.py                       QApplication bootstrap
  audio/                       no UI code
    library.py                 scans the sounds folder -> list of Sound
    loader.py                  decode, level, soften peaks, make seamless loop
    track.py                   one looping track with smooth gain
    engine.py                  output stream, mixer, background loading
  ui/
    audio_controller.py        Qt bridge to the engine (signals keep views in sync)
    main_window.py             TABS list -> QTabWidget, Esc = stop all
    tabs/base.py               BaseTab + AppContext (shared services)
    tabs/audio_tab.py          Tab 1: grouped, scrollable mixer
    tabs/visuals_tab.py        Tab 2: visual + Speed slider + Pause button
    widgets/sound_card.py      Play/Pause + volume card
    widgets/flow_grid.py       grid that reflows columns with window width
  visuals/
    base.py                    BaseVisual: frame timer, eased speed/pause
    __init__.py                VISUALS registry
    bokeh_tunnel.py            the bokeh tunnel (simulation + visual)
    render/
      sprites.py               sprite batch format + glow profiles
      gl_canvas.py             GPU renderer (QOpenGLWidget + GLSL shader)
      raster_canvas.py         CPU fallback renderer (QPainter)
assets/logo.jpg                app logo (you provide it)
assets/audio/                  starter pack bundled with the app (sub-folders = categories)
AutismCalm.spec                PyInstaller recipe for dist\AutismCalm.exe
scripts/
  download_assets.py           starter pack downloader (source of truth)
  synth_sounds.py              offline generators for every starter sound
  download_assets.ps1 / .sh    curl/wget alternatives
```

## Extending

- **Add a sound to the starter pack:** add a line to `PACK` in
  `scripts/download_assets.py`, plus a generator in `scripts/synth_sounds.py`
  as the offline fallback, and credit it in `assets/audio/CREDITS.md`.
- **Add a visual:** subclass `BaseVisual` in `calm/visuals/`, implement
  `tick(dt)` and add the class to `VISUALS`. A picker appears automatically
  once there is more than one. The Speed slider and Pause button work for every
  visual, because `BaseVisual` scales `dt` for you. For lots of soft lights,
  reuse `create_canvas()` from `calm/visuals/render` (see `bokeh_tunnel.py`).
  Visuals can follow playback through `context.audio.playingChanged`.
- **Add a tab:** subclass `BaseTab` and append it to `TABS` in
  `calm/ui/main_window.py`.
