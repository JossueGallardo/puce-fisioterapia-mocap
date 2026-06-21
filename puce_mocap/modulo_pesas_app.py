"""Wrapper compatible para abrir directamente el módulo Qt de pesas."""


def main() -> int:
    from puce_mocap.qt_app import run

    return run("pesas")


if __name__ == "__main__":
    raise SystemExit(main())
