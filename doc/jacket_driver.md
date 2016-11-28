### Jacket Nova API
####说明
所有虚拟机创建在同一个resource group下面，暂定名为ops_resource_group, 包括后面的voluem也是这个resource group下，操作系统磁盘azure自动放在名为vhds的storage container里，网络和子网提前创建好，填写好flavor、image的映射。
linux: boot from instance snapshot can't set adminpass and key. keys were keep from snapshot, password was erased.
windows boot from instance snapshot scenario unknown.
快照：通过VM创建镜像，删除镜像时，调用的原生glance接口，未能在azure上及时删除.每次创建快照时，都做一次残余快照清理。

映射：
Instance:  
Openstack instance: {'uuid': '21b87391-a91e-4ad0-8bac-855271af61fd', 'name': 'azure13'}  
Azure instance: {'name': '21b87391-a91e-4ad0-8bac-855271af61fd'}, os_disk {'name': '21b87391-a91e-4ad0-8bac-855271af61fd.vhd'}, interface {'name': '21b87391-a91e-4ad0-8bac-855271af61fd'}

|Category|API|Azure
|:--|:--|:--
|API versions|List API versions|compute driver管理不了,发行软件时指定
|Limits|List limits|compute driver管理不了,查询DB
|Extensions|List extensions|compute driver管理不了,查询DB."Extensions are a deprecated concept in Nova."
||Get extension|compute driver管理不了,查询DB
|Servers|List servers|compute driver管理不了,查询DB
||Create server|Azure api: Create or update a VM  实现细节: 创建VM过程如下:  1 flavor: 在openstack外创建azure有而原来openstack没有的flavor, 然后在配置文件里写入openstack flavor与azure的映射关系.azure的hardware profile的vm_size,比如"Standard_DS1".  2 image: 镜像两边分别有各自的,然后在配置文件里配置对应关系,创建时用户选用openstack这边的image id,实际创建时通过映射关系找到azure上对应的ID.如果是通过VM创建的image,通过查看image.properties.azure_type确定,就会选择从azure上对应磁盘做为镜像来源启动.update "os_type" of instance according to image.properties.azure_os_type if boot from user made image, or according to image-offer type in azure image market place.   3 boot from volume: 只能使用azure上有的volume,然后创建VM时直接指定这个VHD作为系统盘.  4 keypair: 把相应的keypair的公钥传入到新创建VM.  5 password: 支持创建时指定管理员密码, azure对应位置:os_profile'里面的'admin_password'，关于后续更改系统密码，要通过azure extension来实现，就是通过一些azure官方提供的代理，执行更改密码操作，理论可行.  6 network: 在配置文件里配置好有几个网络,几个子网,创建VM时指定, azure对应位置'network_profile':'network_interfaces':'id'.  7 security group: 创建VM的网卡时,指定哪个网络安全组(Network Security Group (NSG))作用在VM的网卡上,需要提前在azure上创建与openstack安全组对应的NSG.
||List details for servers|compute driver管理不了,查询DB
||Get server details|compute driver管理不了,查询DB
||Update server|compute driver管理不了,更新DB记录
||Delete server|Azure api: Delete a VM  实现细节: azure接口文档没说明删除VM后,跟VM相关的资源是否删除,如果没删除,那按照openstack的做法,对网络接口,系统磁盘进行删除操作.
|Server metadata|Show server metadata|compute driver管理不了,查询DB
||Create or replace server metadata items|compute driver管理不了,查询DB
||Update server metadata items|compute driver管理不了,更新DB
||Show server metadata item details|compute driver管理不了,查询DB
||Create or update server metadata item|compute driver管理不了,更新DB
||Delete server metadata item|compute driver管理不了,更新DB
|Server addresses|List addresses|compute driver管理不了,查询DB
||List addresses by network|compute driver管理不了,查询DB
|Server actions|Change password|Azure api: Create or update a VM  实现细节: 有密码复杂度要求,实现时查看azure文档做检查,复杂度不通过返回错误提示.要通过azure extension来实现，就是通过一些azure官方提供的代理，执行更改密码操作，理论可行
||Reboot server|Azure api: Restart a VM  实现细节: 无
||Rebuild server|Azure api: Redploy 实现细节: 冷迁移到另外的宿主机上，但重新部署不能改变系统镜像。
||Resize server|Azure api: Create or update a VM  实现细节: 选择新的flaovor后,通过这个接口对VM配置进行更新,azure的更新VM接口会要求重启VM.
||Confirm resized server|实现空操作接口即可
||Revert resized server|不支持
||Create image|Azure api: Capture instance 实现细节：复制操作系统磁盘,Openstack会生成一个image记录,然后更新image里面的properties,带上{"azure_type": "azure", "azure_uri": "snapshot-(snapshot.uuid).vhd", "azure_of_type": instance.os_type},将来创建VM时,选择了这个image,可以通过这个参数判断是否为这里生成的snapshot时对应的image,并且可以通过这个URI做为系统盘的来源.跟volume一样,存放在"snapshots"这个storage container里.
|Flavors|List flavors|compute driver管理不了,查询DB
||List details for flavors|compute driver管理不了,查询DB
||Get flavor details|compute driver管理不了,查询DB
|Images|List images|compute driver管理不了,调用glance接口
||List images details|compute driver管理不了,调用glance接口
||Get image details|compute driver管理不了,调用glance接口
||Delete image|compute driver管理不了,调用glance接口
|Image metadata|Show image metadata|compute driver管理不了,调用glance接口
||Create or replace image metadata|compute driver管理不了,调用glance接口
||Update image metadata items|compute driver管理不了,调用glance接口
||Show image metadata item details|compute driver管理不了,调用glance接口
||Create or update image metadata item|compute driver管理不了,调用glance接口
||Delete image metadata item|compute driver管理不了,调用glance接口
|Servers with block device mapping format (servers)|List servers|不明白对应哪个NOVA API接口
||Create server|不明白对应哪个NOVA API接口
|Servers with configuration drive (servers)|Create server with configuration drive|不明白对应哪个NOVA API接口
||Get server information with configuration drive|不明白对应哪个NOVA API接口
||Get server details with configuration drive|不明白对应哪个NOVA API接口
|Servers console (servers)|Get console|azure API不支持
|Servers console output (servers)|Get console output for an instance|azure支持创建VM时,指定storage account的uri,会把启动时的console输出/屏幕截图存储.
|Servers extended attributes (servers)|List servers with extended server attributes|compute driver管理不了,查询DB
||Show extended server attributes|compute driver管理不了,查询DB
|Servers with extended availability zones (servers)|Show server|compute driver管理不了,查询DB
||List details for servers|compute driver管理不了,查询DB
|Servers extended status (servers)|Show server extended status|compute driver管理不了,查询DB
||List extended status for servers|compute driver管理不了,查询DB
|Servers with IP type (servers)|Show IP type|不明白对应哪个NOVA API接口
||List servers with IP type|不明白对应哪个NOVA API接口
|Servers multiple create (servers)|Create multiple servers|Azure api: Create or update a VM  实现细节: 多次创建VM,检查要创建VM的指定资源是否是唯一的,比如指定某个IP,某个磁盘等,是不允许的.
|Servers deferred delete (servers, action)|Force delete server|Azure api: Delete a VM  实现细节: azure的删除本身就是强制的.
||Restore server|Azure api: Stop and deallocate a virtual machine和Start a VM  实现细节: azure支持不占用计算资源的关机,不收费,需要时可以恢复使用.但这些资源要有机制进行定期回收,不然会变成垃圾资源.但soft-delete接口已经不存在了,没意义.
|Servers rescue and unrescue (servers, action)|Rescue server|不支持
||Unrescue server|不支持
|Servers shelve (servers, action)|Shelve server|不支持,它也会涉及到镜像创建,实现不了.
||Remove a shelved instance|不支持
||Restore shelved server|不支持
|Servers start and stop (servers, action)|Start server|Azure api: Start a VM  实现细节: 通过映射关系,找到azure上的VM,执行开机操作.
||Stop server|Azure api: Stop a VM  实现细节: 通过映射关系,找到azure上的VM,执行关闭操作.
|Servers diagnostics (servers, diagnostics)|Get server diagnostics|azure支持创建VM时,指定storage account的uri,会把启动时的console输出/屏幕截图存储,把这个uri存储在VM属性里面.
|Servers and images with disk config (servers, images)|Create server|不明白对应哪个NOVA API接口
||Show server information|不明白对应哪个NOVA API接口
||Update server|不明白对应哪个NOVA API接口
||Resize server|不明白对应哪个NOVA API接口
||Rebuild server|不明白对应哪个NOVA API接口
||List servers|不明白对应哪个NOVA API接口
||Get image information|不明白对应哪个NOVA API接口
||List images|不明白对应哪个NOVA API接口
|Servers availability zones (servers, os-availability-zone)|Create server with availability zone|不支持
||List availability zones|不支持
||List availability zones with details|不支持
||Show availability zone information|不支持
|Servers password (servers, os-server-password)|Get server password|compute driver管理不了,查询DB
||Clear server password|compute driver管理不了,更新DB操作,这个接口在API层面已经定义了只更新vm的metadata,不会真正对VM进行清除密码操作.
|Servers virtual interfaces (servers, os-virtual-interfaces)|List virtual interfaces|compute driver管理不了,查询DB
||Show virtual interface and attached network|不明白对应哪个NOVA API接口
|Servers with volume attachments (servers, os-volume_attachments)|Attach volume|Azure api: Create or update a VM  实现细节: 更新VM信息时带上要挂载的volume的blob uri.'data_disk'.需要提前创建好.
||List volume attachments|compute driver管理不了,查询DB
||Show volume attachment details|compute driver管理不了,查询DB
||Detach volume|Azure api:  Create or update a VM  实现细节: 更新VM信息时减少要卸载的volume的blob uri.'data_disk'.
|Server boot from volume (os-volumes_boot)|Create server|Azure api: Create or update a VM  实现细节: 与普通创建VM基本相同,除了下面这点  - boot from volume: 只能使用azure上有的volume,然后创建VM时直接指定这个VHD作为系统盘.但按照目前思路,这个操作的volume没有来源,依赖没解决.
|Flavors create and delete (flavors)|Create flavor|compute driver管理不了
||Delete flavor|compute driver管理不了
|Flavors with disabled attribute (flavors)|Get flavor disabled status details|compute driver管理不了
||List flavors with flavor disabled status|compute driver管理不了
|Flavors with extended attributes (flavors)|Create flavor with extra data|compute driver管理不了
||Get flavor extra data details|compute driver管理不了
||List flavors with extra data|compute driver管理不了
|Flavors with rxtx_factor extended attribute (flavors)|Create flavor with rxtx_factor|compute driver管理不了
||Get flavor with rxtx_factor|compute driver管理不了
||Get flavor Details with rxtx_factor|compute driver管理不了
|Flavors with extra-specs (flavors, os-extra-specs)|List flavor extra specs|compute driver管理不了
||Create flavor extra specs|compute driver管理不了
||Get flavor extra spec details|compute driver管理不了
||Update flavor extra specs|compute driver管理不了
||Delete flavor extra specs|compute driver管理不了
|Flavors access (flavors, os-flavor-access)|List flavors with access type|compute driver管理不了
||Create private flavor|compute driver管理不了
||Show flavor access type|compute driver管理不了
||List tenants with access to private flavor|compute driver管理不了
||Add access to private flavor|compute driver管理不了
||Delete access from private flavor|compute driver管理不了
|Flavors swap (flavors, os-flavor-swap)|List flavor extra specs|compute driver管理不了
||Create flavor extra specs|compute driver管理不了
|Limits with project usage (limits)|Get limits|compute driver管理不了,但可以查看azure里面的limit,进行配置.
|Limits with project usage for administrators (limits)|Get customer limits|compute driver管理不了,但可以查看azure里面的limit,进行配置.
|Attach interfaces (os-interface)|Create interface|实现不了,因为这个过程会调用网络APIself.network_api.deallocate_port_for_instance,如果网络没对接azure,实现不了.  Azure api: Create or update a VM  实现细节: 更新VM信息时增加某个网络接口的信息.'network_profile':'network_interfaces':'id',需要提前创建好.
||List interfaces|实现不了,因为这个过程会调用网络API,如果网络没对接azure,实现不了.
||Show attached interface information|实现不了,因为这个过程会调用网络APIself.network_api.deallocate_port_for_instance,如果网络没对接azure,实现不了.
||Detach interface|实现不了,因为这个过程会调用网络APIself.network_api.deallocate_port_for_instance,如果网络没对接azure,实现不了.
|Keypairs (os-keypairs)|List keypairs|compute driver管理不了,查询DB
||Create or import keypair|compute driver管理不了,更新DB操作
||Delete keypair||compute driver管理不了,更新DB操作
||Show keypair information|compute driver管理不了,查询DB
|Quota class (os-quota-class-sets)|Show quota|compute driver管理不了,查询DB,但可以查看azure里面的limit,进行配置,以下几条相同.
||Update quota|compute driver管理不了,更新DB操作
|Quota sets (os-quota-sets)|Show quotas|compute driver管理不了,查询DB
||Update quotas|compute driver管理不了,更新DB操作
||Delete quotas|compute driver管理不了,更新DB操作
||Get default quotas|compute driver管理不了,查询DB
||Show quotas for user|compute driver管理不了,查询DB
||Update quotas for user|compute driver管理不了,更新DB操作
||Delete quotas for user|compute driver管理不了,更新DB操作
||Show quota details for user|compute driver管理不了,更新DB操作
|Usage reports (os-simple-tenant-usage)|List usage information for all tenants|compute driver管理不了,查询DB
||Get tenant usage information|同上
|Servers administrative actions (servers, action)|Pause server|azure不支持
||Unpause server|azure不支持
||Suspend server|azure不支持
||Resume server|azure不支持
||Inject network information|实现不了,因为这个过程会调用网络API:self.network_api.get_instance_nw_info ,如果网络没对接azure,实现不了.
||Lock server|azure不支持
||Unlock server|azure不支持
||Create server backup|无法实现.与create image一样,会涉及image操作,依赖没实现.
||Reset server state|compute driver管理不了更新DB操作
||Add floating IP address|实现不了,因为这个过程会调用网络API:self.network_api.allocate_floating_ip和self.network_api.get_floating_ip_by_address,如果网络没对接azure,实现不了.

### Nova Driver Periodic Task Interface
|Interface for|Interface|Azure
|:--|:--|:--
_check_instance_build_time||更新DB记录,驱动处不用实现
_sync_scheduler_instance_info||驱动处不用实现
_heal_instance_info_cache||驱动处不用实现
_poll_rebooting_instances|resume_state_on_host_boot|空操作即可
_poll_rescued_instances|unrescue|不支持
_poll_unconfirmed_resizes||驱动处不用实现
_poll_shelved_instances|destroy|已实现
_instance_usage_audit||驱动处不用实现
_poll_bandwidth_usage||不支持
_poll_volume_usage||不支持
_sync_power_states|get_num_instances, get_info|都已实现
_reclaim_queued_deletes|destroy|已实现
update_available_resource|get_available_nodes, get_available_resource|都已实现
_cleanup_running_deleted_instances|destroy, set_bootable|已实现, 不支持锁定
_run_image_cache_manager_pass||不支持
_run_pending_deletes|delete_instance_files|已实现,_cleanup_instance
_cleanup_incomplete_migrations||不支持migration


### Jacket Cinder API
####说明
OpenStack里面的volume对应azure里面是Storage里面的Page Blog,包括创建VM时指定的操作系统盘,额外挂载的数据盘,存储镜像,从VM导出的镜像,快照都是它.
在名为ops_resource_group的resource group 下面创建名为ops0storage0account的storage account, 用0分隔单词是因为它只接受字母与数据。创建名为volume的storage container,
所有volume数额资源放在里，包括snapshot,backup等。另外名为vhds的storage container是虚拟机系统磁盘存放位置。

- 容量是512B倍数.但由于VM最小接受磁盘容量是1GB,所以这里也建议最小可创建容量为1GB(是站在虚拟机操作系统里看到的大小，blog应该是1GB+512Byte).
- VM挂载磁盘必须是以vhd结尾的page blob,而且是标准的VHD格式文件.
- VHD格式在文件最后512字节是格式内容，创建空page blob时把最后512字节按VHD格式要求写入内容。
- 从volume/snapshot创建volume，只能是以原来的大小创建，因为对应在azure是一个vhd文件，改变其大小而不丢数据，大问题。
- 一个VM只能挂载一块额外数据盘.在操作系统里面看到设备号,至少是第三块设备,因为azure会在创建VM时,除了系统磁盘外,还会挂载一块临时磁盘,官方文档明确不要写数据到临时磁盘.

映射关系：  
Volume:  
Openstack: volume:{'display_name':'testvolume', 'id': '17d95073-1ab7-4906-9518-6e09312f1655', 'name': 'volume-17d95073-1ab7-4906-9518-6e09312f1655'}  
Azure: page blob:{'name': 'volume-17d95073-1ab7-4906-9518-6e09312f1655.vhd'}

Snapshot:  
Openstack: snapshot:{'volume': Volume(), 'metadata': {'azure_snapshot_id': "2016-11-09T14:11:07.6175300Z"}} 其中metadata信息是创建快照后在驱动实现方法处更新snapshot数据库记录。  
Azure: page blog:{'name': 'volume-17d95073-1ab7-4906-9518-6e09312f1655.vhd', 'snapshot': '2016-11-09T14:11:07.6175300Z'}  

另外关于backup,实现不了,因为现在backup的处理逻辑,没有像volume那样和驱动解藕,它的backup:manager.py里面做了很多固定操作,对于所有备份,
它都会按照把volume/snapshot在volume节点上准备好,被做备份的节点/服务来连接进行复制.如果要实现,就不只是在驱动层面实现了.对于azure,从卷生成新卷就是
最实际的备份方法.

|Category|API|Azure
|:--|:--|:--
|API versions|List API versions|volume driver管理不了,发行软件时指定
||Show API version details|volume driver管理不了,发行软件时指定
|API extensions (extensions)|List API extensions|volume driver管理不了,查询DB
|Limits (limits)|Show absolute limits|volume driver管理不了,查询DB,但可以查看azure里面的limit,进行配置.
|Volumes (volumes)|Create volume|Azure api: Copy Blob 实现细节：创建容量为size_Byte + 512 Byte的page blog,然后更新它的最后512字节为VHD格式内容。
||List volumes||volume driver管理不了,查询DB
||List volumes (detailed)|volume driver管理不了,查询DB
||Show volume information|volume driver管理不了,查询DB
||Update volume|volume driver管理不了,更新DB操作
||Delete volume|Azure api: Put Page  实现细节: 通过映射关系,找到azure上某个快照的blob,执行删除操作.
|Volume actions (volumes, action)|Reset volume statuses|volume driver管理不了,更新DB操作
||Set image metadata for volume|volume driver管理不了,更新DB操作:self.db.volume_metadata_update
||Remove image metadata from volume|volume driver管理不了,更新DB操作:self.db.volume_metadata_delete
||Attach volume|Azure api: Create or update a VM  实现细节: 更新VM信息时带上要挂载的volume的blob uri.'data_disk'。
|Backups (backups)|Create backup|Azure api: Copy Blob  实现细节:只在驱动层面实现不了,详细看开头说明.
||List backups|volume driver管理不了,查询DB
||List backups (detailed)|volume driver管理不了,查询DB
||Show backup details|volume driver管理不了,查询DB
||Delete backup|只在驱动层面实现不了,详细看开头说明.
||Restore backup|只在驱动层面实现不了,详细看开头说明.
|Backup actions (backups, action)|Force-delete backup|只在驱动层面实现不了,详细看开头说明.
|Quota sets extension (os-quota-sets)|Show quotas|volume driver管理不了,查询DB
||Update quotas|volume driver管理不了,更新DB
||Delete quotas|volume driver管理不了,更新DB
||Get default quotas|volume driver管理不了,查询DB
||Show quotas for user|volume driver管理不了,查询DB
||Update quotas for user|volume driver管理不了,更新DB
||Delete quotas for user|volume driver管理不了,更新DB
||Show quota details for user|volume driver管理不了,查询DB
|Volume types (types)|List volume types|volume driver管理不了,查询DB
||Create volume type|volume driver管理不了,更新DB
||Update volume type|volume driver管理不了,更新DB
||Update extra specs for a volume type|volume driver管理不了,更新DB
||Show volume type information|volume driver管理不了,查询DB
||Delete volume type|volume driver管理不了,更新DB
|Volume snapshots (snapshots)|Create snapshot|Azure api: Snapshot Blob  实现细节: 在azure上创建快照
||List snapshots|volume driver管理不了,查询DB
||List snapshots (detailed)|volume driver管理不了,查询DB
||Show snapshot information|volume driver管理不了,查询DB
||Update snapshot|volume driver管理不了,更新DB
||Delete snapshot|Azure api: Put Page  实现细节: 跟删除卷一样处理.通过映射关系,找到azure上某个快照的blob,执行删除操作.
||Show snapshot metadata|volume driver管理不了,查询DB
||Update snapshot metadata|volume driver管理不了,更新DB
|Volume image metadata extension (os-vol-image-meta)|Show image metadata for volume|volume driver管理不了,查询DB

###僵尸资源清理
#### 1 虚拟机操作系统磁盘
通常逻辑：创建虚拟机时，操作系统磁盘是跟随虚拟机一同创建，如果虚拟机创建失败，用户进行虚拟机删除操作，对磁盘进行删除。
异常逻辑：删除磁盘blog操作是同步操作，如果删除失败，则manager会收到异常，不会造成僵尸磁盘。但为了azure绝对干净，定期对所有磁盘进行检查，如果是没连接到虚拟机的都进行删除操作。

#### 2 虚拟机网卡
通常逻辑：创建虚拟机时，先创建网卡，虚拟机创建操作是异常操作，所以无论虚拟机创建是否成功，网卡都已经创建好，这里无法做到及时删除。但用户进行虚拟机删除操作，对网卡进行删除。
异常逻辑：定期对网卡进行检查，如果没有连接到虚拟机机都进行删除操作。

#### 3 snapshot 虚拟机快照，实际在openstack处是image
通常逻辑：直接进行删除操作，只在glance服务处删除，无法删除azure处的snapshot blob.现在思路是每次创建虚拟机快照时进行检查删除僵尸快照，因为要调用glance接口，需要context，无法在定期任务执行此操作。
异常逻辑：暂时没想到怎样将它放到定期任务执行。
