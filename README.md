# 😈 MITMOXY 😈
HTTP/HTTPS proxy, write in python, to take in action a man-in-the-middle attack. 

### ALERT!!! This project is under development test it and report a [issue](https://github.com/d3v4s/mitmoxy/issues/new)


## Use

To run the proxies, execute:  
`./mitmoxy.py start`

Test it with curl:  
`https_proxy=localhost:8080 http_proxy=localhost:8080 curl https://devas.info --cacert conf/key/ca.crt`
