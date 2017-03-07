import mock
from unittest import TestCase

from cinder.volume.drivers.azure import adapter

USERNAME = 'AZUREUSER'
PASSWORD = 'PASSWORD'
SUBSCRIBE_ID = 'ID'
RG = 'RG'


class AzureTestCase(TestCase):

    @mock.patch('cinder.volume.drivers.azure.adapter.UserPassCredentials')
    @mock.patch('cinder.volume.drivers.azure.adapter.ComputeManagementClient')
    @mock.patch('cinder.volume.drivers.azure.adapter.ResourceManagementClient')
    def test_start_driver_with_user_password_subscribe_id(
            self, resource, compute, credential):
        credentials = 'credentials'
        credential.return_value = credentials
        azure = adapter.Azure(username=USERNAME,
                              password=PASSWORD, subscription_id=SUBSCRIBE_ID)
        credential.assert_called_once_with(USERNAME, PASSWORD)
        compute.assert_called_once_with(credentials, SUBSCRIBE_ID)
        resource.assert_called_once_with(credentials, SUBSCRIBE_ID)
        self.assertTrue(hasattr(azure, 'compute'))
        self.assertTrue(hasattr(azure, 'resource'))
