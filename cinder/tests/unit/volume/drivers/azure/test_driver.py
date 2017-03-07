import ddt

import mock
from oslo_config import cfg
from oslo_service import loopingcall

from cinder import db
from cinder import exception
from cinder.objects.volume import MetadataObject
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

    def __getitem__(self, name):
        return getattr(self, name)

    def get(self, name, default):
        value = getattr(self, name)
        if not value:
            return default
        return value

    def __setitem__(self, name, value):
        setattr(self, name, value)


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
        metadata_obj = MetadataObject('os_type', 'fake_type')
        self.fake_vol = FakeObj()
        self.fake_vol.name = 'vol_name'
        self.fake_vol.id = 'vol_id'
        self.fake_vol.size = 1
        self.fake_vol.metadata = dict(os_type='fake_type')
        self.fake_vol.volume_metadata = [metadata_obj]
        self.fake_snap = dict(
            name='snap_name',
            id='snap_id',
            volume_id='volume_id',
            properties=dict(os_type='linux', azure_image_size_gb=2),
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

    def test_get_volume_stats(self):
        ret = self.driver.get_volume_stats()
        self.assertEqual(self.configuration.azure_total_capacity_gb,
                         ret['total_capacity_gb'])

    def test_get_name_from_id(self):
        prefix = 'prefix'
        name = 'name'
        ret = self.driver._get_name_from_id(prefix, name)
        self.assertEqual(prefix + '-' + name, ret)

    def test_copy_disk_raise(self):
        # raise test
        self.driver.disks.create_or_update = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver._copy_disk,
            self.fake_vol, 'source')

    def test_create_volume(self):
        self.driver.create_volume(self.fake_vol)
        self.driver.disks.create_or_update.assert_called()

    def test_create_volume_create_raise(self):
        self.driver.disks.create_or_update.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume,
            self.fake_vol)
        self.driver.disks.delete.assert_called()

    def test_create_volume_delete_raise(self):
        self.driver.disks.create_or_update.side_effect = Exception
        self.driver.disks.delete.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume,
            self.fake_vol)

    def test_delete_volume(self):
        self.driver.delete_volume(self.fake_vol)
        self.driver.disks.delete.assert_called()

    def test_delete_volume_miss_raise(self):
        self.driver.disks.delete.side_effect = \
            AzureMissingResourceHttpError('', '')
        self.driver.delete_volume(self.fake_vol)
        self.driver.disks.delete.assert_called()

    def test_delete_volume_delete_raise(self):
        self.driver.disks.delete.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.delete_volume,
            self.fake_vol)

    def test_initialize_connection(self):
        ret = self.driver.initialize_connection(self.fake_vol, 'con')
        self.assertEqual('local', ret['driver_volume_type'])
        self.assertEqual(None, ret['data']['device_path'])

    def test_create_snapshot(self):
        ret = self.driver.create_snapshot(self.fake_snap)
        snapshot_name = self.driver._get_name_from_id(driver.SNAPSHOT_PREFIX,
                                                      self.fake_snap['id'])
        self.assertEqual(snapshot_name,
                         ret['metadata']['azure_snapshot_id'])

    def test_create_snapshot_raise(self):
        self.driver.snapshots.create_or_update.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_snapshot,
            self.fake_snap)

    def test_delete_snapshot(self):
        self.driver.delete_snapshot(self.fake_snap)
        self.driver.snapshots.delete.assert_called()

    def test_delete_snapshot_miss_raise(self):
        self.driver.snapshots.delete.side_effect = \
            AzureMissingResourceHttpError('', '')
        self.driver.delete_snapshot(self.fake_snap)
        self.driver.snapshots.delete.assert_called()

    def test_delete_snapshot_delete_raise(self):
        self.driver.snapshots.delete.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.delete_snapshot,
            self.fake_snap)

    def test_create_volume_from_snapshot_miss(self):
        # non exist volume, raise not found
        self.driver.snapshots.get.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_volume_from_snapshot,
            self.fake_vol, self.fake_snap)

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_copy_disk')
    def test_create_volume_from_snapshot(self, mo_copy):
        self.driver.create_volume_from_snapshot(self.fake_vol, self.fake_snap)
        mo_copy.assert_called()

    def test_create_cloned_volume_miss(self):
        # non exist volume, raise not found
        self.driver.disks.get.side_effect = Exception
        self.assertRaises(
            exception.VolumeNotFound,
            self.driver.create_cloned_volume,
            self.fake_vol, self.fake_snap)

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_copy_disk')
    def test_create_cloned_volume(self, mo_copy):
        self.driver.create_cloned_volume(self.fake_vol, self.fake_snap)
        mo_copy.assert_called()

    def test_create_volume_from_image_miss(self):
        # non exist image, raise not found
        self.driver.disks.get.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.clone_image,
            self.context, self.fake_vol, '', self.fake_snap, '')

    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_copy_disk')
    def test_create_volume_from_image(self, mo_copy):
        self.driver.clone_image(self.context, self.fake_vol, '',
                                      self.fake_snap, '')
        mo_copy.assert_called()

    def test_copy_volume_to_image_miss(self):
        # non exist volume, raise not found
        self.driver.disks.get.side_effect = Exception
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.copy_volume_to_image,
            self.context, self.fake_vol, '', self.fake_snap)

    @mock.patch('cinder.image.image_utils.upload_volume')
    @mock.patch.object(cinder.volume.drivers.azure.driver.AzureDriver,
                       '_copy_disk')
    def test_copy_volume_to_image(self, mo_upload, mo_copy):
        self.fake_vol.size = 2
        self.driver.copy_volume_to_image(self.context,
                                         self.fake_vol,
                                         mock.Mock(),
                                         self.fake_snap)
        mo_copy.assert_called()
