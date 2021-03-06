#!/bin/env python
#-*- coding:utf-8 -*-
# fork from: https://github.com/iambocai/falcon-monit-scripts
__author__ = 'iambocai'

import json
import time
import socket
import os
import re
import sys
import commands
import urllib2, base64

class RedisStats:
    # 如果你是自己编译部署到redis，请将下面的值替换为你到redis-cli路径
    _redis_cli = '/bin/redis-cli'
    _stat_regex = re.compile(ur'(\w+):([0-9]+\.?[0-9]*)\r')

    def __init__(self,  port='6379', passwd=None, host='127.0.0.1'):
        self._cmd = '%s -h %s -p %s info' % (self._redis_cli, host, port)
        if passwd not in ['', None]:
            self._cmd = '%s -h %s -p %s -a %s info' % (self._redis_cli, host, port, passwd)

    def stats(self):
        ' Return a dict containing redis stats '
        info = commands.getoutput(self._cmd)
        return dict(self._stat_regex.findall(info))


def main():
    # ip = socket.gethostname()
    ip = commands.getoutput('''ifconfig `route|grep '^default'|awk '{print $NF}'`|grep inet|awk '{print $2}'|head -n 1''').strip()
    timestamp = int(time.time())
    step = int(os.path.basename(sys.argv[0]).split("_", 1)[0])
    # inst_list中保存了redis配置文件列表，程序将从这些配置中读取port和password，建议使用动态发现的方法获得，如：
    # inst_list = [ i for i in commands.getoutput("find  /etc/ -name 'redis*.conf'" ).split('\n') ]
    insts_list = [ '/etc/redis.conf' ]
    p = []

    monit_keys = [
        ('connected_clients','GAUGE'),
        ('blocked_clients','GAUGE'),
        ('used_memory','GAUGE'),
        ('used_memory_rss','GAUGE'),
        ('mem_fragmentation_ratio','GAUGE'),
        ('total_commands_processed','COUNTER'),
        ('rejected_connections','COUNTER'),
        ('expired_keys','COUNTER'),
        ('evicted_keys','COUNTER'),
        ('keyspace_hits','COUNTER'),
        ('keyspace_misses','COUNTER'),
        ('keyspace_hit_ratio','GAUGE'),
    ]

    for inst in insts_list:
        port = commands.getoutput("sed -n 's/^port *\([0-9]\{4,5\}\)/\\1/p' %s" % inst)
        passwd = commands.getoutput("sed -n 's/^requirepass *\([^ ]*\)/\\1/p' %s" % inst)
        endpoint = ip
        tags = 'port=%s' % port

        try:
            conn = RedisStats(port, passwd)
            stats = conn.stats()
        except Exception,e:
            continue

        for key,vtype in monit_keys:
            #一些老版本的redis中info输出的信息很少，如果缺少一些我们需要采集的key就跳过
            if key not in stats.keys():
                continue
            #计算命中率
            if key == 'keyspace_hit_ratio':
                try:
                    value = float(stats['keyspace_hits'])/(int(stats['keyspace_hits']) + int(stats['keyspace_misses']))
                except ZeroDivisionError:
                    value = 0
            #碎片率是浮点数
            elif key == 'mem_fragmentation_ratio':
                value = float(stats[key])
            else:
                #其他的都采集成counter，int
                try:
                    value = int(stats[key])
                except:
                    continue

            i = {
                'metric': 'redis.%s' % key,
                'endpoint': endpoint,
                'timestamp': timestamp,
                'step': step,
                'value': value,
                'counterType': vtype,
                'tags': tags
            }
            p.append(i)


    print json.dumps(p, sort_keys=True,indent=4)


if __name__ == '__main__':
    sys.stdout.flush()
    main()
    sys.stdout.flush()

