#!/bin/bash

# 生成自签名SSL证书
# 用于开发环境，生产环境请使用正式的SSL证书

# 创建私钥
openssl genrsa -out server.key 2048

# 创建证书签名请求
openssl req -new -key server.key -out server.csr -subj "/C=CN/ST=Beijing/L=Beijing/O=CommercialRealEstate/OU=IT/CN=localhost"

# 创建自签名证书
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

# 清理临时文件
rm server.csr

echo "SSL证书生成完成！"
echo "server.key - 私钥文件"
echo "server.crt - 证书文件"
