# -*- mode: python; coding: utf-8 -*-
import os
import os.path
import logging
import datetime
from drydrop.lib.utils import open_if_exists
from drydrop.app.models import Resource

class VFS(object):
    """Virtual File System == filesystem abstraction for DryDrop"""
    def __init__(self):
        super(VFS, self).__init__()
        
    def fetch_resource_content(self, path):
        logging.warning('fetch_resource not implemented for %s', self.__class__.__name__)
        return None
        
    def fetch_file_timestamp(self, path):
        return None
    
    def get_resource(self, path):
        resource = Resource.find(path=path, generation=self.settings.version)
        if resource is None:
            content = self.fetch_resource_content(path)
            created_on = self.fetch_file_timestamp(path)
            resource = Resource(path=path, content=content, generation=self.settings.version)
            if created_on is not None:
                resource.created_on = created_on
            logging.debug("VFS: creating resource %s with %s", path, content)
            resource.save()
        logging.debug("VFS: returning resource %s", path)
        return resource
        
    def flush_resources(self, count = 1000):
        deleted = Resource.clear(False, count)
        finished = deleted<count
        return finished, deleted
        
    def get_all_resources(self):
        return Resource.all().filter("generation =", self.settings.version).fetch(1000)
    
class LocalVFS(VFS):
    """VFS for local development"""
    
    def __init__(self, settings):
        super(LocalVFS, self).__init__()
        self.settings = settings
    
    def get_resource(self, path):
        # check if file is fresh in cache
        resource = Resource.find(path=path)
        if resource is not None:
            stamp = self.fetch_file_timestamp(path)
            if stamp is not None and resource.created_on != stamp:
                logging.debug("VFS: file %s has been modified since last time => purged from cache", path)
                resource.delete()
        return super(LocalVFS, self).get_resource(path)
        
    def fetch_file_timestamp(self, path):
        root = self.settings.source
        if not root:
            return None
        filepath = os.path.join(root, path)
        try:
            s = os.stat(filepath)
        except:
            return None
        return datetime.datetime.fromtimestamp(s.st_mtime)
        
    def fetch_resource_content(self, path):
        root = self.settings.source
        if not root:
            return None
        filepath = os.path.join(root, path)
        f = open_if_exists(filepath)
        if f is None:
            return None
        try:
            contents = f.read()
        finally:
            f.close()
        return contents

class GAEVFS(VFS):
    """VFS for production"""
    
    def __init__(self, settings):
        super(GAEVFS, self).__init__()
        self.settings = settings