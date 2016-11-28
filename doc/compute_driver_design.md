####1 init host
Azure api: 无  
实现细节: 不用实现.

####2 volume_snapshot_create
Azure api: Snapshot Blob  
实现细节: 跟volume快照同样处理.

####3 get_available_resource
Azure api: 无  
实现细节: 公有云资源可以视为无限,可以给很大的资源量做为返回.

####4 get_available_nodes
Azure api: 无  
实现细节: 对于azure,返回hypervisor_hostname即可.只有一个计算结点.

####5 get_pci_slots_from_xml
Azure api: 无  
实现细节: 不用实现.

####6 spawn
Azure api: Create or update a VM  
实现细节: 创建VM过程如下:

- flavor: 在openstack外创建azure有而原来openstack没有的flavor, 然后在配置文件里写入openstack flavor与azure的映射关系.azure的hardware profile的vm_size,比如"Standard_DS1".
- image: 镜像两边分别有各自的,然后在配置文件里配置对应关系,创建时用户选用openstack这边的image id,实际创建时通过映射关系找到azure上对应的ID. 
- boot from volume: 只能使用azure上有的volume,然后创建VM时直接指定这个VHD作为系统盘.
- key-name: 把相应的keypair的公钥传入到新创建VM.
- password: 支持创建时指定管理员密码, azure对应位置:os_profile'里面的'admin_password'.
- network: 在配置文件里配置好有几个网络,几个子网,创建VM时指定.这些信息只在azure处有,openstack处没有对应的,有个潜在的问题是GUI处显示VM信息时关于网络的超链接就有问题, azure对应位置'network_profile':'network_interfaces':'id'.
- security group: 创建VM的网卡时,指定哪个网络安全组(Network Security Group (NSG))作用在VM的网卡上.

####7 list_instances
Azure api: List VMs in a resource group 和 List VMs in a subscription  
实现细节: 键值转换.

####8 get_info
Azure api: Get VM information  
实现细节: 键值转换.

####9 list_instance_uuids
Azure api: List VMs in a resource group 和 List VMs in a subscription  
实现细节: 对得到的VM 里面的ID进行映射.

####10 rebuild
Azure api: 不用实现,按接口未实现处理  
实现细节: 接口未实现,接口会自动销毁VM,然后以之前的配置新那一个VM.

####11 resume_state_on_host_boot
Azure api: 无  
实现细节: 不用实现,公有云不存在重启宿主机,如果有,也是公有云提供商要负责重启VM.

####12 attach_volume
Azure api: Create or update a VM  
实现细节: 更新VM信息时带上要挂载的volume的blob uri.'data_disk'.需要提前创建好.

####13 detach_volume
Azure api:  Create or update a VM  
实现细节: 更新VM信息时减少要卸载的volume的blob uri.'data_disk'.

####14 attach_interface
Azure api: Create or update a VM  
实现细节: 更新VM信息时增加某个网络接口的信息.'network_profile':'network_interfaces':'id',需要提前创建好.

####15 detach_interface
Azure api: Create or update a VM  
实现细节: 更新VM信息时减少某个网络接口的信息.'network_profile':'network_interfaces':'id'.

####16 get_volume_connector
Azure api: 无  
实现细节: 无法实现

####17 power_off
Azure api: Stop a VM  
实现细节: 通过映射关系,找到azure上的VM,执行关闭操作.

####18 power_on
Azure api: Start a VM  
实现细节: 通过映射关系,找到azure上的VM,执行开机操作.

####19 get_instance_macs
Azure api:  Get VM information 和 Get information about a network interface card  
实现细节: 先通过Get VM information查询VM信息,找到'network_profile':'network_interfaces'的名称,再通过Get information about a network interface card来查询MAC地址.

####20 reboot
Azure api: Restart a VM  
实现细节: 通过映射关系,找到azure上的VM,执行重启操作.

####21 pause
Azure api: 无  
实现细节: 无法实现,原本接口是让VM进入睡眠状态,VM停止使用CPU,把CPU会话信息保存到内存中,可快速恢复.

####22 unpause
Azure api: 无  
实现细节: 无法实现.

####23 destroy
Azure api: Delete a VM  
实现细节: azure接口文档没说明删除VM后,跟VM相关的资源是否删除,如果没删除,那按照openstack的做法:
 
- 内部网络接口要跟随删除
- 挂载的磁盘是卸载,不删除.
- 公网IP解除绑定,不删除

####24 snapshot
Azure api: Snapshot Blob  
实现细节: 跟volume快照同样处理.