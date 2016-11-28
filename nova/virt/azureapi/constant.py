IMAGE_MAPPING = {
    'cirros-0.3.4-x86_64-uec': {
        'publisher': 'Canonical',
        'offer': 'UbuntuServer',
        'sku': '16.04.0-LTS',
        'version': 'latest'
    },
    '1e850173-ac9d-4c0a-82a6-6b197c466319': {
        'publisher': 'Canonical',
        'offer': 'UbuntuServer',
        'sku': '16.04.0-LTS',
        'version': 'latest'
    },
}
"""
flavor in openstack original:
ubuntu@server-1:~/devstack$ openstack flavor show d1
+----+-----------+-------+------+-----------+-------+-----------+
| ID | Name      |   RAM | Disk | Ephemeral | VCPUs | Is Public |
+----+-----------+-------+------+-----------+-------+-----------+
| 1  | m1.tiny   |   512 |    1 |         0 |     1 | True      |
| 2  | m1.small  |  2048 |   20 |         0 |     1 | True      |
| 3  | m1.medium |  4096 |   40 |         0 |     2 | True      |
| 4  | m1.large  |  8192 |   80 |         0 |     4 | True      |
| 42 | m1.nano   |    64 |    0 |         0 |     1 | True      |
| 5  | m1.xlarge | 16384 |  160 |         0 |     8 | True      |
| 84 | m1.micro  |   128 |    0 |         0 |     1 | True      |
| c1 | cirros256 |   256 |    0 |         0 |     1 | True      |
| d1 | ds512M    |   512 |    5 |         0 |     1 | True      |
| d2 | ds1G      |  1024 |   10 |         0 |     1 | True      |
| d3 | ds2G      |  2048 |   10 |         0 |     2 | True      |
| d4 | ds4G      |  4096 |   20 |         0 |     4 | True      |
+----+-----------+-------+------+-----------+-------+-----------+

vm size in azure:
{'name': u'Basic_A0', 'number_of_cores': 1, 'resource_disk_size_in_mb': 20480, 'memory_in_mb': 768, 'max_data_disk_count': 1, 'os_disk_size_in_mb': 1047552}
{'name': u'Basic_A1', 'number_of_cores': 1, 'resource_disk_size_in_mb': 40960, 'memory_in_mb': 1792, 'max_data_disk_count': 2, 'os_disk_size_in_mb': 1047552}
{'name': u'Basic_A2', 'number_of_cores': 2, 'resource_disk_size_in_mb': 61440, 'memory_in_mb': 3584, 'max_data_disk_count': 4, 'os_disk_size_in_mb': 1047552}
{'name': u'Basic_A3', 'number_of_cores': 4, 'resource_disk_size_in_mb': 122880, 'memory_in_mb': 7168, 'max_data_disk_count': 8, 'os_disk_size_in_mb': 1047552}
{'name': u'Basic_A4', 'number_of_cores': 8, 'resource_disk_size_in_mb': 245760, 'memory_in_mb': 14336, 'max_data_disk_count': 16, 'os_disk_size_in_mb': 1047552}

if mapping to other flavor family in azure, need to change "usage_family" in "get_available_resource" method.
"""
FLAVOR_MAPPING = {
    'm1.tiny': 'Basic_A0',
    'm1.small': 'Basic_A1',
    'm1.medium': 'Basic_A2',
    'm1.large': 'Basic_A3',
    'm1.xlarge': 'Basic_A4'
}
