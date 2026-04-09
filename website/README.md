# website/

The Apex marketing site — single HTML file, zero build step, zero dependencies.

## Deploy to Vercel

```bash
cd website
npx vercel
```

When prompted:
- **Set up and deploy?** → yes
- **Which scope?** → your personal account or `apexhq-dev` org
- **Link to existing project?** → no
- **Project name?** → `apex-site`
- **Directory?** → `./`
- **Override settings?** → no

Vercel picks up `vercel.json` automatically. The `public/` folder is served as static assets at the root (so `/09-log-drawer.png` works from `index.html`).

## Local preview

```bash
cd website
python3 -m http.server -d . 8000
```

Then open http://localhost:8000/ — but note that `public/*` files are referenced as absolute paths (`/hero.mp4`), so you need a server that serves from both `./` and `./public/`. On Vercel this works because they flatten `public/` into the root automatically. For local dev:

```bash
cd website
mkdir -p _preview && cp index.html _preview/ && cp public/* _preview/
python3 -m http.server -d _preview 8000
```

## Structure

```
website/
├── index.html          # The whole site, CSS inlined
├── vercel.json         # Caching + clean URLs
├── README.md           # This file
└── public/             # Assets served at /
    ├── hero.mp4        # Inline hero video (497 KB)
    ├── hero.gif        # Fallback + README-embeddable (2.0 MB)
    └── 01-..-11-*.png  # Feature grid screenshots
```

## What the landing page includes

1. **Hero** — tagline, one-click copy install command, auto-playing hero video
2. **The math** — cloud GPU pricing comparison (RunPod, Lambda, AWS vs $29/mo)
3. **Feature grid** — 6 screenshots from the real dashboard
4. **How it works** — 3-step install → start → submit
5. **Stack callout** — "intentionally boring"
6. **Pricing** — 3 tiers (Free, Team $29, Hosted $99)
7. **Footer** — GitHub, Discord, Twitter, license
