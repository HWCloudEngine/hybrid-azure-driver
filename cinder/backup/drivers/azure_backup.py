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

import six

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall

from azure.common import AzureMissingResourceHttpError
from cinder.backup import driver
from cinder import exception
from cinder.i18n import _, _LI, _LW
from cinder.volume.drivers.azure.adapter import Azure

LOG = logging.getLogger(__name__)

service_opts = [
    cfg.StrOpt('azure_volume_container_name',
               default='volumes',
               help='Azure Storage Container Name'),
    cfg.StrOpt('azure_backup_container_name',
               default='backups',
               help='Azure Storage Backup Container Name'),
    cfg.IntOpt('azure_backup_total_capacity_gb',
               help='Total Backup capacity in Azuer, in GB',
               default=500000)
]

CONF = cfg.CONF
CONF.register_opts(service_opts)
VHD_EXT = 'vhd'


class AzureBackupDriver(driver.BackupDriver):

    def __init__(self, context, db_driver=None, execute=None):
        super(AzureBackupDriver, self).__init__(context, db_driver)

        try:
            self.azure = Azure()
        except Exception as e:
            message = (_("Initialize Azure Adapter failed. reason: %s")
                       % six.text_type(e))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)
        self.blob = self.azure.blob
        try:
            self.blob.create_container(
                CONF.azure_backup_container_name)
        except Exception as e:
            message = (_("Initialize Azure Adapter failed. reason: %s")
                       % six.text_type(e))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

    def _get_blob_name(self, name):
        """Get blob name from volume name"""
        return '{}.{}'.format(name, VHD_EXT)

    def _copy_blob(self, container_name, blob_name, source_uri):
        try:
            self.blob.copy_blob(
                container_name,
                blob_name, source_uri)
        except Exception as e:
            message = (_("Copy blob %(blob_name)s from %(source_uri)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=blob_name,
                              source_uri=source_uri,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)

    def _check_exist(self, container_name, blob_name, snapshot=None):
        try:
            exists = self.blob.exists(
                container_name,
                blob_name,
                snapshot=snapshot
            )
        except Exception as e:
            message = (_("Check blob exist %(blob_name)s in Azure failed."
                         " reason: %(reason)s")
                       % dict(blob_name=blob_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            return exists

    def backup(self, backup, volume_file, backup_metadata=True):
        """Backup azure volume to azure .

        only support backup from and to azure.
        """
        volume = self.db.volume_get(self.context,
                                    backup['volume_id'])
        src_blob_name = self._get_blob_name(volume['name'])
        exists = self._check_exist(
            CONF.azure_volume_container_name,
            src_blob_name)
        if not exists:
            LOG.warning(_LW('Back an Inexistent Volume: %s in '
                            'Azure.'), src_blob_name)
            raise exception.VolumeNotFound(volume_id=volume['id'])

        blob_name = self._get_blob_name(backup['name'])
        src_blob_uri = self.blob.make_blob_url(
            CONF.azure_volume_container_name,
            src_blob_name)
        self._copy_blob(CONF.azure_backup_container_name,
                        blob_name,
                        src_blob_uri)

        def _wait_for_copy():
            """Called at an copy until finish."""
            copy = self.blob.get_blob_properties(
                CONF.azure_backup_container_name,
                blob_name)
            state = copy.properties.copy.status

            if state == 'success':
                LOG.info(_LI("Created Backup of Volume: %s in "
                             "Azure."), blob_name)
                raise loopingcall.LoopingCallDone()
            else:
                LOG.debug('Creating Backup of Volume: %(blob_name)s'
                          ' in Azure Progress %(progress)s' %
                          dict(blob_name=blob_name,
                               progress=copy.properties.copy.progress))

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
        timer.start(interval=0.5).wait()

    def restore(self, backup, volume_id, volume_file):
        """Restore volume from backup in azure.

        only support restore backup from and to azure.
        copy blob method will overwrite destination blob is existed.
        """
        target_volume = self.db.volume_get(self.context, volume_id)
        volume_name = target_volume['name']
        backup_name = backup['name']
        src_blob_name = self._get_blob_name(backup_name)
        exists = self._check_exist(
            CONF.azure_backup_container_name,
            src_blob_name)
        if not exists:
            LOG.warning(_LW('Restore an Inexistent Backup: %s in '
                            'Azure.'), src_blob_name)
            raise exception.BackupNotFound(backup_id=backup['id'])

        blob_name = self._get_blob_name(volume_name)
        src_blob_uri = self.blob.make_blob_url(
            CONF.azure_backup_container_name,
            src_blob_name)
        self._copy_blob(CONF.azure_volume_container_name,
                        blob_name,
                        src_blob_uri)

        def _wait_for_copy():
            """Called at an copy until finish."""
            copy = self.blob.get_blob_properties(
                CONF.azure_volume_container_name,
                blob_name)
            state = copy.properties.copy.status

            if state == 'success':
                LOG.info(_LI("Restored Backup of Volume: %s in "
                             "Azure."), blob_name)
                raise loopingcall.LoopingCallDone()
            else:
                LOG.debug('Restoring Backup of Volume: %(blob_name)s'
                          ' in Azure Progress %(progress)s' %
                          dict(blob_name=blob_name,
                               progress=copy.properties.copy.progress))

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
        timer.start(interval=0.5).wait()

    def delete(self, backup):
        """Delete a saved backup in Azure."""
        backup_name = backup['name']
        blob_name = self._get_blob_name(backup_name)
        LOG.debug("Calling Delete Backup '{}' in Azure ..."
                  .format(backup_name))
        try:
            self.blob.delete_blob(
                CONF.azure_backup_container_name,
                blob_name,
                delete_snapshots='include')
        except AzureMissingResourceHttpError:
            # refer lvm driver, if volume to delete doesn't exist, return True.
            message = (_("Backup blob: %s does not exist.") % backup_name)
            LOG.info(message)
            return True
        except Exception as e:
            message = (_("Delete Backup %(backup)s in Azure failed. reason: "
                         "%(reason)s") %
                       dict(backup=backup_name, reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.BackupDriverException(data=message)
        else:
            LOG.info(_LI("Delete Backup %s in Azure finish."), backup_name)


def get_backup_driver(context):
    return AzureBackupDriver(context)
