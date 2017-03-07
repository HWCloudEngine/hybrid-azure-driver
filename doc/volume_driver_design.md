####说明
OpenStack里面的volume对应azure里面是Storage里面的Page Blog,包括创建VM时指定的操作系统盘,额外挂载的数据盘,存储镜像,从VM导出的镜像,快照都是它.

####1 do_setup
Azure api: 无    
实现细节: 不用实现.

####2 check_for_setup_error
Azure api: List Containers, List Blobs    
实现细节: 服务启动时执行上面两个调用操作,看配置是否正常,能与azure通信.

####3 create_volume
Azure api: Managed Disk里面的disk create_or_update, 创建空disk   
实现细节: 指定大小,create_option=empty

####4 create_volume_from_snapshot
Azure api: Managed Disk里面的disk create_or_update, 从快照创建disk   
实现细节: 指定源ID, create_option=copy

####5 create_cloned_volume
Azure api: Managed Disk里面的disk create_or_update, 从现有disk创建disk   
实现细节: 指定源ID, create_option=copy

####6 extend_volume
Azure api: Managed Disk里面的disk create_or_update 
实现细节: 提供扩容后的大小,更新

####7 delete_volume
Azure api: Managed Disk里面的disk delete 
实现细节: 通过映射关系,执行删除操作.

####8 create_snapshot
Azure api: Managed Disk里面的snapshot create_or_update, 从现有disk创建disk   
实现细节: 指定源ID, create_option=copy

####9 delete_snapshot
Azure api: Managed Disk里面的snapshot delete 
实现细节: 通过映射关系,执行删除操作.

####10 get_volume_stats
Azure api:  无
实现细节: managed disk资源没有限制容量

####11 create_export
Azure api:  无  
实现细节: 按设计不用实现

####12 ensure_export
Azure api: 无  
实现细节: 按设计不用实现

####13 remove_export
Azure api: 无  
实现细节: 按设计不用实现

####14 initialize_connection
Azure api: 无    
实现细节: 无须在azure上操作,返回原先存储在volume对象上的信息.

####15 terminate_connection
Azure api: 无  
实现细节: 按设计不用实现

####16 copy_volume_to_image(待定)
Azure api: Managed Disk里面的image create_or_update,
实现细节: 指定源ID, create_option=copy


####17 copy_image_to_volume
Azure api: 无
实现细节: 全部放到clone_image实现,不用到这一步实现

####18 validate_connector
Azure api:  无  
实现细节: 检查配置文件读取的azure storage认证连接信息是否正常.

####19 clone_image(待定)
Azure api: Managed Disk里面的disk create_or_update,
实现细节: 指定源ID, create_option=copy

####20 retype
Azure api: Managed Disk里面的disk create_or_update,
实现细节: 指定新的类型(对应是hdd, ssd)

####21 back
Azure api: Managed Disk里面的snapshot create_or_update,
实现细节: 指定源ID, create_option=copy

####22 restore
Azure api: Managed Disk里面的disk create_or_update,
实现细节: 指定源ID, create_option=copy, 由于不能复制到已有的disk,所以
先对当前卷打快照(为了恢复失败可以回滚),然后删除当前卷,再从备份生成卷.

####23 delete_backup
Azure api: Managed Disk里面的snapshot delete 
实现细节: 通过映射关系,执行删除操作.
