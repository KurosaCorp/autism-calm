# Download the starter pack with curl (built into Windows 10+). Run from the project root:
#   powershell -ExecutionPolicy Bypass -File scripts\download_assets.ps1
# Uses curl.exe explicitly: in Windows PowerShell "curl" is an alias for Invoke-WebRequest.
# Airplane cabin has no free recording; generate it (and any failed download) with:
#   python scripts\download_assets.py
# This file mirrors PACK in scripts/download_assets.py.

$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot "..\assets\audio"
$ua = "AutismCalm/0.2 (open-source ambient sound app; asset setup script) curl"

function Get-Sound($path, $url) {
    $dest = Join-Path $root $path
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    curl.exe -fL --retry 5 --retry-delay 10 -A $ua -o $dest $url
    if ($LASTEXITCODE -ne 0) { Write-Warning "Failed: $path" }
    Start-Sleep -Seconds 3  # be polite to Wikimedia
}

Get-Sound Noise/brown_noise.ogg      "https://upload.wikimedia.org/wikipedia/commons/c/c9/Brownnoise.ogg"
Get-Sound Noise/pink_noise.wav       "https://upload.wikimedia.org/wikipedia/commons/6/61/Pink_noise.wav"
Get-Sound Noise/white_noise.ogg      "https://upload.wikimedia.org/wikipedia/commons/9/98/White-noise-sound-20sec-mono-44100Hz.ogg"
Get-Sound Nature/heavy_rain.mp3      "https://upload.wikimedia.org/wikipedia/commons/5/56/Listening_to_Raindrops_%281035382_-_heavy_loop%29.mp3"
Get-Sound Nature/light_rain.mp3      "https://upload.wikimedia.org/wikipedia/commons/e/ed/Listening_to_Raindrops_%281035382_-_drizzle_loop%29.mp3"
Get-Sound Nature/thunder.ogg         "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rhumphries_-_rbh-thunder-storm.ogg"
Get-Sound Nature/wind.wav            "https://upload.wikimedia.org/wikipedia/commons/4/47/Wind_in_forest_%28Gravity_Sound%29.wav"
Get-Sound Nature/ocean_waves.ogg     "https://upload.wikimedia.org/wikipedia/commons/f/f1/Oceanwavescrushing.ogg"
Get-Sound Nature/fire_crackling.ogg  "https://upload.wikimedia.org/wikipedia/commons/b/b1/Campfire_sound_ambience.ogg"
Get-Sound Ambient/train_ride.ogg     "https://upload.wikimedia.org/wikipedia/commons/8/83/Taiwan_railways_EP727_train_cars_sounds.ogg"
Get-Sound Ambient/deep_space_hum.wav "https://upload.wikimedia.org/wikipedia/commons/4/45/Sounds_of_the_Ancient_Universe_%28PIA16881%29.wav"
Get-Sound Ambient/box_fan.ogg        "https://upload.wikimedia.org/wikipedia/commons/a/a9/Ventilador_de_estudio.ogg"
Get-Sound Rhythmic/cat_purring.ogg   "https://upload.wikimedia.org/wikipedia/commons/4/4c/Purr_%2810_sec_loopable%29.ogg"
Get-Sound Rhythmic/heartbeat.flac    "https://upload.wikimedia.org/wikipedia/commons/a/a4/Human_heart_rate.flac"
Get-Sound Rhythmic/clock_ticking.ogg "https://upload.wikimedia.org/wikipedia/commons/f/ff/Grandfather_Clock_Ticking.ogg"

Write-Host "Done. Files saved to $((Resolve-Path $root).Path)"
