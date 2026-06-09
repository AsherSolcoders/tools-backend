# Toolkit Pro — Backend (FastAPI)

Config-driven tool engine + blog + super-admin API. No visitor data is stored.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Without `DATABASE_URL`, the app uses a local SQLite file (`toolkitpro.db`) so it runs with zero config.
- On first start it seeds a dev super-admin: `admin@toolkitpro.local` / `admin12345`.
- Interactive docs at `/docs`.

## Layout

```
app/
├── main.py              App wiring: CORS, secure headers, rate limit, temp-file sweeper, admin seed
├── config.py            Settings (env)
├── database.py          Engine, session, Base, init_db
├── core/
│   ├── temp_files.py    /tmp upload+result lifecycle, 10-min auto-cleanup
│   └── security.py      Upload validation, sanitization, secure headers, password hashing
├── models/              users, blogs, blog_categories, tool_categories, settings, seo_settings
├── schemas/             Pydantic payloads
├── tools/
│   ├── registry.py      ★ Config-driven tool catalogue (single source of truth)
│   ├── text_tools.py    Processors
│   ├── developer_tools.py
│   ├── image_tools.py
│   └── pdf_tools.py
└── api/routes/          tools, blog, admin, seo (sitemap/robots), health
```

## Key endpoints

| Method | Path                         | Purpose                              |
|--------|------------------------------|--------------------------------------|
| GET    | `/api/tools`                 | List all tools (+`?category=`)       |
| GET    | `/api/tools/categories`      | List tool categories                 |
| GET    | `/api/tools/{slug}`          | Full tool config (drives the UI)     |
| POST   | `/api/tools/{slug}/process`  | Run a tool (multipart: files/text/options) |
| GET    | `/api/tools/download/{token}`| Download a result file               |
| POST   | `/api/tools/download-zip`    | Zip multiple results                 |
| GET    | `/api/blog`                  | Published posts                      |
| POST   | `/api/admin/login`           | Admin login → JWT                    |
| *      | `/api/admin/blogs` …         | Blog/category CRUD (auth)            |
| GET    | `/sitemap.xml`, `/robots.txt`| Dynamic SEO                          |

## Adding a tool

1. Add a `ToolConfig(...)` via `define(...)` in `tools/registry.py`.
2. Register a processor: `@register("<slug>")` with signature
   `fn(files: list[Path], text: str, options: dict) -> ToolResult` in the matching `*_tools.py`.

The API and frontend pick it up automatically. Tools defined without a processor
are surfaced as "coming soon".
