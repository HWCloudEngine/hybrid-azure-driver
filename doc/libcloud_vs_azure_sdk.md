###Apache Libcloud VS. Azure Python SDK
###1. Over View
|Type|License|Last Update(Compute)|Last Update(Volume)|Author|
|:--|:--|:--|:--|:--|
|[Apache Libcloud](http://libcloud.apache.org/)|Apache 2.0|10 months ago|6 months ago|Contributor|
|[Azure SDK](https://azure.microsoft.com/en-us/develop/python/)|MIT|4 days ago|4 days ago|Azure Official|

###2. Supported Matrix
####2.1 [Libcloud(Compute)](https://libcloud.readthedocs.io/en/latest/supported_providers.html#supported-methods-base-compute)
- list nodes
- create node
- reboot node
- destroy node
- list images
- list sizes
- deploy node

####2.2 [Libcloud(Volume)](https://libcloud.readthedocs.io/en/latest/supported_providers.html#supported-methods-block-storage)
- list volumes
- create volume
- destroy volume
- attach volume
- detach volume
- create snapshot

####2.3 Azure SDK(Compute)
#####2.3.1 [Virtual Machines REST API Reference](https://msdn.microsoft.com/en-us/library/mt163647.aspx)
Updated: August 5, 2016
[Python Implementation Module:azure-mgmt-compute](http://azure-sdk-for-python.readthedocs.io/en/latest/ref/azure.mgmt.compute.html)
- Add or update an extension
- Create an availability set
- Create or update a VM
- Delete an availability set
- Delete an extension
- Delete a VM
- Generalize a VM
- Get availability set information
- Get extension information
- Get VM information
- List availability sets in a resource group
- List available VM sizes in an availability set
- List available VM sizes in a region
- List available VM sizes for resizing
- List image offers
- List image publishers
- List image skus
- List image versions
- List VMs in a resource group
- List VMs in a subscription
- Restart a VM
- Save an image from a VM
- Start a VM
- Stop a VM
- Stop and deallocate a VM

#####2.3.2 [Virtual MachinesREST API(classic)](https://msdn.microsoft.com/en-us/library/jj157206.aspx)
Updated: July 10, 2015
The Service Management API includes operations for managing the Virtual Machines in your subscription.
[Python Implementation Module:azure-servicemanagement-legacy](http://azure-sdk-for-python.readthedocs.io/en/latest/servicemanagement.html)

- Add Data Disk
- Add Disk
- Add DNS Server
- Add Load Balancer
- Add OS Image
- Add Virtual IP Address
- Add Role
- Capture Role
- Capture VM Image
- Create Virtual Machine Deployment
- Create VM Image
- Delete Data Disk
- Delete Disk
- Delete DNS Server
- Delete Load Balancer
- Delete OS Image
- Delete Role
- Delete Virtual IP Address
- Delete VM Image
- Download RDP File
- Get Data Disk
- Get Disk
- Get IP Forwarding for Network Interface
- Get IP Forwarding for Role
- Get Role
- List Disks
- List OS Images
- List Resource Extensions
- List Resource Extension Versions
- List VM Images
- Redeploy role
- Restart role
- Set IP Forwarding for Network Interface
- Set IP Forwarding for Role
- Shutdown Role
- Shutdown Roles
- Start Role
- Start Roles
- Update Data Disk
- Update Disk
- Update DNS Server
- Update Load Balancer
- Update Load-Balanced Endpoint Set
- Update OS Image
- Update Role
- Update VM Image

####2.4 Azure SDK(Volume)
[Blob Service REST API](https://msdn.microsoft.com/en-us/library/dd135733.aspx)

- Put Blob
- Get Blob
- Get Blob Properties
- Set Blob Properties
- Get Blob Metadata
- Set Blob Metadata
- Lease Blob
- Snapshot Blob 
- Copy Blob
- Abort Copy Blob
- Delete Blob
- Put Block List
- Get Block List

Operations on the Account (Blob Service)

- List Containers
- Set Blob Service Properties
- Get Blob Service Properties
- Preflight Blob Request
- Get Blob Service Stats

Operations on Containers

- Create Container
- Get Container Properties
- Get Container Metadata
- Set Container Metadata
- Get Container ACL
- Set Container ACL
- Delete Container
- Lease Container
- List Blobs

###3 Conclusion
both licenses, MIT and apache 2.0 are friendly for using, so the most import is the
support API, as shown above, it's obviously Azure python SDK is better than Libcloud.
I propose to use Azure python SDK.

###4 More Info, about "classic" type resources
As you may see above, Azure has "classic" and "non-classic" type management api to respectively
manage classic type resources and non-classic type resources. Here the "classic" means "legacy",
the old type of resources. So we'd better use non-classic resource.