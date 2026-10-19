#!/usr/bin/env sh
# Download the starter pack with curl (or wget). Run from the project root:
#   sh scripts/download_assets.sh
# Airplane cabin has no free recording; generate it (and any failed download) with:
#   python scripts/download_assets.py
# This file mirrors PACK in scripts/download_assets.py.
set -u
ROOT="$(dirname "$0")/../assets/audio"
UA="AutismCalm/0.2 (open-source ambient sound app; asset setup script) curl"

fetch() {
  mkdir -p "$ROOT/$(dirname "$1")"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 5 --retry-delay 10 -A "$UA" -o "$ROOT/$1" "$2" || echo "Failed: $1" >&2
  else
    wget --tries=5 --waitretry=10 -U "$UA" -O "$ROOT/$1" "$2" || echo "Failed: $1" >&2
  fi
  sleep 3  # be polite to Wikimedia
}

fetch Noise/brown_noise.ogg      "https://upload.wikimedia.org/wikipedia/commons/c/c9/Brownnoise.ogg"
fetch Noise/pink_noise.wav       "https://upload.wikimedia.org/wikipedia/commons/6/61/Pink_noise.wav"
fetch Noise/white_noise.ogg      "https://upload.wikimedia.org/wikipedia/commons/9/98/White-noise-sound-20sec-mono-44100Hz.ogg"
fetch Nature/heavy_rain.mp3      "https://upload.wikimedia.org/wikipedia/commons/5/56/Listening_to_Raindrops_%281035382_-_heavy_loop%29.mp3"
fetch Nature/light_rain.mp3      "https://upload.wikimedia.org/wikipedia/commons/e/ed/Listening_to_Raindrops_%281035382_-_drizzle_loop%29.mp3"
fetch Nature/thunder.ogg         "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rhumphries_-_rbh-thunder-storm.ogg"
fetch Nature/wind.wav            "https://upload.wikimedia.org/wikipedia/commons/4/47/Wind_in_forest_%28Gravity_Sound%29.wav"
fetch Nature/ocean_waves.ogg     "https://upload.wikimedia.org/wikipedia/commons/f/f1/Oceanwavescrushing.ogg"
fetch Nature/fire_crackling.ogg  "https://upload.wikimedia.org/wikipedia/commons/b/b1/Campfire_sound_ambience.ogg"
fetch Ambient/train_ride.ogg     "https://upload.wikimedia.org/wikipedia/commons/8/83/Taiwan_railways_EP727_train_cars_sounds.ogg"
fetch Ambient/deep_space_hum.wav "https://upload.wikimedia.org/wikipedia/commons/4/45/Sounds_of_the_Ancient_Universe_%28PIA16881%29.wav"
fetch Ambient/box_fan.ogg        "https://upload.wikimedia.org/wikipedia/commons/a/a9/Ventilador_de_estudio.ogg"
fetch Rhythmic/cat_purring.ogg   "https://upload.wikimedia.org/wikipedia/commons/4/4c/Purr_%2810_sec_loopable%29.ogg"
fetch Rhythmic/heartbeat.flac    "https://upload.wikimedia.org/wikipedia/commons/a/a4/Human_heart_rate.flac"
fetch Rhythmic/clock_ticking.ogg "https://upload.wikimedia.org/wikipedia/commons/f/ff/Grandfather_Clock_Ticking.ogg"

echo "Done. Files saved to $ROOT"
