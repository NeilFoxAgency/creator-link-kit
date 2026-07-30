import unittest

import creator_link_kit


class PublicApiTests(unittest.TestCase):
    def test_all_declared_public_objects_are_importable(self):
        for name in creator_link_kit.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(creator_link_kit, name))
        self.assertEqual(creator_link_kit.__version__, "0.2.0")


if __name__ == "__main__":
    unittest.main()
