import os


# function to decode the buffer
def decode_buffer(buffer):
    enc_type = ['utf-8', 'utf-16', 'ascii', 'ISO-8859-1']
    for enc in enc_type:
        try:
            buffer = buffer.decode(encoding=enc, errors='strict')
            return buffer
        except UnicodeDecodeError:
            continue
    raise Exception('[!!] Encode buffer failed!!!')


# function to get configuration from file
def get_conf(file_conf):
    from json import load
    with open(file_conf) as file:
        return load(file)


# get cert and key path and return if already exists
def fake_certificate_exists(host):
    fake_dir = "conf/key/fake-gen"
    if not os.path.exists(fake_dir):
        os.makedirs(fake_dir)

    cert_path = "%s/%s.crt" % (fake_dir, host)
    key_path = "%s/%s.key" % (fake_dir, host)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True   # , (cert_path, key_path)
    return False    # , (cert_path, key_path)


# function to check if bypass the error
def bypass_error(e: Exception):
    # no bypass error if not have arguments
    if len(e.args) < 1:
        return False

    # bypass timeout exceptions, fail too many time, and port not found
    if e.args[0] == 'timed out' or \
            e.args[0] == 'The read operation timed out' or \
            e.args[0] == 'Wait fake SSL server fail too many time' or \
            e.args[0] == 'Free port for fake SSL server not found':
        return True

    # bypass ssl exceptions
    if len(e.args) >= 2 and (e.args[1] == '[SSL: SSLV3_ALERT_BAD_CERTIFICATE] sslv3 alert bad certificate '
                                          '(_ssl.c:1076)' or
                             e.args[1] == '[SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca (_ssl.c:1076)' or
                             e.args[1] == '[SSL: HTTPS_PROXY_REQUEST] https proxy request (_ssl.c:1076)' or
                             e.args[1] == '[SSL: HTTP_REQUEST] http request (_ssl.c:1076)'):
        return True

    return False
