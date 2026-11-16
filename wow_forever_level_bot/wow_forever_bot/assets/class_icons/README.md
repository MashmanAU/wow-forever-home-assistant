# WoW class icons

The container build vendors the nine 64×64 PNG class icons used by WoW Forever from:

- Source: https://github.com/orourkek/Wow-Icons/tree/master/images/class/64
- Pinned asset commit: `5d9ad053876920138f68d69a4197fc18771b9505`
- Licence: The Unlicense; see `UNLICENSE.txt` in this directory.

The release keeps source control text-only and reproducible: `vendor_class_icons.py` downloads the exact pinned files during the GitHub container build, validates the PNG signature and 64×64 dimensions, and fails the build if any asset is unavailable or malformed. The running app uses only the files embedded in the built container and performs no asset download at runtime.
