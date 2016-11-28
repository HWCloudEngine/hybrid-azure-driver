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
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage import CloudStorageAccount
from nova import conf
from nova.i18n import _LI
from oslo_config import cfg
from oslo_log import log as logging

# TODO(haifeng) remove these option block to nova/conf/azureapi
CONF = conf.CONF
LOG = logging.getLogger(__name__)

compute_opts = [
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
               help='Auzre password of user of subscription'),
    cfg.StrOpt('vnet_name',
               default='vnet',
               help='Auzre Virtual Network Name'),
    cfg.StrOpt('vsubnet_id',
               default='None',
               help='Auzre Virtual Subnet ID'),
    cfg.StrOpt('vsubnet_name',
               default='vsubnet',
               help='Auzre Virtual Subnet Name'),
    cfg.IntOpt('cleanup_span',
               default=60,
               help='Cleanup span in seconds to cleanup zombie resources'
                    'in Azure.'),
    cfg.IntOpt('async_timeout',
               default=600,
               help='Timeout for async api invoke.')
]

CONF.register_opts(compute_opts, 'azure')


class Azure(object):

    def __init__(self):
        credentials = UserPassCredentials(CONF.azure.username,
                                          CONF.azure.password)
        LOG.info(_LI('Login with Azure username and password.'))
        self.resource = ResourceManagementClient(credentials,
                                                 CONF.azure.subscription_id)
        self.compute = ComputeManagementClient(credentials,
                                               CONF.azure.subscription_id)
        self.storage = StorageManagementClient(credentials,
                                               CONF.azure.subscription_id)
        self.network = NetworkManagementClient(credentials,
                                               CONF.azure.subscription_id)
        account_keys = self.storage.storage_accounts.list_keys(
            CONF.azure.resource_group, CONF.azure.storage_account)
        key_str = account_keys.keys[0].value
        self.account = CloudStorageAccount(
            account_name=CONF.azure.storage_account,
            account_key=key_str)
        self.blob = self.account.create_page_blob_service()
        LOG.info(_LI('Azure Management Clients Initialized'))
