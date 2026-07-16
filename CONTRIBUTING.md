# Contributing

Contributions are welcome.

1. Fork the repository and create a focused branch.
2. Add or update tests for behavioral changes.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python -m compileall -q src`.
5. Open a pull request that explains the problem and the chosen behavior.

Keep the core package dependency-free unless a dependency creates clear value
that cannot reasonably be achieved with the Python standard library.
