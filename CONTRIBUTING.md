# Contributing

Contributions are welcome.

1. Fork the repository and create a focused branch.
2. Add or update tests for behavioral changes.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python -m compileall -q src`.
5. Run `ruff check src tests`.
6. Run `ruff format --check src tests`.
7. Open a pull request that explains the problem and the chosen behavior.

If you change `action.yml` or `.github/workflows/example-audit.yml`, keep the
README GitHub Action section in sync.

Keep the core package dependency-free unless a dependency creates clear value
that cannot reasonably be achieved with the Python standard library. Optional
extras such as `yaml` and `qr` must remain optional and must not become required
for the default install path.
