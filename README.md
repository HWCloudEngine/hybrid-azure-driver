# hybrid-azure-driver
# This is the driver of OpenStack nova and cinder for Azure Cloud.

###HOW TO

####1 Get codes
devstack, then stop n-cpu screen.
`
git clond https://github.com/yanheven/azure_driver
cp -r azure_driver/nova/virt/azureapi /opt/stack/nova/nova/virt/azureapi
pip install -r azure_driver/nova/virt/azureapi/requirements.txt

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
