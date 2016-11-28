import datetime
import uuid


def generate_vhd_footer(size):
    """Generate vhd footer.

    :param size: size from the perspective of the virtual machine
    :return footer in bytes.
    """
    # Fixed VHD Footer Format Specification
    # spec: https://technet.microsoft.com/en-us/virtualization/bb676673.aspx#E3B
    # Field         Size (bytes)
    # Cookie        8
    # Features      4
    # Version       4
    # Data Offset   8
    # TimeStamp     4
    # Creator App   4
    # Creator Ver   4
    # CreatorHostOS 4
    # Original Size 8
    # Current Size  8
    # Disk Geo      4
    # Disk Type     4
    # Checksum      4
    # Unique ID     16
    # Saved State   1
    # Reserved      427
    # the ascii string 'conectix'
    cookie = bytearray([0x63, 0x6f, 0x6e, 0x65, 0x63, 0x74, 0x69, 0x78])
    # no features enabled
    features = bytearray([0x00, 0x00, 0x00, 0x02])
    # current file version
    version = bytearray([0x00, 0x01, 0x00, 0x00])
    # in the case of a fixed disk, this is set to -1
    data_offset = bytearray([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
    # hex representation of seconds since january 1st 2000
    timestamp = bytearray.fromhex(hex(long(datetime.datetime.now().strftime("%s")) - 946684800).replace('L', '').replace('0x', '').zfill(8))
    # ascii code for 'wa' = windowsazure
    creator_app = bytearray([0x77, 0x61, 0x00, 0x00])
    # ascii code for version of creator application
    creator_version = bytearray([0x00, 0x07, 0x00, 0x00])
    # creator host os. windows or mac, ascii for 'wi2k'
    creator_os = bytearray([0x57, 0x69, 0x32, 0x6b])
    original_size = bytearray.fromhex(hex(size).replace('0x', '').zfill(16))
    current_size = bytearray.fromhex(hex(size).replace('0x', '').zfill(16))
    # ox820=2080 cylenders, 0x10=16 heads, 0x3f=63 sectors/track or cylender,
    disk_geometry = bytearray([0x08, 0x20, 0x10, 0x3f])
    # 0x2 = fixed hard disk
    disk_type = bytearray([0x00, 0x00, 0x00, 0x02])
    # a uuid
    unique_id = bytearray.fromhex(uuid.uuid4().hex)
    # saved state and reserved
    saved_reserved = bytearray(428)
    # Compute Checksum
    # Checksum = ones compliment of sum of all fields excluding checksum field
    to_checksum_array = cookie + features + version + data_offset + timestamp + creator_app + creator_version + creator_os + original_size + current_size + disk_geometry + disk_type + unique_id + saved_reserved

    total = 0
    for b in to_checksum_array:
        total += b

    total = ~total

    # handle two's compliment
    def tohex(val, nbits):
      return hex((val + (1 << nbits)) % (1 << nbits))

    checksum = bytearray.fromhex(tohex(total, 32).replace('0x', ''))

    blob_data = cookie + features + version + data_offset + timestamp + creator_app + creator_version + creator_os + original_size + current_size + disk_geometry + disk_type + checksum + unique_id + saved_reserved

    return bytes(blob_data)
