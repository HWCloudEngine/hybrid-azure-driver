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
