"""Download the starter pack of ambient sounds into assets/audio.

Run from the project root:

    python scripts/download_assets.py           # fetch anything missing
    python scripts/download_assets.py --force   # replace existing files
    python scripts/download_assets.py --synth   # no internet: generate every sound offline

Sounds come from Wikimedia Commons (public domain / Creative Commons; see
assets/audio/CREDITS.md). Files are fetched one at a time with a pause in
between, as Wikimedia asks of scripts. If a download fails, a synthesized
stand-in is generated so the app always works out of the box.

To add a sound to the pack, add a line to PACK: the category folder, the
local file name (which becomes the label in the app), and the exact
Commons file title, or None to always synthesize it.
"""

import argparse
import hashlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

import soundfile as sf

from synth_sounds import GENERATORS, SR, synthesize

AUDIO_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio"
USER_AGENT = "AutismCalm/0.2 (open-source ambient sound app; asset setup script) python-urllib"
PAUSE_SECONDS = 3
# Longer server back-off requests are not waited out: a stand-in is generated instead.
MAX_RETRY_WAIT = 60
AUDIO_EXTENSIONS = (".wav", ".ogg", ".oga", ".flac", ".mp3", ".aif", ".aiff")

# (category folder, local file name, Wikimedia Commons file title or None)
PACK = [
    ("Noise", "brown_noise.ogg", "Brownnoise.ogg"),
    ("Noise", "pink_noise.wav", "Pink noise.wav"),
    ("Noise", "white_noise.ogg", "White-noise-sound-20sec-mono-44100Hz.ogg"),
    ("Nature", "heavy_rain.mp3", "Listening to Raindrops (1035382 - heavy loop).mp3"),
    ("Nature", "light_rain.mp3", "Listening to Raindrops (1035382 - drizzle loop).mp3"),
    ("Nature", "thunder.ogg", "Rhumphries - rbh-thunder-storm.ogg"),
    ("Nature", "wind.wav", "Wind in forest (Gravity Sound).wav"),
    ("Nature", "ocean_waves.ogg", "Oceanwavescrushing.ogg"),
    ("Nature", "fire_crackling.ogg", "Campfire sound ambience.ogg"),
    ("Ambient", "airplane_cabin.wav", None),  # no suitable free recording; generated
    ("Ambient", "train_ride.ogg", "Taiwan railways EP727 train cars sounds.ogg"),
    ("Ambient", "deep_space_hum.wav", "Sounds of the Ancient Universe (PIA16881).wav"),
    ("Ambient", "box_fan.ogg", "Ventilador de estudio.ogg"),
    ("Rhythmic", "cat_purring.ogg", "Purr (10 sec loopable).ogg"),
    ("Rhythmic", "heartbeat.flac", "Human heart rate.flac"),
    ("Rhythmic", "clock_ticking.ogg", "Grandfather Clock Ticking.ogg"),
]


def commons_url(title: str) -> str:
    """Direct file URL for a Commons title (Commons shards files by the MD5 of the name)."""
    name = title.replace(" ", "_")
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{urllib.parse.quote(name)}"


class RateLimited(Exception):
    pass


def download(url: str, dest: Path, attempts: int = 4) -> None:
    tmp = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=60) as response, open(tmp, "wb") as f:
                    while chunk := response.read(1 << 16):
                        f.write(chunk)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429:
                    raise
                wait = int(exc.headers.get("Retry-After") or 10 * attempt)
                if wait > MAX_RETRY_WAIT or attempt == attempts:
                    raise RateLimited(f"server asked us to wait {wait}s") from exc
                print(f" rate-limited, waiting {wait}s...", end="", flush=True)
                time.sleep(wait)
        with sf.SoundFile(str(tmp)) as f:  # make sure the app will be able to decode it
            f.read(1024)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)


def existing(folder: Path, stem: str) -> Path | None:
    for ext in AUDIO_EXTENSIONS:
        if (folder / f"{stem}{ext}").is_file():
            return folder / f"{stem}{ext}"
    return None


def remove_stem(folder: Path, stem: str, keep: Path | None = None) -> None:
    for ext in AUDIO_EXTENSIONS:
        path = folder / f"{stem}{ext}"
        if path != keep:
            path.unlink(missing_ok=True)


def generate(folder: Path, stem: str) -> Path:
    dest = folder / f"{stem}.wav"
    sf.write(str(dest), synthesize(stem, seed=zlib.crc32(stem.encode())), SR, subtype="PCM_16")
    return dest


# Stand-ins generated because a download failed are listed here, so the next
# run tries to replace them with the real recording.
STANDINS = AUDIO_DIR / ".standins"


def read_standins() -> set[str]:
    return set(STANDINS.read_text().split()) if STANDINS.is_file() else set()


def write_standins(standins: set[str]) -> None:
    if standins:
        STANDINS.write_text("\n".join(sorted(standins)) + "\n")
    else:
        STANDINS.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="replace files that already exist")
    parser.add_argument("--synth", action="store_true", help="generate every sound offline instead of downloading")
    args = parser.parse_args()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    standins = read_standins()
    counts = {"present": 0, "downloaded": 0, "generated": 0, "stand-in": 0}
    first_download = True
    rate_limited = False
    for category, filename, title in PACK:
        folder = AUDIO_DIR / category
        folder.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem
        key = f"{category}/{stem}"
        found = existing(folder, stem)
        retry_standin = key in standins and title and not args.synth and not rate_limited

        if found and not args.force and not retry_standin:
            print(f"  ok        {category}/{found.name}" + ("  (stand-in)" if key in standins else ""))
            counts["present"] += 1
            continue

        if title and not args.synth and not rate_limited:
            if not first_download:
                time.sleep(PAUSE_SECONDS)
            first_download = False
            print(f"  download  {category}/{filename} ...", end="", flush=True)
            try:
                download(commons_url(title), folder / filename)
                remove_stem(folder, stem, keep=folder / filename)
                standins.discard(key)
                print(" done")
                counts["downloaded"] += 1
                continue
            except RateLimited as exc:
                rate_limited = True  # stop hammering the server; generate the rest
                print(f" rate-limited ({exc})")
            except Exception as exc:
                print(f" failed ({exc})")
            if found:  # keep the existing stand-in rather than regenerating it
                counts["present"] += 1
                continue

        if stem not in GENERATORS:
            print(f"  skip      {category}/{filename} (no offline version; try again later)")
            continue
        remove_stem(folder, stem)
        path = generate(folder, stem)
        if title:  # a real recording exists; try again next run
            standins.add(key)
            counts["stand-in"] += 1
            print(f"  generate  {category}/{path.name}  (stand-in until the download works)")
        else:
            counts["generated"] += 1
            print(f"  generate  {category}/{path.name}")

    write_standins(standins)
    print(
        f"\n{counts['downloaded']} downloaded, {counts['generated']} generated, "
        f"{counts['stand-in']} stand-ins, {counts['present']} already present -> {AUDIO_DIR}"
    )
    if standins:
        print("Some sounds are generated stand-ins. Run this script again later to fetch the real recordings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
