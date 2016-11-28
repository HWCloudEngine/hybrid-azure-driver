#
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import units

from azure.common import AzureMissingResourceHttpError
from cinder import exception
from cinder.i18n import _, _LE, _LI, _LW
from cinder import interface
from cinder.volume import driver
from cinder.volume.drivers.azure.adapter import Azure
from cinder.volume.drivers.azure import vhd_utils as azutils


LOG = logging.getLogger(__name__)

volume_opts = [
    cfg.StrOpt('azure_storage_account',
               default='ops0storage0account',
               help="""Azure Storage Account Name, should be unique in Azure,
Storage account name must be between 3 and 24 characters in length
and use numbers and lower-case letters only."""),
    cfg.StrOpt('azure_storage_account_key',
               help='Azure Storage Account Key'),
    cfg.StrOpt('azure_storage_container_name',
               default='volumes',
               help='Azure Storage Container Name'),
    cfg.IntOpt('azure_total_capacity_gb',
               help='Total capacity in Azuer, in GB',
               default=500000)
]

CONF = cfg.CONF
CONF.register_opts(volume_opts)
VHD_EXT = '.vhd'


@interface.volumedriver
class AzureDriver(driver.VolumeDriver):
    """Executes commands relating to Volumes."""

    VERSION = '0.33.0'

    def __init__(self, vg_obj=None, *args, **kwargs):
        # Parent sets db, host, _execute and base config
        super(AzureDriver, self).__init__(*args, **kwargs)

        self.configuration.append_config_values(volume_opts)

        self.azure = Azure()
        self.blob = self.azure.blob
        self.blob.create_container(
            self.configuration.azure_storage_container_name)

    def check_for_setup_error(self):
        pass

    def get_volume_stats(self, refresh=False):
        """Obtain status of the volume service.

        :param refresh: Whether to get refreshed information
        """

        if not self._stats:
            backend_name = self.configuration.safe_get('volume_backend_name')
            if not backend_name:
                backend_name = self.__class__.__name__
            # TODO(haifeng) free capacity need to refresh
            data = {'volume_backend_name': backend_name,
                    'vendor_name': 'Azure',
                    'driver_version': self.VERSION,
                    'storage_protocol': 'vhd',
                    'reserved_percentage': 0,
                    'total_capacity_gb':
                        self.configuration.azure_total_capacity_gb,
                    'free_capacity_gb':
                        self.configuration.azure_total_capacity_gb}
            self._stats = data
        return self._stats

    def _get_blob_name(self, name):
        """Get blob name from volume name"""
        return '{}{}'.format(name, VHD_EXT)

    def _copy_blob(self, blob_name, source_uri):
        try:
            self.blob.copy_blob(
                self.configuration.azure_storage_container_name,
                blob_name, source_uri)
        except Exception:
            message = (_("Copy blob %(blob_name)s from %(source_uri)s in Azure"
                         " failed.")
                       % dict(blob_name=blob_name, source_uri=source_uri))
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)

    def _check_exist(self, blob_name, snapshot=None):
        try:
            exists = self.blob.exists(
                self.configuration.azure_storage_container_name,
                blob_name,
                snapshot=snapshot
            )
        except Exception:
            message = (_("Check blob exist %s in Azure failed.")
                       % blob_name)
            if snapshot:
                message = (_("Check snapshot %(snapshot)s exist for blob"
                             " %(blob_name)s in Azure failed.")
                           % dict(snapshot=snapshot, blob_name=blob_name))
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            return exists

    def create_volume(self, volume):
        size = volume.size * units.Gi
        blob_size = size + 512
        blob_name = self._get_blob_name(volume.name)
        LOG.debug("Calling Create Volume '{}' in Azure ..."
                  .format(volume.name))
        vhd_footer = azutils.generate_vhd_footer(size)
        try:
            self.blob.create_blob(
                self.configuration.azure_storage_container_name,
                blob_name, blob_size)
            self.blob.update_page(
                self.configuration.azure_storage_container_name,
                blob_name, vhd_footer,
                start_range=size, end_range=blob_size - 1)
        except Exception:
            try:
                self.blob.delete_blob(
                    self.configuration.azure_storage_container_name,
                    blob_name)
            except Exception:
                LOG.error(_LE('Delete blob %s after create failure failed'),
                          blob_name)
            message = (_("Create Volume %s in Azure failed.") % volume.name)
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            LOG.info(_LI('Created Volume : %s in Azure.'), volume.name)

    def delete_volume(self, volume):
        blob_name = self._get_blob_name(volume.name)
        LOG.debug("Calling Delete Volume '{}' in Azure ..."
                  .format(volume.name))
        try:
            self.blob.delete_blob(
                self.configuration.azure_storage_container_name,
                blob_name, delete_snapshots='include')
        except AzureMissingResourceHttpError:
            message = (_("Volume blob: %s does not exist.") % volume.name)
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        except Exception:
            message = (_("Delete Volume %s in Azure failed.") % volume.name)
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            LOG.info(_LI("Delete Volume %s in Azure finish."), volume.name)

    def remove_export(self, context, volume):
        pass

    def ensure_export(self, context, volume):
        pass

    def create_export(self, context, volume, connector, vg=None):
        # nothing to do in azure.
        pass

    def initialize_connection(self, volume, connector, **kwargs):
        blob_name = self._get_blob_name(volume.name)
        vhd_uri = self.blob.make_blob_url(
            self.configuration.azure_storage_container_name, blob_name)
        connection_info = {
            'driver_volume_type': 'vhd',
            'data': {'volume_name': volume.name,
                     'volume_id': volume.id,
                     'vhd_uri': vhd_uri,
                     'vhd_size_gb': volume.size,
                     'vhd_name': volume.name
                     }
        }
        return connection_info

    def validate_connector(self, connector):
        pass

    def terminate_connection(self, volume, connector, **kwargs):
        pass

    def create_snapshot(self, snapshot):
        try:
            snapshot_blob = self.blob.snapshot_blob(
                self.configuration.azure_storage_container_name,
                self._get_blob_name(snapshot['volume_name'])
            )
        except Exception:
            message = (_("Create Snapshop %s in Azure failed.")
                       % snapshot['volume_name'])
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        azure_snapshot_id = snapshot_blob.snapshot
        LOG.info('Created Snapshot: {} in Azure.'.format(azure_snapshot_id))
        metadata = snapshot['metadata']
        metadata['azure_snapshot_id'] = azure_snapshot_id
        return dict(metadata=metadata)

    def delete_snapshot(self, snapshot):
        azure_snapshot_id = snapshot['metadata']['azure_snapshot_id']
        LOG.debug('Calling Delet Snapshot: %s in Azure.' % azure_snapshot_id)
        try:
            self.blob.delete_blob(
                self.configuration.azure_storage_container_name,
                self._get_blob_name(snapshot['volume_name']),
                snapshot=azure_snapshot_id
            )
        except AzureMissingResourceHttpError:
            message = (_("Snapshot blob: %s does not exist.")
                       % azure_snapshot_id)
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        except Exception:
            message = (_("Create Snapshop %s in Azure failed.")
                       % azure_snapshot_id)
            LOG.error(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            LOG.info(_LI('Deleted Snapshot: %s in Azure.'), azure_snapshot_id)

    def create_volume_from_snapshot(self, volume, snapshot):
        blob_name = self._get_blob_name(volume.name)
        azure_snapshot_id = snapshot['metadata']['azure_snapshot_id']
        old_blob_uri = self.blob.make_blob_url(
            self.configuration.azure_storage_container_name,
            self._get_blob_name(snapshot['volume_name']))
        snapshot_uri = '{}?snapshot={}'.format(old_blob_uri,
                                               azure_snapshot_id)
        exists = self._check_exist(
            self._get_blob_name(snapshot['volume_name']),
            snapshot=azure_snapshot_id)
        if not exists:
            LOG.warning(_LW('Copy an Inexistent Snapshot: %s in '
                            'Azure.'), azure_snapshot_id)
            raise exception.SnapshotNotFound(snapshot_id=snapshot['id'])
        self._copy_blob(blob_name, snapshot_uri)

        def _wait_for_copy():
            """Called at an copy until finish."""
            copy = self.blob.get_blob_properties(
                self.configuration.azure_storage_container_name,
                blob_name)
            state = copy.properties.copy.status

            if state == 'success':
                LOG.info(_LI("Created Volume from Snapshot: %s in "
                             "Azure."), azure_snapshot_id)
                raise loopingcall.LoopingCallDone()
            else:
                LOG.debug(_(
                    'Create Volume from Snapshot: %(azure_snapshot_id)s in'
                    ' Azure Progress %(progress)s'),
                    dict(azure_snapshot_id=azure_snapshot_id,
                         progress=copy.properties.copy.progress))

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
        timer.start(interval=0.5).wait()

        if volume['size'] != snapshot['volume_size']:
            LOG.warn(_LW("Created Volume from Snapshot: %(blob_name)s in Azure"
                         " can't be resized, use Snapshot size %(volume_size)s"
                         " GB for new Volume."),
                     dict(blob_name=blob_name,
                          volume_size=snapshot['volume_size']))
            volume.update(dict(size=snapshot['volume_size']))
            volume.save()

    def create_cloned_volume(self, volume, src_vref):
        src_blob_name = self._get_blob_name(src_vref['name'])
        exists = self._check_exist(src_blob_name)
        if not exists:
            LOG.warning(_LW('Copy an Inexistent Volume: %s in '
                            'Azure.'), src_blob_name)
            raise exception.VolumeNotFound(volume_id=src_vref['id'])

        blob_name = self._get_blob_name(volume.name)
        src_blob_uri = self.blob.make_blob_url(
            self.configuration.azure_storage_container_name, src_blob_name)
        self._copy_blob(blob_name, src_blob_uri)

        def _wait_for_copy():
            """Called at an copy until finish."""
            copy = self.blob.get_blob_properties(
                self.configuration.azure_storage_container_name,
                blob_name)
            state = copy.properties.copy.status

            if state == 'success':
                LOG.info(_LI("Created Cloned Volume: %s in "
                             "Azure."), blob_name)
                raise loopingcall.LoopingCallDone()
            else:
                LOG.debug(_(
                    'Create Cloned Volume: %(blob_name)s in'
                    ' Azure Progress %(progress)s'),
                    dict(blob_name=blob_name,
                         progress=copy.properties.copy.progress))

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
        timer.start(interval=0.5).wait()
        if volume['size'] != src_vref['size']:
            LOG.warn(_LW("Created Cloned Volume: %(blob_name)s in Azure"
                         " can't be resized, use Source  size %(volume_size)s"
                         " GB for new Volume."),
                     dict(blob_name=blob_name,
                          volume_size=src_vref['size']))
            volume.update(dict(size=src_vref['size']))
            volume.save()
