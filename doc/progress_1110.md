###已经实现情况
####Compute:  
创建虚拟机，创建时插入系统用户密码，用户名统一为azureuser.未实现创建完后续更改密码，未实现创建时插入密钥。  
已实现虚拟机操作：power on/off, reboot, rebuild(不能更换镜像), resize, delete, attach(不支持指定系统里面设备号，且单个VM最多两块voluem)/detach volume

####Volume:  
volume create(from volume/snapshot), delete  
snapshot create, delete
