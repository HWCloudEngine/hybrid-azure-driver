import mock
from unittest import TestCase

from cinder.volume.drivers.azure import adapter

USERNAME = 'AZUREUSER'
PASSWORD = 'PASSWORD'
SUBSCRIBE_ID = 'ID'
RG = 'RG'
SAC = 'SC'
KEY = 'KEY'


class FakeKey(object):
    class Value(object):
        value = KEY
    keys = [Value()]


class AzureTestCase(TestCase):

    @mock.patch('cinder.volume.drivers.azure.adapter.UserPassCredentials')
    @mock.patch('cinder.volume.drivers.azure.adapter.StorageManagementClient')
    @mock.patch('cinder.volume.drivers.azure.adapter.CloudStorageAccount')
    def test_start_driver_with_user_password_subscribe_id(
            self, cloudstorage, storage, credential):
        storage().storage_accounts.list_keys = mock.Mock(return_value=FakeKey)
        cloudstorage.create_page_blob_service = mock.Mock()

        azure = adapter.Azure(username=USERNAME,
                              password=PASSWORD, subscription_id=SUBSCRIBE_ID,
                              storage_account=SAC)

        credential.assert_called_once_with(USERNAME, PASSWORD)
        storage.assert_called_with(credential(), SUBSCRIBE_ID)
        cloudstorage.assert_called_once_with(account_name=SAC, account_key=KEY)
        self.assertTrue(hasattr(azure, 'blob'))
        self.assertTrue(hasattr(azure, 'storage'))
