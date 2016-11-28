import mock

from nova import context
from nova import objects
from nova import test
from nova.virt import fake
from nova.virt.azureapi.driver import AzureDriver
from nova.tests import uuidsentinel as uuids
from nova.tests.unit import fake_instance


class AzureDriverTestCase(test.NoDBTestCase):

    @mock.patch('nova.virt.azureapi.driver.Azure')
    @mock.patch('nova.image.API')
    @mock.patch('nova.volume.cinder.API')
    def setUp(self, mock_cinder, mock_image, mock_azure):
        super(AzureDriverTestCase, self).setUp()
        self.mock_cinder = mock_cinder
        self.mock_image = mock_image
        self.mock_azure = mock_azure

        self.flags(group='azure', username='username',
                   password='username', subscription_id='subscription_id',
                   storage_account='storage_account', location='location',
                   resource_group='resource_group', vnet_name='vnet_name',
                   vsubnet_id='vsubnet_id', vsubnet_name='vsubnet_name',
                   cleanup_span=60)

        self.drvr = AzureDriver(fake.FakeVirtAPI())
        self.context = context.get_admin_context()

    def test_init_raise(self):
        self.mock_azure.side_effect = Exception('init_raise')
        try:
            AzureDriver(fake.FakeVirtAPI())
        except Exception:
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
