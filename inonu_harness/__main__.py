from .cli import main

if __name__ == "__main__":  # importing this module must not run the CLI
    raise SystemExit(main())
