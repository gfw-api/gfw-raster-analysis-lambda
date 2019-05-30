from raster_analysis import geoprocessing
from shapely.geometry import Polygon
from unittest import mock
import numpy as np
import pandas as pd
import affine

A = np.array([[1, 2, 3],
              [2, 3, 4],
              [3, 4, 5]])

B = np.array([[2, 3, 4],
              [3, 4, 5],
              [4, 5, 6]])

C = np.array([[3, 4, 5],
              [4, 5, 6],
              [5, 6, 7]])

AREA = 769.288482

AREA_ARRAY = np.array([[3., 4., 5., AREA],
                       [3., 4., 5., AREA],
                       [4., 5., 6., AREA],
                       [3., 4., 5., AREA],
                       [4., 5., 6., AREA],
                       [5., 6., 7., AREA]])

MASK = np.array([[False, False, True],
                 [False, True, True],
                 [True, True, True]])

GEOMETRY = Polygon([(0, 0), (1, 1), (1, 0)])

EXTENT = GEOMETRY.bounds


class DummySrc(object):
    def __init__(self):
        self.nodata = 0
        self.transform = affine.Affine.identity()


class DummySrcA(DummySrc):

    def read(self, band, masked, window):
        if masked:
            return np.ma.array(A, mask=MASK)
        else:
            return A


class DummySrcB(DummySrc):

    def read(self, band, masked, window):
        if masked:
            return np.ma.array(B, mask=MASK)
        else:
            return B


class DummySrcC(DummySrc):

    def read(self, band, masked, window):
        if masked:
            return np.ma.array(C, mask=MASK)
        else:
            return C


def test__mask_by_threshold():
    result = geoprocessing._mask_by_threshold(A, 2)
    expected_result = np.array([[False, False, True],
                                [False, True, True],
                                [True, True, True]])

    np.testing.assert_array_equal(result, expected_result)


def test__mask_by_nodata():
    result = geoprocessing._mask_by_nodata(A, 2)
    expected_result = np.array([[True, False, True],
                                [False, True, True],
                                [True, True, True]])

    np.testing.assert_array_equal(result, expected_result)


@mock.patch("raster_analysis.geoprocessing.read_window_ignore_missing")
def test__build_array(mock_data):
    mock_data.side_effect = [(B, None, None), (C, None, None)]
    result = geoprocessing._build_array(MASK, A, "src_b", "src_c", geom=GEOMETRY)
    expected_result = np.array([[3, 4, 5],
                                [3, 4, 5],
                                [4, 5, 6],
                                [3, 4, 5],
                                [4, 5, 6],
                                [5, 6, 7]])

    np.testing.assert_array_equal(result, expected_result)


@mock.patch("raster_analysis.geoprocessing.read_window_ignore_missing")
def test__build_array_with_area(mock_data):
    mock_data.side_effect = [(B, None, None), (C, None, None)]
    result = geoprocessing._build_array(MASK, A, "src_b", "src_c", geom=GEOMETRY, area=True)
    expected_result = AREA_ARRAY

    np.testing.assert_allclose(result, expected_result, rtol=1e-6, atol=0)


def test__sum():
    result = geoprocessing._sum(AREA_ARRAY)
    expected_result = pd.DataFrame(
        {'col0': [3., 4., 5.],
         'col1': [4., 5., 6.],
         'col2': [5., 6., 7.],
         'value': [AREA * 3, AREA * 2, AREA]})

    pd.testing.assert_frame_equal(result, expected_result)
