import unittest

import minchin.releaser


class Test_Setup(unittest.TestCase):

    def test_we_live(self):
        '''Test we should *always* pass'''
        pass

    def test_version(self):
        '''Version is available'''
        self.assertIsNotNone(minchin.releaser.__version__)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
