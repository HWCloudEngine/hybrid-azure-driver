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
import six

from azure.common import AzureMissingResourceHttpError
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.compute.models import StorageAccountTypes
from cinder import exception
from cinder.i18n import _, _LE, _LI, _LW
from cinder.image import image_utils
from cinder.volume import driver
from cinder.volume.drivers.azure.adapter import Azure
from cinder.volume.drivers.azure.adapter import volume_opts as ad_opts

LOG = logging.getLogger(__name__)

volume_opts = [
    cfg.IntOpt('azure_total_capacity_gb',
               help='Total capacity in Azuer, in GB',
               default=500000)
]

volume_opts.extend(ad_opts)
CONF = cfg.CONF
CONF.register_opts(volume_opts)
VHD_EXT = 'vhd'
IMAGE_PREFIX = 'image'
SNAPSHOT_PREFIX = 'snapshot'
VOLUME_PREFIX = 'volume'


class AzureDriver(driver.VolumeDriver):
    """Executes commands relating to Volumes.

    all reference about 'disk' is 'managed disk' in Azure."""
    VERSION = '0.33.0'

    def __init__(self, vg_obj=None, *args, **kwargs):
        # Parent sets db, host, _execute and base config
        super(AzureDriver, self).__init__(*args, **kwargs)

        self.configuration.append_config_values(volume_opts)

        try:
            self.azure = Azure()
            self.disks = self.azure.compute.disks
            self.snapshots = self.azure.compute.snapshots
            self.images = self.azure.compute.images
        except Exception as e:
            message = (_("Initialize Azure Adapter failed. reason: %s")
                       % six.text_type(e))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)

    def check_for_setup_error(self):
        pass

    def get_volume_stats(self, refresh=False):
        """Obtain status of the volume service.

        :param refresh: Whether to get refreshed information
        """

        if not self._stats or refresh:
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

    def _get_name_from_id(self, prefix, resource_id):
        return '{}-{}'.format(prefix, resource_id)

    def _copy_disk(self, disk_name, source_id, azure_type, size=None):
        disk_dict = {
            'location': self.configuration.location,
            'account_type': azure_type,
            'creation_data': {
                'create_option': DiskCreateOption.copy,
                'source_uri': source_id
            }
        }
        if size:
            disk_dict['disk_size_gb'] = size
        try:
            async_action = self.disks.create_or_update(
                self.configuration.resource_group,
                disk_name,
                disk_dict
            )
            async_action.result()
        except Exception as e:
            message = (_("Copy disk %(blob_name)s from %(source_id)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=disk_name, source_id=source_id,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)

    def create_volume(self, volume):
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == volume.volume_type.name \
            else StorageAccountTypes.standard_lrs
        disk_name = self._get_name_from_id(VOLUME_PREFIX, volume.id)
        disk_dict = {
            'location': self.configuration.location,
            'account_type': azure_type,
            'creation_data': {
                'create_option': DiskCreateOption.empty,
            },
            'disk_size_gb': volume.size
        }
        LOG.debug("Calling Create Disk '{}' in Azure ..."
                  .format(disk_name))
        try:
            async_action = self.disks.create_or_update(
                self.configuration.resource_group,
                disk_name,
                disk_dict
            )
            async_action.result()
        except Exception as e:
            try:
                self.disks.delete(
                    self.configuration.resource_group,
                    disk_name
                )
            except Exception:
                LOG.error(_LE('Delete Disk %s after create failure failed'),
                          volume.name)
            message = (_("Create Disk %(volume)s in Azure failed. reason: "
                         "%(reason)s") %
                       dict(volume=disk_name, reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        LOG.info(_LI('Created Disk : %s in Azure.'), disk_name)

    def delete_volume(self, volume):
        disk_name = self._get_name_from_id(VOLUME_PREFIX, volume.id)
        LOG.debug("Calling Delete Disk '{}' in Azure ..."
                  .format(disk_name))
        try:
            async_action = self.disks.delete(
                self.configuration.resource_group,
                disk_name
            )
            async_action.result()
        except AzureMissingResourceHttpError:
            # refer lvm driver, if volume to delete doesn't exist, return True.
            message = (_("Disk: %s does not exist.") % disk_name)
            LOG.info(message)
        except Exception as e:
            message = (_("Delete Disk %(volume)s in Azure failed. reason: "
                         "%(reason)s") %
                       dict(volume=disk_name, reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        LOG.info(_LI("Delete Disk %s in Azure finish."), disk_name)

    def remove_export(self, context, volume):
        pass

    def ensure_export(self, context, volume):
        pass

    def create_export(self, context, volume, connector, vg=None):
        # nothing to do in azure.
        pass

    def initialize_connection(self, volume, connector, **kwargs):
        """driver_volume_type mush be local, and device_path mush be None

        inorder to let backup process skip some useless steps
        """
        # blob_name = self._get_blob_name(volume.name)
        # vhd_uri = self.blob.make_blob_url(
        #     self.configuration.azure_storage_container_name, blob_name)
        metadata = volume.get('volume_metadata', [])
        metadata_dict = {item['key']: item['value'] for item in metadata}
        os_type = metadata_dict.get('os_type')
        connection_info = {
            'driver_volume_type': 'local',
            'data': {'volume_name': volume.name,
                     'volume_id': volume.id,
                     # 'vhd_uri': vhd_uri,
                     'vhd_size_gb': volume.size,
                     'vhd_name': volume.name,
                     'device_path': None,
                     'os_type': os_type
                     }
        }
        return connection_info

    def validate_connector(self, connector):
        pass

    def terminate_connection(self, volume, connector, **kwargs):
        pass

    def create_snapshot(self, snapshot):
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, snapshot['volume_id'])
        snapshot_name = self._get_name_from_id(
            SNAPSHOT_PREFIX, snapshot['id'])
        try:
            source_disk = self.disks.get(
                self.configuration.resource_group,
                disk_name
            )
            snapshot_dict = {
                'location': self.configuration.location,
                'creation_data': {
                    'create_option': DiskCreateOption.copy,
                    'source_uri': source_disk.id
                }
            }
            async_action = self.snapshots.create_or_update(
                self.configuration.resource_group,
                snapshot_name,
                snapshot_dict
            )
            async_action.result()
        except Exception as e:
            message = (_("Create Snapshop %(volume)s in Azure failed. reason: "
                         "%(reason)s")
                       % dict(volume=disk_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        LOG.info(_LI('Created Snapshot: %s in Azure.') % snapshot_name)
        metadata = snapshot['metadata']
        metadata['azure_snapshot_id'] = snapshot_name
        return dict(metadata=metadata)

    def delete_snapshot(self, snapshot):
        snapshot_name = self._get_name_from_id(
            SNAPSHOT_PREFIX, snapshot['id'])
        LOG.debug('Calling Delet Snapshot: %s in Azure.' % snapshot_name)
        try:
            async_action = self.snapshots.delete(
                self.configuration.resource_group,
                snapshot_name,
            )
            async_action.result()
        except AzureMissingResourceHttpError:
            # If the snapshot isn't present, then don't attempt to delete
            LOG.warning(_LW("snapshot: %s not found, "
                            "skipping delete operations"), snapshot['name'])
            LOG.info(_LI('Successfully deleted snapshot: %s'), snapshot['id'])
        except Exception as e:
            message = (_("Create Snapshop %(snapshop)s in Azure failed. "
                         "reason: %(reason)s")
                       % dict(snapshop=snapshot_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        LOG.info(_LI('Deleted Snapshot: %s in Azure.'), snapshot_name)

    def create_volume_from_snapshot(self, volume, snapshot):
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == volume.volume_type.name \
            else StorageAccountTypes.standard_lrs
        snapshot_name = self._get_name_from_id(
            SNAPSHOT_PREFIX, snapshot['id'])
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume.id)
        try:
            snapshot_obj = self.snapshots.get(
                self.configuration.resource_group,
                snapshot_name
            )
        except Exception as e:
            message = (_("Create Volume from Snapshot %(snapshop)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(snapshop=snapshot_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        else:
            self._copy_disk(disk_name, snapshot_obj.id, azure_type,
                            volume['size'])

    def create_cloned_volume(self, volume, src_vref):
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == src_vref['volume_type']['name'] \
            else StorageAccountTypes.standard_lrs
        src_vref_name = self._get_name_from_id(
            VOLUME_PREFIX, src_vref['id'])
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume.id)
        try:
            src_vref_obj = self.disks.get(
                self.configuration.resource_group,
                src_vref_name
            )
        except Exception as e:
            message = (_("Create Cloned Volume %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=src_vref_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeNotFound(volume_id=src_vref['id'])
        self._copy_disk(disk_name, src_vref_obj.id, azure_type,
                        volume['size'])

    def clone_image(self, context, volume,
                    image_location, image_meta,
                    image_service):
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == volume.volume_type.name \
            else StorageAccountTypes.standard_lrs
        # image to create volume must has os_type property.
        os_type = image_meta['properties'].get('os_type')
        if not os_type:
            message = (_("Create Volume from Image %(image_id)s in Azure"
                         " failed. reason: image miss os_type property.")
                       % dict(image_id=image_meta['id']))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        image_name = self._get_name_from_id(
            IMAGE_PREFIX, image_meta['id'])
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume.id)
        try:
            image_obj = self.disks.get(
                self.configuration.resource_group,
                image_name
            )
        except Exception as e:
            message = (_("Create Volume from Image %(image_id)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(image_id=image_meta['id'],
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        self._copy_disk(disk_name, image_obj.id, azure_type)

        metadata = volume['metadata']
        metadata['os_type'] = os_type
        LOG.info(_LI("Created Volume: %(disk_name)s from Image in Azure."),
                 dict(disk_name=disk_name))
        return dict(metadata=metadata), True

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        """Nothing need to do since we copy image to volume in clone_image."""
        pass

    def copy_volume_to_image(self, context, volume, image_service, image_meta):
        """Copy the volume to the specified image.

        copy disk to image and disk for image.
        """
        # TODO(haifeng)user delete iamge on openstack, image still in Azure.
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == volume.volume_type.name \
            else StorageAccountTypes.standard_lrs
        metadata = volume.get('volume_metadata', [])
        metadata_dict = {item['key']: item['value'] for item in metadata}
        os_type = metadata_dict.get('os_type')
        if not os_type:
            reason = 'Volume miss os_type can\'t copy to Image.'
            message = (_("Copy Volume to Image %(image_id)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(image_id=image_meta['id'],
                              reason=reason))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)

        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume['id'])
        image_name = self._get_name_from_id(
            IMAGE_PREFIX, image_meta['id'])
        try:
            disk_obj = self.disks.get(
                self.configuration.resource_group,
                disk_name
            )
        except Exception as e:
            message = (_("Create Image from Volume %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume['id'],
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        self._copy_disk(image_name, disk_obj.id, azure_type)
        try:
            image_dict = {
                'location': self.configuration.location,
                'storage_profile': {
                    'os_disk': {
                        'os_type': os_type,
                        'os_state': "Generalized",
                        'managed_disk': {
                            'id': disk_obj.id
                        }
                    }
                }
            }
            async_action = self.images.create_or_update(
                self.configuration.resource_group,
                image_name,
                image_dict
            )
            async_action.result()
        except Exception as e:
            message = (_("Copy Volume to Image %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=disk_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)

        # create a empty file to glance
        with image_utils.temporary_file() as tmp:
            image_utils.upload_volume(context,
                                      image_service,
                                      image_meta,
                                      tmp)

        image_meta['disk_format'] = 'vhd'
        image_meta['properties'] = {'os_type': os_type,
                                    'azure_image_size_gb':
                                        volume.size
                                    }
        image_service.update(context, image_meta['id'], image_meta)

    def retype(self, context, volume, new_type, diff, host):
        azure_type = StorageAccountTypes.premium_lrs \
            if 'azure_ssd' == new_type.name \
            else StorageAccountTypes.standard_lrs
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume['id'])
        try:
            disk_obj = self.disks.get(
                self.configuration.resource_group,
                disk_name
            )
        except Exception as e:
            message = (_("Retype Volume %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume['id'],
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        disk_obj.account_type = azure_type
        try:
            async_action = self.disks.create_or_update(
                self.configuration.resource_group,
                disk_name,
                disk_obj
            )
            async_action.result()
        except Exception as e:
            message = (_("Retype disk %(blob_name)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=disk_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        return True

    def extend_volume(self, volume, new_size):
        disk_name = self._get_name_from_id(
            VOLUME_PREFIX, volume['id'])
        try:
            disk_obj = self.disks.get(
                self.configuration.resource_group,
                disk_name
            )
        except Exception as e:
            message = (_("Extend Volume %(volume)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(volume=volume['id'],
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
        disk_obj.disk_size_gb = new_size
        try:
            async_action = self.disks.create_or_update(
                self.configuration.resource_group,
                disk_name,
                disk_obj
            )
            async_action.result()
        except Exception as e:
            message = (_("Extend disk %(blob_name)s in Azure"
                         " failed. reason: %(reason)s")
                       % dict(blob_name=disk_name,
                              reason=six.text_type(e)))
            LOG.exception(message)
            raise exception.VolumeBackendAPIException(data=message)
