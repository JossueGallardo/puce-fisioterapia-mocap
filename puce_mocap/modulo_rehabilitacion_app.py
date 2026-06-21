"""Wrapper compatible para abrir directamente el módulo Qt de rehabilitación."""


def main() -> int:
    from puce_mocap.qt_app import run

    return run("rehab")


if __name__ == "__main__":
    raise SystemExit(main())
