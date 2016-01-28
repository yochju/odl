# Copyright 2014, 2015 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

"""Test for X-ray transforms."""

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library

standard_library.install_aliases()

# External
import numpy as np
import pytest

# Internal
import odl
from odl import tomo
from odl.util.testutils import almost_equal


# Find the valid projectors
projectors = []
if tomo.ASTRA_AVAILABLE:
    projectors += ['par2d cpu unifrom',
                   'cone2d cpu unifrom',
                   'par2d cpu random',
                   'cone2d cpu random']
if tomo.ASTRA_CUDA_AVAILABLE:
    projectors += ['par2d cuda unifrom',
                   'cone2d cuda unifrom',
                   'par3d cuda unifrom',
                   'cone3d cuda unifrom',
                   'cone3d cuda random',
                   'helical cuda unifrom']


@pytest.fixture(scope="module",
                params=projectors)
def projector(request):
    n_voxels = 100
    n_angles = 100
    n_pixels = 100

    geom, version, angle = request.param.split()

    if angle == 'unifrom':
        angle_intvl = odl.Interval(0, 2 * np.pi)
        agrid = odl.uniform_sampling(angle_intvl, n_angles)
    elif angle == 'random':
        angle_intvl = odl.Interval(0, 2 * np.pi)
        minp = 2 * (2.0 * np.pi) / n_angles
        maxp = (2.0 * np.pi) - 2 * (2.0 * np.pi) / n_angles
        points = np.sort(np.random.rand(n_angles)) * (maxp - minp) + minp

        agrid = odl.TensorGrid(points, as_midp=True)
    else:
        raise ValueError('agnle not valid')

    if geom == 'par2d':
        # Discrete reconstruction space
        discr_reco_space = odl.uniform_discr([-20, -20],
                                             [20, 20],
                                             [n_voxels] * 2, dtype='float32')

        # Geometry
        dparams = odl.Interval(-30, 30)
        dgrid = odl.uniform_sampling(dparams, n_pixels)

        geom = tomo.Parallel2dGeometry(angle_intvl, dparams, agrid, dgrid)
        return tomo.XrayTransform(discr_reco_space, geom,
                                  backend='astra_' + version)

    elif geom == 'par3d':
        # Discrete reconstruction space
        discr_reco_space = odl.uniform_discr([-20, -20, -20],
                                             [20, 20, 20],
                                             [n_voxels] * 3, dtype='float32')

        # Geometry
        dparams = odl.Rectangle([-30, -30], [30, 30])
        dgrid = odl.uniform_sampling(dparams, [n_pixels] * 2)

        geom = tomo.Parallel3dGeometry(angle_intvl, dparams, agrid, dgrid)

        # X-ray transform
        return tomo.XrayTransform(discr_reco_space, geom,
                                  backend='astra_' + version)

    elif geom == 'cone2d':
        # Discrete reconstruction space
        discr_reco_space = odl.uniform_discr([-20, -20],
                                             [20, 20],
                                             [n_voxels] * 2, dtype='float32')

        # Geometry
        dparams = odl.Interval(-30, 30)
        dgrid = odl.uniform_sampling(dparams, n_pixels)

        geom = tomo.FanFlatGeometry(angle_intvl, dparams,
                                    src_radius=200, det_radius=100,
                                    agrid=agrid, dgrid=dgrid)

        # X-ray transform
        return tomo.XrayTransform(discr_reco_space, geom,
                                  backend='astra_' + version)

    elif geom == 'cone3d':
        # Discrete reconstruction space
        discr_reco_space = odl.uniform_discr([-20, -20, -20],
                                             [20, 20, 20],
                                             [n_voxels] * 3, dtype='float32')

        # Geometry
        dparams = odl.Rectangle([-30, -30], [30, 30])
        dgrid = odl.uniform_sampling(dparams, [n_pixels] * 2)

        geom = tomo.CircularConeFlatGeometry(angle_intvl, dparams,
                                             src_radius=200, det_radius=100,
                                             agrid=agrid, dgrid=dgrid)

        # X-ray transform
        return tomo.XrayTransform(discr_reco_space, geom,
                                  backend='astra_' + version)

    elif geom == 'helical':
        # Discrete reconstruction space
        discr_reco_space = odl.uniform_discr([-20, -20, 0],
                                             [20, 20, 40],
                                             [n_voxels] * 3, dtype='float32')

        # overwrite angle
        angle_intvl = odl.Interval(0, 8 * 2 * np.pi)
        agrid = odl.uniform_sampling(angle_intvl, n_angles)

        dparams = odl.Rectangle([-30, -3], [30, 3])
        dgrid = odl.uniform_sampling(dparams, [n_pixels] * 2)
        geom = tomo.HelicalConeFlatGeometry(angle_intvl, dparams, pitch=5.0,
                                            src_radius=200, det_radius=100,
                                            agrid=agrid, dgrid=dgrid)

        # X-ray transform
        return tomo.XrayTransform(discr_reco_space, geom,
                                  backend='astra_' + version)
    else:
        raise ValueError('geom not valid')


def test_projector(projector):
    """Test discrete X-ray transform using ASTRA for reconstruction."""

    # TODO: this needs to be improved
    # Accept 10% errors
    places = 1

    # Domain element
    one_vol = projector.domain.one()

    # Forward projection
    data = projector(one_vol)

    # Range element
    one_proj = projector.range.one()

    # Back projection
    backproj = projector.adjoint(one_proj)

    # Adjoint matching
    inner_proj = data.inner(one_proj)
    inner_vol = one_vol.inner(backproj)
    assert almost_equal(inner_vol, inner_proj, places=places)


if __name__ == '__main__':
    pytest.main(str(__file__.replace('\\', '/') + ' -v'))
