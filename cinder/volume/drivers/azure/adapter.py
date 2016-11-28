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

from azure.common.credentials import UserPassCredentials
from azure.mgmt.storage import StorageManagementClient
from azure.storage import CloudStorageAccount
from cinder.i18n import _LI
from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

volume_opts = [
    cfg.StrOpt('location',
               default='westus',
               help='Azure Datacenter Location'),
    cfg.StrOpt('resource_group',
               default='ops_resource_group',
               help='Azure Resource Group Name'),
    cfg.StrOpt('storage_account',
               default='ops0storage0account',
               help="""Azure Storage Account Name, should be unique in Azure,
    Storage account name must be between 3 and 24 characters in length
    and use numbers and lower-case letters only."""),
    cfg.StrOpt('subscription_id',
               help='Azure subscription ID'),
    cfg.StrOpt('username',
               help='Auzre username of subscription'),
    cfg.StrOpt('password',
               help='Auzre password of user of subscription')
]

CONF.register_opts(volume_opts, 'azure')


class Azure(object):

    def __init__(self, username=CONF.azure.username,
                 password=CONF.azure.password,
                 subscription_id=CONF.azure.subscription_id,
                 resource_group=CONF.azure.resource_group,
                 storage_account=CONF.azure.storage_account):

        credentials = UserPassCredentials(username, password)
        LOG.info(_LI('Login with Azure username and password.'))
        self.storage = StorageManagementClient(credentials,
                                               subscription_id)
        account_keys = self.storage.storage_accounts.list_keys(
            resource_group, storage_account)
        key_str = account_keys.keys[0].value
        self.account = CloudStorageAccount(
            account_name=storage_account,
            account_key=key_str)
        self.blob = self.account.create_page_blob_service()
        LOG.info(_LI('Azure Management Clients Initialized'))
