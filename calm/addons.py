"""Load third-party add-ons from the user's Add-ons folder.

An add-on is either a single ``.py`` file or a folder containing
``__init__.py`` (a package, which may hold several modules and data files),
placed in ``%LOCALAPPDATA%\\AutismCalm\\Addons``. It is imported once at
startup. Its visuals are:

* the classes in a module-level ``VISUALS`` list, if it defines one, or
* otherwise every ``BaseVisual`` subclass defined in the add-on module.

A broken add-on (import error, bad VISUALS entry) is skipped and logged; it
never stops the app. Add-ons run as normal Python code with the same rights
as the app, so users should only install add-ons they trust.
"""

import importlib.util
import inspect
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from calm import config
from calm.visuals.base import BaseVisual

log = logging.getLogger(__name__)

MODULE_PREFIX = "autismcalm_addons."


@dataclass
class Addon:
    name: str   # file or folder name, e.g. "breathing_circle"
    path: Path
    visuals: list[type[BaseVisual]] = field(default_factory=list)
    error: str | None = None


def find_addon_paths(directory: Path) -> list[Path]:
    """Add-on files and package folders in ``directory``, sorted by name."""
    if not directory.is_dir():
        return []
    paths = []
    for path in directory.iterdir():
        if path.name.startswith((".", "_")):
            continue  # hidden files, __pycache__, disabled add-ons (_name.py)
        if (path.is_file() and path.suffix == ".py") or (path.is_dir() and (path / "__init__.py").is_file()):
            paths.append(path)
    return sorted(paths, key=lambda p: p.name.lower())


def load_addons(directory: Path = config.ADDONS_DIR) -> list[Addon]:
    """Import every add-on in ``directory`` and collect its visuals."""
    try:
        directory.mkdir(parents=True, exist_ok=True)  # so users can find the folder
    except OSError:
        log.warning("Could not create the add-ons folder %s", directory)
    addons = []
    for path in find_addon_paths(directory):
        addon = Addon(name=path.stem if path.is_file() else path.name, path=path)
        try:
            module = _import(path, addon.name)
            addon.visuals = _visuals_in(module)
            if addon.visuals:
                log.info("Loaded add-on %s: %s", addon.name, ", ".join(v.name for v in addon.visuals))
            else:
                log.info("Loaded add-on %s (no visuals)", addon.name)
        except (Exception, SystemExit) as exc:  # an add-on calling sys.exit() must not quit the app
            addon.error = f"{type(exc).__name__}: {exc}"
            log.exception("Skipping add-on %s", path)
        addons.append(addon)
    return addons


def _import(path: Path, name: str) -> ModuleType:
    parent = MODULE_PREFIX.rstrip(".")
    if parent not in sys.modules:  # namespace that all add-on modules live under
        namespace = ModuleType(parent)
        namespace.__path__ = []
        sys.modules[parent] = namespace
    module_name = MODULE_PREFIX + re.sub(r"\W", "_", name)
    if path.is_dir():
        spec = importlib.util.spec_from_file_location(
            module_name, path / "__init__.py", submodule_search_locations=[str(path)]
        )
    else:
        spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # lets a package import its own submodules
    write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep the user's Add-ons folder free of __pycache__
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    finally:
        sys.dont_write_bytecode = write_bytecode
    return module


def _visuals_in(module: ModuleType) -> list[type[BaseVisual]]:
    declared = getattr(module, "VISUALS", None)
    if declared is not None:
        bad = [v for v in declared if not (inspect.isclass(v) and issubclass(v, BaseVisual))]
        if bad:
            raise TypeError(f"VISUALS must only contain BaseVisual subclasses, got {bad!r}")
        return list(declared)
    return [
        obj
        for obj in vars(module).values()
        if inspect.isclass(obj)
        and issubclass(obj, BaseVisual)
        and obj is not BaseVisual
        and obj.__module__ == module.__name__
    ]
