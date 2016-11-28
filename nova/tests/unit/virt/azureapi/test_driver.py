import mock

from azure.mgmt.compute import models as azcpumodels
from azure.storage.blob import models as azsmodels
from nova import conf
from nova import context
from nova import exception as nova_ex
from nova import objects
from nova import test
from nova.virt.azureapi import driver
from nova.virt.azureapi.driver import AzureDriver
from nova.virt.azureapi.driver import power_state
from nova.virt.azureapi.driver import time
from nova.virt.azureapi import exception
from nova.virt import fake
from nova.tests import uuidsentinel as uuids
from nova.tests.unit import fake_instance
import nova.tests.unit.image.fake

CONF = conf.CONF
LOCATION = 'westus'
FakeVirtualMachine = azcpumodels.VirtualMachine(LOCATION)
FakeAction = mock.Mock()
FakeAction.wait.return_value = None


class FakeObj(object):
    pass


class FakeLoopingCall(object):
    def start(self, *a, **k):
        return self

    def wait(self):
        return None


class AzureDriverTestCase(test.NoDBTestCase):

    @mock.patch('nova.virt.azureapi.driver.Azure')
    @mock.patch(
        'nova.virt.azureapi.driver.loopingcall.FixedIntervalLoopingCall')
    def setUp(self, mock_loop, mock_azure):
        super(AzureDriverTestCase, self).setUp()
        self.mock_azure = mock_azure
        self.mock_loop_call = mock_loop

        self.flags(group='azure', username='username',
                   password='username', subscription_id='subscription_id',
                   storage_account='storage_account', location='location',
                   resource_group='resource_group', vnet_name='vnet_name',
                   vsubnet_id='vsubnet_id', vsubnet_name='vsubnet_name',
                   cleanup_span=60)

        self.drvr = AzureDriver(fake.FakeVirtAPI())
        self.drvr._image_api = mock.Mock()
        self.drvr._volume_api = mock.Mock()
        self.context = context.get_admin_context()
        self.image_api = \
            nova.tests.unit.image.fake.stub_out_image_service(self)
        self.fake_instance = self._create_instance()

    def tearDown(self):
        super(AzureDriverTestCase, self).tearDown()
        nova.tests.unit.image.fake.FakeImageService_reset()

    def test_init_raise(self):
        self.mock_azure.side_effect = Exception()
        self.assertRaises(Exception, self.drvr.__init__,
                          fake.FakeVirtAPI())

    def _create_instance(self, params=None):
        """Create a test instance."""
        if not params:
            params = {}

        flavor = objects.Flavor(memory_mb=512,
                                swap=0,
                                vcpu_weight=None,
                                root_gb=10,
                                id=2,
                                name=u'm1.tiny',
                                ephemeral_gb=20,
                                rxtx_factor=1.0,
                                flavorid=u'1',
                                vcpus=1,
                                extra_specs={})
        flavor.update(params.pop('flavor', {}))

        inst = {}
        inst['id'] = 1
        inst['uuid'] = '52d3b512-1152-431f-a8f7-28f0288a622b'
        inst['os_type'] = 'linux'
        inst['image_ref'] = uuids.fake_image_ref
        inst['reservation_id'] = 'r-fakeres'
        inst['user_id'] = 'fake'
        inst['project_id'] = 'fake'
        inst['instance_type_id'] = 2
        inst['ami_launch_index'] = 0
        inst['host'] = 'host1'
        inst['root_gb'] = flavor.root_gb
        inst['ephemeral_gb'] = flavor.ephemeral_gb
        inst['config_drive'] = True
        inst['kernel_id'] = 2
        inst['ramdisk_id'] = 3
        inst['key_data'] = 'ABCDEFG'
        inst['system_metadata'] = {}
        inst['metadata'] = {}
        inst['task_state'] = None

        inst.update(params)

        instance = fake_instance.fake_instance_obj(
            self.context, expected_attrs=['metadata', 'system_metadata',
                                          'pci_devices'],
            flavor=flavor, **inst)

        for field in ['numa_topology', 'vcpu_model']:
            setattr(instance, field, None)

        return instance

    def test_precreate_network_raise(self):
        network_info = dict(location=CONF.azure.location,
                            address_space=dict(
                                address_prefixes=['10.0.0.0/16']))
        # network get exception
        self.drvr.network.virtual_networks.get.side_effect = Exception()
        self.assertRaises(exception.NetworkCreateFailure,
                          self.drvr._precreate_network)
        self.drvr.network.virtual_networks.get.side_effect = None
        self.drvr.network.virtual_networks.get.return_value = None

        # subnet get exception, delete network before raise
        self.drvr.network.subnets.get.side_effect = Exception()
        self.assertRaises(exception.SubnetCreateFailure,
                          self.drvr._precreate_network)
        self.drvr.network.virtual_networks.create_or_update.assert_called_with(
            CONF.azure.resource_group, CONF.azure.vnet_name, network_info)
        self.drvr.network.virtual_networks.delete.assert_called_with(
            CONF.azure.resource_group, CONF.azure.vnet_name)

    def test_get_info_raise(self):
        self.drvr.compute.virtual_machines.get.side_effect = \
            Exception()
        self.assertRaises(exception.InstanceGetFailure,
                          self.drvr.get_info,
                          self.fake_instance)

    def test_get_info(self):
        FakeVirtualMachine.instance_view = \
            azcpumodels.VirtualMachineInstanceView(
                statuses=[azcpumodels.InstanceViewStatus(
                    code='PowerState/running')])

        self.drvr.compute.virtual_machines.get.return_value = \
            FakeVirtualMachine

        # running state test
        instance_info = self.drvr.get_info(self.fake_instance)
        self.assertEqual(power_state.RUNNING, instance_info.state)

        # stop state test
        shutdown_staues = ['deallocating', 'deallocated',
                           'stopping', 'stopped']
        for i in shutdown_staues:
            FakeVirtualMachine.instance_view = \
                azcpumodels.VirtualMachineInstanceView(
                    statuses=[azcpumodels.InstanceViewStatus(
                        code='PowerState/' + i)])
            instance_info = self.drvr.get_info(self.fake_instance)
            self.assertEqual(power_state.SHUTDOWN, instance_info.state)

        # empty instance_view test
        FakeVirtualMachine.instance_view = None
        instance_info = self.drvr.get_info(self.fake_instance)
        self.assertEqual(power_state.NOSTATE, instance_info.state)

        # empty instance_view.statuses test
        FakeVirtualMachine.instance_view = \
            azcpumodels.VirtualMachineInstanceView(statuses=None)
        instance_info = self.drvr.get_info(self.fake_instance)
        self.assertEqual(power_state.NOSTATE, instance_info.state)

        # empty instance_view.statuses[0].code test
        FakeVirtualMachine.instance_view = \
            azcpumodels.VirtualMachineInstanceView(
                statuses=[azcpumodels.InstanceViewStatus(code=None)])
        instance_info = self.drvr.get_info(self.fake_instance)
        self.assertEqual(power_state.NOSTATE, instance_info.state)

    @mock.patch.object(time, 'time')
    @mock.patch.object(AzureDriver, '_cleanup_deleted_os_disks')
    @mock.patch.object(AzureDriver, '_cleanup_deleted_nics')
    @mock.patch.object(AzureDriver, '_cleanup_deleted_snapshots')
    def test_get_available_resource(self, mo_1, mo_2, mo_3, mock_time):
        mock_time.return_value = \
            self.drvr.cleanup_time + CONF.azure.cleanup_span + 1
        self.drvr.compute.usage.list.side_effect = \
            Exception()
        self.assertRaises(exception.ComputeUsageListFailure,
                          self.drvr.get_available_resource,
                          'node_name')
        for i in (mo_1, mo_2, mo_3):
            i.assert_called_once()

        usage_family = 'basicAFamily'
        self.drvr.compute.usage.list.side_effect = None
        self.drvr.compute.usage.list.return_value = [
            azcpumodels.Usage(2, 8, azcpumodels.UsageName('cores')),
            azcpumodels.Usage(1, 4, azcpumodels.UsageName(usage_family))]
        available_resource = self.drvr.get_available_resource('node_name')
        self.assertEqual(4, available_resource['vcpus'])
        self.assertEqual(1, available_resource['vcpus_used'])

    def test_prepare_network_profile_raise(self):
        self.drvr.network.network_interfaces.create_or_update.side_effect = \
            Exception()
        self.assertRaises(Exception,
                          self.drvr._prepare_network_profile,
                          'instance_uuid')

    def test_prepare_network_profile(self):
        id_str = 'nic_id'
        fake_creation = mock.Mock()

        nic = FakeObj()
        nic.id = id_str

        fake_creation.result.return_value = nic
        self.drvr.network.network_interfaces.create_or_update.return_value = \
            fake_creation
        network_profile = self.drvr._prepare_network_profile('instance_uuid')
        self.assertEqual(id_str,
                         network_profile['network_interfaces'][0]['id'])

    def test_get_image_from_mapping_not_found(self):
        image = FakeObj()
        image.name = 'fake_image_name'
        self.assertRaises(exception.ImageAzureMappingNotFound,
                          self.drvr._get_image_from_mapping,
                          image)

    def test_get_size_from_flavor_not_found(self):
        flavor = dict(name='fake_image_name')
        self.assertRaises(exception.FlavorAzureMappingNotFound,
                          self.drvr._get_size_from_flavor,
                          flavor)

    def test_prepare_os_profile_without_image_reference(self):
        os = self.drvr._prepare_os_profile(self.fake_instance, dict(), None)
        self.assertIsNone(os)

    def test_prepare_os_profile(self):
        self.fake_instance.save = mock.Mock()
        # linux os type
        storage = dict(image_reference=dict(offer=driver.LINUX_OFFER[0]))
        password = 'password'
        key_data = 'key_data'
        self.fake_instance.key_data = key_data
        os = self.drvr._prepare_os_profile(
            self.fake_instance, storage, password)
        self.assertEqual(driver.LINUX_OS, self.fake_instance.os_type)
        actual_key = os['linux_configuration']['ssh']['public_keys'][0]
        self.assertEqual(key_data, actual_key['key_data'])

        # no key data for linux instance
        self.fake_instance.key_data = None
        os = self.drvr._prepare_os_profile(
            self.fake_instance, storage, password)
        self.assertEqual(password, os['admin_password'])

        # windows os type
        storage = dict(image_reference=dict(offer=driver.WINDOWS_OFFER[0]))
        os = self.drvr._prepare_os_profile(
            self.fake_instance, storage, password)
        self.assertEqual(driver.WINDOWS_OS, self.fake_instance.os_type)
        self.assertEqual(password, os['admin_password'])

        # unkown os type
        storage = dict(image_reference=dict(offer='unkown_os_type'))
        self.assertRaises(exception.OSTypeNotFound,
                          self.drvr._prepare_os_profile,
                          *(self.fake_instance, storage, password))

        self.assertEqual(3, self.fake_instance.save.call_count)

    def test_create_vm_parameters(self):
        # os profile is None
        vm = self.drvr._create_vm_parameters('', '', '', None)
        self.assertNotIn('os_profile', vm)

        # os profile is not None
        vm = self.drvr._create_vm_parameters('', '', '', 'os_profile')
        self.assertIn('os_profile', vm)

    @mock.patch.object(AzureDriver, '_copy_blob')
    @mock.patch.object(AzureDriver, '_get_image_from_mapping')
    @mock.patch(
        'nova.virt.azureapi.driver.loopingcall.FixedIntervalLoopingCall')
    def test_prepare_storage_profile(self, mock_loop_call,
                                     mock_image_mapping, mock_copy_blob):
        mock_loop_call.return_value = mock.MagicMock()
        image_meta = FakeObj()
        image_meta.id = 'image_id'
        image = dict(id='image_id',
                     properties=dict(azure_type=driver.AZURE,
                                     azure_uri='azure_uri',
                                     azure_os_type=driver.LINUX_OS))
        self.drvr._image_api.get.return_value = image

        # boot from azure export images.
        blob = azsmodels.Blob()
        blob.properties.copy.status = 'pending'
        self.drvr.blob.get_blob_properties.return_value = blob
        storage_profile = self.drvr._prepare_storage_profile(
            self.context, image_meta, self.fake_instance)
        blob.properties.copy.status = 'success'
        self.assertIn('os_type', storage_profile['os_disk'])
        mock_copy_blob.assert_called()
        self.assertEqual(0, mock_image_mapping.call_count)
        self.assertEqual(1, mock_copy_blob.call_count)

        # bad parameters in image properties
        image['properties'] = dict(azure_type=driver.AZURE)
        self.assertRaises(
            nova_ex.ImageUnacceptable,
            self.drvr._prepare_storage_profile,
            *(self.context, image_meta, self.fake_instance))

        # boot from normal openstack images
        image['properties'] = dict()
        storage_profile = self.drvr._prepare_storage_profile(
            self.context, image_meta, self.fake_instance)
        self.assertIn('image_reference', storage_profile)
        self.assertNotIn('os_type', storage_profile['os_disk'])
        self.assertEqual(1, mock_copy_blob.call_count)
        self.assertEqual(1, mock_image_mapping.call_count)
        mock_image_mapping.assert_called()

    @mock.patch.object(AzureDriver, '_check_password')
    @mock.patch.object(AzureDriver, '_get_size_from_flavor')
    @mock.patch.object(AzureDriver, '_prepare_network_profile')
    @mock.patch.object(AzureDriver, '_prepare_storage_profile')
    @mock.patch.object(AzureDriver, '_prepare_os_profile')
    @mock.patch.object(AzureDriver, '_create_vm_parameters')
    @mock.patch.object(AzureDriver, '_create_update_instance')
    @mock.patch.object(AzureDriver, '_cleanup_instance')
    def test_spawn(self, mo_clean, mo_update_ins, mo_vm_pare, mo_os, mo_sto,
                   mo_net, mo_size, mo_pass):
        # invalid pass
        mo_pass.return_value = False
        self.assertRaises(
            exception.PasswordInvalid,
            self.drvr.spawn,
            *('context', self.fake_instance, 'im', 'inj', 'pass'))

        # raise and check clean up
        mo_pass.return_value = True
        mo_update_ins.side_effect = \
            exception.InstanceCreateUpdateFailure(reason='', instance_uuid='')
        self.assertRaises(
            exception.InstanceCreateUpdateFailure,
            self.drvr.spawn,
            *('context', self.fake_instance, 'im', 'inj', 'pass'))
        mo_clean.assert_called()

    def test_get_instance(self):
        # miss test
        self.drvr.compute.virtual_machines.get.side_effect = \
            exception.AzureMissingResourceHttpError('mesg', 'status')
        self.assertRaises(
            nova_ex.InstanceNotFound,
            self.drvr._get_instance,
            self.fake_instance.uuid)

        # raise test
        self.drvr.compute.virtual_machines.get.side_effect = Exception
        self.assertRaises(
            exception.InstanceGetFailure,
            self.drvr._get_instance,
            self.fake_instance.uuid)

    def test_create_update_instance(self):
        # miss test
        self.drvr.compute.virtual_machines.create_or_update.side_effect = \
            exception.AzureMissingResourceHttpError('mesg', 'status')
        self.assertRaises(
            nova_ex.InstanceNotFound,
            self.drvr._create_update_instance,
            *(self.fake_instance, 'param'))

        # raise test
        self.drvr.compute.virtual_machines.create_or_update.side_effect = \
            Exception
        self.assertRaises(
            exception.InstanceCreateUpdateFailure,
            self.drvr._create_update_instance,
            *(self.fake_instance, 'param'))

    def test_copy_blob(self):
        # raise test
        self.drvr.blob.copy_blob.side_effect = \
            exception.AzureMissingResourceHttpError('mesg', 'status')
        self.assertRaises(
            exception.BlobNotFound,
            self.drvr._copy_blob,
            *('cont', 'blob', 'source'))

        # raise test
        self.drvr.blob.copy_blob.side_effect = Exception
        self.assertRaises(
            exception.BlobCopyFailure,
            self.drvr._copy_blob,
            *('cont', 'blob', 'source'))

    def test_delete_blob(self):
        # inexist test
        self.drvr.blob.delete_blob.side_effect = \
            exception.AzureMissingResourceHttpError('mesg', 'status')
        self.drvr._delete_blob('cont', 'blob')

        # raise test
        self.drvr.blob.delete_blob.side_effect = Exception
        self.assertRaises(
            exception.BlobDeleteFailure,
            self.drvr._delete_blob,
            *('cont', 'blob'))

    @mock.patch.object(AzureDriver, '_delete_blob')
    def test_cleanup_instance(self, mock_delete_blob):
        fake_delete = mock.Mock()
        fake_delete.wait.return_value = None
        self.drvr.network.network_interfaces.delete.return_value = fake_delete
        # raise in delete blob
        mock_delete_blob.side_effect = Exception
        self.drvr._cleanup_instance(self.fake_instance)
        self.drvr.network.network_interfaces.delete.assert_called()

        # raise in delete net interface
        self.drvr.network.network_interfaces.delete.side_effect = Exception

    @mock.patch.object(AzureDriver, '_cleanup_instance')
    def test_destroy(self, mock_clean):

        # raise test
        self.drvr.compute.virtual_machines.delete.side_effect = Exception
        self.assertRaises(
            exception.InstanceDeleteFailure,
            self.drvr.destroy,
            *('cont', self.fake_instance, 'net'))

        # not raise
        fake_action = mock.Mock()
        fake_action.wait.return_value = None
        self.drvr.compute.virtual_machines.delete.side_effect = None
        self.drvr.compute.virtual_machines.delete.return_value = fake_action
        self.drvr.destroy('cont', self.fake_instance, 'net')
        mock_clean.assert_called()

    def _test_instance_action(self, action_methon, invoke_api, paras,
                              exep=Exception):
        # raise test
        invoke_api.side_effect = Exception
        self.assertRaises(
            exep,
            action_methon,
            *paras)

        # not raise
        fake_action = mock.Mock()
        fake_action.wait.return_value = None
        invoke_api.side_effect = None
        invoke_api.return_value = fake_action
        action_methon(*paras)

    def test_instance_action(self):
        self._test_instance_action(
            self.drvr.reboot,
            self.drvr.compute.virtual_machines.restart,
            ('cont', self.fake_instance, 'net', 're_type'),
            nova_ex.InstanceRebootFailure)
        self._test_instance_action(
            self.drvr.power_off,
            self.drvr.compute.virtual_machines.power_off,
            (self.fake_instance,),
            nova_ex.InstancePowerOffFailure)
        self._test_instance_action(
            self.drvr.power_on,
            self.drvr.compute.virtual_machines.start,
            ('cont', self.fake_instance, 'net'),
            nova_ex.InstancePowerOnFailure)

    def test_rebuild(self):
        self.fake_instance.save = mock.Mock()
        # raise
        self.drvr.compute.virtual_machines.redeploy.side_effect = Exception
        self.assertRaises(
            Exception,
            self.drvr.rebuild,
            *('cont', self.fake_instance, '1', '2', '3', '4', '5', '6'))

        # not raise
        self.drvr.compute.virtual_machines.redeploy.side_effect = None
        fake_action = mock.Mock()
        fake_action.wait.return_value = None
        self.drvr.compute.virtual_machines.redeploy.return_value = fake_action
        self.drvr.rebuild('cont', self.fake_instance,
                          '1', '2', '3', '4', '5', '6')
        self.fake_instance.save.assert_called()

    @mock.patch.object(AzureDriver, '_get_size_from_flavor')
    def test_get_new_size(self, mock_size):
        size_name = 'size_name'
        size_obj = [FakeObj()]
        size_obj[0].name = size_name
        self.drvr.compute.virtual_machines.list_available_sizes.\
            return_value = size_obj
        # mapping not found
        mock_size.side_effect = \
            exception.FlavorAzureMappingNotFound(flavor_name='')
        size = self.drvr._get_new_size(self.fake_instance, 'flavor')
        self.assertEqual(None, size)

        #
        mock_size.side_effect = None
        mock_size.return_value = size_name
        size = self.drvr._get_new_size(self.fake_instance, 'flavor')
        self.assertEqual(size_name, size)

    @mock.patch.object(AzureDriver, '_get_new_size')
    @mock.patch.object(AzureDriver, '_get_instance')
    @mock.patch.object(AzureDriver, '_create_update_instance')
    def test_migrate_disk_and_power_off(self, mo_create, mo_get, mo_size):

        # raise
        mo_size.return_value = None
        self.assertRaises(
            exception.FlavorInvalid,
            self.drvr.migrate_disk_and_power_off,
            *('cont', self.fake_instance, 'dest', 'flavor', 'net'))

        # not raise
        size_old = 'size_old'
        size_new = 'size_new'
        vm_ojb = FakeObj()
        vm_size_obj = FakeObj()
        vm_size_obj.vm_size = size_old
        vm_ojb.hardware_profile = vm_size_obj
        mo_size.return_value = size_new
        mo_get.return_value = vm_ojb
        flag = self.drvr.migrate_disk_and_power_off(
            'cont', self.fake_instance, 'dest', 'flavor', 'net')
        self.assertEqual(True, flag)
        self.assertEqual(size_new, vm_ojb.hardware_profile.vm_size)

    @mock.patch.object(AzureDriver, '_get_instance')
    @mock.patch.object(AzureDriver, '_create_update_instance')
    def test_attach_volume(self, mo_create, mo_get):
        vm_ojb = FakeObj()
        luns = [FakeObj() for i in range(16)]
        for i in range(16):
            luns[i].lun = i
        data_disks_obj = FakeObj()
        data_disks_obj.data_disks = luns
        vm_ojb.storage_profile = data_disks_obj
        mo_get.return_value = vm_ojb
        conn_info = dict(data=dict(vhd_name='vhd_name',
                                   vhd_uri='vhd_uri',
                                   vhd_size_gb='vhd_size_gb'))
        # raise
        # self.drvr.attach_volume(
        #         'cont', conn_info, self.fake_instance, 'mp')
        self.assertRaises(
            nova_ex.NovaException,
            self.drvr.attach_volume,
            *('cont', conn_info, self.fake_instance, 'mp'))

        # not raise
        lun_ojb = FakeObj()
        lun_ojb.lun = 1
        data_disks_obj.data_disks = [lun_ojb]
        self.drvr.attach_volume(
            'cont', conn_info, self.fake_instance, 'mp')
        self.assertEqual(2, len(data_disks_obj.data_disks))
        self.assertEqual(2, data_disks_obj.data_disks[1]['lun'])

    @mock.patch.object(AzureDriver, '_get_instance')
    @mock.patch.object(AzureDriver, '_create_update_instance')
    def test_detach_volume(self, mo_create, mo_get):
        disk_name = 'disk_name'
        vm_ojb = FakeObj()
        disk = FakeObj()
        disk.name = disk_name + 'not found'
        data_disks_obj = FakeObj()
        data_disks_obj.data_disks = [disk]
        vm_ojb.storage_profile = data_disks_obj
        mo_get.return_value = vm_ojb
        conn_info = dict(data=dict(vhd_name=disk_name,
                                   vhd_uri='vhd_uri',
                                   vhd_size_gb='vhd_size_gb'))
        # not found, no raise
        self.drvr.detach_volume(conn_info, self.fake_instance, 'mp')
        self.assertEqual(0, mo_create.call_count)

        # not raise
        disk.name = disk_name
        self.drvr.detach_volume(conn_info, self.fake_instance, 'mp')
        self.assertEqual(1, mo_create.call_count)
        self.assertEqual(0, len(data_disks_obj.data_disks))

    @mock.patch(
        'nova.virt.azureapi.driver.loopingcall.FixedIntervalLoopingCall')
    @mock.patch.object(AzureDriver, '_copy_blob')
    def test_snapshot(self, mock_copy, mock_loop_call):
        mock_loop_call.return_value = mock.MagicMock()
        update_stask = mock.Mock()
        image_id = 'image_id'
        self.drvr._image_api.get.return_value = dict(id=image_id)
        self.drvr.blob.make_blob_url = lambda x, y: y
        self.drvr._get_snapshot_blob_name_from_id = lambda x: x
        self.drvr._get_blob_name = lambda x: x
        self.drvr.snapshot('cont', self.fake_instance, 'id', update_stask)
        mock_copy.assert_called_with(driver.SNAPSHOT_CONTAINER,
                                     image_id,
                                     self.fake_instance.uuid)
