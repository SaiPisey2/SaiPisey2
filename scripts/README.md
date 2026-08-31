# Profile card generators

Two scripts render the SVG cards embedded in the profile README. Both read
only public GitHub REST endpoints, so neither needs a personal access token —
`GITHUB_TOKEN` is passed in CI purely to lift the anonymous rate limit.

| Script | Output | Source |
|---|---|---|
| `gen_stats.py` | `metrics/stats.svg`, `metrics/languages.svg` | `/users/:user/repos`, each repo's `languages_url`, `/search/issues` |
| `gen_upstream.py` | `metrics/upstream.svg` | `/search/issues`, with simple-icons marks inlined at build time |

`gen_stats.py` keeps an `EXCLUDE` set for repositories that hold a copy of an
upstream project rather than original work. GitHub does not flag those as
forks, so without the exclusion their vendored code dominates the language
totals.

Run either locally with `python3 scripts/<script>.py`; both write into
`metrics/` and print what they found.
