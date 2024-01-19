import os
import tempfile
from pathlib import Path

import pytest

curdir = Path(__file__).parent
repo_dir = curdir.parent
test_output_dir = curdir / "outputs"


def test_read_write_ion():
    """Test basic read write"""
    from copy import copy, deepcopy

    from sparc.sparc_parsers.ion import _read_ion, _write_ion

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)
        test_ion = tempdir / "test.ion"
        test_ion_w = tempdir / "test_w.ion"
        ion_content = """#=========================
# format of ion file
#=========================
# ATOM_TYPE: <atom type name> <valence charge>
# N_TYPE_ATOM: <num of atoms of this type>
# COORD:
# <xcoord> <ycoord> <zcoord>
# ...
# RELAX:
# <xrelax> <yrelax> <zrelax>
# ...


# Reminder: when changing number of atoms, change the RELAX flags accordingly
#           as well.

ATOM_TYPE: Si                # atom type followed with valence charge
PSEUDO_POT: ../../../psps/14_Si_4_1.9_1.9_pbe_n_v1.0.psp8
N_TYPE_ATOM: 1               # number of atoms of this type
COORD:                       # coordinates follows
6.5 6.5 6.5


ATOM_TYPE: H                 # atom type followed with valence charge
PSEUDO_POT:  ../../../psps/01_H_1_1.0_1.0_pbe_v1.0.psp8   # pseudopotential
N_TYPE_ATOM: 4               # number of atoms of this type
COORD:                       # coordinates follows
8.127432021000001   8.127432021000001   8.127432021000001
4.872567978999999   4.872567978999999   8.127432021000001
4.872567978999999   8.127432021000001   4.872567978999999
8.127432021000001   4.872567978999999   4.872567978999999


    """
        with open(test_ion, "w") as fd:
            fd.write(ion_content)

        data_dict = _read_ion(test_ion)
        assert "ion" in data_dict
        assert "atom_blocks" in data_dict["ion"]
        assert data_dict["ion"]["atom_blocks"][0]["ATOM_TYPE"] == "Si"
        assert data_dict["ion"]["atom_blocks"][0]["N_TYPE_ATOM"] == 1
        assert data_dict["ion"]["atom_blocks"][1]["ATOM_TYPE"] == "H"
        assert data_dict["ion"]["atom_blocks"][1]["N_TYPE_ATOM"] == 4
        assert "comments" in data_dict["ion"]
        assert len(data_dict["ion"]["sorting"]["sort"]) == 0

        # Write test
        with pytest.raises(ValueError):
            _write_ion(test_ion_w, {})
        with pytest.raises(ValueError):
            _write_ion(test_ion_w, {"ion": {}})
        _write_ion(test_ion_w, data_dict)
        new_data_dict = _read_ion(test_ion_w)

        assert (
            new_data_dict["ion"]["comments"][0]
            == "Ion File Generated by SPARC ASE Calculator"
        )
        # Make a no comment file
        data_dict_wo_comment = deepcopy(data_dict)
        data_dict_wo_comment["ion"]["comments"] = []
        _write_ion(test_ion_w, data_dict_wo_comment)

        new_data_dict = _read_ion(test_ion_w)

        assert len(new_data_dict["ion"]["comments"]) == 1
        assert new_data_dict["ion"]["atom_blocks"][0]["N_TYPE_ATOM"] == 1
        assert new_data_dict["ion"]["atom_blocks"][1]["N_TYPE_ATOM"] == 4


def test_read_write_ion_w_sort():
    """Test basic read write"""
    from copy import copy, deepcopy

    from sparc.sparc_parsers.ion import _read_ion, _write_ion

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)
        test_ion = tempdir / "test.ion"
        test_ion_w = tempdir / "test_w.ion"

        ion_content = """#=========================
# format of ion file
#=========================
# ATOM_TYPE: <atom type name> <valence charge>
# N_TYPE_ATOM: <num of atoms of this type>
# COORD:
# <xcoord> <ycoord> <zcoord>
# ...
# RELAX:
# <xrelax> <yrelax> <zrelax>
# ...


# Reminder: when changing number of atoms, change the RELAX flags accordingly
#           as well.

# ASE-SORT:
# 1 2 3 4 0
# END ASE-SORT

# There is another comment line

ATOM_TYPE: Si                # atom type followed with valence charge
PSEUDO_POT: ../../../psps/14_Si_4_1.9_1.9_pbe_n_v1.0.psp8
N_TYPE_ATOM: 1               # number of atoms of this type
COORD:                       # coordinates follows
6.5 6.5 6.5


ATOM_TYPE: H                 # atom type followed with valence charge
PSEUDO_POT:  ../../../psps/01_H_1_1.0_1.0_pbe_v1.0.psp8   # pseudopotential
N_TYPE_ATOM: 4               # number of atoms of this type
COORD:                       # coordinates follows
8.127432021000001   8.127432021000001   8.127432021000001
4.872567978999999   4.872567978999999   8.127432021000001
4.872567978999999   8.127432021000001   4.872567978999999
8.127432021000001   4.872567978999999   4.872567978999999
"""
        with open(test_ion, "w") as fd:
            fd.write(ion_content)

        data_dict = _read_ion(test_ion)
        assert all(["ASE-SORT" not in line for line in data_dict["ion"]["comments"]])
        assert tuple(data_dict["ion"]["sorting"]["sort"]) == (4, 0, 1, 2, 3)
        assert tuple(data_dict["ion"]["sorting"]["resort"]) == (1, 2, 3, 4, 0)

        _write_ion(test_ion_w, data_dict)
        new_data_dict = _read_ion(test_ion_w)


def test_ion_coord_conversion():
    import numpy as np
    from ase.units import Angstrom, Bohr

    from sparc.sparc_parsers.ion import _ion_coord_to_ase_pos

    data_dict1 = {
        "ion": {
            "atom_blocks": [
                {
                    "ATOM_TYPE": "Cu",
                    "ATOMIC_MASS": "63.546",
                    "PSEUDO_POT": "../../../psps/29_Cu_19_1.7_1.9_pbe_n_v1.0.psp8",
                    "N_TYPE_ATOM": 4,
                    "COORD_FRAC": np.array(
                        [
                            [0.0, 0.0, 0.0],
                            [0.0, 0.5, 0.5],
                            [0.5, 0.0, 0.5],
                            [0.5, 0.5, 0.0],
                        ]
                    ),
                }
            ],
            "comments": [
                "=========================",
                "format of ion file",
                "=========================",
                "ATOM_TYPE: <atom type name>",
                "N_TYPE_ATOM: <num of atoms of this type>",
                "COORD:",
                "<xcoord> <ycoord> <zcoord>",
                "...",
                "RELAX:",
                "<xrelax> <yrelax> <zrelax>",
                "...",
                "atom type",
                "atomic mass (amu)",
                "pseudopotential file",
                "number of atoms of this type",
                "COORD:                      # Cartesian coordinates (au)",
                "fractional coordinates (in lattice vector basis)",
            ],
            "sorting": {"sort": [3, 2, 1, 0], "resort": [3, 2, 1, 0]},
        }
    }
    # FCC Cu
    cell = np.eye(3) * 2.867
    _ion_coord_to_ase_pos(data_dict1, cell)
    assert "_ase_positions" in data_dict1["ion"]["atom_blocks"][0]
    assert np.isclose(
        data_dict1["ion"]["atom_blocks"][0]["_ase_positions"][1, 1], 2.867 / 2
    )

    data_dict2 = {
        "ion": {
            "atom_blocks": [
                {
                    "ATOM_TYPE": "Cu",
                    "ATOMIC_MASS": "63.546",
                    "PSEUDO_POT": "../../../psps/29_Cu_19_1.7_1.9_pbe_n_v1.0.psp8",
                    "N_TYPE_ATOM": 4,
                    "COORD": np.array(
                        [
                            [0.0, 0.0, 0.0],
                            [0.0, 0.5, 0.5],
                            [0.5, 0.0, 0.5],
                            [0.5, 0.5, 0.0],
                        ]
                    )
                    * 5.416914,
                }
            ],
            "comments": [
                "=========================",
                "format of ion file",
                "=========================",
                "ATOM_TYPE: <atom type name>",
                "N_TYPE_ATOM: <num of atoms of this type>",
                "COORD:",
                "<xcoord> <ycoord> <zcoord>",
                "...",
                "RELAX:",
                "<xrelax> <yrelax> <zrelax>",
                "...",
                "atom type",
                "atomic mass (amu)",
                "pseudopotential file",
                "number of atoms of this type",
                "COORD:                      # Cartesian coordinates (au)",
                "fractional coordinates (in lattice vector basis)",
            ],
            "sorting": {"sort": [3, 2, 1, 0], "resort": [3, 2, 1, 0]},
        }
    }

    # A fake cell, this should not interfere
    cell = np.eye(3) * 3.00
    _ion_coord_to_ase_pos(data_dict2, cell)
    assert "_ase_positions" in data_dict2["ion"]["atom_blocks"][0]
    assert np.isclose(
        data_dict2["ion"]["atom_blocks"][0]["_ase_positions"][1, 1],
        5.416914 * 0.5 * Bohr / Angstrom,
    )

    data_dict3 = data_dict2.copy()
    data_dict3["ion"]["atom_blocks"][0]["COORD_FRAC"] = data_dict1["ion"][
        "atom_blocks"
    ][0]["COORD_FRAC"]
    # Duplicate COORD and COORD_FRAC
    with pytest.raises(KeyError):
        _ion_coord_to_ase_pos(data_dict3, cell)

    with pytest.raises(KeyError):
        _ion_coord_to_ase_pos(data_dict3, cell=None)


def test_read_sort():
    from sparc.sparc_parsers.ion import InvalidSortingComment, _read_sort_comment

    comments = [
        "=========================",
        "format of ion file",
        "=========================",
        "ATOM_TYPE: <atom type name>",
        "N_TYPE_ATOM: <num of atoms of this type>",
        "COORD:",
        "<xcoord> <ycoord> <zcoord>",
        "...",
        "RELAX:",
        "<xrelax> <yrelax> <zrelax>",
        "...",
        "atom type",
        "atomic mass (amu)",
        "pseudopotential file",
        "number of atoms of this type",
        "COORD:                      # Cartesian coordinates (au)",
        "fractional coordinates (in lattice vector basis)",
        "ASE-SORT:",
        "0 1 ",
        "2",
        "3",
        "END ASE-SORT",
        "There are more comments below",
        "One more comment line",
    ]
    sort, resort, new_lines = _read_sort_comment(comments)
    assert tuple(sort) == (0, 1, 2, 3)
    assert tuple(resort) == (0, 1, 2, 3)
    assert "There are more comments below" in new_lines
    assert len(new_lines) == len(comments) - 5

    # Test invalid comment
    comments2 = [
        "=========================",
        "format of ion file",
        "=========================",
        "ATOM_TYPE: <atom type name>",
        "N_TYPE_ATOM: <num of atoms of this type>",
        "COORD:",
        "<xcoord> <ycoord> <zcoord>",
        "...",
        "RELAX:",
        "<xrelax> <yrelax> <zrelax>",
        "...",
        "atom type",
        "atomic mass (amu)",
        "pseudopotential file",
        "number of atoms of this type",
        "COORD:                      # Cartesian coordinates (au)",
        "fractional coordinates (in lattice vector basis)",
        "ASE-SORT:",
        "0 1 ",
        "2",
        "3",
        "END ASE-SORT",
        "There are more comments below",
        "One more comment line",
        "ASE-SORT:",
        "0 1 ",
        "2",
        "3",
        "END ASE-SORT",
    ]
    with pytest.raises(InvalidSortingComment):
        _read_sort_comment(comments2)
