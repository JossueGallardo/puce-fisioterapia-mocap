"""Wrapper compatible para abrir directamente el módulo Qt de marcha."""


def main() -> int:
    from puce_mocap.qt_app import run

    return run("gait")


if __name__ == "__main__":
    raise SystemExit(main())
