# Cardiff

Business cards as code. Cardiff turns a structured JSON or YAML request into a print-ready PDF business card through one shared validation and rendering core.

Cardiff is pre-alpha. The CLI currently supports one request per run and ships one approved template, `business-card`.

## Install

Cardiff requires Python 3.12 or newer.

```bash
python -m pip install cardiff-cli
```

The distribution is named `cardiff-cli`; the installed command is `cardiff`.

Optional: install XeLaTeX and put `xelatex` on `PATH` for Unicode-safe PDF rendering. Without it, Cardiff falls back to its built-in deterministic adapter, which supports ASCII-only preview text.

## Quick Start

The bundled `business-card` template requires a logo. Put one at `assets/logo.png` (`.png`, `.jpg`, `.jpeg`, `.svg`, and `.pdf` are accepted), then create `request.yaml`:

```yaml
identity:
  full_name: Ada Lovelace
  role: Computing Pioneer
  email: ada@example.com
template:
  id: business-card
assets:
  logo: logo.png
```

Validate it, then render it:

```bash
cardiff validate request.yaml --approved-asset-root assets
cardiff render request.yaml --approved-asset-root assets --output card.pdf
```

Useful options:

- `--approved-asset-root DIR` (both commands, repeatable): allow asset paths such as `assets.logo` to resolve inside `DIR`.
- `--deterministic` (`render`): force the built-in deterministic adapter even when `xelatex` is available.
- `--template-root DIR` (`render`): resolve templates from `DIR` instead of the bundled templates.
- `--reference-evidence PATH` (`render`): compare the normalized render evidence against an approved JSON record.

Each command prints one JSON status object to standard output.

## Exit Codes

- `0`: command succeeded
- `1`: validation rejected the request
- `2`: CLI usage or required file/path error
- `3`: render failed after validation succeeded
- `4`: render succeeded but reference-evidence comparison failed

## Documentation

- [Project README](https://github.com/zcalifornia-ph/cardiff#readme)
- [CLI quickstart](https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/cli-quickstart.md)
- [Validation contract](https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/validation-contract.md)
- [Render pipeline](https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/render-pipeline.md)
- [Template authoring](https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/template-authoring.md)
- [Issues](https://github.com/zcalifornia-ph/cardiff/issues)

## License

Apache License 2.0. See [LICENSE.txt](https://github.com/zcalifornia-ph/cardiff/blob/main/LICENSE.txt).
