import unittest
import numpy as np
from src.mapping.seed_matrix import SeedMatrix, interpolate_between_selections

class TestSeedMatrix(unittest.TestCase):
    def setUp(self):
        self.sm = SeedMatrix()

    def test_map_uv_to_z_zeros(self):
        z = self.sm.map_uv_to_z(0.0, 0.0)
        self.assertEqual(len(z), 8)
        self.assertTrue(all(0.0 <= val <= 1.0 for val in z), "All values should be clamped between 0 and 1")
        self.assertAlmostEqual(z[6], 0.0) # ensemble cohesion = u = 0.0

    def test_map_uv_to_z_ones(self):
        z = self.sm.map_uv_to_z(1.0, 1.0)
        self.assertEqual(len(z), 8)
        self.assertTrue(all(0.0 <= val <= 1.0 for val in z), "All values should be clamped between 0 and 1")
        self.assertAlmostEqual(z[2], 1.0) # motion intensity = v = 1.0

    def test_map_uv_to_z_center(self):
        z = self.sm.map_uv_to_z(0.5, 0.5)
        self.assertEqual(len(z), 8)
        self.assertTrue(all(0.0 <= val <= 1.0 for val in z), "All values should be clamped between 0 and 1")

    def test_map_uv_to_z_out_of_bounds(self):
        z = self.sm.map_uv_to_z(-0.5, 1.5)
        self.assertEqual(len(z), 8)
        self.assertTrue(all(0.0 <= val <= 1.0 for val in z), "Values should be handled and mapped robustly, resulting in outputs between 0 and 1")
        
    def test_interpolate_between_selections(self):
        uv1 = (0.0, 0.0)
        uv2 = (1.0, 1.0)
        uv_mid = interpolate_between_selections(uv1, uv2, 0.5)
        self.assertEqual(uv_mid, (0.5, 0.5))

if __name__ == '__main__':
    unittest.main()
