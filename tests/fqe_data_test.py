#   Copyright 2020 Google LLC

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http:gc/www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""Unittesting for the fqe_data module
"""
import copy
from io import StringIO
from itertools import product
import os
import sys

import pytest

import numpy

import openfermion as of

from fqe import fqe_data
from fqe import fci_graph
import tests.unittest_data as fud
from tests.unittest_data.fqe_data_loader import FqeDataLoader
from tests.unittest_data.build_hamiltonian \
     import to_spin1, to_spin2, to_spin3, to_spin4, build_H3
import fqe
import fqe.settings


def test_fqe_init(c_or_python):
    """Check that we initialize the private values
    """
    fqe.settings.use_accelerated_code = c_or_python
    test = fqe_data.FqeData(2, 4, 10)
    assert test.n_electrons() == 6
    assert test.nalpha() == 2
    assert test.nbeta() == 4
    assert test.lena() == 45
    assert test.lenb() == 210
    pre_graph = fci_graph.FciGraph(2, 4, 10)
    test = fqe_data.FqeData(2, 4, 10, fcigraph=pre_graph)
    assert isinstance(test, fqe_data.FqeData)


def test_fqe_init_raises():
    """Check whether initialization with an incorrect FciGraph
       raises an exception.
    """
    wrong_graph = fci_graph.FciGraph(1, 4, 10)
    with pytest.raises(ValueError):
        _ = fqe_data.FqeData(2, 4, 10, wrong_graph)


def test_fqe_data_scale():
    """Scale the entire vector
    """
    test = fqe_data.FqeData(1, 1, 2)
    test.scale(0. + .0j)
    ref = numpy.zeros((2, 2), dtype=numpy.complex128)
    assert numpy.allclose(test.coeff, ref)


def test_fqe_data_fill():
    """Fill the coefficient vector
    """
    test = fqe_data.FqeData(1, 1, 2)
    test.fill(1. + .0j)
    ref = numpy.ones((2, 2), dtype=numpy.complex128)
    assert numpy.allclose(test.coeff, ref)


def test_fqe_data_generator():
    """Access each element of any given vector
    """
    test = fqe_data.FqeData(1, 1, 2)
    gtest = test.generator()
    testx = list(next(gtest))
    assert [1, 1, .0 + 0.j] == testx
    testx = list(next(gtest))
    assert [1, 2, .0 + .0j] == testx
    testx = list(next(gtest))
    assert [2, 1, .0 + .0j] == testx
    testx = list(next(gtest))
    assert [2, 2, .0 + .0j] == testx


def test_fqe_data_set_add_element_and_retrieve():
    """Set elements and retrieve them one by one
    """
    test = fqe_data.FqeData(1, 1, 2)
    test[(2, 2)] = 3.14 + .00159j
    assert test[(2, 2)] == 3.14 + .00159j
    test[(2, 1)] = 1.61 + .00803j
    assert test[(2, 1)] == 1.61 + .00803j


def test_fqe_data_init_vec():
    """Set vectors in the fqedata set using different strategies
    """
    test = fqe_data.FqeData(1, 1, 2)
    test.set_wfn(strategy='ones')
    ref = numpy.ones((2, 2), dtype=numpy.complex128)
    assert numpy.allclose(test.coeff, ref)
    test.set_wfn(strategy='zero')
    ref = numpy.zeros((2, 2), dtype=numpy.complex128)
    assert numpy.allclose(test.coeff, ref)
    test.set_wfn(strategy='hartree-fock')
    ref = numpy.zeros((2, 2), dtype=numpy.complex128)
    ref[0, 0] = 1
    assert numpy.allclose(test.coeff, ref)


def test_fqe_data_set_wfn_data():
    """Set vectors in the fqedata set from a data block
    """
    test = fqe_data.FqeData(1, 1, 2)
    ref = numpy.random.rand(2, 2) + 1.j * numpy.random.rand(2, 2)
    test.set_wfn(strategy='from_data', raw_data=ref)
    assert numpy.allclose(test.coeff, ref)


def test_fqe_data_manipulation():
    """The fqedata can be conjugated in place
    """
    test = fqe_data.FqeData(1, 1, 2)
    ref = numpy.random.rand(2, 2) + 1.j * numpy.random.rand(2, 2)
    test.set_wfn(strategy='from_data', raw_data=ref)
    assert numpy.allclose(test.beta_inversion(), ref[:, (1, 0)])
    test.conj()
    assert numpy.allclose(test.coeff, numpy.conj(ref))


def test_fqe_deepcopy():
    test = fqe_data.FqeData(1, 1, 2)
    test.set_wfn(strategy='ones')
    out = copy.deepcopy(test)
    assert test.coeff is not out.coeff
    assert numpy.allclose(test.coeff, out.coeff)
    assert test._core is out._core


def test_fqe_empty_copy():
    test = fqe_data.FqeData(1, 1, 2)
    ref = numpy.random.rand(2, 2) + 1.j * numpy.random.rand(2, 2)
    test.set_wfn(strategy='from_data', raw_data=ref)
    test2 = test.empty_copy()
    assert test.coeff.shape == test2.coeff.shape
    assert not numpy.any(test2.coeff)


def test_fqe_data_initialize_errors():
    """There are many ways to not initialize a wavefunction
    """
    bad0 = numpy.ones((5, 3), dtype=numpy.complex64)
    bad1 = numpy.ones((4, 6), dtype=numpy.complex64)
    good1 = numpy.random.rand(2, 2) + numpy.random.rand(2, 2) * 1.j
    test = fqe_data.FqeData(1, 1, 2)
    with pytest.raises(ValueError):
        test.set_wfn()
    with pytest.raises(ValueError):
        test.set_wfn(strategy='from_data')
    with pytest.raises(AttributeError):
        test.set_wfn(strategy='ones', raw_data=1)
    with pytest.raises(ValueError):
        test.set_wfn(strategy='onse')
    with pytest.raises(ValueError):
        test.set_wfn(strategy='ones', raw_data=good1)
    with pytest.raises(ValueError):
        test.set_wfn(strategy='from_data', raw_data=bad0)
    with pytest.raises(ValueError):
        test.set_wfn(strategy='from_data', raw_data=bad1)
    assert test.set_wfn(strategy='from_data', raw_data=good1) is None
    bad_graph = fci_graph.FciGraph(5, 6, 7)
    with pytest.raises(ValueError):
        fqe_data.FqeData(1, 1, 2, fcigraph=bad_graph)


@pytest.fixture
def fixture():
    test = fqe_data.FqeData(1, 2, 4)
    test.set_wfn(strategy='random')
    return test


def test_fqe_data_vacuum():
    """Make sure that the vacuum exists
    """
    test = fqe_data.FqeData(0, 0, 2)
    assert test.n_electrons() == 0
    assert test.nalpha() == 0
    assert test.nbeta() == 0
    assert test.lena() == 1
    assert test.lenb() == 1


def test_get_fcigraph():
    """Test consistency of get_fcigraph
    """
    test = fqe_data.FqeData(1, 1, 2)
    assert test.get_fcigraph() is test._core


def test_apply_diagonal_unitary_dim(fixture):
    """Diagonal evoltion requires only the diagonal elements
    """
    h1e = numpy.random.rand(4, 4)
    with pytest.raises(ValueError):
        fixture.evolve_diagonal(h1e)


def test_apply_diagonal_inplace_raises(fixture):
    """Check if apply_diagonal_inplace fails for non-diagonal Hamiltonians
    """
    bad_h1e = numpy.random.rand(6, 6)
    with pytest.raises(ValueError):
        fixture.apply_diagonal_inplace(bad_h1e)


def test_apply_inplace_empty(fixture):
    """Check if apply_diagonal_inplace works for no arrays
    """
    test = copy.deepcopy(fixture)
    fixture.apply_inplace((None, None))
    assert numpy.allclose(test.coeff, fixture.coeff)


def test_apply_diagonal_inplace(c_or_python, fixture):
    """Check apply_diagonal_inplace for special cases
    """
    fqe.settings.use_accelerated_code = c_or_python
    h1e = numpy.ones(8, dtype=numpy.complex128)
    ref = copy.deepcopy(fixture)
    print(ref.coeff)
    fixture.apply_diagonal_inplace(h1e)
    print(fixture.coeff)
    assert numpy.allclose(ref.coeff * 3.0, fixture.coeff)

    # test when passing non-contiguous array
    ref = copy.deepcopy(fixture)
    h1big = numpy.ones((8, 10), dtype=numpy.complex128)
    fixture.apply_diagonal_inplace(h1big[:, 2])
    assert numpy.allclose(ref.coeff * 3.0, fixture.coeff)


def test_evolve_diagonal(c_or_python, fixture):
    """Test evolve_diagonal
    """
    fqe.settings.use_accelerated_code = c_or_python
    h1e = numpy.ones(8, dtype=numpy.complex128) * numpy.pi * 1.j
    test = fixture
    ref = copy.deepcopy(test)
    ocoeff = test.evolve_diagonal(h1e)
    # for non-contiguous array, inplace
    h1big = numpy.ones((8, 10), dtype=numpy.complex128) * numpy.pi * 1.j
    fixture.evolve_diagonal(h1big[:, 3], inplace=True)
    assert numpy.allclose(ref.coeff, -1 * ocoeff)
    assert numpy.allclose(ref.coeff, -1 * fixture.coeff)


def test_evolve_diagonal_coulomb(c_or_python):
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    hamil = loader.get_diagonal_coulomb()
    diag, vij = hamil.iht(0.1)
    out = test.evolve_diagonal_coulomb(diag, vij)
    ref = loader.get_diagonal_coulomb_ref()
    assert numpy.allclose(ref, out)


def test_diagonal_coulomb_inplace():
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    hamil = loader.get_diagonal_coulomb()
    diag, vij = hamil.iht(0.1)
    out = test.evolve_diagonal_coulomb(diag, vij)
    test.evolve_diagonal_coulomb(diag, vij, inplace=True)
    assert numpy.allclose(out, test.coeff)


def test_diagonal_coulomb_vs_array(c_or_python):
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    rng = numpy.random.default_rng(454417)
    data = fqe_data.FqeData(nalpha, nbeta, norb)
    data.set_wfn(strategy='ones')
    data.scale(1. / data.norm())

    # random diagonal coulomb operator
    vij = 8 * rng.uniform(0, 1, size=(norb, norb))
    h2 = numpy.zeros((norb, norb, norb, norb))
    h1 = numpy.zeros((norb, norb))
    diag = numpy.zeros((norb))
    h1 = numpy.zeros((norb, norb))
    for i in range(norb):
        diag[i] = -vij[i, i]
        for j in range(norb):
            h2[i, j, i, j] = -vij[i, j]

    out = data.apply_diagonal_coulomb(diag, vij)
    ref = data.apply((h1, h2))
    assert numpy.allclose(ref.coeff, out)

    # test inplace
    data.apply_diagonal_coulomb(diag, vij, inplace=True)
    assert numpy.allclose(ref.coeff, data.coeff)


def test_indv_nbody(c_or_python):
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    daga = [1]
    undaga = [2]
    dagb = []
    undagb = []
    ref = loader.get_indv_ref(daga, undaga, dagb, undagb)
    out = test.apply_individual_nbody(complex(1), daga, undaga, dagb, undagb)
    assert numpy.allclose(ref, out.coeff)


def test_indv_nbody_empty_map():
    """ Test if apply_individual_nbody_accumulate is doing nothing
        for empty alpha and beta maps
    """

    norb = 3
    nalpha = 2
    nbeta = 2

    test = fqe_data.FqeData(nalpha, nbeta, norb)
    test.set_wfn(strategy='ones')

    test_ref = copy.deepcopy(test)

    # test for alpha maps
    daga = [2, 0, 1]
    undaga = [2, 1, 0]
    dagb = []
    undagb = []

    test.apply_individual_nbody_accumulate(1., test, daga, undaga, \
                                                     dagb, undagb)

    assert numpy.all(test.coeff == test_ref.coeff)

    # test for beta maps
    daga = []
    undaga = []
    dagb = [2, 0, 1]
    undagb = [2, 1, 0]

    test.apply_individual_nbody_accumulate(1., test, daga, undaga, \
                                                     dagb, undagb)

    assert numpy.all(test.coeff == test_ref.coeff)


def test_evolve_inplace_nbody_trivial(c_or_python):
    """Test 'evolve_inplace_nbody_trivial' using 'evolve_diagonal'
    """
    fqe.settings.use_accelerated_code = c_or_python
    test = fqe_data.FqeData(1, 2, 4)
    test.set_wfn(strategy='ones')
    ref = copy.deepcopy(test)

    h1e = numpy.zeros(8, dtype=numpy.complex128)
    h1e[0] = 1.j * numpy.pi
    ocoeff = test.evolve_diagonal(h1e)

    test.evolve_inplace_individual_nbody_trivial(numpy.pi / 2, 1, [0], [])
    assert numpy.allclose(ocoeff, test.coeff)


def test_evolve_individual_nbody_nontrivial(c_or_python):
    """ Test evolve_individual_nbody_nontrivial
    """
    fqe.settings.use_accelerated_code = c_or_python

    time = 0.001
    coeff = 0.5

    daga = [2, 0]
    undaga = [2, 1]
    dagb = [1, 0]
    undagb = [1, 0]

    norb = 3
    nalpha = 2
    nbeta = 2

    data = fqe_data.FqeData(nalpha, nbeta, norb)

    data.set_wfn(strategy='ones')
    data.scale(1. / data.norm())

    evolved_data = data.evolve_individual_nbody_nontrivial(
        time, coeff, daga, undaga, dagb, undagb)

    ref_coeff = numpy.array(
        [[0.33333333 + 0.j, 0.33333333 + 0.j, 0.33333333 + 0.j],
         [0.33333329 - 0.00016667j, 0.33333333 + 0.j, 0.33333333 + 0.j],
         [0.33333329 - 0.00016667j, 0.33333333 + 0.j, 0.33333333 + 0.j]])

    assert numpy.allclose(evolved_data.coeff, ref_coeff)


def test_apply_raises(fixture):
    """ Check if apply throws exceptions because of incorrect dimensions
        of operator array or orbitals.
    """
    empty_operators = ()
    with pytest.raises(ValueError):
        _ = fixture.apply(empty_operators)
    h1 = numpy.random.rand(2, 2)
    with pytest.raises(ValueError):
        _ = fixture.apply((h1,))


def test_apply1_spatial(c_or_python):
    """ Check apply for 1-body operators only, spatial orbitals
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    h1 = loader.get_harray(1)
    ref = loader.get_href('1')
    out = test.apply((h1,))
    assert numpy.allclose(ref, out.coeff)


def test_apply_spatial1_onecolumn(c_or_python):
    """Test the code path for Python _apply_array_spatial1 with one column
    """
    fqe.settings.use_accelerated_code = c_or_python
    work = fqe_data.FqeData(2, 1, 3)
    work.set_wfn(strategy='ones')
    # dummy Hamiltonian with one nonzero column
    h1 = numpy.asarray(
        [[1.0 + 0.j, 0. + 0.j, 0.0 + 0.j], [0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j],
         [1.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j]],
        dtype=numpy.complex128)
    work.apply_inplace((h1,))
    assert numpy.allclose(
        work.coeff,
        numpy.asarray(
            [[2. + 0.j, 1. + 0.j, 2. + 0.j], [2. + 0.j, 1. + 0.j, 2. + 0.j],
             [0. + 0.j, -1. + 0.j, 0. + 0.j]],
            dtype=numpy.complex128))


@pytest.fixture
def onecolumn_fixture():
    work = fqe_data.FqeData(1, 1, 2)
    work.set_wfn(strategy='ones')
    return work


def test_apply_spin1_onecolumn_first(c_or_python, onecolumn_fixture):
    """Test the code path for Python _apply_array_spin1 with one column
       (first nonzero column)
    """
    fqe.settings.use_accelerated_code = c_or_python
    h1 = numpy.asarray([[1.0 + 0.j, 0. + 0.j, 0.0 + 0.j, 0.0 + 0.j],
                        [0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j],
                        [1.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j],
                        [1.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j]],
                       dtype=numpy.complex128)

    onecolumn_fixture.apply_inplace((h1,))
    assert numpy.allclose(
        onecolumn_fixture.coeff,
        numpy.asarray([[1. + 0.j, 1. + 0.j], [0. + 0.j, 0. + 0.j]],
                      dtype=numpy.complex128))


def test_apply_spin1_onecolumn_last(c_or_python, onecolumn_fixture):
    """Test the code path for Python _apply_array_spin1 with one column
       (first nonzero column)
    """
    fqe.settings.use_accelerated_code = c_or_python
    h1 = numpy.asarray([[0.0 + 0.j, 0. + 0.j, 0.0 + 0.j, 1.0 + 0.j],
                        [0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 1.0 + 0.j],
                        [0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j],
                        [0.0 + 0.j, 0.0 + 0.j, 0.0 + 0.j, 1.0 + 0.j]],
                       dtype=numpy.complex128)

    onecolumn_fixture.apply_inplace((h1,))
    assert numpy.allclose(
        onecolumn_fixture.coeff,
        numpy.asarray([[0. + 0.j, 1. + 0.j], [0. + 0.j, 1. + 0.j]],
                      dtype=numpy.complex128))


def test_apply12_spatial(c_or_python):
    """ Test _apply_array_spatial12
        (application of 1- and 2-body operators, spatial orbitals)
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    h1 = loader.get_harray(1)
    h2 = loader.get_harray(2)
    ref = loader.get_href('12')
    out = test.apply((h1, h2))
    assert numpy.allclose(ref, out.coeff)


@pytest.mark.parametrize("use_complex", [False, True])
def test_apply12_spatial(c_or_python, use_complex):
    """ Test _apply_array_spatial12 for a complex Hamiltonian
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 6
    nalpha = 2
    nbeta = 3

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    h1 = loader.get_harray(1)
    h2 = loader.get_harray(2)

    if use_complex:
        # convert h1 and h2 to complex to make sure
        # we're testing both real and complex codepaths
        h1 = h1.astype(numpy.complex128)
        h2 = h2.astype(numpy.complex128)
        # if imaginary part is zero numpy.iscomplex returns False
        # so we add a small complex component to pretend we have
        # a complex Hamiltonian
        h1 += (1e-7) * 1j
    ref = loader.get_href('12')
    out = test.apply((h1, h2))
    assert numpy.allclose(ref, out.coeff)


@pytest.fixture
def fixture_for_1234():
    norb = 4
    nalpha = 2
    nbeta = 1

    return FqeDataLoader(nalpha, nbeta, norb)


def test_apply123_spatial(c_or_python, fixture_for_1234):
    """ Test application of 1-, 2- and 3-body operators,
        spatial orbitals
    """
    fqe.settings.use_accelerated_code = c_or_python

    test = fixture_for_1234.get_fqe_data()
    h1 = fixture_for_1234.get_harray(1)
    h2 = fixture_for_1234.get_harray(2)
    h3 = fixture_for_1234.get_harray(3)
    ref = fixture_for_1234.get_href('123')
    out = test.apply((h1, h2, h3))
    assert numpy.allclose(ref, out.coeff)


def test_apply_3body_only(c_or_python, fixture_for_1234):
    """ Test application of the 3-body operator only
    """
    fqe.settings.use_accelerated_code = c_or_python

    test = fixture_for_1234.get_fqe_data()
    h3 = fixture_for_1234.get_harray(3)

    out = test.apply((None, None, h3))
    ref = numpy.array([[
        1.77037169 + 1.78556681j, 2.02983483 + 3.01074068j,
        3.82147367 + 2.32065247j, 4.76373241 + 3.53610165j
    ],
                       [
                           3.56436625 + 0.42831728j, 2.39560533 + 1.02255804j,
                           5.61350286 + 0.35078737j, 7.21582771 + 0.59595624j
                       ],
                       [
                           1.33053394 + 0.11884194j, -0.42788912 + 0.7387948j,
                           1.87629239 - 0.34479045j, 2.52754663 - 0.14313679j
                       ],
                       [
                           2.86556047 - 3.47122166j, 1.15265926 - 5.34148196j,
                           2.99598843 - 5.18765167j, 4.12435545 - 7.57196417j
                       ],
                       [
                           -2.18143974 - 4.51070818j, -5.27980187 - 6.7607571j,
                           -6.14420032 - 6.63702669j, -7.31839539 - 9.49151351j
                       ],
                       [
                           -6.8296471 - 0.28793326j, -7.60243083 - 0.18066159j,
                           -11.39744174 - 0.31132574j,
                           -14.39599744 - 0.14089318j
                       ]])
    assert numpy.allclose(ref, out.coeff)


def test_apply1234_spatial(c_or_python, fixture_for_1234):
    """ Test application of 1-, 2-, 3- and 4-body operators,
        spatial orbitals
    """
    fqe.settings.use_accelerated_code = c_or_python

    test = fixture_for_1234.get_fqe_data()
    h1 = fixture_for_1234.get_harray(1)
    h2 = fixture_for_1234.get_harray(2)
    h3 = fixture_for_1234.get_harray(3)
    h4 = fixture_for_1234.get_harray(4)
    ref = fixture_for_1234.get_href('1234')
    out = test.apply((h1, h2, h3, h4))
    assert numpy.allclose(ref, out.coeff)


def test_apply1234_spin(c_or_python):
    """ Test application of 1-, 2-, 3- and 4-body operators,
        spin orbitals
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 2
    nalpha = 1
    nbeta = 1

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    h1 = loader.get_harray(1)
    h2 = loader.get_harray(2)
    h3 = loader.get_harray(3)
    h4 = loader.get_harray(4)
    h1 = to_spin1(h1)
    h2 = to_spin2(h2)
    h3 = to_spin3(h3)
    h4 = to_spin4(h4)
    ref = loader.get_href('1234')
    out = test.apply((h1, h2, h3, h4))
    assert numpy.allclose(ref, out.coeff)


def test_rdm1234(c_or_python):
    fqe.settings.use_accelerated_code = c_or_python
    norb = 4
    nalpha = 2
    nbeta = 1

    loader = FqeDataLoader(nalpha, nbeta, norb)
    test = loader.get_fqe_data()
    rd1 = loader.get_rdm(1)
    rd2 = loader.get_rdm(2)
    rd3 = loader.get_rdm(3)
    rd4 = loader.get_rdm(4)
    od1, od2, od3, od4 = test.rdm1234()

    assert numpy.allclose(rd1, od1)
    assert numpy.allclose(rd2, od2)
    assert numpy.allclose(rd3, od3)
    assert numpy.allclose(rd4, od4)

    # test spin sum of 3-rdm
    pdm3 = test.get_three_pdm()
    out = pdm3[::2, ::2, ::2, ::2, ::2, ::2]
    out += pdm3[1::2, 1::2, 1::2, 1::2, 1::2, 1::2]
    out += pdm3[1::2, ::2, ::2, 1::2, ::2, ::2]
    out += pdm3[::2, 1::2, ::2, ::2, 1::2, ::2]
    out += pdm3[::2, ::2, 1::2, ::2, ::2, 1::2]
    out += pdm3[::2, 1::2, 1::2, ::2, 1::2, 1::2]
    out += pdm3[1::2, ::2, 1::2, 1::2, ::2, 1::2]
    out += pdm3[1::2, 1::2, ::2, 1::2, 1::2, ::2]
    assert numpy.allclose(rd3, out)


def test_1_body(c_or_python):
    """Check apply and rdm functions for 1-body terms
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 4
    scale = 4.071607802007311
    h1e_spa = numpy.zeros((norb, norb), dtype=numpy.complex128)
    for i in range(norb):
        for j in range(norb):
            h1e_spa[i, j] += (i + j) * 0.02
        h1e_spa[i, i] += i * 2.0

    h1e_spin = numpy.zeros((2 * norb, 2 * norb), dtype=numpy.complex128)
    h1e_spin[:norb, :norb] = h1e_spa
    h1e_spin[norb:, norb:] = h1e_spa

    wfn = numpy.asarray(
        [[
            -0.9986416294264632 + 0.j, 0.0284839005060597 + 0.j,
            0.0189102058837960 + 0.j, -0.0096809878541792 + 0.j,
            -0.0096884853951631 + 0.j, 0.0000930227399218 + 0.j
        ],
         [
             0.0284839005060596 + 0.j, -0.0008124361774354 + 0.j,
             -0.0005393690860379 + 0.j, 0.0002761273781438 + 0.j,
             0.0002763412278424 + 0.j, -0.0000026532545717 + 0.j
         ],
         [
             0.0189102058837960 + 0.j, -0.0005393690860379 + 0.j,
             -0.0003580822950200 + 0.j, 0.0001833184879206 + 0.j,
             0.0001834604608161 + 0.j, -0.0000017614718954 + 0.j
         ],
         [
             -0.0096809878541792 + 0.j, 0.0002761273781438 + 0.j,
             0.0001833184879206 + 0.j, -0.0000938490075630 + 0.j,
             -0.0000939216898957 + 0.j, 0.0000009017769626 + 0.j
         ],
         [
             -0.0096884853951631 + 0.j, 0.0002763412278424 + 0.j,
             0.0001834604608161 + 0.j, -0.0000939216898957 + 0.j,
             -0.0000939944285181 + 0.j, 0.0000009024753531 + 0.j
         ],
         [
             0.0000930227399218 + 0.j, -0.0000026532545717 + 0.j,
             -0.0000017614718954 + 0.j, 0.0000009017769626 + 0.j,
             0.0000009024753531 + 0.j, -0.0000000086650004 + 0.j
         ]],
        dtype=numpy.complex128)

    work = fqe_data.FqeData(2, 2, norb)
    work.coeff = numpy.copy(wfn)
    test = work.apply(tuple([h1e_spa]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    test = work.apply(tuple([h1e_spin]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    rdm1 = work.rdm1(work)
    energy = numpy.tensordot(h1e_spa, rdm1[0], axes=([0, 1], [0, 1]))
    assert round(abs(energy - scale), 7) == 0


def test_2_body(c_or_python):
    """Check apply for two body terms
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 4
    scale = -7.271991091302982
    h1e_spa = numpy.zeros((norb, norb), dtype=numpy.complex128)
    h2e_spa = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)
    for i in range(norb):
        for j in range(norb):
            for k in range(norb):
                for l in range(norb):
                    h2e_spa[i, j, k, l] += (i + k) * (j + l) * 0.02

    h2e_spin = numpy.zeros((2 * norb, 2 * norb, 2 * norb, 2 * norb),
                           dtype=numpy.complex128)
    h2e_spin[norb:, norb:, norb:, norb:] = h2e_spa
    h2e_spin[:norb, norb:, :norb, norb:] = h2e_spa
    h2e_spin[norb:, :norb, norb:, :norb] = h2e_spa
    h1e_spin = numpy.zeros((2 * norb, 2 * norb), dtype=numpy.complex128)

    wfn = numpy.asarray(
        [[
            -0. + 0.j, -0.0228521148088829 + 0.j, 0.0026141627151228 + 0.j,
            -0.0350670839771777 + 0.j, 0.0040114914627326 + 0.j,
            0.0649058425241095 + 0.j
        ],
         [
             0.0926888005534875 + 0.j, -0.0111089171383541 + 0.j,
             0.0727533722636203 + 0.j, -0.2088241794624313 + 0.j,
             -0.1296798587246719 + 0.j, 0.1794528138441346 + 0.j
         ],
         [
             -0.0106031152277513 + 0.j, -0.0163529872130018 + 0.j,
             -0.0063065366721411 + 0.j, -0.0031557043526629 + 0.j,
             0.0179284033727408 + 0.j, 0.0295275972773592 + 0.j
         ],
         [
             0.1422330484480838 + 0.j, 0.0302351700257210 + 0.j,
             0.1062328653022619 + 0.j, -0.2478900249182474 + 0.j,
             -0.2072966151359754 + 0.j, 0.1410812707838873 + 0.j
         ],
         [
             -0.0162707187155699 + 0.j, 0.0344029957577157 + 0.j,
             -0.0164836712764185 + 0.j, 0.0864570191796392 + 0.j,
             0.0170673494703135 + 0.j, -0.1236759770908710 + 0.j
         ],
         [
             -0.2632598664406648 + 0.j, -0.0049122508165550 + 0.j,
             -0.2024668199753644 + 0.j, 0.5371585425189981 + 0.j,
             0.3747249320637363 + 0.j, -0.4061235786466031 + 0.j
         ]],
        dtype=numpy.complex128)
    work = fqe_data.FqeData(2, 2, norb)
    work.coeff = numpy.copy(wfn)
    test = work.apply(tuple([h1e_spa, h2e_spa]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    test = work.apply(tuple([h1e_spin, h2e_spin]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)

    energy = 0.
    rdm2 = work.rdm12(work)
    energy = numpy.tensordot(h2e_spa,
                             rdm2[1],
                             axes=([0, 1, 2, 3], [0, 1, 2, 3]))
    assert round(abs(energy - scale), 7) == 0


def test_3_body(c_or_python):
    """Check appply for three body terms
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 4
    scale = -0.3559955456514945

    h1e_spa = numpy.zeros((norb, norb), dtype=numpy.complex128)
    h2e_spa = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)

    h1e_spin = numpy.zeros((2 * norb, 2 * norb), dtype=numpy.complex128)
    h2e_spin = numpy.zeros((2 * norb, 2 * norb, 2 * norb, 2 * norb),
                           dtype=numpy.complex128)

    h3e_spa = build_H3(norb)
    h3e_spin = to_spin3(h3e_spa)

    wfn = numpy.asarray(
        [[
            -0.0314812075046431 + 0.j, -0.0297693820182802 + 0.j,
            -0.3098997729788456 + 0.j, -0.0160305969536710 + 0.j,
            -0.1632524087723557 + 0.j, 0.0034291897632257 + 0.j
        ],
         [
             0.0164437672481284 + 0.j, 0.0992736004782678 + 0.j,
             -0.3815809991854478 + 0.j, 0.0473449883500741 + 0.j,
             -0.1676924530298831 + 0.j, 0.0862645617838693 + 0.j
         ],
         [
             0.1945647573956160 + 0.j, 0.4887086137642586 + 0.j,
             -0.0626741792078922 + 0.j, 0.2409165890485374 + 0.j,
             0.0882595335020335 + 0.j, 0.2992959491992316 + 0.j
         ],
         [
             0.0054805849814896 + 0.j, 0.0441542029539851 + 0.j,
             -0.1990143955204461 + 0.j, 0.0209311955324630 + 0.j,
             -0.0893288238000901 + 0.j, 0.0403909822493594 + 0.j
         ],
         [
             0.0715644878248155 + 0.j, 0.2095150416316441 + 0.j,
             -0.2162188374553924 + 0.j, 0.1024657089267621 + 0.j,
             -0.0574510118765082 + 0.j, 0.1413852823605560 + 0.j
         ],
         [
             -0.0035087946895569 + 0.j, 0.0261754436118892 + 0.j,
             -0.2259825345335916 + 0.j, 0.0119418158614160 + 0.j,
             -0.1073075831421863 + 0.j, 0.0314016025783124 + 0.j
         ]],
        dtype=numpy.complex128)
    work = fqe_data.FqeData(2, 2, norb)
    work.coeff = numpy.copy(wfn)
    test = work.apply(tuple([h1e_spa, h2e_spa, h3e_spa]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    test = work.apply(tuple([h1e_spin, h2e_spin, h3e_spin]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)

    energy = 0.
    rdm3 = work.rdm123(work)
    energy = numpy.tensordot(h3e_spa,
                             rdm3[2],
                             axes=([0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 5]))
    assert round(abs(energy - scale), 7) == 0


def test_lowfilling_2_body(c_or_python):
    """Check low filling 2 body functions
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 8
    scale = -127.62690492408638
    h1e_spa = numpy.zeros((norb, norb), dtype=numpy.complex128)
    h2e_spa = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)
    for i in range(norb):
        for j in range(norb):
            h1e_spa[i, j] += (i + j) * 0.02
            for k in range(norb):
                for l in range(norb):
                    h2e_spa[i, j, k, l] += (i + k) * (j + l) * 0.02
        h1e_spa[i, i] += i * 2.0

    h2e_spin = numpy.zeros((2 * norb, 2 * norb, 2 * norb, 2 * norb),
                           dtype=numpy.complex128)
    h2e_spin[:norb, :norb, :norb, :norb] = h2e_spa
    h2e_spin[norb:, norb:, norb:, norb:] = h2e_spa
    h2e_spin[:norb, norb:, :norb, norb:] = h2e_spa
    h2e_spin[norb:, :norb, norb:, :norb] = h2e_spa

    h1e_spin = numpy.zeros((2 * norb, 2 * norb), dtype=numpy.complex128)
    h1e_spin[:norb, :norb] = h1e_spa
    h1e_spin[norb:, norb:] = h1e_spa

    wfn = numpy.asarray(
        [[
            -0.0932089487476626 + 0.j, -0.0706587098642184 + 0.j,
            -0.0740438603927790 + 0.j, -0.0805502046061131 + 0.j,
            -0.0879038682813978 + 0.j, -0.0955090389840755 + 0.j,
            -0.1031456871031518 + 0.j, 0.0478568383864201 + 0.j,
            0.0633827785124240 + 0.j, 0.0745259163770606 + 0.j,
            0.0840931201605038 + 0.j, 0.0928361109948333 + 0.j,
            0.1010454451455466 + 0.j, 0.0100307721513250 + 0.j,
            0.0151358782333622 + 0.j, 0.0186106754313070 + 0.j,
            0.0213309864526485 + 0.j, 0.0236300924351082 + 0.j,
            0.0044254845218365 + 0.j, 0.0070218120829127 + 0.j,
            0.0087913981858984 + 0.j, 0.0101147655457833 + 0.j,
            0.0023845600555775 + 0.j, 0.0038543613277461 + 0.j,
            0.0048365508368202 + 0.j, 0.0013785456136308 + 0.j,
            0.0022237693216097 + 0.j, 0.0007983521363725 + 0.j
        ],
         [
             -0.0706587098642178 + 0.j, -0.0535799644805679 + 0.j,
             -0.0561621201665438 + 0.j, -0.0611127396392170 + 0.j,
             -0.0667080800401726 + 0.j, -0.0724963145713807 + 0.j,
             -0.0783104615368883 + 0.j, 0.0362946558453897 + 0.j,
             0.0480801293766977 + 0.j, 0.0565452115431265 + 0.j,
             0.0638177200315103 + 0.j, 0.0704673713830835 + 0.j,
             0.0767142655027953 + 0.j, 0.0076098535772196 + 0.j,
             0.0114848140629482 + 0.j, 0.0141238594629412 + 0.j,
             0.0161911260447960 + 0.j, 0.0179393197803398 + 0.j,
             0.0033581855204487 + 0.j, 0.0053290007599329 + 0.j,
             0.0066727963434466 + 0.j, 0.0076782000447207 + 0.j,
             0.0018096892986237 + 0.j, 0.0029253127397735 + 0.j,
             0.0036709502967018 + 0.j, 0.0010461510220687 + 0.j,
             0.0016874859899826 + 0.j, 0.0006056338822255 + 0.j
         ],
         [
             -0.0740438603927787 + 0.j, -0.0561621201665439 + 0.j,
             -0.0588835317647236 + 0.j, -0.0640892811820629 + 0.j,
             -0.0699730349182325 + 0.j, -0.0760611581510978 + 0.j,
             -0.0821784870045671 + 0.j, 0.0380493572253727 + 0.j,
             0.0504150338726772 + 0.j, 0.0593032803495607 + 0.j,
             0.0669438933923514 + 0.j, 0.0739337523853319 + 0.j,
             0.0805033453158931 + 0.j, 0.0079802568306227 + 0.j,
             0.0120457790229829 + 0.j, 0.0148161421021887 + 0.j,
             0.0169875044698748 + 0.j, 0.0188247358774655 + 0.j,
             0.0035224345072349 + 0.j, 0.0055902910608630 + 0.j,
             0.0070007963509055 + 0.j, 0.0080565705944120 + 0.j,
             0.0018984262136024 + 0.j, 0.0030689226269545 + 0.j,
             0.0038513663784351 + 0.j, 0.0010974040292900 + 0.j,
             0.0017700790623805 + 0.j, 0.0006350955899765 + 0.j
         ],
         [
             -0.0805502046061130 + 0.j, -0.0611127396392171 + 0.j,
             -0.0640892811820629 + 0.j, -0.0697709929145195 + 0.j,
             -0.0761928007143594 + 0.j, -0.0828392816369428 + 0.j,
             -0.0895196906394810 + 0.j, 0.0414093333097644 + 0.j,
             0.0548777958277241 + 0.j, 0.0645653775224049 + 0.j,
             0.0728978585871946 + 0.j, 0.0805244351502411 + 0.j,
             0.0876956887910217 + 0.j, 0.0086875935025343 + 0.j,
             0.0131155090310228 + 0.j, 0.0161344201159119 + 0.j,
             0.0185018723715049 + 0.j, 0.0205060708439888 + 0.j,
             0.0038354916415492 + 0.j, 0.0060878144653612 + 0.j,
             0.0076247166205728 + 0.j, 0.0087755824097035 + 0.j,
             0.0020673955074163 + 0.j, 0.0033422558667758 + 0.j,
             0.0041946064275996 + 0.j, 0.0011950411403562 + 0.j,
             0.0019274878665384 + 0.j, 0.0006913896613698 + 0.j
         ],
         [
             -0.0879038682813978 + 0.j, -0.0667080800401727 + 0.j,
             -0.0699730349182325 + 0.j, -0.0761928007143594 + 0.j,
             -0.0832228884203967 + 0.j, -0.0905006437743802 + 0.j,
             -0.0978177104156161 + 0.j, 0.0452070446002034 + 0.j,
             0.0599220813094387 + 0.j, 0.0705132985316171 + 0.j,
             0.0796279867576509 + 0.j, 0.0879744736965231 + 0.j,
             0.0958260519616467 + 0.j, 0.0094871413422558 + 0.j,
             0.0143247308172882 + 0.j, 0.0176246438642299 + 0.j,
             0.0202138107719987 + 0.j, 0.0224068123423515 + 0.j,
             0.0041893882517588 + 0.j, 0.0066502602384193 + 0.j,
             0.0083300744834015 + 0.j, 0.0095884672142172 + 0.j,
             0.0022584221967322 + 0.j, 0.0036512802189782 + 0.j,
             0.0045826772251442 + 0.j, 0.0013054316974975 + 0.j,
             0.0021054626468748 + 0.j, 0.0007550406190823 + 0.j
         ],
         [
             -0.0955090389840754 + 0.j, -0.0724963145713808 + 0.j,
             -0.0760611581510978 + 0.j, -0.0828392816369428 + 0.j,
             -0.0905006437743802 + 0.j, -0.0984337272436734 + 0.j,
             -0.1064119434705389 + 0.j, 0.0491363849304351 + 0.j,
             0.0651423541994335 + 0.j, 0.0766700738224950 + 0.j,
             0.0865959280828922 + 0.j, 0.0956893872104286 + 0.j,
             0.1042472167970307 + 0.j, 0.0103147081264282 + 0.j,
             0.0155765596317315 + 0.j, 0.0191676597499300 + 0.j,
             0.0219867194465590 + 0.j, 0.0243756043574970 + 0.j,
             0.0045557939936183 + 0.j, 0.0072326704541114 + 0.j,
             0.0090605735850667 + 0.j, 0.0104304446906017 + 0.j,
             0.0024562390786220 + 0.j, 0.0039713166539076 + 0.j,
             0.0049846092976104 + 0.j, 0.0014197505092668 + 0.j,
             0.0022897685595554 + 0.j, 0.0008209402995558 + 0.j
         ],
         [
             -0.1031456871031516 + 0.j, -0.0783104615368884 + 0.j,
             -0.0821784870045671 + 0.j, -0.0895196906394810 + 0.j,
             -0.0978177104156160 + 0.j, -0.1064119434705388 + 0.j,
             -0.1150574703780492 + 0.j, 0.0530841730676872 + 0.j,
             0.0703885797701098 + 0.j, 0.0828591379542015 + 0.j,
             0.0936022826400370 + 0.j, 0.1034488646606583 + 0.j,
             0.1127192007021945 + 0.j, 0.0111465358327448 + 0.j,
             0.0168351205472870 + 0.j, 0.0207193263523689 + 0.j,
             0.0237699704752715 + 0.j, 0.0263563247899062 + 0.j,
             0.0049242160312684 + 0.j, 0.0078183881518368 + 0.j,
             0.0097953491006253 + 0.j, 0.0112774977763678 + 0.j,
             0.0026551893586058 + 0.j, 0.0042932196362405 + 0.j,
             0.0053889243371543 + 0.j, 0.0015347279404732 + 0.j,
             0.0024751324196980 + 0.j, 0.0008871979051059 + 0.j
         ],
         [
             0.0478568383864203 + 0.j, 0.0362946558453899 + 0.j,
             0.0380493572253729 + 0.j, 0.0414093333097646 + 0.j,
             0.0452070446002036 + 0.j, 0.0491363849304353 + 0.j,
             0.0530841730676874 + 0.j, -0.0245896077262418 + 0.j,
             -0.0325787119037790 + 0.j, -0.0383196917055469 + 0.j,
             -0.0432537738587132 + 0.j, -0.0477667877832336 + 0.j,
             -0.0520077495879191 + 0.j, -0.0051569376472646 + 0.j,
             -0.0077837684268431 + 0.j, -0.0095734521543978 + 0.j,
             -0.0109759092324096 + 0.j, -0.0121623297719945 + 0.j,
             -0.0022761672502031 + 0.j, -0.0036123061115051 + 0.j,
             -0.0045236052861667 + 0.j, -0.0052056302394887 + 0.j,
             -0.0012267594356805 + 0.j, -0.0019831309524021 + 0.j,
             -0.0024887367357783 + 0.j, -0.0007091921185375 + 0.j,
             -0.0011439505861497 + 0.j, -0.0004105047100228 + 0.j
         ],
         [
             0.0633827785124241 + 0.j, 0.0480801293766978 + 0.j,
             0.0504150338726773 + 0.j, 0.0548777958277243 + 0.j,
             0.0599220813094388 + 0.j, 0.0651423541994336 + 0.j,
             0.0703885797701099 + 0.j, -0.0325787119037789 + 0.j,
             -0.0431710947588731 + 0.j, -0.0507874726011044 + 0.j,
             -0.0573366752009018 + 0.j, -0.0633296145334488 + 0.j,
             -0.0689635416033258 + 0.j, -0.0068343851445359 + 0.j,
             -0.0103171588116347 + 0.j, -0.0126911520866933 + 0.j,
             -0.0145524023549991 + 0.j, -0.0161276826541549 + 0.j,
             -0.0030172211717766 + 0.j, -0.0047888872655546 + 0.j,
             -0.0059976549435675 + 0.j, -0.0069026585616367 + 0.j,
             -0.0016263750218300 + 0.j, -0.0026292915846609 + 0.j,
             -0.0032998224462503 + 0.j, -0.0009402171689085 + 0.j,
             -0.0015165713341375 + 0.j, -0.0005441079703957 + 0.j
         ],
         [
             0.0745259163770607 + 0.j, 0.0565452115431266 + 0.j,
             0.0593032803495608 + 0.j, 0.0645653775224050 + 0.j,
             0.0705132985316173 + 0.j, 0.0766700738224951 + 0.j,
             0.0828591379542016 + 0.j, -0.0383196917055468 + 0.j,
             -0.0507874726011044 + 0.j, -0.0597577654738798 + 0.j,
             -0.0674750224174231 + 0.j, -0.0745398719073566 + 0.j,
             -0.0811841157083844 + 0.j, -0.0080409915614317 + 0.j,
             -0.0121403686992950 + 0.j, -0.0149359962345797 + 0.j,
             -0.0171288718393260 + 0.j, -0.0189856868739057 + 0.j,
             -0.0035506750471442 + 0.j, -0.0056361815471105 + 0.j,
             -0.0070595682080437 + 0.j, -0.0081256669495500 + 0.j,
             -0.0019141787176441 + 0.j, -0.0030947583955419 + 0.j,
             -0.0038842133504801 + 0.j, -0.0011066095688561 + 0.j,
             -0.0017849313027864 + 0.j, -0.0006402627649506 + 0.j
         ],
         [
             0.0840931201605039 + 0.j, 0.0638177200315105 + 0.j,
             0.0669438933923515 + 0.j, 0.0728978585871947 + 0.j,
             0.0796279867576511 + 0.j, 0.0865959280828924 + 0.j,
             0.0936022826400372 + 0.j, -0.0432537738587131 + 0.j,
             -0.0573366752009018 + 0.j, -0.0674750224174230 + 0.j,
             -0.0762014388911379 + 0.j, -0.0841935419819257 + 0.j,
             -0.0917127501271965 + 0.j, -0.0090788459751881 + 0.j,
             -0.0137092367988992 + 0.j, -0.0168684763149219 + 0.j,
             -0.0193477423708684 + 0.j, -0.0214480172066346 + 0.j,
             -0.0040098065252804 + 0.j, -0.0063656567859586 + 0.j,
             -0.0079741053378899 + 0.j, -0.0091792705012122 + 0.j,
             -0.0021619812807855 + 0.j, -0.0034956033622817 + 0.j,
             -0.0043875577124121 + 0.j, -0.0012498813526957 + 0.j,
             -0.0020159924385349 + 0.j, -0.0007230068845453 + 0.j
         ],
         [
             0.0928361109948334 + 0.j, 0.0704673713830836 + 0.j,
             0.0739337523853320 + 0.j, 0.0805244351502413 + 0.j,
             0.0879744736965232 + 0.j, 0.0956893872104287 + 0.j,
             0.1034488646606584 + 0.j, -0.0477667877832334 + 0.j,
             -0.0633296145334488 + 0.j, -0.0745398719073566 + 0.j,
             -0.0841935419819257 + 0.j, -0.0930385680749462 + 0.j,
             -0.1013633964849744 + 0.j, -0.0100287970688324 + 0.j,
             -0.0151457408869239 + 0.j, -0.0186385502523309 + 0.j,
             -0.0213808655430506 + 0.j, -0.0237050202449841 + 0.j,
             -0.0044302766233828 + 0.j, -0.0070338881689814 + 0.j,
             -0.0088120902029262 + 0.j, -0.0101449441689803 + 0.j,
             -0.0023889937934257 + 0.j, -0.0038628759058110 + 0.j,
             -0.0048488135739727 + 0.j, -0.0013811372618551 + 0.j,
             -0.0022276672932052 + 0.j, -0.0007987714877135 + 0.j
         ],
         [
             0.1010454451455467 + 0.j, 0.0767142655027955 + 0.j,
             0.0805033453158932 + 0.j, 0.0876956887910219 + 0.j,
             0.0958260519616469 + 0.j, 0.1042472167970309 + 0.j,
             0.1127192007021947 + 0.j, -0.0520077495879190 + 0.j,
             -0.0689635416033258 + 0.j, -0.0811841157083844 + 0.j,
             -0.0917127501271965 + 0.j, -0.1013633964849744 + 0.j,
             -0.1104498479460201 + 0.j, -0.0109220524146663 + 0.j,
             -0.0164969501381274 + 0.j, -0.0203040666204849 + 0.j,
             -0.0232945155349613 + 0.j, -0.0258300805618901 + 0.j,
             -0.0048258445032997 + 0.j, -0.0076626991670747 + 0.j,
             -0.0096008361985846 + 0.j, -0.0110541015974222 + 0.j,
             -0.0026026264096256 + 0.j, -0.0042085508090221 + 0.j,
             -0.0052830037727099 + 0.j, -0.0015046604086598 + 0.j,
             -0.0024268648080439 + 0.j, -0.0008700379823503 + 0.j
         ],
         [
             0.0100307721513248 + 0.j, 0.0076098535772195 + 0.j,
             0.0079802568306225 + 0.j, 0.0086875935025341 + 0.j,
             0.0094871413422557 + 0.j, 0.0103147081264281 + 0.j,
             0.0111465358327447 + 0.j, -0.0051569376472645 + 0.j,
             -0.0068343851445359 + 0.j, -0.0080409915614316 + 0.j,
             -0.0090788459751880 + 0.j, -0.0100287970688323 + 0.j,
             -0.0109220524146661 + 0.j, -0.0010820888500130 + 0.j,
             -0.0016336916745034 + 0.j, -0.0020098092566090 + 0.j,
             -0.0023047841926255 + 0.j, -0.0025545105496307 + 0.j,
             -0.0004778214850290 + 0.j, -0.0007584626578703 + 0.j,
             -0.0009499904411404 + 0.j, -0.0010934276452102 + 0.j,
             -0.0002576070346975 + 0.j, -0.0004164935290353 + 0.j,
             -0.0005227440490688 + 0.j, -0.0001489428167668 + 0.j,
             -0.0002402549461684 + 0.j, -0.0000861964148710 + 0.j
         ],
         [
             0.0151358782333620 + 0.j, 0.0114848140629481 + 0.j,
             0.0120457790229828 + 0.j, 0.0131155090310226 + 0.j,
             0.0143247308172880 + 0.j, 0.0155765596317313 + 0.j,
             0.0168351205472868 + 0.j, -0.0077837684268430 + 0.j,
             -0.0103171588116346 + 0.j, -0.0121403686992949 + 0.j,
             -0.0137092367988990 + 0.j, -0.0151457408869238 + 0.j,
             -0.0164969501381272 + 0.j, -0.0016336916745034 + 0.j,
             -0.0024667869775821 + 0.j, -0.0030350785201450 + 0.j,
             -0.0034809513036669 + 0.j, -0.0038585754441044 + 0.j,
             -0.0007215479252973 + 0.j, -0.0011454555012199 + 0.j,
             -0.0014348503746547 + 0.j, -0.0016516564616475 + 0.j,
             -0.0003890681283363 + 0.j, -0.0006290811229198 + 0.j,
             -0.0007896155046868 + 0.j, -0.0002249669274892 + 0.j,
             -0.0003628927530546 + 0.j, -0.0001301821479848 + 0.j
         ],
         [
             0.0186106754313068 + 0.j, 0.0141238594629411 + 0.j,
             0.0148161421021886 + 0.j, 0.0161344201159117 + 0.j,
             0.0176246438642297 + 0.j, 0.0191676597499298 + 0.j,
             0.0207193263523687 + 0.j, -0.0095734521543977 + 0.j,
             -0.0126911520866931 + 0.j, -0.0149359962345795 + 0.j,
             -0.0168684763149217 + 0.j, -0.0186385502523307 + 0.j,
             -0.0203040666204846 + 0.j, -0.0020098092566090 + 0.j,
             -0.0030350785201450 + 0.j, -0.0037347476660277 + 0.j,
             -0.0042839226801363 + 0.j, -0.0047492190140155 + 0.j,
             -0.0008878484665224 + 0.j, -0.0014095989495987 + 0.j,
             -0.0017659030573584 + 0.j, -0.0020329282320441 + 0.j,
             -0.0004788118523197 + 0.j, -0.0007742401712282 + 0.j,
             -0.0009718798519265 + 0.j, -0.0002768770599085 + 0.j,
             -0.0004466352998364 + 0.j, -0.0001602070064119 + 0.j
         ],
         [
             0.0213309864526483 + 0.j, 0.0161911260447959 + 0.j,
             0.0169875044698746 + 0.j, 0.0185018723715048 + 0.j,
             0.0202138107719985 + 0.j, 0.0219867194465588 + 0.j,
             0.0237699704752713 + 0.j, -0.0109759092324094 + 0.j,
             -0.0145524023549990 + 0.j, -0.0171288718393259 + 0.j,
             -0.0193477423708682 + 0.j, -0.0213808655430504 + 0.j,
             -0.0232945155349611 + 0.j, -0.0023047841926256 + 0.j,
             -0.0034809513036669 + 0.j, -0.0042839226801363 + 0.j,
             -0.0049144373497770 + 0.j, -0.0054488583542370 + 0.j,
             -0.0010183568456194 + 0.j, -0.0016169602405916 + 0.j,
             -0.0020258756040775 + 0.j, -0.0023324347971913 + 0.j,
             -0.0005492732437389 + 0.j, -0.0008882353764349 + 0.j,
             -0.0011150442437882 + 0.j, -0.0003176411092681 + 0.j,
             -0.0005123990519779 + 0.j, -0.0001837766721926 + 0.j
         ],
         [
             0.0236300924351080 + 0.j, 0.0179393197803396 + 0.j,
             0.0188247358774653 + 0.j, 0.0205060708439886 + 0.j,
             0.0224068123423513 + 0.j, 0.0243756043574968 + 0.j,
             0.0263563247899060 + 0.j, -0.0121623297719944 + 0.j,
             -0.0161276826541547 + 0.j, -0.0189856868739055 + 0.j,
             -0.0214480172066344 + 0.j, -0.0237050202449838 + 0.j,
             -0.0258300805618898 + 0.j, -0.0025545105496307 + 0.j,
             -0.0038585754441044 + 0.j, -0.0047492190140155 + 0.j,
             -0.0054488583542370 + 0.j, -0.0060420985947139 + 0.j,
             -0.0011289124125787 + 0.j, -0.0017926732858756 + 0.j,
             -0.0022462383823203 + 0.j, -0.0025863865172608 + 0.j,
             -0.0006089870988719 + 0.j, -0.0009848620958035 + 0.j,
             -0.0012364191938801 + 0.j, -0.0003521920455659 + 0.j,
             -0.0005681403170259 + 0.j, -0.0002037461412343 + 0.j
         ],
         [
             0.0044254845218365 + 0.j, 0.0033581855204487 + 0.j,
             0.0035224345072349 + 0.j, 0.0038354916415492 + 0.j,
             0.0041893882517588 + 0.j, 0.0045557939936183 + 0.j,
             0.0049242160312684 + 0.j, -0.0022761672502030 + 0.j,
             -0.0030172211717765 + 0.j, -0.0035506750471441 + 0.j,
             -0.0040098065252804 + 0.j, -0.0044302766233828 + 0.j,
             -0.0048258445032996 + 0.j, -0.0004778214850290 + 0.j,
             -0.0007215479252973 + 0.j, -0.0008878484665224 + 0.j,
             -0.0010183568456194 + 0.j, -0.0011289124125787 + 0.j,
             -0.0002110827207494 + 0.j, -0.0003351244017925 + 0.j,
             -0.0004198279099549 + 0.j, -0.0004833016536958 + 0.j,
             -0.0001138436123904 + 0.j, -0.0001840902953333 + 0.j,
             -0.0002310879292246 + 0.j, -0.0000658413060907 + 0.j,
             -0.0001062184195155 + 0.j, -0.0000381092073714 + 0.j
         ],
         [
             0.0070218120829127 + 0.j, 0.0053290007599329 + 0.j,
             0.0055902910608629 + 0.j, 0.0060878144653612 + 0.j,
             0.0066502602384193 + 0.j, 0.0072326704541114 + 0.j,
             0.0078183881518367 + 0.j, -0.0036123061115051 + 0.j,
             -0.0047888872655546 + 0.j, -0.0056361815471104 + 0.j,
             -0.0063656567859585 + 0.j, -0.0070338881689813 + 0.j,
             -0.0076626991670746 + 0.j, -0.0007584626578703 + 0.j,
             -0.0011454555012199 + 0.j, -0.0014095989495987 + 0.j,
             -0.0016169602405916 + 0.j, -0.0017926732858757 + 0.j,
             -0.0003351244017925 + 0.j, -0.0005321088384111 + 0.j,
             -0.0006666614741756 + 0.j, -0.0007675214276221 + 0.j,
             -0.0001807752507452 + 0.j, -0.0002923455706983 + 0.j,
             -0.0003670083285081 + 0.j, -0.0001045660424699 + 0.j,
             -0.0001687007953383 + 0.j, -0.0000605278120603 + 0.j
         ],
         [
             0.0087913981858983 + 0.j, 0.0066727963434466 + 0.j,
             0.0070007963509054 + 0.j, 0.0076247166205728 + 0.j,
             0.0083300744834015 + 0.j, 0.0090605735850667 + 0.j,
             0.0097953491006252 + 0.j, -0.0045236052861667 + 0.j,
             -0.0059976549435675 + 0.j, -0.0070595682080436 + 0.j,
             -0.0079741053378898 + 0.j, -0.0088120902029261 + 0.j,
             -0.0096008361985845 + 0.j, -0.0009499904411404 + 0.j,
             -0.0014348503746548 + 0.j, -0.0017659030573584 + 0.j,
             -0.0020258756040775 + 0.j, -0.0022462383823203 + 0.j,
             -0.0004198279099549 + 0.j, -0.0006666614741756 + 0.j,
             -0.0008353123926024 + 0.j, -0.0009617709694017 + 0.j,
             -0.0002265042646076 + 0.j, -0.0003663260682315 + 0.j,
             -0.0004599168552371 + 0.j, -0.0001310344644699 + 0.j,
             -0.0002114149700167 + 0.j, -0.0000758540138051 + 0.j
         ],
         [
             0.0101147655457833 + 0.j, 0.0076782000447207 + 0.j,
             0.0080565705944120 + 0.j, 0.0087755824097035 + 0.j,
             0.0095884672142172 + 0.j, 0.0104304446906017 + 0.j,
             0.0112774977763678 + 0.j, -0.0052056302394886 + 0.j,
             -0.0069026585616367 + 0.j, -0.0081256669495499 + 0.j,
             -0.0091792705012121 + 0.j, -0.0101449441689802 + 0.j,
             -0.0110541015974222 + 0.j, -0.0010934276452103 + 0.j,
             -0.0016516564616476 + 0.j, -0.0020329282320441 + 0.j,
             -0.0023324347971913 + 0.j, -0.0025863865172609 + 0.j,
             -0.0004833016536958 + 0.j, -0.0007675214276221 + 0.j,
             -0.0009617709694017 + 0.j, -0.0011074680397378 + 0.j,
             -0.0002607899089926 + 0.j, -0.0004218076478657 + 0.j,
             -0.0005296107343134 + 0.j, -0.0001508871579564 + 0.j,
             -0.0002434581563674 + 0.j, -0.0000873510874605 + 0.j
         ],
         [
             0.0023845600555774 + 0.j, 0.0018096892986237 + 0.j,
             0.0018984262136024 + 0.j, 0.0020673955074162 + 0.j,
             0.0022584221967322 + 0.j, 0.0024562390786220 + 0.j,
             0.0026551893586058 + 0.j, -0.0012267594356805 + 0.j,
             -0.0016263750218300 + 0.j, -0.0019141787176440 + 0.j,
             -0.0021619812807854 + 0.j, -0.0023889937934256 + 0.j,
             -0.0026026264096256 + 0.j, -0.0002576070346975 + 0.j,
             -0.0003890681283363 + 0.j, -0.0004788118523197 + 0.j,
             -0.0005492732437389 + 0.j, -0.0006089870988719 + 0.j,
             -0.0001138436123904 + 0.j, -0.0001807752507451 + 0.j,
             -0.0002265042646076 + 0.j, -0.0002607899089926 + 0.j,
             -0.0000614256118145 + 0.j, -0.0000993474215613 + 0.j,
             -0.0001247332113847 + 0.j, -0.0000355422683851 + 0.j,
             -0.0000573511578580 + 0.j, -0.0000205833183553 + 0.j
         ],
         [
             0.0038543613277461 + 0.j, 0.0029253127397735 + 0.j,
             0.0030689226269545 + 0.j, 0.0033422558667758 + 0.j,
             0.0036512802189782 + 0.j, 0.0039713166539076 + 0.j,
             0.0042932196362405 + 0.j, -0.0019831309524021 + 0.j,
             -0.0026292915846609 + 0.j, -0.0030947583955418 + 0.j,
             -0.0034956033622817 + 0.j, -0.0038628759058110 + 0.j,
             -0.0042085508090221 + 0.j, -0.0004164935290354 + 0.j,
             -0.0006290811229199 + 0.j, -0.0007742401712282 + 0.j,
             -0.0008882353764349 + 0.j, -0.0009848620958035 + 0.j,
             -0.0001840902953333 + 0.j, -0.0002923455706983 + 0.j,
             -0.0003663260682315 + 0.j, -0.0004218076478657 + 0.j,
             -0.0000993474215613 + 0.j, -0.0001606958398292 + 0.j,
             -0.0002017758795160 + 0.j, -0.0000574980065047 + 0.j,
             -0.0000927895458989 + 0.j, -0.0000333080137258 + 0.j
         ],
         [
             0.0048365508368202 + 0.j, 0.0036709502967018 + 0.j,
             0.0038513663784351 + 0.j, 0.0041946064275996 + 0.j,
             0.0045826772251442 + 0.j, 0.0049846092976103 + 0.j,
             0.0053889243371543 + 0.j, -0.0024887367357783 + 0.j,
             -0.0032998224462503 + 0.j, -0.0038842133504801 + 0.j,
             -0.0043875577124120 + 0.j, -0.0048488135739727 + 0.j,
             -0.0052830037727099 + 0.j, -0.0005227440490688 + 0.j,
             -0.0007896155046868 + 0.j, -0.0009718798519265 + 0.j,
             -0.0011150442437882 + 0.j, -0.0012364191938802 + 0.j,
             -0.0002310879292246 + 0.j, -0.0003670083285080 + 0.j,
             -0.0004599168552371 + 0.j, -0.0005296107343134 + 0.j,
             -0.0001247332113847 + 0.j, -0.0002017758795160 + 0.j,
             -0.0002533796646063 + 0.j, -0.0000722062275436 + 0.j,
             -0.0001165384801596 + 0.j, -0.0000418403418188 + 0.j
         ],
         [
             0.0013785456136309 + 0.j, 0.0010461510220687 + 0.j,
             0.0010974040292901 + 0.j, 0.0011950411403563 + 0.j,
             0.0013054316974975 + 0.j, 0.0014197505092668 + 0.j,
             0.0015347279404732 + 0.j, -0.0007091921185375 + 0.j,
             -0.0009402171689085 + 0.j, -0.0011066095688561 + 0.j,
             -0.0012498813526957 + 0.j, -0.0013811372618550 + 0.j,
             -0.0015046604086598 + 0.j, -0.0001489428167668 + 0.j,
             -0.0002249669274892 + 0.j, -0.0002768770599085 + 0.j,
             -0.0003176411092681 + 0.j, -0.0003521920455659 + 0.j,
             -0.0000658413060907 + 0.j, -0.0001045660424699 + 0.j,
             -0.0001310344644699 + 0.j, -0.0001508871579564 + 0.j,
             -0.0000355422683851 + 0.j, -0.0000574980065047 + 0.j,
             -0.0000722062275436 + 0.j, -0.0000205802660191 + 0.j,
             -0.0000332207592566 + 0.j, -0.0000119319467562 + 0.j
         ],
         [
             0.0022237693216097 + 0.j, 0.0016874859899826 + 0.j,
             0.0017700790623805 + 0.j, 0.0019274878665384 + 0.j,
             0.0021054626468749 + 0.j, 0.0022897685595555 + 0.j,
             0.0024751324196980 + 0.j, -0.0011439505861497 + 0.j,
             -0.0015165713341375 + 0.j, -0.0017849313027864 + 0.j,
             -0.0020159924385349 + 0.j, -0.0022276672932052 + 0.j,
             -0.0024268648080439 + 0.j, -0.0002402549461685 + 0.j,
             -0.0003628927530546 + 0.j, -0.0004466352998365 + 0.j,
             -0.0005123990519779 + 0.j, -0.0005681403170259 + 0.j,
             -0.0001062184195155 + 0.j, -0.0001687007953383 + 0.j,
             -0.0002114149700167 + 0.j, -0.0002434581563674 + 0.j,
             -0.0000573511578580 + 0.j, -0.0000927895458989 + 0.j,
             -0.0001165384801596 + 0.j, -0.0000332207592566 + 0.j,
             -0.0000536359914926 + 0.j, -0.0000192728640005 + 0.j
         ],
         [
             0.0007983521363725 + 0.j, 0.0006056338822255 + 0.j,
             0.0006350955899765 + 0.j, 0.0006913896613698 + 0.j,
             0.0007550406190823 + 0.j, 0.0008209402995558 + 0.j,
             0.0008871979051059 + 0.j, -0.0004105047100228 + 0.j,
             -0.0005441079703957 + 0.j, -0.0006402627649506 + 0.j,
             -0.0007230068845453 + 0.j, -0.0007987714877135 + 0.j,
             -0.0008700379823503 + 0.j, -0.0000861964148710 + 0.j,
             -0.0001301821479848 + 0.j, -0.0001602070064120 + 0.j,
             -0.0001837766721926 + 0.j, -0.0002037461412343 + 0.j,
             -0.0000381092073714 + 0.j, -0.0000605278120603 + 0.j,
             -0.0000758540138051 + 0.j, -0.0000873510874605 + 0.j,
             -0.0000205833183553 + 0.j, -0.0000333080137258 + 0.j,
             -0.0000418403418188 + 0.j, -0.0000119319467562 + 0.j,
             -0.0000192728640005 + 0.j, -0.0000069327159862 + 0.j
         ]],
        dtype=numpy.complex128)
    work = fqe_data.FqeData(2, 2, norb)
    work._low_thresh = 0.3  # enable low-filling code for C and python
    work.coeff = numpy.copy(wfn)
    test = work.apply(tuple([h1e_spa, h2e_spa]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    test = work.apply(tuple([h1e_spin, h2e_spin]))
    assert numpy.allclose(numpy.multiply(wfn, scale), test.coeff)
    low_fill = work.rdm12(work)
    # we need to check both ket != bra and ket == bra
    # by passing ket explicitly as a bra parameter we test the
    # bra != ket codepath
    low_fill_nobra = work.rdm12()
    half_fill = work._rdm12_halffilling(work)
    assert numpy.allclose(low_fill[0], half_fill[0])
    assert numpy.allclose(low_fill[1], half_fill[1])
    assert numpy.allclose(low_fill_nobra[0], half_fill[0])
    assert numpy.allclose(low_fill_nobra[1], half_fill[1])


def test_s2_inplace():
    """Check application of S^2 operator
    """
    work = fqe_data.FqeData(2, 1, 3)
    work.set_wfn(strategy='ones')
    work.apply_inplace_s2()
    assert numpy.allclose(
        work.coeff,
        numpy.asarray([[0.75 + 0.j, 0.75 + 0.j, 1.75 + 0.j],
                       [0.75 + 0.j, -0.25 + 0.j, 0.75 + 0.j],
                       [1.75 + 0.j, 0.75 + 0.j, 0.75 + 0.j]],
                      dtype=numpy.complex128))


def test_apply_columns_recursive_inplace(c_or_python):
    """Test the 'apply_columns_recursive_inplace' function
    assuming that the 'apply' is working correctly
    """
    fqe.settings.use_accelerated_code = c_or_python
    norb = 3
    seed = 432452  # for (fixed) random number generation
    test = fqe_data.FqeData(2, 1, norb)
    test.set_wfn(strategy='ones')
    rng = numpy.random.default_rng(seed)
    Ua = rng.uniform(-1, 1, size=(norb, norb))
    Ub = rng.uniform(-1, 1, size=(norb, norb))
    Umat = numpy.zeros((2 * norb, 2 * norb))
    Umat[:norb, :norb] = Ua
    Umat[norb:, norb:] = Ub
    current = copy.deepcopy(test)
    for i in range(2 * norb):
        temp = numpy.zeros(Umat.shape)
        temp[:, i] = Umat[:, i]
        current.ax_plus_y(1, current.apply((temp,)))

    test.apply_columns_recursive_inplace(Ua, Ub)
    assert numpy.allclose(test.coeff, current.coeff)


def test_data_print():
    """Check that data is printed correctly
    """
    numpy.random.seed(seed=409)
    work = fqe_data.FqeData(2, 1, 3)
    work.set_wfn(strategy='random')

    save_stdout = sys.stdout
    sys.stdout = chkprint = StringIO()
    work.print_sector()
    sys.stdout = save_stdout
    outstring = chkprint.getvalue()

    expected = """Sector N = 3 : S_z = 1
11:1 (0.28037731872261007+0.32599673701893295j)
11:10 (-0.20776778596031897-0.44964676904932527j)
11:100 (-0.5982592155589743+0.8138588036401146j)
101:1 (-0.7693909581835316+0.5010963131770999j)
101:10 (-0.1070553281124611-0.28468034534579584j)
101:100 (-1.281809519779826+0.44627728700958064j)
110:1 (-1.0699984614118179+0.33282913446024576j)
110:10 (1.150470965359522+0.028245225856149195j)
110:100 (0.3009872766528208-0.021023741905447858j)
"""
    assert outstring == expected


def test_random_wfn_opdm_tpdm_alpha_beta(c_or_python):
    """Check we can compute opdm-alpha, opdm-beta from dveca, dvecb"""
    fqe.settings.use_accelerated_code = c_or_python
    norb = 4
    sz = 2
    wfn = fqe.Wavefunction([[norb, sz, norb]])
    wfn.set_wfn(strategy='random')

    ladder_up = [
        of.get_sparse_operator(of.FermionOperator(((i, 1))), n_qubits=2 * norb)
        for i in range(2 * norb)
    ]
    ladder_dwn = [op.conj().T for op in ladder_up]

    work = wfn.sector((norb, sz))
    dveca, dvecb = work.calculate_dvec_spin()
    alpha_opdm = numpy.einsum('ijkl,kl->ij', dveca, work.coeff.conj())
    beta_opdm = numpy.einsum('ijkl,kl->ij', dvecb, work.coeff.conj())
    aopdm, bopdm = work.get_spin_opdm()
    assert numpy.allclose(aopdm, alpha_opdm)
    assert numpy.allclose(bopdm, beta_opdm)

    state = numpy.zeros(2**(2 * norb), dtype=numpy.complex128)
    for alpha_string, beta_string in product(work._core._astr,
                                             work._core._bstr):
        # needs to be flipped for OpenFermion Ordering
        a_string_binary = numpy.binary_repr(alpha_string, width=norb)[::-1]
        a_idx = work._core._aind[alpha_string]
        b_string_binary = numpy.binary_repr(beta_string, width=norb)[::-1]
        b_idx = work._core._bind[beta_string]
        joined_string = a_string_binary + b_string_binary
        joined_idx = int(joined_string, 2)
        state[joined_idx] = work.coeff[a_idx, b_idx]

    test_alpha_opdm = numpy.zeros((norb, norb), dtype=numpy.complex128)
    for i, j in product(range(4), repeat=2):
        op = ladder_up[i] @ ladder_dwn[j]
        test_alpha_opdm[i, j] = state.conj().T @ op @ state
    assert numpy.allclose(test_alpha_opdm, alpha_opdm)
    test_beta_opdm = numpy.zeros((norb, norb), dtype=numpy.complex128)
    for i, j in product(range(4), repeat=2):
        op = ladder_up[i + norb] @ ladder_dwn[j + norb]
        test_beta_opdm[i, j] = state.conj().T @ op @ state

    assert numpy.allclose(test_beta_opdm, beta_opdm)

    spin_summed_opdm = alpha_opdm + beta_opdm
    test_spin_summed_opdm = work.rdm1()[0]
    assert numpy.allclose(test_spin_summed_opdm, spin_summed_opdm)

    tpdm_ab = numpy.einsum('liab,jkab->ijkl', dveca.conj(), dvecb)
    tpdm_ab_fqedata = work.get_ab_tpdm()
    test_tpdm_ab = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)
    for i, j, k, l in product(range(norb), repeat=4):
        op = ladder_up[i] @ ladder_dwn[l] @ ladder_up[j + norb] @ \
              ladder_dwn[k + norb]
        test_tpdm_ab[i, j, k, l] = state.conj().T @ op @ state
    assert numpy.allclose(tpdm_ab, test_tpdm_ab)
    assert numpy.allclose(tpdm_ab, tpdm_ab_fqedata)

    alpha_opdm_2, tpdm_aa = work.get_aa_tpdm()
    assert numpy.allclose(alpha_opdm_2, alpha_opdm)
    test_tpdm_aa = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)
    for i, j, k, l in product(range(norb), repeat=4):
        op = ladder_up[i] @ ladder_up[j] @ ladder_dwn[k] @ ladder_dwn[l]
        test_tpdm_aa[i, j, k, l] = state.conj().T @ op @ state
        assert numpy.isclose(test_tpdm_aa[i, j, k, l], tpdm_aa[i, j, k, l])

    beta_opdm_2, tpdm_bb = work.get_bb_tpdm()
    assert numpy.allclose(beta_opdm_2, beta_opdm)
    test_tpdm_bb = numpy.zeros((norb, norb, norb, norb), dtype=numpy.complex128)
    for i, j, k, l in product(range(norb), repeat=4):
        op = ladder_up[i + norb] @ ladder_up[j + norb] @  \
              ladder_dwn[k + norb] @ ladder_dwn[l + norb]
        test_tpdm_bb[i, j, k, l] = state.conj().T @ op @ state
        assert numpy.isclose(test_tpdm_bb[i, j, k, l], tpdm_bb[i, j, k, l])

    cirq_wf = fqe.to_cirq(wfn).reshape((-1, 1))
    test_of_tpdm = numpy.zeros(tuple([2 * norb] * 4), dtype=numpy.complex128)
    of_opdm, of_tpdm = work.get_openfermion_rdms()
    for i, j, k, l in product(range(2 * norb), repeat=4):
        op = ladder_up[i] @ ladder_up[j] @ ladder_dwn[k] @ ladder_dwn[l]
        test_of_tpdm[i, j, k, l] = cirq_wf.conj().T @ op @ cirq_wf
        assert numpy.isclose(of_tpdm[i, j, k, l], test_of_tpdm[i, j, k, l])

    test_of_opdm = numpy.zeros_like(of_opdm)
    for i, j in product(range(2 * norb), repeat=2):
        op = ladder_up[i] @ ladder_dwn[j]
        test_of_opdm[i, j] = cirq_wf.conj().T @ op @ cirq_wf
        assert numpy.isclose(test_of_opdm[i, j], of_opdm[i, j])


@pytest.mark.skip(reason='Logic check. Not code check')
def test_lih_spin_block_three_rdm():
    """This test checks the logic of the 3-RDM code but not the code itself
    """
    unit_test_path = fud.__path__[0]
    three_pdm = numpy.load(os.path.join(unit_test_path, "lih_three_pdm.npy"))
    three_ccc_pdm = numpy.load(os.path.join(unit_test_path, "lih_ccc_pdm.npy"))
    opdm = numpy.load(os.path.join(unit_test_path, "lih_opdm.npy"))
    tpdm = numpy.load(os.path.join(unit_test_path, "lih_tpdm.npy"))
    krond = numpy.eye(three_pdm.shape[0] // 2)

    # extract spin-blocks
    ckckck_aaa = three_ccc_pdm[::2, ::2, ::2, ::2, ::2, ::2]
    ckckck_aab = three_ccc_pdm[::2, ::2, ::2, ::2, 1::2, 1::2]
    ckckck_abb = three_ccc_pdm[::2, ::2, 1::2, 1::2, 1::2, 1::2]
    ckckck_bbb = three_ccc_pdm[1::2, 1::2, 1::2, 1::2, 1::2, 1::2]

    # p^ r^ t^ u s q = p^ q r^ s t^ u + d(q, r) p^ t^ s u - d(q, t)p^ r^ s u
    #                 + d(s, t)p^ r^ q u - d(q,r)d(s,t)p^ u
    ccckkk_aaa = numpy.einsum('pqrstu->prtusq', ckckck_aaa)
    ccckkk_aaa += numpy.einsum('qr,ptsu->prtusq', krond,
                               tpdm[::2, ::2, ::2, ::2])
    ccckkk_aaa -= numpy.einsum('qt,prsu->prtusq', krond,
                               tpdm[::2, ::2, ::2, ::2])
    ccckkk_aaa += numpy.einsum('st,prqu->prtusq', krond,
                               tpdm[::2, ::2, ::2, ::2])
    ccckkk_aaa -= numpy.einsum('qr,st,pu->prtusq', krond, krond, opdm[::2, ::2])
    assert numpy.allclose(ccckkk_aaa, three_pdm[::2, ::2, ::2, ::2, ::2, ::2])

    ccckkk_aab = numpy.einsum('pqrstu->prtusq', ckckck_aab)
    ccckkk_aab += numpy.einsum('qr,ptsu->prtusq', krond,
                               tpdm[::2, 1::2, ::2, 1::2])
    ccckkk_abb = numpy.einsum('pqrstu->prtusq', ckckck_abb)
    ccckkk_abb += numpy.einsum('st,prqu->prtusq', krond,
                               tpdm[::2, 1::2, ::2, 1::2])

    ccckkk_bbb = numpy.einsum('pqrstu->prtusq', ckckck_bbb)
    ccckkk_bbb += numpy.einsum('qr,ptsu->prtusq', krond,
                               tpdm[1::2, 1::2, 1::2, 1::2])
    ccckkk_bbb -= numpy.einsum('qt,prsu->prtusq', krond,
                               tpdm[1::2, 1::2, 1::2, 1::2])
    ccckkk_bbb += numpy.einsum('st,prqu->prtusq', krond,
                               tpdm[1::2, 1::2, 1::2, 1::2])
    ccckkk_bbb -= numpy.einsum('qr,st,pu->prtusq', krond, krond,
                               opdm[1::2, 1::2])

    test_ccckkk = numpy.zeros_like(three_pdm)
    # same spin
    test_ccckkk[::2, ::2, ::2, ::2, ::2, ::2] = ccckkk_aaa
    test_ccckkk[1::2, 1::2, 1::2, 1::2, 1::2, 1::2] = ccckkk_bbb

    # different spin-aab
    # (aab,baa), (aab,aba), (aab,aab)
    # (aba,baa), (aba,aba), (aba,aab)
    # (baa,baa), (baa,aba), (baa,aab)
    test_ccckkk[::2, ::2, 1::2, 1::2, ::2, ::2] = ccckkk_aab
    test_ccckkk[::2, ::2, 1::2, ::2, 1::2, ::2] = numpy.einsum(
        'pqrstu->pqrtsu', -ccckkk_aab)
    test_ccckkk[::2, ::2, 1::2, ::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->pqrtus', ccckkk_aab)

    test_ccckkk[::2, 1::2, ::2, 1::2, ::2, ::2] = numpy.einsum(
        'pqrstu->prqstu', -ccckkk_aab)
    test_ccckkk[::2, 1::2, ::2, ::2, 1::2, ::2] = numpy.einsum(
        'pqrstu->prqtsu', ccckkk_aab)
    test_ccckkk[::2, 1::2, ::2, ::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->prqtus', -ccckkk_aab)

    test_ccckkk[1::2, ::2, ::2, 1::2, ::2, ::2] = numpy.einsum(
        'pqrstu->rpqstu', ccckkk_aab)
    test_ccckkk[1::2, ::2, ::2, ::2, 1::2, ::2] = numpy.einsum(
        'pqrstu->rpqtsu', -ccckkk_aab)
    test_ccckkk[1::2, ::2, ::2, ::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->rpqtus', ccckkk_aab)

    # different spin-abb
    # (abb,bba), (abb,bab), (abb,abb)
    # (bab,bba), (bab,bab), (bab,abb)
    # (abb,bba), (abb,bab), (abb,abb)
    test_ccckkk[::2, 1::2, 1::2, 1::2, 1::2, ::2] = ccckkk_abb
    test_ccckkk[::2, 1::2, 1::2, 1::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->pqrsut', -ccckkk_abb)
    test_ccckkk[::2, 1::2, 1::2, ::2, 1::2, 1::2] = numpy.einsum(
        'pqrstu->pqrust', ccckkk_abb)

    test_ccckkk[1::2, ::2, 1::2, 1::2, 1::2, ::2] = numpy.einsum(
        'pqrstu->qprstu', -ccckkk_abb)
    test_ccckkk[1::2, ::2, 1::2, 1::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->qprsut', ccckkk_abb)
    test_ccckkk[1::2, ::2, 1::2, ::2, 1::2, 1::2] = numpy.einsum(
        'pqrstu->qprust', -ccckkk_abb)

    test_ccckkk[1::2, 1::2, ::2, 1::2, 1::2, ::2] = numpy.einsum(
        'pqrstu->qrpstu', ccckkk_abb)
    test_ccckkk[1::2, 1::2, ::2, 1::2, ::2, 1::2] = numpy.einsum(
        'pqrstu->qrpsut', -ccckkk_abb)
    test_ccckkk[1::2, 1::2, ::2, ::2, 1::2, 1::2] = numpy.einsum(
        'pqrstu->qrpust', ccckkk_abb)

    assert numpy.allclose(three_pdm[::2, ::2, 1::2, 1::2, ::2, ::2], ccckkk_aab)
    assert numpy.allclose(three_pdm[::2, 1::2, 1::2, 1::2, 1::2, ::2],
                          ccckkk_abb)
    assert numpy.allclose(three_pdm[::2, ::2, 1::2, ::2, 1::2, ::2],
                          test_ccckkk[::2, ::2, 1::2, ::2, 1::2, ::2])
    assert numpy.allclose(three_pdm[::2, ::2, 1::2, ::2, ::2, 1::2],
                          test_ccckkk[::2, ::2, 1::2, ::2, ::2, 1::2])

    assert numpy.allclose(three_pdm[::2, 1::2, ::2, 1::2, ::2, ::2],
                          test_ccckkk[::2, 1::2, ::2, 1::2, ::2, ::2])
    assert numpy.allclose(three_pdm[::2, 1::2, ::2, ::2, 1::2, ::2],
                          test_ccckkk[::2, 1::2, ::2, ::2, 1::2, ::2])
    assert numpy.allclose(three_pdm[::2, 1::2, ::2, ::2, ::2, 1::2],
                          test_ccckkk[::2, 1::2, ::2, ::2, ::2, 1::2])
    assert numpy.allclose(three_pdm[1::2, ::2, ::2, 1::2, ::2, ::2],
                          test_ccckkk[1::2, ::2, ::2, 1::2, ::2, ::2])
    assert numpy.allclose(three_pdm[1::2, ::2, ::2, ::2, 1::2, ::2],
                          test_ccckkk[1::2, ::2, ::2, ::2, 1::2, ::2])
    assert numpy.allclose(three_pdm[1::2, ::2, ::2, ::2, ::2, 1::2],
                          test_ccckkk[1::2, ::2, ::2, ::2, ::2, 1::2])

    assert numpy.allclose(test_ccckkk[::2, 1::2, 1::2, 1::2, 1::2, ::2],
                          three_pdm[::2, 1::2, 1::2, 1::2, 1::2, ::2])
    assert numpy.allclose(test_ccckkk[::2, 1::2, 1::2, 1::2, ::2, 1::2],
                          three_pdm[::2, 1::2, 1::2, 1::2, ::2, 1::2])
    assert numpy.allclose(test_ccckkk[::2, 1::2, 1::2, ::2, 1::2, 1::2],
                          three_pdm[::2, 1::2, 1::2, ::2, 1::2, 1::2])
    assert numpy.allclose(test_ccckkk[1::2, ::2, 1::2, 1::2, 1::2, ::2],
                          three_pdm[1::2, ::2, 1::2, 1::2, 1::2, ::2])
    assert numpy.allclose(test_ccckkk[1::2, ::2, 1::2, 1::2, ::2, 1::2],
                          three_pdm[1::2, ::2, 1::2, 1::2, ::2, 1::2])
    assert numpy.allclose(test_ccckkk[1::2, ::2, 1::2, ::2, 1::2, 1::2],
                          three_pdm[1::2, ::2, 1::2, ::2, 1::2, 1::2])
    assert numpy.allclose(test_ccckkk[1::2, 1::2, ::2, 1::2, 1::2, ::2],
                          three_pdm[1::2, 1::2, ::2, 1::2, 1::2, ::2])
    assert numpy.allclose(test_ccckkk[1::2, 1::2, ::2, 1::2, ::2, 1::2],
                          three_pdm[1::2, 1::2, ::2, 1::2, ::2, 1::2])
    assert numpy.allclose(test_ccckkk[1::2, 1::2, ::2, ::2, 1::2, 1::2],
                          three_pdm[1::2, 1::2, ::2, ::2, 1::2, 1::2])

    assert numpy.allclose(test_ccckkk, three_pdm)
