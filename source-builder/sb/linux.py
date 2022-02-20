#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2012 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

#
# This code is based on what ever doco about spec files I could find and
# RTEMS project's spec files.
#

import multiprocessing
import platform
import pprint
import os

from . import path

def load():
    uname = os.uname()
    if uname[4].startswith('arm'):
        cpu = 'arm'
    else:
        cpu = uname[4]

    version = uname[2]
    defines = {
        '_ncpus':           ('none',    'none',     str(multiprocessing.cpu_count())),
        '_os':              ('none',    'none',     'linux'),
        '_host':            ('triplet', 'required', cpu + '-linux-gnu'),
        '_host_vendor':     ('none',    'none',     'gnu'),
        '_host_os':         ('none',    'none',     'linux'),
        '_host_os_version': ('none',    'none',     version),
        '_host_cpu':        ('none',    'none',     cpu),
        '_host_alias':      ('none',    'none',     '%{nil}'),
        '_host_arch':       ('none',    'none',     cpu),
        '_usr':             ('dir',     'required', '/usr'),
        '_var':             ('dir',     'required', '/var'),
        '_prefix':          ('dir',     'optional', '/opt'),
        '__bzip2':          ('exe',     'required', '/bin/bzip2'),
        '__gzip':           ('exe',     'required', '/bin/gzip'),
        '__tar':            ('exe',     'required', '/bin/tar')
        }

    # platform.dist() was removed in Python 3.8
    if hasattr(platform, 'dist'):
        # Works for LSB distros
        try:
            distro = platform.dist()[0]
            distro_ver = float(platform.dist()[1])
        except ValueError:
         # Non LSB distro found, use failover"
         pass
    else:
         distro = ''

    # Non LSB - fail over to issue
    if distro == '':
        try:
            issue = open('/etc/issue').read()
            distro = issue.split(' ')[0]
            distro_ver = float(issue.split(' ')[2])
        except:
            pass

    distro = distro.lower()

    # Manage distro aliases
    if distro in ['centos']:
        distro = 'redhat'
    elif distro in ['fedora']:
        if distro_ver < 17:
            distro = 'redhat'
    elif distro in ['ubuntu', 'mx', 'linuxmint']:
        distro = 'debian'

    variations = {
        'debian' : { '__bzip2':        ('exe',     'required', '/bin/bzip2'),
                     '__chgrp':        ('exe',     'required', '/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/bin/chown'),
                     '__grep':         ('exe',     'required', '/bin/grep'),
                     '__sed':          ('exe',     'required', '/bin/sed') },
        'redhat' : { '__bzip2':        ('exe',     'required', '/bin/bzip2'),
                     '__chgrp':        ('exe',     'required', '/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/bin/chown'),
                     '__install_info': ('exe',     'required', '/sbin/install-info'),
                     '__grep':         ('exe',     'required', '/bin/grep'),
                     '__sed':          ('exe',     'required', '/bin/sed'),
                     '__touch':        ('exe',     'required', '/bin/touch') },
        'fedora' : { '__chown':        ('exe',     'required', '/usr/bin/chown'),
                     '__install_info': ('exe',     'required', '/usr/sbin/install-info') },
        'arch'   : { '__gzip':         ('exe',     'required', '/usr/bin/gzip'),
                     '__chown':        ('exe',     'required', '/usr/bin/chown') },
        'suse'   : { '__chgrp':        ('exe',     'required', '/usr/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/usr/sbin/chown') },
        'gentoo' : { '__bzip2':        ('exe',     'required', '/bin/bzip2'),
                     '__chgrp':        ('exe',     'required', '/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/bin/chown'),
                     '__gzip':         ('exe',     'required', '/bin/gzip'),
                     '__grep':         ('exe',     'required', '/bin/grep'),
                     '__sed':          ('exe',     'required', '/bin/sed') },
        }

    if distro in variations:
        for v in variations[distro]:
            if path.exists(variations[distro][v][2]):
                defines[v] = variations[distro][v]

    defines['_build']        = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os']     = defines['_host_os']
    defines['_build_cpu']    = defines['_host_cpu']
    defines['_build_alias']  = defines['_host_alias']
    defines['_build_arch']   = defines['_host_arch']

    return defines

if __name__ == '__main__':
    pprint.pprint(load())
