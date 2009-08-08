# -*- mode: python; coding: utf-8 -*-
import os
import datetime
import logging
import string
from drydrop_handler import DRY_ROOT
from drydrop.app.core.controller import BaseController
from drydrop.lib.json import json_parse
from drydrop.app.core.events import log_event

class HookController(BaseController):

    # see http://github.com/guides/post-receive-hooks
    def github(self):
        payload = self.params.get('payload', None)
        logging.debug("Received github hook: %s", payload)
        if not payload:
            return
        
        data = json_parse(payload)
        paths = []
        names = []
        for commit in data['commits']:
            author = commit['author']['email']
            try:
                names.index(author)
            except:
                names.append(author)
            try:
                paths.extend(commit['added'])
            except:
                pass
            try:
                paths.extend(commit['removed'])
            except:
                pass
            try:
                paths.extend(commit['modified'])
            except:
                pass
                
        authors = string.join(names, ',')
        log_event("Received github hook for commit %s (%d changes)" % (data['after'], len(paths)), 0, authors)

        repo_url = data['repository']['url'] # like http://github.com/darwin/drydrop
        branch = data['ref'].split('/').pop() # takes 'master' from 'refs/heads/master'
        
        root_url = "%s/raw/%s" % (repo_url, branch) # creates http://github.com/darwin/drydrop/raw/master
        if not root_url.endswith('/'):
            root_url = root_url + '/'
        source_url = self.handler.settings.source
        if not source_url.endswith('/'):
            source_url = source_url + '/'
            
        # now we have:
        # http://github.com/darwin/drydrop/raw/master/ in root_url
        # http://github.com/darwin/drydrop/raw/master/tutorial/ in source_url
        
        # safety check
        if not source_url.startswith(root_url):
            log_event("Source url '%s' is not affected by incoming changeset url '%s'" % (source_url, root_url), 0, authors)
            logging.info("Source url '%s' is not affected by incoming changeset url '%s'", source_url, root_url)
            return
        
        vfs = self.handler.vfs
        for path in paths:
            prefix = source_url[len(root_url):] # prefix is 'tutorial/'
            if not path.startswith(prefix):
                logging.warning("Unexpected: path '%s' should begin with '%s'. Skipping file.", path, prefix)
            else:
                # path is something like tutorial/start.html
                path = path[len(prefix):] # stripped to 'start.html'
                logging.info("Flushing resource %s", path)
                vfs.flush_resource(path)