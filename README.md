# hybrid-azure-driver
# This is the driver of OpenStack nova and cinder for Azure Cloud.

###HOW TO

####1 Get code and Register Azure Subscription Account

#####1.1 deploy OpenStack and git clone code from repo.
fresh deploy openstack via devstack(or manually),
clone code from azure_driver repo, include nova and cinder folders.

#####1.2 Register Azure Account and make a Subscription
create an user for subscription, then mark down subscription_id,
username and password of user, this credential info will be filled into
config file for both nova and cinder.  

create resource group with name "ops_resource_group" via Azure Portal,
and storage account with name "ops0storage0account" under the resource group just created.

####2 nova

devstack, then stop n-cpu screen. if you deploy openstack manually, the 
following steps may be little different. believe if you can manually deploy, 
you can do the following steps right.
```
$cp -r nova/virt/azureapi /opt/stack/nova/nova/virt/
$pip install -r /opt/stack/nova/nova/virt/azureapi/requirements.txt

$cp /etc/nova/nova.conf /etc/nova/nova-compute.conf
$vi /etc/nova/nova-compute.conf

[DEFAULT]
compute_driver=azureapi.AzureDriver
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
async_timeout = 600

$/usr/local/bin/nova-compute --config-file /etc/nova/nova-compute.conf & echo $! >/opt/stack/status/stack/n-cpu.pid; fg || echo "n-cpu failed to start" | tee "/opt/stack/status/stack/n-cpu.failure"
```

####3 cinder
#####3.1 volume

devstack, then stop c-vol screen.
```
$cp -r cinder/volume/drivers/azure /opt/stack/cinder/cinder/volume/drivers/
$pip install -r /opt/stack/cinder/cinder/volume/drivers/azure/requirements.txt

$cp /etc/cinder/cinder.conf /etc/cinder/cinder-volume.conf
$vi /etc/cinder/cinder-volume.conf

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

$/usr/local/bin/cinder-volume --config-file /etc/cinder/cinder-volume.conf  & echo ! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"
```

#####3.2 backup
devstack, create a new screen:c-backup
```
$cp -r cinder/backup/drivers/azure_backup.py /opt/stack/cinder/cinder/backup/drivers/
$pip install -r /opt/stack/cinder/cinder/volume/drivers/azure/requirements.txt

$cp /etc/cinder/cinder.conf /etc/cinder/cinder-backup.conf
$vi /etc/cinder/cinder-backup.conf

[DEFAULT]
backup_driver = cinder.backup.drivers.azure_backup

[azure]
location = westus
resource_group = ops_resource_group
storage_account = ops0storage0account
subscription_id = 62257576-b9df-484a-b643-2df9ce9e7086
username = xxxxxx@yanhevenoutlook.onmicrosoft.com
password = xxxxxx
azure_volume_container_name = volumes
azure_backup_container_name = backups

$/usr/local/bin/cinder-backup --config-file /etc/cinder/cinder-backup.conf & echo $! >/opt/stack/status/stack/c-bac.pid; fg || echo "c-bac failed to start" | tee "/opt/stack/status/stack/c-bac.failure"
```

####4 Advanced configuration
for nova, add more image and flavor mapping, in nova/virt/azureapi/constant.py

####5 Supported Matrix by Driver
#####5.1 Nova
|API|Note
|:--|:--|
|server create|boot from image(azure image marketplace) or snapshot(snapshot from azure instance), insert key(linux), insert user/password, use default rule(allow all traffic in/out)|
|server delete||
|server reboot||
|server power off|only one mode|
|server power on||
|server rebuild|redeploy with original instance config, can't change config|
|server resize||
|server attach volume||
|server detach volume||
|server snapshot||
and all periodic tasks, must implement interfaces, also add periodic cleanup 
for azure zombie resources.

#####5.2 Cinder
|API|Note
|:--|:--|
|volume create|3 types:empty, from snapshot, from volume|
|volume delete||
|volume snapshot create||
|volume snapshot delete||
|attach volume||
|backup crate||
|backup delete||
|backup restore||
