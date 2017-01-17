import ddt

import mock
from oslo_config import cfg
from oslo_service import loopingcall
from oslo_utils import units

from cinder import db
from cinder import exception
from cinder.tests.unit import test_volume
from cinder.volume.drivers.azure import driver
from cinder.volume.drivers.azure.driver import AzureMissingResourceHttpError
import cinder.volume.utils


CONF = cfg.CONF


class FakeLoopingCall(object):

    def __init__(self, method):
        self.call = method

    def start(self, *a, **k):
        return self

    def wait(self):
        self.call()


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
        self.stubs.Set(loopingcall, 'FixedIntervalLoopingCall',
                       lambda a: FakeLoopingCall(a))

    def test_empty_methods_implement(self):
        self.driver.check_for_setup_error()
        self.driver.ensure_export(self.context, self.fake_vol)
        self.driver.create_export(self.context, self.fake_vol, 'conn')
        self.driver.remove_export(self.context, self.fake_vol)
        self.driver.validate_connector('conn')
        self.driver.terminate_connection(self.fake_vol, 'conn')

    @mock.patch('cinder.volume.drivers.azure.driver.Azure')
    def test_init_raise(self, mock_azure):
        mock_azure.side_effect = Exception
        self.assertRaises(exception.VolumeBackendAPIException,
                          driver.AzureDriver,
                          configuration=self.configuration, db=db)

    @mock.patch('cinder.volume.drivers.azure.driver.Azure')
    def test_init_create_blob_container_raise(self, mock_azure):
        blob = mock.Mock()
        blob.blob.create_container.side_effect = Exception
        mock_azure.return_value = blob
        self.assertRaises(exception.VolumeBackendAPIException,
                          driver.AzureDriver,
                          configuration=self.configuration, db=db)

    def test_get_volume_stats(self):
        ret = self.driver.get_volume_stats()
        self.assertEqual(self.configuration.azure_total_capacity_gb,
                         ret['total_capacity_gb'])

    def test_get_blob_name(self):
        name = 'name'
        ret = self.driver._get_blob_name(name)
        self.assertEqual(name + '.' + driver.VHD_EXT, ret)

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
    def test_create_volume(self, mo_vhd):
        mo_vhd.return_value = 'vhd_footer'
        self.driver.create_volume(self.fake_vol)
        self.driver.blob.update_page.assert_called()

    @mock.patch.object(cinder.volume.drivers.azure.vhd_utils,
                       'generate_vhd_footer')
    def test_create_volume_create_raise(self, mo_vhd):
        mo_vhd.return_value = 'vhd_footer'
        self.driver.blob.update_page.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume,
            self.fake_vol)
        self.driver.blob.delete_blob.assert_called()

    @mock.patch.object(cinder.volume.drivers.azure.vhd_utils,
                       'generate_vhd_footer')
    def test_create_volume_delete_raise(self, mo_vhd):
        mo_vhd.return_value = 'vhd_footer'
        self.driver.blob.update_page.side_effect = Exception
        self.driver.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume,
            self.fake_vol)

    def test_delete_volume(self):
        self.driver.delete_volume(self.fake_vol)
        self.driver.blob.delete_blob.assert_called()

    def test_delete_volume_miss_raise(self):
        self.driver.blob.delete_blob.side_effect = \
            AzureMissingResourceHttpError('', '')
        self.driver.delete_volume(self.fake_vol)
        self.driver.blob.delete_blob.assert_called()

    def test_delete_volume_delete_raise(self):
        self.driver.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.delete_volume,
            self.fake_vol)

    def test_initialize_connection(self):
        ret = self.driver.initialize_connection(self.fake_vol, 'con')
        self.assertEqual('local', ret['driver_volume_type'])
        self.assertEqual(None, ret['data']['device_path'])

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
        self.driver.delete_snapshot(self.fake_snap)
        self.driver.blob.delete_blob.assert_called()

    def test_delete_snapshot_miss_raise(self):
        self.driver.blob.delete_blob.side_effect = \
            AzureMissingResourceHttpError('', '')
        self.driver.delete_snapshot(self.fake_snap)
        self.driver.blob.delete_blob.assert_called()

    def test_delete_snapshot_delete_raise(self):
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

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_volume_from_snapshot(self, mo_exit):
        mo_exit.return_value = True
        self.fake_snap['volume_size'] = 1
        self.fake_vol.size = 2
        self.fake_vol.update = mock.Mock()
        self.fake_vol.save = mock.Mock()
        self.driver.create_volume_from_snapshot(self.fake_vol, self.fake_snap)
        self.fake_vol.update.assert_called_once_with(
            dict(size=self.fake_snap['volume_size']))
        self.fake_vol.save.assert_called_once()

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_cloned_volume_miss(self, mo_exit):
        # non exist volume, raise not found
        mo_exit.return_value = False
        self.assertRaises(
            exception.VolumeNotFound,
            self.driver.create_cloned_volume,
            self.fake_vol, self.fake_snap)

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_cloned_volume(self, mo_exit):
        mo_exit.return_value = True
        self.fake_snap['size'] = 1
        self.fake_vol.size = 2
        self.fake_vol.update = mock.Mock()
        self.fake_vol.save = mock.Mock()
        self.driver.create_cloned_volume(self.fake_vol, self.fake_snap)
        self.fake_vol.update.assert_called_once_with(
            dict(size=self.fake_snap['size']))
        self.fake_vol.save.assert_called_once()

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_volume_from_image_miss(self, mo_exit):
        # non exist image, raise not found
        mo_exit.return_value = False
        self.assertRaises(
            exception.ImageNotFound,
            self.driver.clone_image,
            self.context, self.fake_vol, '', self.fake_snap, '')

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_check_exist')
    def test_create_volume_from_image(self, mo_exit):
        mo_exit.return_value = True
        size = 1
        self.fake_snap['size'] = size * units.Gi
        self.fake_vol.size = 2
        self.fake_vol.update = mock.Mock()
        self.fake_vol.save = mock.Mock()
        self.driver.clone_image(self.context, self.fake_vol, '',
                                self.fake_snap, '')
        self.fake_vol.update.assert_called_once_with(
            dict(size=size))
        self.fake_vol.save.assert_called_once()
