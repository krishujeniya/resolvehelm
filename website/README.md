# ResolveHelm public website

The public website is a static, self-contained implementation of the design direction in the supplied `Web.md`, adapted to the real ResolveHelm project.

## Brand and design

- Dark navy base: `#071321`
- Primary blue: `#73b8ff`
- Decision amber: `#f7bd63`
- Dependency-free HTML, CSS, inline SVG, and Canvas 2D in `website/index.html`
- Responsive landing page with a scroll-responsive particle field, fallback, motion controls, keyboard-accessible scenarios and FAQ, example case carousel, and honest demo dialog
- Content grounded in the existing README and AI_HANDOFF: Gmail support, policy/knowledge-base checks, deterministic safeguards, tickets and operator review

The page intentionally omits the source template's fictional brand, fictional prices, invented clients and unsubstantiated performance claims. No real customer data or authentication appears on the marketing page.

## GitHub Pages

The workflow at `.github/workflows/deploy-pages.yml` builds the existing React dashboard, then assembles:

```text
public-site/
  index.html         # ResolveHelm landing page
  app/
    index.html       # Existing Vite dashboard
    assets/          # Dashboard's compiled assets
```

Once GitHub Pages uses **GitHub Actions** as its deployment source, the URLs are:

- Landing page: https://krishujeniya.github.io/resolvehelm/
- Authenticated admin console: https://krishujeniya.github.io/resolvehelm/app/

The code is committed in the repository; successful hosting requires the GitHub Pages workflow to finish.

## Connecting the backend

Set the GitHub Actions repository variable `VITE_API_URL` to the deployed HTTPS FastAPI backend URL before building, or enter it in the dashboard sign-in modal. The backend must be hosted separately: GitHub Pages serves only static files. Configure a narrowly scoped `CORS_ALLOWED_ORIGINS` for `https://krishujeniya.github.io`, supply the backend credentials and required provider settings, and retain production dry-run/sending safety review. Do not commit API keys or email tokens.

## Verification

Recommended browser checks: 320, 390, 768, 1024, 1440 and 1920px; keyboard-only navigation, tabs, carousel, dialog, FAQ and mobile menu; disabled JavaScript, reduced motion and failed Canvas rendering; and real sign-in against a configured backend. The website's examples never contact the API. CI builds the existing dashboard and checks both assembled entry points. No Lighthouse scores are claimed without measurement.
