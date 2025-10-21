import unittest
import os
from src.config import parse_config


class TestConfig(unittest.TestCase):
    def test_config_peerinfo(self):
        os.chdir("./tests")
        conf = parse_config()
        self.assertEqual(conf.file_name, "TheFile.dat")


if __name__ == "__main__":
    unittest.main()
