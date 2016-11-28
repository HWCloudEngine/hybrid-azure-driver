import testtools

from cinder.volume.drivers.azure.vhd_utils import generate_vhd_footer


class GenerateVhdFooterTestCase(testtools.TestCase):

    def test_generate_vhd_footer(self):
        footer = generate_vhd_footer(1024)
        self.assertEqual(512, len(footer))
