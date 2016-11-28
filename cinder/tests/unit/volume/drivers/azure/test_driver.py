import ddt

import mock
from oslo_config import cfg

from cinder import db
from cinder import exception
from cinder.tests.unit import test_volume
from cinder.volume.drivers.azure import driver
from cinder.volume.drivers.azure.driver import AzureMissingResourceHttpError
import cinder.volume.utils


CONF = cfg.CONF


class FakeObj(object):

    def __getitem__(self, item):
        self.__getattribute__(item)


@ddt.ddt
class AzureVolumeDriverTestCase(test_volume.DriverTestCase):
    """Test case for VolumeDriver"""
    driver_name = "cinder.volume.drivers.azure.driver.AzureDriver"
    FAKE_VOLUME = {'name': 'test1',
                   'id': 'test1'}

    @mock.patch('cinder.volume.drivers.azure.driver.Azure')
    def setUp(self, mock_azure):
        self.mock_azure = mock_azure
        super(AzureVolumeDriverTestCase, self).setUp()

        self.driver = driver.AzureDriver(configuration=self.configuration,
                                         db=db)
        self.fake_vol = FakeObj()
        self.fake_vol.name = 'vol_name'
        self.fake_vol.id = 'vol_id'
        self.fake_vol.size = 1
        self.fake_snap = dict(
            name='snap_name',
            id='snap_id',
            volume_name='vol_name',
            metadata=dict(azure_snapshot_id='snap_id'))

    @mock.patch('cinder.volume.drivers.azure.driver.Azure')
    def test_init_raise(self, mock_azure):
        mock_azure.side_effect = Exception
        self.assertRaises(exception.VolumeBackendAPIException,
                          driver.AzureDriver,
                          configuration=self.configuration, db=db)

    def test_copy_blob_raise(self):
        # raise test
        self.driver.blob.copy_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver._copy_blob,
            self.fake_vol, 'source')

    def test_check_exist_raise(self):
        # raise test
        self.driver.blob.exists.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver._check_exist,
            self.fake_vol)

    def test_check_exist(self):
        self.driver.blob.exists.side_effect = None
        exist = self.driver.blob.exists.retrun_value = True
        self.assertEqual(True, exist)

    @mock.patch.object(cinder.volume.drivers.azure.vhd_utils,
                       'generate_vhd_footer')
    def test_create_volume_raise(self, mo_vhd):
        mo_vhd.return_value = 'vhd_footer'
        self.driver.blob.update_page.side_effect = Exception
        self.driver.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume,
            self.fake_vol)

    def test_delete_volume(self):
        self.driver.blob.delete_blob.side_effect = \
            AzureMissingResourceHttpError('', '')
        flag = self.driver.delete_volume(self.fake_vol)
        self.assertEqual(True, flag)

    def test_delete_volume_raise(self):
        self.driver.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.delete_volume,
            self.fake_vol)

    def test_create_snapshot(self):
        snap_obj = FakeObj()
        snap_obj.snapshot = 'snap_id'
        self.driver.blob.snapshot_blob.return_value = snap_obj
        ret = self.driver.create_snapshot(self.fake_snap)
        self.assertEqual(snap_obj.snapshot,
                         ret['metadata']['azure_snapshot_id'])

    def test_create_snapshot_raise(self):
        self.driver.blob.snapshot_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_snapshot,
            self.fake_snap)

    def test_delete_snapshot(self):
        self.driver.blob.delete_blob.side_effect = \
            AzureMissingResourceHttpError('', '')
        ret = self.driver.delete_snapshot(self.fake_snap)
        self.assertEqual(True, ret)

    def test_delete_snapshot_raise(self):
        self.driver.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.delete_snapshot,
            self.fake_snap)

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_volume_from_snapshot_miss(self, mo_exit):
        # non exist volume, raise not found
        mo_exit.return_value = False
        self.assertRaises(
            exception.SnapshotNotFound,
            self.driver.create_volume_from_snapshot,
            self.fake_vol, self.fake_snap)

    @mock.patch(
        'cinder.volume.drivers.azure.driver'
        '.loopingcall.FixedIntervalLoopingCall')
    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_volume_from_snapshot(self, mo_exit, mock_loop_call):
        mock_loop_call.return_value = mock.MagicMock()
        mo_exit.return_value = True
        self.fake_snap['volume_size'] = 1
        self.fake_vol.size = 2
        self.fake_vol.update = mock.Mock()
        self.fake_vol.save = mock.Mock()
        self.driver.create_volume_from_snapshot(self.fake_vol, self.fake_snap)
        self.fake_vol.update.assert_called_once_with(
            dict(size=self.fake_snap['volume_size']))
        self.fake_vol.save.assert_called_once()
