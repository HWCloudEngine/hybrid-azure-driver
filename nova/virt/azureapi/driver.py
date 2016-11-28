import re
import time

from oslo_log import log as logging
from oslo_service import loopingcall

import nova.conf
from nova.i18n import _, _LE, _LI
from nova.virt import driver
from nova.virt.azureapi.adapter import Azure
from nova.virt.azureapi import constant
from nova.virt.azureapi import exception
from nova.compute import power_state
from nova.virt.hardware import InstanceInfo
from nova.compute import arch
from nova.compute import hv_type
from nova.compute import vm_mode
from nova.compute import task_states
from nova.volume import cinder
from nova import image

CONF = nova.conf.CONF
LOG = logging.getLogger(__name__)
VOLUME_CONTAINER = 'volumes'
SNAPSHOT_CONTAINER = 'snapshots'
VHDS_CONTAINER = 'vhds'
AZURE = 'azure'
USER_NAME = 'azureuser'
VHD_EXT = '.vhd'

# TODO need complete according to image mapping.
LINUX_OFFER = ['UbuntuServer', 'RedhatServer']
WINDOWS_OFFER = ['WindowsServerEssentials']

LINUX_OS = 'Linux'
WINDOWS_OS = 'Windows'


class AzureDriver(driver.ComputeDriver):
    capabilities = {
        "has_imagecache": False,
        "supports_recreate": True,
        "supports_migrate_to_same_host": True,
        "supports_attach_interface": False,
        "supports_device_tagging": False,
    }

    def __init__(self, virtapi):
        super(AzureDriver, self).__init__(virtapi)
        self.azure = Azure()
        self.compute = self.azure.compute
        self.network = self.azure.network
        self.storage = self.azure.storage
        self.resource = self.azure.resource
        self.blob = self.azure.blob

        self._volume_api = cinder.API()
        self._image_api = image.API()

        self.cleanup_time = time.time()
        self.zombie_nics = []

    def _get_blob_name(self, name):
        """Get blob name from volume name
        """
        return '{}{}'.format(name, VHD_EXT)

    def _precreate_network(self):
        """Pre Create Network info in Azure.
        """
        # Creaet Network
        # Create Subnet
        net_info = self.network.virtual_networks.get(
            CONF.azure.resource_group,
            CONF.azure.vnet_name)
        if not net_info:
            async_vnet_creation = self.network.virtual_networks.create_or_update(
                CONF.azure.resource_group,
                CONF.azure.vnet_name,
                {
                    'location': CONF.azure.location,
                    'address_space': {
                        'address_prefixes': ['10.0.0.0/16']
                    }
                }
            )
            async_vnet_creation.wait()
            LOG.info("Create Network")

        # Create Subnet
        subnet_info = self.network.subnets.get(
            CONF.azure.resource_group,
            CONF.azure.vnet_name,
            CONF.azure.vsubnet_name,)
        if not subnet_info:
            # subnet can't recreate, check existing before create.
            async_subnet_creation = self.network.subnets.create_or_update(
                CONF.azure.resource_group,
                CONF.azure.vnet_name,
                CONF.azure.vsubnet_name,
                {'address_prefix': '10.0.0.0/16'}
            )
            subnet_info = async_subnet_creation.result()
        CONF.set_override('vsubnet_id', subnet_info.id, 'azure')
        LOG.info("Create/Update Subnet:{}".format(CONF.azure.vsubnet_id))

    def init_host(self, host):
        self.resource.providers.register('Microsoft.Network')
        LOG.info("Register Microsoft.Network")
        self.resource.providers.register('Microsoft.Compute')
        LOG.info("Register Microsoft.Compute")
        self.resource.providers.register('Microsoft.Storage')
        LOG.info("Register Microsoft.Storage")

        self.resource.resource_groups.create_or_update(
            CONF.azure.resource_group, {'location': CONF.azure.location})
        LOG.info("Create/Update Resource Group")
        storage_async_operation = self.storage.storage_accounts.create(
            CONF.azure.resource_group,
            CONF.azure.storage_account,
            {
                'sku': {'name': 'standard_lrs'},
                'kind': 'storage',
                'location': CONF.azure.location
            }
        )
        storage_async_operation.wait()
        LOG.info("Create/Update Storage Account")

        self.blob.create_container(SNAPSHOT_CONTAINER)
        LOG.info("Create/Update Storage Container: {}".
                  format(SNAPSHOT_CONTAINER))

        self._precreate_network()
        LOG.info("Create/Update Ntwork and Subnet, Done.")

    def get_host_ip_addr(self):
        return CONF.my_ip

    def get_available_nodes(self, refresh=False):
        return 'azure-{}'.format(CONF.azure.location)

    def list_instances(self):
        """Return the names of all the instances known to the virtualization
        layer, as a list.
        """
        instances = []
        pages = self.compute.virtual_machines.list(CONF.azure.resource_group)
        for i in pages:
            instances.append(i.name)
        return instances

    def list_instance_uuids(self):
        """Return the UUIDS of all the instances known to the virtualization
        layer, as a list. azure vm.name is vm.uuid in openstack.
        """
        return self.list_instances()

    def get_info(self, instance):
        """Get the current status of an instance
        state for azure:running, deallocating, deallocated,
        stopping , stopped
        """
        shutdown_staues = ['deallocating', 'deallocated',
                           'stopping', 'stopped']
        instance_id = instance.uuid
        state = power_state.NOSTATE
        status = 'Unkown'
        try:
            vm = self.compute.virtual_machines.get(
                CONF.azure.resource_group, instance_id, expand='instanceView')
        except exception.CloudError:
            LOG.warn('Get instance info from Azure failed.{}'
                     .format(exception.CloudError),instance=instance)
        else:
            LOG.debug('vm info is: {}'.format(vm))
            if vm and vm.instance_view and vm.instance_view.statuses:
                for i in vm.instance_view.statuses:
                    if 'PowerState' in i.code:
                        status = i.code.split('/')[1]
                        if 'running' == status:
                            state = power_state.RUNNING
                        elif status in shutdown_staues:
                            state = power_state.SHUTDOWN
                        break
            LOG.info('vm: {} state is : {}'.format(instance_id, status))
        return InstanceInfo(state=state, id=instance_id)

    def get_available_resource(self, nodename):
        # delete zombied os disk blob
        curent_time = time.time()
        if curent_time - self.cleanup_time > CONF.azure.cleanup_span:
            self.cleanup_time = curent_time
            self._cleanup_deleted_os_disks()
            self._cleanup_deleted_nics()
        usage_family = 'basicAFamily'
        page = self.compute.usage.list(CONF.azure.location)
        usages = [i for i in page]
        cores = 0
        cores_by_family = 0
        cores_used = 0
        cores_used_by_family = 0
        for i in usages:
            if i.name and i.name.value:
                if 'cores' == i.name.value:
                    cores = i.limit if i.limit else 0
                    cores_used = i.current_value if i.current_value else 0
                    break
                if usage_family == i.name.value:
                    cores_by_family = i.limit
                    cores_used_by_family = i.current_value \
                        if i.current_value else 0
        cores = min(cores, cores_by_family)
        cores_used = min(cores_used, cores_by_family)
        return {'vcpus': cores,
                'memory_mb': 100000000,
                'local_gb': 100000000,
                'vcpus_used': cores_used,
                'memory_mb_used': 0,
                'local_gb_used': 0,
                'hypervisor_type': hv_type.HYPERV,
                'hypervisor_version': 0300,
                'hypervisor_hostname': nodename,
                'cpu_info': '{"model": ["Intel(R) Xeon(R) CPU E5-2670 0 @ '
                            '2.60GHz"], "topology": {"cores": 16, "threads": '
                            '32}}',
                'supported_instances': [(arch.I686, hv_type.HYPERV,
                                         vm_mode.HVM),
                    (arch.X86_64, hv_type.HYPERV, vm_mode.HVM)],
                'numa_topology': None
                }

    def _prepare_network_profile(self, instance_uuid):
        """Create a Network Interface for a VM.
        """
        async_nic_creation = self.network.network_interfaces.create_or_update(
            CONF.azure.resource_group,
            instance_uuid,
            {
                'location': CONF.azure.location,
                'ip_configurations': [{
                    'name': instance_uuid,
                    'subnet': {
                        'id': CONF.azure.vsubnet_id
                    }
                }]
            }
        )
        nic = async_nic_creation.result()
        LOG.info("Create a Nic:{}".format(nic.id))
        network_profile = {
                'network_interfaces': [{
                    'id': nic.id,
                }]
            }
        return network_profile

    def _get_image_from_mapping(self, image_meta):
        image_name = image_meta.name
        image_ref = constant.IMAGE_MAPPING.get(image_name, None)
        if not image_ref:
            raise exception.ImageAzureMappingNotFound(image_name=image_name)
        LOG.debug("Get image mapping:{}".format(image_ref))
        return image_ref

    def _get_size_from_flavor(self, flavor):
        flavor_name = flavor.get('name')
        vm_size = constant.FLAVOR_MAPPING.get(flavor_name, None)
        if not vm_size:
            raise exception.FlavorAzureMappingNotFound(
                flavor_name=flavor_name)
        LOG.debug("Get size mapping:{}".format(vm_size))
        return vm_size

    def _prepare_os_profile(self, instance, storage_profile, admin_password):
        if 'image_reference' not in storage_profile:
            return None
        os_profile = dict(computer_name=instance.hostname,
                          admin_username=USER_NAME)
        image_offer = storage_profile['image_reference']['offer']
        if image_offer in LINUX_OFFER:
            os_type = LINUX_OS
        elif image_offer in WINDOWS_OFFER:
            os_type = WINDOWS_OS
        else:
            raise Exception('Unabled to decide os type of instance.')

        if os_type == LINUX_OS:
            if instance.get('key_data'):
                key_data = str(instance.key_data)
                os_profile['linux_configuration'] = {
                    'ssh': {
                        'public_keys': [
                            {
                                'path': '/home/' + USER_NAME +
                                        '/.ssh/authorized_keys',
                                'key_data': key_data
                            }
                        ]
                    }
                }
            else:
                os_profile['admin_password'] = admin_password
        else:
            os_profile['admin_password'] = admin_password
        instance.os_type = os_type
        instance.save()
        return os_profile

    def _create_vm_parameters(self, storage_profile, vm_size,
                              network_profile, os_profile):
        """Create the VM parameters structure.
        """
        vm_parameters = {
            'location': CONF.azure.location,
            'os_profile': os_profile,
            'hardware_profile': {
                'vm_size': vm_size
            },
            'storage_profile': storage_profile,
            'network_profile': network_profile,
        }

        # if boot from user create azure image, os_profile is not needed,
        # and all user data are the same as image's orignal vm.
        if not os_profile:
            del vm_parameters['os_profile']
        LOG.debug("Create vm parameters:{}".format(vm_parameters))
        return vm_parameters

    def _prepare_storage_profile(self, context, image_meta, instance):
        image = self._image_api.get(context, image_meta.id)
        image_properties = image.get('properties', None)

        # boot from azure export images.
        if image_properties and 'azure_type' in image_properties:
            if image_properties['azure_type'] == AZURE \
                    and 'azure_uri' in image_properties \
                    and 'azure_os_type' in image_properties:
                disk_name = self._get_blob_name(instance.uuid)
                uri = image['properties']['azure_uri']

                # copy image diskt to new disk for instance.
                self.blob.copy_blob(VHDS_CONTAINER, disk_name, uri)

                def _wait_for_copy():
                    """Called at an copy until finish."""
                    copy = self.blob.get_blob_properties(
                        VHDS_CONTAINER, disk_name)
                    state = copy.properties.copy.status
                    if state == 'success':
                        LOG.info(_LI("Copied image disk to new blob:{} in"
                                     " Azure.".format(disk_name)))
                        raise loopingcall.LoopingCallDone()
                    else:
                        LOG.info(
                            'copy os disk: {} in Azure Progress '
                            '{}'.format(disk_name,
                                        copy.properties.copy.progress))

                timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
                timer.start(interval=0.5).wait()

                disk_uri = self.blob.make_blob_url(VHDS_CONTAINER, disk_name)
                storage_profile = {
                    'os_disk': {
                        'name': instance.uuid,
                        'caching': 'None',
                        'create_option': 'attach',
                        'vhd': {'uri': disk_uri},
                        'os_type': image_properties['azure_os_type']
                    }
                }
            else:
                raise Exception('Wrong parameters os Azure crated image!')

        # boot from normal openstack images.
        else:
            image_reference = self._get_image_from_mapping(image_meta) or None
            uri = self.blob.make_blob_url(
                VHDS_CONTAINER, self._get_blob_name(instance.uuid))
            storage_profile = {
                'image_reference': image_reference,
                'os_disk': {
                    'name': instance.uuid,
                    'caching': 'None',
                    'create_option': 'fromImage',
                    'vhd': {'uri': uri}
                }
            }

        return storage_profile

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        if not self._check_password(admin_password):
            raise exception.PasswordInvalid(
                instance_uuid=instance.uuid)
        instance_uuid = instance.uuid
        storage_profile = self._prepare_storage_profile(
            context, image_meta, instance)
        vm_size = self._get_size_from_flavor(instance.get_flavor()) or None
        network_profile = self._prepare_network_profile(instance_uuid)
        os_profile = self._prepare_os_profile(
            instance, storage_profile, admin_password)
        vm_parameters = self._create_vm_parameters(
            storage_profile, vm_size, network_profile, os_profile)

        async_vm_action = self.compute.virtual_machines.create_or_update(
            CONF.azure.resource_group, instance_uuid, vm_parameters)
        LOG.debug("Calling Create Instance in Azure ...", instance=instance)
        async_vm_action.wait()
        LOG.info("Create Instance in Azure Finish.", instance=instance)

    def _cleanup_instance(self, instance):
        # 1 clean os disk vhd
        os_blob_name = self._get_blob_name(instance.uuid)
        try:
            self.blob.delete_blob(VHDS_CONTAINER, os_blob_name)
            LOG.info("Delete instance's Volume", instance=instance)
        except exception.AzureMissingResourceHttpError:
            LOG.info('os blob: {} does not exist.')
        # 1 clean network interface
        async_vm_action = self.network.network_interfaces.delete(
            CONF.azure.resource_group, instance.uuid
        )
        async_vm_action.wait()
        LOG.info("Delete instance's Interface", instance=instance)

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        LOG.debug("Calling Delete Instance in Azure ...", instance=instance)
        async_vm_action = self.compute.virtual_machines.delete(
            CONF.azure.resource_group, instance.uuid)
        async_vm_action.wait()
        LOG.info("Delete Instance in Azure Finish.", instance=instance)
        self._cleanup_instance(instance)
        LOG.info("Delete and Clean Up Instance in Azure Finish.",
                 instance=instance)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        async_vm_action = self.compute.virtual_machines.restart(
            CONF.azure.resource_group, instance.uuid)
        async_vm_action.wait()
        LOG.info("Restart Instance in Azure Finish.", instance=instance)

    def power_off(self, instance, timeout=0, retry_interval=0):
        async_vm_action = self.compute.virtual_machines.power_off(
            CONF.azure.resource_group, instance.uuid)
        async_vm_action.wait()
        LOG.info("Power off Instance in Azure Finish.", instance=instance)

    def power_on(self, context, instance, network_info,
                 block_device_info=None):
        async_vm_action = self.compute.virtual_machines.start(
            CONF.azure.resource_group, instance.uuid)
        async_vm_action.wait()
        LOG.info("Power On Instance in Azure Finish.", instance=instance)

    def rebuild(self, context, instance, image_meta, injected_files,
                admin_password, bdms, detach_block_devices,
                attach_block_devices, network_info=None,
                recreate=False, block_device_info=None,
                preserve_ephemeral=False):
        async_vm_action = self.compute.virtual_machines.redeploy(
            CONF.azure.resource_group, instance.uuid)
        LOG.debug("Calling Rebuild Instance in Azure ...", instance=instance)
        async_vm_action.wait()
        LOG.info("Rebuild Instance in Azure Finish.", instance=instance)
        instance.task_state = task_states.REBUILD_SPAWNING
        instance.save()

    def finish_migration(self, context, migration, instance, disk_info,
                         network_info, image_meta, resize_instance,
                         block_device_info=None, power_on=True):
        # nothing need to do.
        pass

    def _get_new_size(self, instance, flavor):
        sizes = self.compute.virtual_machines.list_available_sizes(
            CONF.azure.resource_group, instance.uuid)
        vm_size = self._get_size_from_flavor(flavor) or None
        for i in sizes:
            if vm_size == i.name:
                LOG.debug('Resize Instance, get new size', instance=instance)
                return i.name
        LOG.warn('Resize Instance, size invalid in Azure', instance=instance)
        raise exception.FlavorInvalid(
            flavor_name=instance.get_flavor(),
            instance_uuid = instance.uuid)

    def migrate_disk_and_power_off(self, context, instance, dest,
                                   flavor, network_info,
                                   block_device_info=None,
                                   timeout=0, retry_interval=0):
        size_obj = self._get_new_size(instance, flavor)
        vm = self.compute.virtual_machines.get(
            CONF.azure.resource_group, instance.uuid)
        vm.hardware_profile.vm_size = size_obj
        async_vm_action = self.compute.virtual_machines.create_or_update(
            CONF.azure.resource_group, instance.uuid, vm)
        LOG.debug("Calling Resize Instance in Azure ...", instance=instance)
        async_vm_action.wait()
        LOG.info("Resize Instance in Azure finish", instance=instance)
        return True

    def get_volume_connector(self, instance):
        # nothing need to do with volume
        props = {}
        props['platform'] = 'azure'
        props['os_type'] = 'azure'
        props['ip'] = CONF.my_ip
        props['host'] = CONF.host
        return props

    def confirm_migration(self, migration, instance, network_info):
        # nothing need to do with volume
        pass

    def set_admin_password(self, instance, new_pass):
        # extension = self.compute.virtual_machine_extensions.get(
        #     CONF.azure.resource_group, instance.uuid, 'enablevmaccess')

        if not self._check_password(new_pass):
            LOG.exception(_LE('set_admin_password failed: password does not'
                              ' meet reqirements.'),
                          instance=instance)
            raise Exception
        vm = self.compute.virtual_machines.get(
            CONF.azure.resource_group, instance.uuid)
        vm.os_profile.admin_password = new_pass
        async_vm_action = self.compute.virtual_machines.create_or_update(
            CONF.azure.resource_group, instance.uuid, vm)
        LOG.debug("Calling Reset Password of Instance in Azure ...",
                  instance=instance)
        async_vm_action.wait()
        LOG.info("Reset Password of Instance in Azure finish",
                  instance=instance)

    def _check_password(self, password):
        """Check password according to azure's specification.

        :param password: password to set for a instance.
        :return: True or False, True for passed, False for failed.
        """
        rule = re.compile("(?=^.{8,72}$)((?=.*\d)(?=.*[A-Z])(?=.*[a-z])|"
                          "(?=.*\d)(?=.*[^A-Za-z0-9])(?=.*[a-z])|(?=.*[^A"
                          "-Za-z0-9])(?=.*[A-Z])(?=.*[a-z])|(?=.*\d)(?=.*"
                          "[A-Z])(?=.*[^A-Za-z0-9]))^.*")
        if not rule.match(password):
            return False

        disallow = ["abc@123", "P@$$w0rd", "P@ssw0rd", "P@ssword123",
                    "Pa$$word", "pass@word1", "Password!", "Password1",
                    "Password22", "iloveyou!"]
        return not password in disallow

    def attach_volume(self, context, connection_info, instance, mountpoint,
                      disk_bus=None, device_type=None, encryption=None):
        data = connection_info['data']
        vm = self.compute.virtual_machines.get(
            CONF.azure.resource_group, instance.uuid)
        data_disks = vm.storage_profile.data_disks
        luns = [i.lun for i in data_disks]
        new_lun = 0
        for i in range(100):
            if i not in luns:
                new_lun = i
                break
        data_disk = dict(lun=new_lun,
                         name=data['vhd_name'],
                         vhd=dict(uri=data['vhd_uri']),
                         create_option='attach',
                         disk_size_gb = data['vhd_size_gb'])
        data_disks.append(data_disk)
        async_vm_action = self.compute.virtual_machines.create_or_update(
            CONF.azure.resource_group, instance.uuid, vm)
        LOG.debug("Calling Attach Volume to  Instance in Azure ...",
                  instance=instance)
        async_vm_action.wait()
        LOG.info("Attach Volume to Instance in Azure finish",
                  instance=instance)

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        vhd_name = connection_info['data']['vhd_name']
        vm = self.compute.virtual_machines.get(
            CONF.azure.resource_group, instance.uuid)
        data_disks = vm.storage_profile.data_disks
        not_found = True
        for i in range(len(data_disks)):
            if vhd_name == data_disks[i].name:
                del data_disks[i]
                not_found = False
                break
        if not_found:
            LOG.warn('Volume: %s was not attached to Instance!' % vhd_name,
                     instance=instance)
            return
        async_vm_action = self.compute.virtual_machines.create_or_update(
            CONF.azure.resource_group, instance.uuid, vm)
        LOG.debug("Calling Detach Volume to  Instance in Azure ...",
                  instance=instance)
        async_vm_action.wait()
        LOG.info("Detach Volume to Instance in Azure finish",
                  instance=instance)

    def snapshot(self, context, instance, image_id, update_task_state):
        # TODO when delete snapshot in glance, snapshot blob still in azure,
        # need add deleting zombied snapshot to periodic task.
        self._cleanup_deleted_snapshots(context)

        update_task_state(task_state=task_states.IMAGE_PENDING_UPLOAD)
        snapshot = self._image_api.get(context, image_id)
        snapshot_name = self._get_snapshot_blob_name_from_id(snapshot['id'])
        snapshot_url = self.blob.make_blob_url(SNAPSHOT_CONTAINER,
                                               snapshot_name)
        vm_osdisk_url = self.blob.make_blob_url(
            VHDS_CONTAINER, self._get_blob_name(instance.uuid))
        metadata = {'is_public': False,
                    'status': 'active',
                    'name': snapshot_name,
                    'disk_format': 'vhd',
                    'container_format': 'bare',
                    'properties': {'azure_type': AZURE,
                                   'azure_uri': snapshot_url,
                                   'azure_os_type': instance.os_type,
                                   'kernel_id': instance.kernel_id,
                                   'image_location': 'snapshot',
                                   'image_state': 'available',
                                   'owner_id': instance.project_id,
                                   'ramdisk_id': instance.ramdisk_id,
                                   }
                    }
        self._image_api.update(context, image_id, metadata, 'Azure image')
        LOG.info("Update image for snapshot image.", instance=instance)

        self.blob.copy_blob(SNAPSHOT_CONTAINER, snapshot_name, vm_osdisk_url)
        LOG.info("Calling copy os disk in Azure...",
                  insget_available_nodestance=instance)
        update_task_state(task_state=task_states.IMAGE_UPLOADING,
                          expected_state=task_states.IMAGE_PENDING_UPLOAD)
        def _wait_for_copy():
            """Called at an copy until finish."""
            copy = self.blob.get_blob_properties(SNAPSHOT_CONTAINER,
                                                 snapshot_name)
            state = copy.properties.copy.status

            if state == 'success':
                LOG.info(_LI("Copied osdisk to new blob:{} for instance:{} in"
                             " Azure.".format(snapshot_name, instance.uuid)))
                raise loopingcall.LoopingCallDone()
            else:
                LOG.debug(
                    'copy os disk: {} in Azure Progress '
                    '{}'.format(snapshot_name, copy.properties.copy.progress))

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_copy)
        timer.start(interval=0.5).wait()

        LOG.info('Created Image from Instance: {} in Azure'
                  '.'.format(instance.uuid))

    def resume_state_on_host_boot(self, context, instance, network_info,
                                  block_device_info=None):
        pass

    def delete_instance_files(self, instance):
        self._cleanup_instance(instance)
        return True

    def _get_snapshot_blob_name_from_id(self, id):
        return 'snapshot-{}.{}'.format(id, VHD_EXT)

    def _cleanup_deleted_snapshots(self, context):
        images = self._image_api.get_all(context)
        image_ids = [self._get_snapshot_blob_name_from_id(i['id'])
                     for i in images]
        snapshot_blobs = self.blob.list_blobs(SNAPSHOT_CONTAINER)
        blob_ids = [i.name for i in snapshot_blobs]
        zombied_ids = set(blob_ids) - set(image_ids)
        for i in zombied_ids:
            self.blob.delete_blob(SNAPSHOT_CONTAINER, i)
            LOG.info('Delete zombie snapshot: {} blob in Azure'.format(i))

    def _cleanup_deleted_nics(self):
        nics = self.network.network_interfaces.list(CONF.azure.resource_group)
        zombie_ids = [i.name for i in nics if not i.virtual_machine]
        to_delete_ids = set(self.zombie_nics) & set(zombie_ids)
        self.zombie_nics = set(zombie_ids) - set(to_delete_ids)
        for i in to_delete_ids:
            self.network.network_interfaces.delete(
                CONF.azure.resource_group, i
            )
            LOG.info('Delete zombie Nic: {} in Azure'.format(i))

    def _cleanup_deleted_os_disks(self):
        blobs = self.blob.list_blobs(VHDS_CONTAINER)
        for i in blobs:
            if 'unlocked' == i.properties.lease.status \
                    and 'available' == i.properties.lease.state \
                    and VHD_EXT in i.name:
                try:
                    self.blob.delete_blob(VHDS_CONTAINER, i.name)
                    LOG.info('Delete zombie os disk: {} blob in Azure'
                             .format(i.name))
                except exception.AzureMissingResourceHttpError:
                    LOG.info('os blob: {} does not exist.')
