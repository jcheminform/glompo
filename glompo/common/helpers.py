""" Useful static functions used throughout GloMPO. """
import os
from typing import Optional, Sequence, Tuple, Union

import numpy as np
import yaml

__all__ = ("LiteralWrapper",
           "FileNameHandler",
           "nested_string_formatting",
           "is_bounds_valid",
           "literal_presenter",
           "distance",
           "glompo_colors")


def nested_string_formatting(nested_str: str) -> str:
    """ Reformat strings produced by the _CombiCore class (used by hunter and checkers) by indenting each level
        depending on its nested level.
    """

    # Strip first and last parenthesis if there
    if nested_str[0] == '[':
        nested_str = nested_str[1:]
    if nested_str[-1] == ']':
        nested_str = nested_str[:-1]

    # Move each level to new line
    nested_str = nested_str.replace('[', '[\n')
    nested_str = nested_str.replace(']', '\n]')

    # Split into lines
    level_count = 0
    lines = nested_str.split('\n')

    # Indent based on number of opening and closing brackets seen.
    for i, line in enumerate(lines):
        if '[' in line:
            lines[i] = f"{' ' * level_count}{line}"
            level_count += 1
            continue
        if ']' in line:
            level_count -= 1
        lines[i] = f"{' ' * level_count}{line}"

    nested_str = "\n".join(lines)

    return nested_str


def is_bounds_valid(bounds: Sequence[Tuple[float, float]], raise_invalid=True) -> bool:
    """ Checks if provided bounds are valid.
        If True raise_invalid raises an error if the bounds are invalid otherwise a bool is returned.
    """

    for bnd in bounds:
        if bnd[0] >= bnd[1]:
            if raise_invalid:
                raise ValueError("Invalid bounds encountered. Min and max bounds may not be equal nor may they be in"
                                 "the opposite order. ")
            return False

        if not np.all(np.isfinite(bnd)):
            if raise_invalid:
                raise ValueError("Non-finite bounds found.")
            return False

    return True


def literal_presenter(dumper: yaml.Dumper, data: str):
    """ Wrapper around string for correct presentation in YAML file. """
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.replace(' \n', '\n'), style='|')


def distance(pt1: Sequence[float], pt2: Sequence[float]):
    """ Calculate the straight line distance between two points in Euclidean space. """
    return np.sqrt(np.sum((np.array(pt1) - np.array(pt2)) ** 2))


def glompo_colors(opt_id: Optional[int] = None) -> Union['matplotlib.colors.ListedColormap', Tuple]:
    """ Returns a matplotlib Colormap instance containing the custom GloMPO color cycle.
        If opt_id is provided than the specific color at that index is returned instead.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    colors = []
    for cmap in ("tab20", "tab20b", "tab20c", "Set1", "Set2", "Set3", "Dark2"):
        for col in plt.get_cmap(cmap).colors:
            colors.append(col)

    cmap = ListedColormap(colors, "glompo_colormap")
    if opt_id:
        return cmap(opt_id)

    return cmap


class LiteralWrapper(str):
    """ Used by yaml to save some block strings as literals """


class FileNameHandler:
    """ Context manager to manage the creation of new files in a different directory from the working one. """

    def __init__(self, name: str):
        """ Decomposes name into a path to a new directory. The final leaf (directory or file) is returned when the
            context manager is created and the working directory is changed to one level up from this final leaf while
            within the context manager. The working directory is returned when exiting the manager.
        """
        self.filename = name
        self.orig_dir = os.getcwd()
        if os.sep in name:
            path, self.filename = name.rsplit(os.sep, 1)
            os.makedirs(path, exist_ok=True)
            os.chdir(path)

    def __enter__(self):
        return self.filename

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.orig_dir)
