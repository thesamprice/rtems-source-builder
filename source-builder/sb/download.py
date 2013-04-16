#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2013 Chris Johns (chrisj@rtems.org)
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
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

import os
import stat
import sys
import urllib2
import urlparse

import error
import git
import log
import path

def _notice(opts, text):
    if not opts.quiet() and not log.default.has_stdout():
        print text
    log.output(text)
    log.flush()

def _output(opts, text):
    if not opts.quiet():
        log.output(text)

def _http_parser(source, config, opts):
    #
    # Is the file compressed ?
    #
    esl = source['ext'].split('.')
    if esl[-1:][0] == 'gz':
        source['compressed'] = '%{__gzip} -dc'
    elif esl[-1:][0] == 'bz2':
        source['compressed'] = '%{__bzip2} -dc'
    elif esl[-1:][0] == 'bz2':
        source['compressed'] = '%{__zip} -u'
    elif esl[-1:][0] == 'xz':
        source['compressed'] = '%{__xz} -dc'

def _git_parser(source, config, opts):
    #
    # Symlink.
    #
    us = source['url'].split('?')
    source['path'] = path.dirname(us[0])
    source['file'] = path.basename(us[0])
    source['name'], source['ext'] = path.splitext(source['file'])
    if len(us) > 1:
        source['args'] = us[1:]
    source['local'] = \
        path.join(source['local_prefix'], 'git', source['file'])
    source['symlink'] = source['local']


def _file_parser(source, config, opts):
    #
    # Symlink.
    #
    source['symlink'] = source['local']

parsers = { 'http': _http_parser,
            'ftp':  _http_parser,
            'git':  _git_parser,
            'file': _file_parser }

def parse_url(url, pathkey, config, opts):
    #
    # Split the source up into the parts we need.
    #
    source = {}
    source['url'] = url
    source['path'] = path.dirname(url)
    source['file'] = path.basename(url)
    source['name'], source['ext'] = path.splitext(source['file'])
    #
    # Get the file. Checks the local source directory first.
    #
    source['local'] = None
    for p in config.define(pathkey).split(':'):
        local = path.join(path.abspath(p), source['file'])
        if source['local'] is None:
            source['local_prefix'] = path.abspath(p)
            source['local'] = local
        if path.exists(local):
            source['local_prefix'] = path.abspath(p)
            source['local'] = local
            break
    source['script'] = ''
    for p in parsers:
        if url.startswith(p):
            source['type'] = p
            if parsers[p](source, config, opts):
                break
    return source

def _http_downloader(url, local, config, opts):
    if path.exists(local):
        return True
    #
    # Hack for GitHub.
    #
    if url.startswith('https://api.github.com'):
        url = urlparse.urljoin(url, config.expand('tarball/%{version}'))
    _notice(opts, 'download: %s -> %s' % (url, os.path.relpath(path.host(local))))
    failed = False
    if not opts.dry_run():
        _in = None
        _out = None
        try:
            _in = urllib2.urlopen(url)
            _out = open(path.host(local), 'wb')
            _out.write(_in.read())
        except IOError, err:
            msg = 'download: %s: error: %s' % (url, str(err))
            _notice(opts, msg)
            if path.exists(local):
                os.remove(path.host(local))
            failed = True
        except ValueError, err:
            msg = 'download: %s: error: %s' % (url, str(err))
            _notice(opts, msg)
            if path.exists(local):
                os.remove(path.host(local))
            failed = True
        except:
            msg = 'download: %s: error' % (url)
            print >> sys.stderr, msg
            if _out is not None:
                _out.close()
            raise
        if _out is not None:
            _out.close()
        if _in is not None:
            del _in
        if not failed:
            if not path.isfile(local):
                raise error.general('source is not a file: %s' % (path.host(local)))
    return not failed

def _git_downloader(url, local, config, opts):
    rlp = os.path.relpath(path.host(local))
    us = url.split('?')
    repo = git.repo(local, opts, config.macros)
    if not repo.valid():
        _notice(opts, 'git: clone: %s -> %s' % (us[0], rlp))
        if not opts.dry_run():
            repo.clone(us[0], local)
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'branch':
            _notice(opts, 'git: checkout: %s => %s' % (us[0], _as[1]))
            if not opts.dry_run():
                repo.checkout(_as[1])
        elif _as[0] == 'pull':
            _notice(opts, 'git: pull: %s' % (us[0]))
            if not opts.dry_run():
                repo.pull()
        elif _as[0] == 'fetch':
            _notice(opts, 'git: fetch: %s -> %s' % (us[0], rlp))
            if not opts.dry_run():
                repo.fetch()
        elif _as[0] == 'reset':
            arg = []
            if len(_as) > 1:
                arg = ['--%s' % (_as[1])]
            _notice(opts, 'git: reset: %s' % (us[0]))
            if not opts.dry_run():
                repo.reset(arg)
    return True

def _file_downloader(url, local, config, opts):
    if path.exists(local):
        return True
    return path.isdir(url)

downloaders = { 'http': _http_downloader,
                'ftp':  _http_downloader,
                'git':  _git_downloader,
                'file':  _file_downloader }

def get_file(url, local, opts, config):
    if local is None:
        raise error.general('source/patch path invalid')
    if not path.isdir(path.dirname(local)) and not opts.download_disabled():
        _notice(opts,
                'Creating source directory: %s' % (os.path.relpath(path.host(path.dirname(local)))))
    _output(opts, 'making dir: %s' % (path.host(path.dirname(local))))
    if not opts.dry_run():
        path.mkdir(path.dirname(local))
    if not path.exists(local) and opts.download_disabled():
        raise error.general('source not found: %s' % (path.host(local)))
    #
    # Check if a URL hasbeen provided on the command line.
    #
    url_bases = opts.urls()
    urls = []
    if url_bases is not None:
        for base in url_bases:
            if base[-1:] != '/':
                base += '/'
            url_path = urlparse.urlsplit(url)[2]
            slash = url_path.rfind('/')
            if slash < 0:
                url_file = url_path
            else:
                url_file = url_path[slash + 1:]
            urls.append(urlparse.urljoin(base, url_file))
    urls.append(url)
    if opts.trace():
        print '_url:', ','.join(urls), '->', local
    for url in urls:
        for dl in downloaders:
            if url.startswith(dl):
                if downloaders[dl](url, local, config, opts):
                    return
    if not opts.dry_run():
        raise error.general('downloading %s: all paths have failed, giving up' % (url))
