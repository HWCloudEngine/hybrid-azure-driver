import sys

from oslo_log import log as logging
from oslo_utils import importutils
import six

import nova.conf
from nova.i18n import _, _LE, _LI
from nova import utils
from nova.virt import event as virtevent
from oslo_config import cfg
from azure.common.credentials import UserPassCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.storage import CloudStorageAccount

CONF = nova.conf.CONF
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
               help='Auzre Virtual Network Name'),
    cfg.StrOpt('vsubnet_id',
               help='Auzre Virtual Subnte ID'),
    cfg.StrOpt('vsubnet_name',
               help='Auzre Virtual Subnte Name'),
    cfg.IntOpt('cleanup_span',
               default=60,
               help='Cleanup span in seconds to cleanup zombie resources'
                    'in Azure.')
]

CONF.register_opts(compute_opts, 'azure')
# CONF.import_opt('my_ip', 'nova.netconf')


class Azure(object):

    def __init__(self, username=CONF.azure.username,
                 password=CONF.azure.password,
                 subscription_id=CONF.azure.subscription_id,
                 resource_group=CONF.azure.resource_group,
                 storage_account=CONF.azure.storage_account):

        credentials = UserPassCredentials(username, password)
        LOG.info('Login with Azure username and password.')
        self.resource = ResourceManagementClient(credentials,
                                                 subscription_id)
        self.compute = ComputeManagementClient(credentials,
                                               subscription_id)
        self.storage = StorageManagementClient(credentials,
                                               subscription_id)
        self.network = NetworkManagementClient(credentials,
                                               subscription_id)
        account_keys = self.storage.storage_accounts.list_keys(
            resource_group, storage_account)
        key_str = account_keys.keys[0].value
        self.account = CloudStorageAccount(
            account_name=storage_account,
            account_key=key_str)
        self.blob = self.account.create_page_blob_service()
        LOG.info('Azure Management Clients Initialized')
