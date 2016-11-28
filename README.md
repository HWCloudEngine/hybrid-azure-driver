# hybrid-azure-driver
# This is the driver of OpenStack nova and cinder for Azure Cloud.

###HOW TO

####1 Get codes
devstack, then stop n-cpu screen.
`
git clond https://github.com/yanheven/azure_driver
##### nova
cp -r azure_driver/nova/virt/azureapi /opt/stack/nova/nova/virt/
pip install -r /opt/stack/nova/nova/virt/azureapi/requirements.txt

cp /etc/nova/nova.conf /etc/nova/nova-azure.conf
vi /etc/nova/nova-azure.conf

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
`
/usr/local/bin/nova-compute --config-file /etc/nova/nova-azure.conf & echo $! >/opt/stack/status/stack/n-cpu.pid; fg || echo "n-cpu failed to start" | tee "/opt/stack/status/stack/n-cpu.failure"

#####cinder
`
cp -r azure_driver/cinder/volume/drivers/azure /opt/stack/cinder/cinder/volume/drivers/
pip install -r /opt/stack/cinder/cinder/volume/drivers/azure/requirements.txt

cp /etc/cinder/cinder.conf /etc/cinder/cinder-azure.conf
vi /etc/cinder/cinder-azure.conf

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
username = test@yanhevenoutlook.onmicrosoft.com
password = Zm1vdXRs
azure_storage_container_name = volumes
azure_total_capacity_gb = 500000
`
/usr/local/bin/cinder-volume --config-file /etc/cinder/cinder.conf.azure  & echo $! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"
