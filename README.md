# hybrid-azure-driver
# This is the driver of OpenStack nova and cinder for Azure Cloud.

###HOW TO

####1 Get code and Register Azure Subscription Account
#####1.1 git clone code from repo.
include nova and cinder folders.
#####1.2 Register Azure Account and make a Subscription
create an user for subscription, then mark down subscription_id,
username and password of user, this credential info will be filled into
config file for both nova and cinder.

####2 nova
`
devstack, then stop n-cpu screen. if you deploy openstack manually, the 
following steps may be little different. believe if you can manually deploy, 
you can do the following steps right.

cp -r nova/virt/azureapi /opt/stack/nova/nova/virt/
pip install -r /opt/stack/nova/nova/virt/azureapi/requirements.txt

cp /etc/nova/nova.conf /etc/nova/nova-compute.conf
vi /etc/nova/nova-compute.conf

[DEFAULT]
compute_driver=nova.virt.azureapi.AzureDriver
[azure]
location = westus
resource_group = ops_resource_group
storage_account = ops0storage0account
subscription_id = 62257576-b9df-484a-b643-2df9ce9e7086
username = xxxxxxxxxx@yanhevenoutlook.onmicrosoft.com
password = xxxxxxxxx
vnet_name = ops_vnet
vsubnet_id = none
subnet_name = ops_vsubnet
cleanup_span = 60

/usr/local/bin/nova-compute --config-file /etc/nova/nova-compute.conf & echo $! >/opt/stack/status/stack/n-cpu.pid; fg || echo "n-cpu failed to start" | tee "/opt/stack/status/stack/n-cpu.failure"
`

####3 cinder
`
devstack, then stop c-vol screen.

cp -r cinder/volume/drivers/azure /opt/stack/cinder/cinder/volume/drivers/
pip install -r /opt/stack/cinder/cinder/volume/drivers/azure/requirements.txt

cp /etc/cinder/cinder.conf /etc/cinder/cinder-volume.conf
vi /etc/cinder/cinder-volume.conf

[DEFAULT]
#enabled_backends = lvmdriver-1
enabled_backends = azure

[azure]
volume_driver = cinder.volume.drivers.azure.driver.AzureDriver
volume_backend_name = azure
location = westus
resource_group = ops_resource_group
storage_account = ops0storage0account
subscription_id = 62257576-b9df-484a-b643-2df9ce9e7086
username = xxxxxx@yanhevenoutlook.onmicrosoft.com
password = xxxxxx
azure_storage_container_name = volumes
azure_total_capacity_gb = 500000

/usr/local/bin/cinder-volume --config-file /etc/cinder/cinder-volume.conf  & echo 
$! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"
`