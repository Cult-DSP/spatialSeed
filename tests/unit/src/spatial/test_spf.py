import unittest
import numpy as np
import math
from src.spatial.spf import SPFResolver, spherical_to_cartesian, clamp_to_cube

class TestSPF(unittest.TestCase):
    def setUp(self):
        self.resolver = SPFResolver()
        self.default_z = np.array([0.5]*8)
        self.zero_z = np.zeros(8)
        self.one_z = np.ones(8)

    def test_spherical_to_cartesian(self):
        # Front, ear level
        x, y, z = spherical_to_cartesian(0.0, 0.0, 1.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 1.0)
        self.assertAlmostEqual(z, 0.0)

        # Right, ear level
        x, y, z = spherical_to_cartesian(90.0, 0.0, 1.0)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 0.0)

        # Top
        x, y, z = spherical_to_cartesian(0.0, 90.0, 1.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 1.0)

    def test_clamp_to_cube(self):
        self.assertEqual(clamp_to_cube(1.5, -2.0, 0.5), (1.0, -1.0, 0.5))
        self.assertEqual(clamp_to_cube(0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def test_resolve_style_profile_vocals_lead(self):
        classification = {"category": "vocals", "role_hint": "lead"}
        mir = {} # Doesn't matter for resolve_style_profile largely right now
        sp = self.resolver.resolve_style_profile("11.1", classification, mir, self.default_z)
        
        self.assertEqual(sp.category, "vocals")
        self.assertEqual(sp.role, "lead")
        # Lead vocals should be near center
        self.assertTrue(-0.2 <= sp.base_x <= 0.2)
        # Verify base distance logic somewhat works out
        self.assertTrue(0.0 <= sp.base_y <= 1.0)
        self.assertTrue(0.0 <= sp.base_z <= 1.0)

    def test_resolve_style_profile_left_right(self):
        classification = {"category": "guitar", "role_hint": "rhythm"}
        mir = {}

        sp_left = self.resolver.resolve_style_profile("11.1", classification, mir, self.default_z, stereo_side="left")
        sp_right = self.resolver.resolve_style_profile("11.2", classification, mir, self.default_z, stereo_side="right")
        
        self.assertTrue(sp_left.base_x > sp_right.base_x or sp_left.base_x < sp_right.base_x)

    def test_resolve_style_profile_motion_intensity(self):
        classification = {"category": "other", "role_hint": "unknown"}
        mir = {}
        
        sp_static = self.resolver.resolve_style_profile("11.1", classification, mir, self.zero_z)
        self.assertEqual(sp_static.motion_type, "static")

if __name__ == '__main__':
    unittest.main()
