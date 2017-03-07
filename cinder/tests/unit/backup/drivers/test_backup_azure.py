import ddt
import mock
from oslo_config import cfg
from oslo_service import loopingcall
from cinder.backup.drivers import azure_backup
from cinder import context
from cinder import exception
from cinder import test
from cinder.volume.drivers.azure.driver import AzureMissingResourceHttpError
import cinder.volume.utils

CONF = cfg.CONF


class FakeObj(object):
    def __getitem__(self, item):
        self.__getattribute__(item)


class FakeLoopingCall(object):
    def __init__(self, method):
        self.call = method
        print(str(method))

    def start(self, *a, **k):
        return self

    def wait(self):
        self.call()


@ddt.ddt
class AzureBackupDriverTestCase(test.TestCase):
    @mock.patch('cinder.backup.drivers.azure_backup.Azure')
    def setUp(self, mock_azure):
        self.mock_azure = mock_azure
        super(AzureBackupDriverTestCase, self).setUp()
        self.cxt = context.get_admin_context()
        self.driver = azure_backup.AzureBackupDriver(self.cxt)
        self.fack_backup = dict(name='backup_name',
                                id='backup_id',
                                volume_id='volume_id',
                                snapshot_id=None)
        self.stubs.Set(loopingcall, 'FixedIntervalLoopingCall',
                       lambda a: FakeLoopingCall(a))

    @mock.patch('cinder.backup.drivers.azure_backup.Azure')
    def test_init_adapter_raise(self, mock_azure):
        mock_azure.side_effect = Exception
        self.assertRaises(exception.BackupDriverException,
                          azure_backup.AzureBackupDriver,
                          self.cxt)

    def test_get_name_from_id(self):
        prefix = 'prefix'
        name = 'name'
        ret = self.driver._get_name_from_id(prefix, name)
        self.assertEqual(prefix + '-' + name, ret)

    def test_copy_disk_raise(self):
        # raise test
        self.driver.disks.create_or_update.side_effect = Exception
        self.assertRaises(
            exception.BackupDriverException,
            self.driver._copy_disk,
            self.fack_backup, 'source')

    def test_copy_snapshot_raise(self):
        # raise test
        self.driver.snapshots.create_or_update.side_effect = Exception
        self.assertRaises(
            exception.BackupDriverException,
            self.driver._copy_snapshot,
            self.fack_backup, 'source')

    def test_delete_backup_miss(self):
        self.driver.snapshots.delete.side_effect = \
            AzureMissingResourceHttpError('', '')
        flag = self.driver.delete(self.fack_backup)
        self.assertEqual(True, flag)

    def test_delete_backup_exception(self):
        self.driver.snapshots.delete.side_effect = Exception
        self.assertRaises(
            exception.BackupDriverException,
            self.driver.delete,
            self.fack_backup)

    def test_delete_backup(self):
        self.driver.snapshots.delete = mock.Mock()
        self.driver.delete(self.fack_backup)
        self.driver.snapshots.delete.assert_called()

    def test_backup_miss(self):
        self.driver.disks.get.side_effect = Exception
        self.assertRaises(
            exception.VolumeNotFound,
            self.driver.backup,
            self.fack_backup, 'vol_file')

    @mock.patch.object(cinder.backup.drivers.azure_backup.AzureBackupDriver,
                       '_copy_snapshot')
    def test_backup(self, mo_copy):
        self.driver.db.volume_get = mock.Mock(return_value=self.fack_backup)
        self.driver.backup(self.fack_backup, 'vol_file')
        mo_copy.assert_called()

    def test_restore_miss(self):
        self.driver.snapshots.get.side_effect = Exception
        self.assertRaises(
            exception.BackupNotFound,
            self.driver.restore,
            self.fack_backup, 'vol_id', 'vol_file')

    @mock.patch.object(cinder.backup.drivers.azure_backup.AzureBackupDriver,
                       '_copy_disk')
    def test_restore(self, mo_copy):
        self.driver.db.volume_get = mock.Mock(return_value=self.fack_backup)
        self.driver.restore(self.fack_backup, 'vol_id', 'vol_file')
        mo_copy.assert_called()


class GetBackupDriverTestCase(test.TestCase):
    @mock.patch('cinder.backup.drivers.azure_backup.AzureBackupDriver')
    def test_get_backup_driver(self, mock_driver):
        context = 'context'
        azure_backup.get_backup_driver(context)
        mock_driver.assert_called_with(context)
