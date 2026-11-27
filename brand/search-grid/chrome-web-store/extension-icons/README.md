# Search Grid: new icons for the next store upload

Drop these four files into the yt-grid-extension repo's `icons/` folder, replacing the old red-grid files of the same names:

| File here | Replaces | Used by manifest.json |
|---|---|---|
| icon16.png | icons/icon16.png | `icons."16"`, `action.default_icon."16"` |
| icon32.png | icons/icon32.png | `icons."32"`, `action.default_icon."32"` |
| icon48.png | icons/icon48.png | `icons."48"`, `action.default_icon."48"` |
| icon128.png | icons/icon128.png | `icons."128"`, `action.default_icon."128"` (96 px art, 16 px clear each side, per the Chrome Web Store guide) |

The file names and paths match the manifest of version 1.2.1, so manifest.json needs no path changes, only a version bump (for example 1.2.2) before packaging.

Store listing images (upload in the Developer Dashboard, Store listing tab):
- Small promo tile 440x280: ../search-grid-promo-small-440x280.png
- Marquee 1400x560 (optional): ../search-grid-marquee-1400x560.png
- Store icon: the same icon128.png

Prompt for Claude Code (cc), to paste in ~/dev/yt-grid-extension:

    Replace icons/icon16.png, icons/icon32.png, icons/icon48.png and icons/icon128.png with the four files I'll put in ~/Downloads/search-grid-icons/ (same names). Bump manifest.json version from 1.2.1 to 1.2.2. Load the unpacked extension, check the toolbar icon and the popup still show, build the store zip the way 1.2.1 was built, commit and push. Then delete ~/Downloads/search-grid-icons/.
