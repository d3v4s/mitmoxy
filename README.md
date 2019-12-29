# 😈 MITMOXY 😈
HTTP/HTTPS proxy, write in python, to take in action a man-in-the-middle attack. 

### ALERT!!! This project is under development test it and report a [issue](https://github.com/d3v4s/mitmoxy/issues/new)


## Install

To install Mitmoxy run `./install.py`.

## Use

To start the proxies, execute:  
`./mitmoxy.py start`

If you have installed mitmoxy, you can start the systemd unit with:  
`systemctl start mitmoxy`

Test it with curl:  
`https_proxy=localhost:8080 http_proxy=localhost:8080 curl https://devas.info --cacert conf/key/ca.crt`
