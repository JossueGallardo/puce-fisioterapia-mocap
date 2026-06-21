"""Acceso estable a recursos incluidos en el paquete PUCE."""

from __future__ import annotations

from importlib.resources import files


def resource_file(*parts: str):
    resource = files("puce_mocap").joinpath("resources")
    for part in parts:
        resource = resource.joinpath(part)
    return resource
