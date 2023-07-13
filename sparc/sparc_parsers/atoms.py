"""Convert ase atoms to structured dict following SPARC format
and vice versa
"""

import numpy as np

from ase import Atoms, Atom
from ase.units import Bohr

# from .sparc_parsers.ion import read_ion, write_ion

from .ion import _ion_coord_to_ase_pos
from .inpt import _inpt_cell_to_ase_cell
from .pseudopotential import find_pseudo_path
from .utils import make_reverse_mapping
from ase.constraints import FixAtoms, FixedLine, FixedPlane

from warnings import warn
from copy import deepcopy


def atoms_to_dict(
    atoms,
    sort=True,
    direct=False,
    wrap=False,
    ignore_constraints=False,
    psp_dir=None,
    pseudopotentials={},
    comments="",
):
    """Given an ASE Atoms object, convert to SPARC ion and inpt data dict

    psp_dir: search path for psp8 files pseudopotentials: a mapping
    between symbol and psp file names, similar to QE like 'Na':
    'Na-pbe.psp8'. If the file name does not contain path information,
    use psp_dir / filname, otherwise use the file path.

    We don't do any env variable replace ment for psp_dir, it should be handled by the
    explicit _write_ion_and_inpt() function

    At this step, the copy_psp is not applied, since we don't yet know the location to write

    """
    # Step 1: if we should sort the atoms?
    # origin_atoms = atoms.copy()
    # sort = True re-calculate the sorting information
    # sort = list re-uses the sorting information
    if sort:
        if isinstance(sort, list):
            sort_ = np.array(sort)
            resort_ = make_reverse_mapping(sort_)
        else:
            sort_ = np.argsort(atoms.get_chemical_symbols())
            resort_ = make_reverse_mapping(sort_)
        # This is the sorted atoms object
        atoms = atoms[sort_]
    else:
        sort_ = []
        resort_ = []

    # Step 2: determine the counts of each element
    symbol_counts = count_symbols(atoms.get_chemical_symbols())
    write_spin = np.any(atoms.get_initial_magnetic_moments() != 0)
    has_charge = np.any(atoms.get_initial_charges() != 0)
    if has_charge:
        warn(
            "SPARC currently doesn't support changing total number of electrons! "
            "via nomimal charges. The initial charges in the structure will be ignored."
        )

    relax_mask = relax_from_all_constraints(atoms.constraints, len(atoms))
    write_relax = (len(relax_mask) > 0) and (not ignore_constraints)

    atom_blocks = []
    # Step 3: write each block
    for symbol, start, end in symbol_counts:
        block_dict = {}
        block_dict["ATOM_TYPE"] = symbol
        block_dict["N_TYPE_ATOM"] = end - start
        # TODO: make pseudo finding work
        # TODO: write comment that psp file may not exist
        try:
            psp_file = find_pseudo_path(symbol, psp_dir, pseudopotentials)
            # TODO: add option to determine if psp file exists!
            block_dict["PSEUDO_POT"] = psp_file.resolve().as_posix()

        except Exception:
            warn(
                (
                    f"Failed to find pseudo potential file for symbol {symbol}. I will use a dummy file name"
                )
            )
            block_dict[
                "PSEUDO_POT"
            ] = f"{symbol}-dummy.psp8        # Please replace with real psp file name!"
        # TODO: atomic mass?
        p_atoms = atoms[start:end]
        if direct:
            pos = p_atoms.get_scaled_positions(wrap=wrap)
            block_dict["COORD_FRAC"] = pos
        else:
            # TODO: should we use default converter?
            pos = p_atoms.get_positions(wrap=wrap) / Bohr
            block_dict["COORD"] = pos
        if write_spin:
            # TODO: should we process atoms with already calculated magmoms?
            block_dict["SPIN"] = p_atoms.get_initial_magnetic_moments()
        if write_relax:
            relax_this_block = relax_mask[start:end]
            block_dict["RELAX"] = relax_this_block
        # TODO: get write_relax
        atom_blocks.append(block_dict)

    # Step 4: inpt part
    # TODO: what if atoms does not have cell?
    cell_au = atoms.cell / Bohr
    inpt_blocks = {"LATVEC": cell_au, "LATVEC_SCALE": [1.0, 1.0, 1.0]}

    if not isinstance(comments, list):
        comments = comments.split("\n")
    ion_data = {
        "atom_blocks": atom_blocks,
        "comments": comments,
        "sorting": {"sort": sort_, "resort": resort_},
    }
    inpt_data = {"params": inpt_blocks, "comments": []}
    return {"ion": ion_data, "inpt": inpt_data}


def dict_to_atoms(data_dict):
    """Given a SPARC struct dict, construct the ASE atoms object

    Note: this method supports only 1 Atoms at a time
    """
    ase_cell = _inpt_cell_to_ase_cell(data_dict)
    new_data_dict = deepcopy(data_dict)
    _ion_coord_to_ase_pos(new_data_dict, ase_cell)
    # Now the real thing to construct an atom object
    atoms = Atoms()
    atoms.cell = ase_cell
    relax_dict = {}

    atoms_count = 0
    atom_blocks = new_data_dict["ion"]["atom_blocks"]
    for block in atom_blocks:
        element = block["ATOM_TYPE"]
        positions = block["_ase_positions"]
        if positions.ndim == 1:
            positions = positions.reshape(1, -1)
            # Consider moving spins to another function
        spins = block.get("SPIN", None)
        if spins is None:
            spins = np.zeros(len(positions))
        for pos, spin in zip(positions, spins):
            # TODO: What about charge?
            atoms.append(Atom(symbol=element, position=pos, magmom=spin))
        relax = block.get("RELAX", np.array([]))
        # Reshape relax into 2d array
        relax = relax.reshape((-1, 3))
        for i, r in enumerate(relax, start=atoms_count):
            relax_dict[i] = r
        atoms_count += len(positions)

    if "sorting" in data_dict["ion"]:
        resort = data_dict["ion"]["sorting"].get(
            "resort", np.arange(len(atoms))
        )
        # Resort may be None
        if len(resort) == 0:
            resort = np.arange(len(atoms))
    else:
        resort = np.arange(len(atoms))

    if len(resort) != len(atoms):
        # TODO: new exception
        raise ValueError(
            "Length of resort mapping is different from the number of atoms!"
        )
    # TODO: check if this mapping is correct
    print(relax_dict)
    sort = make_reverse_mapping(resort)
    print(resort, sort)
    sorted_relax_dict = {sort[i]: r for i, r in relax_dict.items()}
    # Now we do a sort on the atom indices. The atom positions read from
    # .ion correspond to the `sort` and we use `resort` to transform

    # TODO: should we store the sorting information in SparcBundle?

    atoms = atoms[resort]
    constraints = constraints_from_relax(sorted_relax_dict)
    atoms.constraints = constraints

    # TODO: set pbc and relax
    atoms.pbc = True
    return atoms


def count_symbols(symbols):
    """Count the number of consecutive elements.
    Output tuple is: element, start, end
    For example, "CHCHHO" --> [('C', 0, 1), ('H', 1, 2), ('C', 2, 3), ('H', 3, 5), ('O', 5, 6)]
    """
    counts = []
    current_count = 1
    current_symbol = symbols[0]
    for i, symbol in enumerate(symbols[1:], start=1):
        if symbol == current_symbol:
            current_count += 1
        else:
            counts.append((current_symbol, i - current_count, i))
            current_count = 1
            current_symbol = symbol
    end = len(symbols)
    counts.append((current_symbol, end - current_count, end))
    return counts


def constraints_from_relax(relax_dict):
    """
    Convert the SPARC RELAX fields to ASE's constraints

    Arguments
    relax: bool vector of size Nx3, i.e. [[True, True, True], [True, False, False]]

    Supported ase constraints will be FixAtoms, FixedLine and FixedPlane.
    For constraints in the same direction, all indices will be gathered.

    Note: ase>=3.22 will have FixedLine and FixedPlane accepting only 1 index at a time!

    The relax vector must be already sorted!
    """
    if len(relax_dict) == 0:
        return []

    cons_list = []
    # gathered_indices is an intermediate dict that contains
    # key: relax mask if not all True
    # indices: indices that share the same mask
    #
    gathered_indices = {}

    # breakpoint()
    for i, r in relax_dict.items():
        r = np.array(r)
        r = tuple(np.ndarray.tolist(r.astype(bool)))
        if np.all(r):
            continue

        if r not in gathered_indices:
            gathered_indices[r] = [i]
        else:
            gathered_indices[r].append(i)

    for relax_type, indices in gathered_indices.items():
        degree_freedom = 3 - relax_type.count(False)

        # DegreeF == 0 --> fix atom
        if degree_freedom == 0:
            cons_list.append(FixAtoms(indices=indices))
        # DegreeF == 1 --> move along line, fix line
        elif degree_freedom == 1:
            for ind in indices:
                cons_list.append(
                    FixedLine(ind, np.array(relax_type).astype(int))
                )
        # DegreeF == 1 --> move along line, fix plane
        elif degree_freedom == 2:
            for ind in indices:
                cons_list.append(
                    FixedPlane(ind, (~np.array(relax_type)).astype(int))
                )
    return cons_list


def relax_from_constraint(constraint):
    """returns dict of {atom_index: relax_dimensions} for the given constraint"""
    type_name = constraint.todict()["name"]
    if isinstance(constraint, FixAtoms):
        dimensions = [False] * 3
        expected_free = 0
    elif isinstance(constraint, FixedLine):
        # Only supports orthogonal basis!
        dimensions = [d == 1 for d in constraint.dir]
        expected_free = 1
    elif isinstance(constraint, FixedPlane):
        dimensions = [d != 1 for d in constraint.dir]
        expected_free = 2
    else:
        warn(
            f"The constraint type {type_name} is not supported by"
            " SPARC's .ion format. This constraint will be"
            " ignored"
        )
        return {}
    if dimensions.count(True) != expected_free:
        warn(
            "SPARC's .ion filetype can only support freezing entire "
            f"dimensions (x,y,z). The {type_name} constraint will be ignored"
        )
        return {}
    return {i: dimensions for i in constraint.get_indices()}  # atom indices


def relax_from_all_constraints(constraints, natoms):
    """converts ASE atom constraints to SPARC relaxed dimensions for the atoms"""
    if len(constraints) == 0:
        return []

    relax = [
        [True, True, True],
    ] * natoms  # assume relaxed in all dimensions for all atoms
    for c in constraints:
        for atom_index, rdims in relax_from_constraint(c).items():
            if atom_index >= natoms:
                raise ValueError(
                    (
                        "Number of total atoms smaller than the constraint indices!\n"
                        "Please check your input"
                    )
                )
            # There might be multiple constraints applied on one index,
            # always make it more constrained
            relax[atom_index] = list(np.bitwise_and(relax[atom_index], rdims))
    return relax