####1 init host
None

####2 list_instances
Azure api: List VMs in a resource group & List VMs in a subscription
TODO: None

####3 get_info
Azure api: Get VM information
TODO: attributes mapping base on nova instance model.

####4 list_instance_uuids
Azure api: list_instances
TODO: instance's id from azure is "the identifying URL of the virtual machine",
      need to convert to uuid type.
      
####5 rebuild
Azure api: None
TODO: None, let instance be destroyed and be spawned with previous infomation.
