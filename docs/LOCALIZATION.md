# Public language access layers

English is the canonical methodology language. Localized home pages explain the
public introduction; they do not translate normative standards, modules,
identifiers or protected architecture names. German (`de/`) is the structural
reference for the Korean (`ko/`, `ko-KR`) introduction.

## Sources and generated files

- `tools/build_localization.py`: language definitions, public introduction text,
  generated home pages and `data/localization/localization-policy.json`.
- `header.js`: language selector, navigation labels and footer notices.
- `tools/build_ai_compatibility.py`: language metadata, reciprocal `hreflang`
  alternatives, sitemap, search coverage and website language declarations.
- `tools/validate_ai_compatibility.py`: expected document languages.
- `tests/test_localization.py`: registry agreement, content topology, links,
  section anchors, discovery metadata and canonical English boundaries.

The Korean home page uses the shared stylesheet and header/footer loader, just
like German. Navigation to untranslated documents retains their English pages.
The Korean PDF link explicitly names and downloads the existing English
canonical PDF, since no Korean PDF is published.

## Korean terminology

| Source concept | Korean rendering |
| --- | --- |
| canonical version / methodology | 정본 / 정본 방법론 |
| system validity | 시스템의 유효성 |
| system integrity | 시스템 무결성 |
| interoperability | 상호 운용성 |
| governance | 거버넌스 |
| methodological reference authority | 방법론적 기준 기관 |
| non-executable authority | 시스템을 직접 실행하지 않는 기준 기관 |

OOF®, OriginOpen® Foundation, Structured Reality™, UCL™,
Global AI Incident Intelligence™ and MIP® — Methodological Intellectual Property
retain their source spelling. The footer states that the published English HTML
text prevails in case of ambiguity.

## Rebuild and validation

Run the rebuild and validation sequence in `.github/workflows/ai-compatibility.yml`.
The localization regression tests run there after discovery generation:

```sh
python -m unittest tests.test_localization
```

Serve the repository over HTTP to check dynamically loaded shared UI. Verify
`/ko/` and `/ko/index.html` at desktop and mobile widths, Korean/German/English
switching, the Korean footer, and the English canonical and PDF links.
