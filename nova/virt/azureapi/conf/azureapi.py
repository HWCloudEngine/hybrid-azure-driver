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

CONF = cfg.CONF

azure_group = cfg.OptGroup('azure',
                           title='Azure Options',
                           help="""
Azure options are used when the compute_driver is set to use
Azure (compute_driver=azureapi.AzureDriver).
""")

azure_opts = [
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


def register_opts(conf):
    conf.register_group(azure_group)
    conf.register_opts(azure_opts, group=azure_group)


def list_opts():
    return {azure_group: azure_opts}
