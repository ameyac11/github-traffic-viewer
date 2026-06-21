# Changelog

## [0.1.7] - 2026-06-21
### Fixed
- **Subset sync data loss**: Running `gitlytics sync --metrics views` no longer erases existing columns (e.g. `clones`, `stars`, `forks`) from historical CSV rows — affected columns are now merged rather than overwritten.
- **FastAPI null/None crash**: Dashboard no longer throws `TypeError` when a CSV has empty or missing metric cells — all integer conversions in `process.py` now use the safe `_safe_int` helper.
- **Capitalized "Date" column rejected**: CSV files with a capitalized `Date` header are now accepted and automatically normalised to `date` before validation.
- **Releases count capped at 100**: Total release count now uses GitHub's Link header pagination to return the true total, even for repositories with more than 100 releases.
- **Misleading "Total Commits" label**: Clarified in comments and documentation that `total_commits` reflects the trailing 12-month (52-week) GitHub stat, not a lifetime count.
- **Range scaling discarded real data**: The dashboard range selector (`30D`, `90D`) now uses actual historical daily data points when a sufficient number of CSV records are available, rather than always multiplying the last 14 days by a static scale factor.
- **Relative data directory path resolution**: Added auto-resolution to look in the parent directory (`..`) for relative data directories if they aren't found locally. This fixes silent CSV loading failures and resolves the issue where the expanded repository Daily Trends line charts were capped at 14 days of data when the dashboard was launched from a package subdirectory.

## [0.1.6] - 2026-06-20

### Added
- Added `-m` / `--metrics` filtering parameters to CLI commands (`fetch`, `sync`) and Python API functions to selectively fetch or sync specific metrics.
- Implemented concurrent threading in the backend for faster deep API fetching of commits, pull requests, releases, and community profiles.
- Added a backend endpoint to query public user profiles and repositories.
- Added PNG, PDF, and Developer Card export features to download high-resolution dashboard snapshots, multi-page PDF reports, and shareable summary cards.
- Integrated a global export state hook and CSS overrides to disable transitions and Recharts animations during exports, preventing incomplete or transparent visual elements.
- Applied Apache-2.0 License with Commons Clause v1.0.

### Changed
- Improved the frontend dashboard UI/UX styling, metrics card layouts, and avatar ring aesthetics.
- Optimized and corrected traffic date normalization logic in `process.py`.
## [0.1.5] - 2026-06-18
### Changed
- Updated the primary project logo to a newer, higher-resolution version across the dashboard and README.

### Fixed
- Addressed minor bugs and visual inconsistencies in the dashboard interface to improve overall user experience.

## [0.1.4] - 2026-06-17
### Added
- Added official documentation portal links (`docs.gitlytics.dev`) to PyPI metadata and README.

### Changed
- Renamed the internal `frontend` directory to `dashboard` to match Vercel deployments.
- Updated PyPI metadata with the official project domain (`gitlytics.dev`) and author contact info.
- Improved GitHub Actions workflow to use `npm ci` for deterministic UI builds on Node 24.
- Refactored internal API error messaging to accurately reflect the new dashboard directory structure.

## [0.1.3] - 2026-06-17
### Fixed
- Bumped version to 0.1.3 to resolve PyPI upload conflict (version 0.1.2 was already taken).

## [0.1.2] - 2026-06-16
### Fixed
- Traffic data now always returns exactly 14 days, even when GitHub omits dates with zero views.
- Background sync cron process no longer hangs silently — exits cleanly on expired tokens (401).
- Database no longer fragments when the sync cron job runs from a different working directory.
- Cron logs now appear correctly in all environments instead of being swallowed by stdout buffering.
- Star and fork counts now reflect the latest snapshot rather than an inflated cumulative sum.
- Fixed `export_json_database` doubling traffic counts when reading overlapping monthly and yearly CSV files.
- Fixed JSON timeseries payload missing `clones` due to a duplicate `unique_visitors` dictionary key.
- Fixed CLI package entry point (added `__main__.py`) allowing execution via `python -m gitlytics`.

### Changed
- JSON exports now strip private repositories by default (`export_public_only=True`) to prevent accidental leaks.
- Dashboard now preloads historical CSVs on boot instead of relying solely on live GitHub API data.
- React frontend now reads the API URL from `VITE_API_URL`, allowing independent deployment (e.g. Vercel).

### Added
- Added `docs/api_documentation.md` with code examples and parameter tables for `fetch_traffic`, `sync`, and `serve_dashboard`.
- `croniter` dependency for cron scheduling support.

## [0.1.1] - 2026-06-15
### Changed
- Migrated dashboard from Streamlit to React + Vite.
- Replaced Streamlit backend with FastAPI + Uvicorn.
- Renamed CLI command and project to `gitlytics`.
- Redesigned dashboard UI with dark mode and animated charts.
- PyPI build now bundles the compiled React frontend automatically.

### Removed
- Streamlit dashboard and runner.

## [0.1.0] - 2026-06-14
### Added
- Initial release.
- Core traffic fetching logic.
- CLI commands: `fetch`, `sync`, `dashboard`.
- Streamlit dashboard.
- GitHub Actions automation template.
- PyPI distribution support.