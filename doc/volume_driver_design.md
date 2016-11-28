####说明
OpenStack里面的volume对应azure里面是Storage里面的Page Blog,包括创建VM时指定的操作系统盘,额外挂载的数据盘,存储镜像,从VM导出的镜像,快照都是它.

####1 do_setup
Azure api: 无    
实现细节: 不用实现.

####2 check_for_setup_error
Azure api: List Containers, List Blobs    
实现细节: 服务启动时执行上面两个调用操作,看配置是否正常,能与azure通信.

####3 create_volume
Azure api: Put Page    
实现细节: 指定要创建的卷的大小,512byte的倍数,最大1TB.没有ID,只能通过container_name和blob_name来对卷进行定位.所以要把azure卷信息添加到volume,目前看到可以放到provider_id.

####4 create_volume_from_snapshot
Azure api: Copy Blob    
实现细节: 要把azure blob信息添加到volume,放到provider_id.

####5 create_cloned_volume
AAzure api: Copy Blob  
实现细节: 要把azure blob信息添加到volume,放到provider_id.

####6 extend_volume
Azure api: Put Page  
实现细节: 获得调整后大小,传递给azure更新blob的content_length.

####7 delete_volume
Azure api: Put Page  
实现细节: 通过映射关系,找到azure上某个快照的blob,执行删除操作.

####8 create_snapshot
Azure api: Snapshot Blob  
实现细节: 在azure上创建快照,然后把新创建的快照映射到openstack里面的卷快照,与卷的创建类似.

####9 delete_snapshot
Azure api: Delete Blob  
实现细节: 通过映射关系,找到azure上某个快照的blob,执行删除操作.

####10 get_volume_stats
Azure api:  Get Blob  
实现细节: 通过映射关系,找到azure上的blob,获取详细信息,最后做键值转换.

####11 create_export
Azure api:  无  
实现细节: 无法实现

####12 ensure_export
Azure api: 无  
实现细节: 无法实现

####13 remove_export
Azure api: 无  
实现细节: 无法实现

####14 initialize_connection
Azure api: 无    
实现细节: 无须在azure上操作,返回原先存储在volume对象上的azure blob的信息.

####15 terminate_connection
Azure api: 无  
实现细节: 无法实现

####16 copy_volume_to_image
Azure api: Copy Blob  
实现细节: 由于VHD特殊格式原因,无法把glance里面的image与azure里面的blob对接

####17 copy_image_to_volume
Azure api: Copy Blob  
实现细节: 由于VHD特殊格式原因,无法把glance里面的image与azure里面的blob对接

####18 validate_connector
Azure api:  无  
实现细节: 检查配置文件读取的azure storage认证连接信息是否正常.

####19 clone_image
Azure api: Copy Blob  
实现细节: 本身azure里面的blog 就跟image存储性质一样,是page blob,所以无须作另外工作,参考clone volume.
