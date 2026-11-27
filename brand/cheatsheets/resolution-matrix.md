# Cheatsheets Resolution Matrix

Platforms: VS Code extension (Marketplace publishing is next): the 128 px Marketplace / Open VSX icon and a monochrome view icon for its sidebar.

## Source Files (master/)
| File | Dimensions | Notes | Status |
|---|---|---|---|
| cheatsheets-hero.svg / -dark.svg | 512×512 vector; PNG 512, 1024 | 3D hero: banners, cards, motion | DONE |
| cheatsheets-icon.svg / -dark.svg | 128×128 vector | Flat tile: every icon export | DONE |
| cheatsheets-wordmark.svg / -dark.svg | 128 high, vector | Icon + name + AN OAT TOOL | DONE |

## Exports — Banner (hero card)
| Use | Size | Format | File | Status |
|---|---|---|---|---|
| GitHub social preview | 1280×640 | PNG | exports/github-social-1280x640.png | DONE |
| Link preview (Open Graph); LinkedIn and X shares | 1200×630 | PNG | exports/og-image-1200x630.png | DONE |

## Exports — Icon (flat tile)
| Use | Size | Format | File | Status |
|---|---|---|---|---|
| VS Code Marketplace / Open VSX icon | 128×128 | PNG | exports/vscode-marketplace-icon-128.png | DONE |

## Exports — Icon (monochrome)
| Use | Size | Format | File | Status |
|---|---|---|---|---|
| VS Code view-container icon | vector | SVG | exports/vscode-view-icon.svg | DONE |

## Motion (motion/)
| Variant | Still | Loop | Status |
|---|---|---|---|
| calm | motion/cheatsheets-calm.png (1536×1024) | motion/cheatsheets-calm.mp4 (1536×1024, H.264, 24 fps, no audio) | DONE |
| night-spotlight | motion/cheatsheets-night-spotlight.png (1536×1024) | motion/cheatsheets-night-spotlight.mp4 (1536×1024, H.264, 24 fps, no audio) | DONE |
| night-storm | motion/cheatsheets-night-storm.png (1536×1024) | motion/cheatsheets-night-storm.mp4 (1536×1024, H.264, 24 fps, no audio) | DONE |
| snow | motion/cheatsheets-snow.png (1536×1024) | motion/cheatsheets-snow.mp4 (1536×1024, H.264, 24 fps, no audio) | DONE |

## Not made yet (platform not shipped)
| Use | Size | Format | When | Status |
|---|---|---|---|---|
| VS Code gallery banner colour | n/a | package.json | Set galleryBanner.color to the icon lip colour when publishing | LATER |

## Total exports required: 4
## Total exports complete: 4
## Source files captured: 3 of 3
## Motion: 4 of 4
## Export script: cheatsheets-export.sh
## Completed: 2026-11-27
