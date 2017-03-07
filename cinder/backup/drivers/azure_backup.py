#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging
import six

from azure.common import AzureMissingResourceHttpError
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.compute.models import StorageAccountTypes
from cinder.backup import driver
from cinder import exception
from cinder.i18n import _, _LI
from cinder.volume.drivers.azure.adapter import Azure
from cinder.volume.drivers.azure.adapter import CONF

LOG = logging.getLogger(__name__)
BACKUP_PREFIX = 'backup'
VOLUME_PREFIX = 'volume'
SNAPSHOT_PREFIX = 'snapshot'
TMP_PREFIX = 'tmp'


class AzureBackupDriver(driver.BackupDriver):
    def __init__(self, context, db_driver=None, execute=None):
        super(AzureBackupDriver, self).__init__(context, db_driver)

        try:
            self.azure = Azure()
            self.disks = self.azure.compute.disks
            self.snapshots = self.azure.compute.snapshots
        except Exception as e:
            message = (_("Initialize Azure Adapter failed. reason: %s")
                       % six.text_type(e))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

    def _copy_disk(self, disk_name, source_id, azure_type):
        disk_dict = {
            'location': CONF.azure.location,
            'account_type': azure_type,
            'creation_data': {
                'create_option': DiskCreateOption.copy,
                'source_uri': source_id
            }
        }
        try:
            async_action = self.disks.create_or_update(
                CONF.azure.resource_group,
                disk_name,
                disk_dict
            )
            async_action.result()
        except Exception as e:
            try:
                self.disks.delete(
                    CONF.azure.resource_group,
                    disk_name
                )
            except Exception:
                LOG.exception(_('Failed to elete disk %s after create disk'
                              ' failed') % disk_name)
            message = (_("Copy disk %(blob_name)s from %(source_id)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=disk_name, source_id=source_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

    def _copy_snapshot(self, disk_name, source_id, size=None):
        disk_dict = {
            'location': CONF.azure.location,
            'creation_data': {
                'create_option': DiskCreateOption.copy,
                'source_uri': source_id
            }
        }
        if size:
            disk_dict['disk_size_gb'] = size
        try:
            async_action = self.snapshots.create_or_update(
                CONF.azure.resource_group,
                disk_name,
                disk_dict
            )
            async_action.result()
        except Exception as e:
            try:
                self.snapshots.delete(
                    CONF.azure.resource_group,
                    disk_name
                )
            except Exception:
                LOG.exception(_('Failed to elete snapshot %s after create'
                              ' failed') % disk_name)
            message = (_("Copy disk %(blob_name)s from %(source_id)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=disk_name, source_id=source_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

    def _get_name_from_id(self, prefix, resource_id):
        return '{}-{}'.format(prefix, resource_id)

    def backup(self, backup, volume_file, backup_metadata=True):
        """Backup azure volume to azure .

        only support backup from and to azure.
        """
        volume = self.db.volume_get(self.context,
                                    backup['volume_id'])

        # backup with --snapshot-id
        if backup['snapshot_id'] is not None:
            src_vref_name = self._get_name_from_id(
                SNAPSHOT_PREFIX, backup['snapshot_id'])
            resource_driver = self.snapshots

        # backup volume
        else:
            src_vref_name = self._get_name_from_id(
                VOLUME_PREFIX, volume['id'])
            resource_driver = self.disks

        disk_name = self._get_name_from_id(
            BACKUP_PREFIX, backup['id'])
        try:
            src_vref_obj = resource_driver.get(
                CONF.azure.resource_group,
                src_vref_name
            )
        except Exception as e:
            message = (_("Create Back of %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=src_vref_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeNotFound(volume_id=volume['id'])
        else:
            self._copy_snapshot(disk_name, src_vref_obj.id)

    def restore(self, backup, volume_id, volume_file):
        """Restore volume from backup in azure.

        only support restore backup from and to azure.
        delete volume disk and then copy backup to volume disk, since
        managed disk have no restore operation.
        """
        target_volume = self.db.volume_get(self.context,
                                           volume_id)
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == target_volume['volume_type']['name'] \
            else StorageAccountTypes.standard_lrs
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, target_volume['id'])
        backup_name = self._get_name_from_id(
            BACKUP_PREFIX, backup['id'])
        # tmp snapshot to store original disk
        tmp_disk_name = TMP_PREFIX + '-' + disk_name
        try:
            backup_obj = self.snapshots.get(
                CONF.azure.resource_group,
                backup_name
            )
            disk_obj = self.disks.get(
                CONF.azure.resource_group,
                disk_name
            )
        except Exception as e:
            message = (_("Restoring Backup of Volume: %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupNotFound(backup_id=backup['id'])

        # 1 snapshot volume disk
        self._copy_snapshot(tmp_disk_name, disk_obj.id)

        try:
            # 2 delete original disk
            async_action = self.disks.delete(
                CONF.azure.resource_group,
                disk_name
            )
            async_action.result()
        except Exception as e:
            message = (_("Restoring Backup of Volume: %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

        try:
            # restore from backup
            self._copy_disk(disk_name, backup_obj.id, azure_type)
        except Exception as e:
            # roll back
            try:
                tmp_obj = self.snapshots.get(
                    CONF.azure.resource_group,
                    tmp_disk_name
                )
                self._copy_disk(disk_name, tmp_obj.id, azure_type)
            except Exception:
                message = (_("Restoring Backup of Volume: %(volume)s in Azure"
                             " failed, and the original volume are damaged.")
                           % dict(volume=volume_id))
                LOG.exception(message)
                raise exception.BackupDriverException(backup_id=backup['id'])
            else:
                message = (_("Restoring Backup of Volume: %(volume)s in Azure"
                             " failed, rolled back to the original volume.")
                           % dict(volume=volume_id))
                LOG.exception(message)
            message = (_("Restoring Backup of Volume: %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)
        finally:
            try:
                # delete tmp disk
                async_action = self.snapshots.delete(
                    CONF.azure.resource_group,
                    tmp_disk_name
                )
                async_action.result()
            except Exception as e:
                message = (_("Delete Tmp disk during Restore Backup of Volume:"
                             " %(volume)s in Azure failed. reason: %(reason)s")
                           % dict(volume=volume_id,
                                  reason=six.text_type(e)))
                LOG.exception(message)
                raise exception.BackupDriverException(data=message)

    def delete(self, backup):
        """Delete a saved backup in Azure."""
        disk_name = self._get_name_from_id(BACKUP_PREFIX, backup['id'])
        LOG.debug("Calling Delete Backup '{}' in Azure ..."
                  .format(disk_name))
        try:
            async_action = self.snapshots.delete(
                CONF.azure.resource_group,
                disk_name
            )
            async_action.result()
        except AzureMissingResourceHttpError:
            # refer lvm driver, if volume to delete doesn't exist, return True.
            message = (_("Backup: %s does not exist.") % disk_name)
            LOG.info(message)
        except Exception as e:
            message = (_("Delete Backup %(volume)s in Azure failed. reason: "
                         "%(reason)s") %
                       dict(volume=disk_name, reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)
        else:
            LOG.info(_LI("Delete Backup %s in Azure finish."), disk_name)
        return True


def get_backup_driver(context):
    return AzureBackupDriver(context)
