#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
import os
import logging
import uuid
from hashlib import md5

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import signer, ssh_key_string_to_obj
from .utils import private_key_validator


__all__ = ['AdminUser', 'SystemUser',]
logger = logging.getLogger(__name__)


class AdminUser(models.Model):
    """
    A privileged user that ansible can use it to push system user and so on
    """
    BECOME_METHOD_CHOICES = (
        ('sudo', 'sudo'),
        ('su', 'su'),
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    _private_key = models.TextField(max_length=4096, blank=True, null=True, verbose_name=_('SSH private key'), validators=[private_key_validator,])
    become = models.BooleanField(default=True)
    become_method = models.CharField(choices=BECOME_METHOD_CHOICES, default='sudo', max_length=4)
    become_user = models.CharField(default='root', max_length=64)
    _become_pass = models.CharField(default='', max_length=128)
    _public_key = models.TextField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.CharField(max_length=32, null=True, verbose_name=_('Created by'))

    def __str__(self):
        return self.name

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        else:
            return ''

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            key_str = signer.unsign(self._private_key)
            return ssh_key_string_to_obj(key_str)
        else:
            return None

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

    @property
    def private_key_file(self):
        if not self.private_key:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_name = md5(self._private_key.encode()).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            self.private_key.write_private_key_file(key_path)
        return key_path

    @property
    def public_key(self):
        return signer.unsign(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = signer.sign(public_key_raw)

    @property
    def become_pass(self):
        return signer.unsign(self._become_pass)

    @become_pass.setter
    def become_pass(self, password):
        self._become_pass = signer.sign(password)

    def get_related_assets(self):
        assets = []
        for cluster in self.cluster_set.all():
            assets.extend(cluster.assets.all())
        assets.extend(self.asset_set.all())
        return list(set(assets))

    @property
    def assets_amount(self):
        return len(self.get_related_assets())

    class Meta:
        ordering = ['name']

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue


class SystemUser(models.Model):
    PROTOCOL_CHOICES = (
        ('ssh', 'ssh'),
    )
    AUTH_METHOD_CHOICES = (
        ('P', 'Password'),
        ('K', 'Public key'),
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    cluster = models.ManyToManyField('assets.Cluster', verbose_name=_("Cluster"))
    _password = models.CharField(max_length=256, blank=True, verbose_name=_('Password'))
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    _private_key = models.TextField(max_length=8192, blank=True, verbose_name=_('SSH private key'))
    _public_key = models.TextField(max_length=8192, blank=True, verbose_name=_('SSH public key'))
    auth_method = models.CharField(choices=AUTH_METHOD_CHOICES, default='K', max_length=1, verbose_name=_('Auth method'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/sbin/ifconfig', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        return None

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            return signer.unsign(self._private_key)
        return None

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

    @property
    def private_key_file(self):
        if not self.private_key:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_name = md5(self._private_key.encode()).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            self.private_key.write_private_key_file(key_path)
        return key_path

    @property
    def public_key(self):
        if self._public_key:
            return signer.unsign(self._public_key)
        else:
            return None

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = signer.sign(public_key_raw)

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'shell': self.shell,
            'sudo': self.sudo,
            'password': self.password,
            'public_key': self.public_key,
            'private_key_file': self.private_key_file,
        }

    def get_clusters_assets(self):
        from .asset import Asset
        clusters = self.cluster.all()
        return Asset.objects.filter(cluster__in=clusters)

    @property
    def assets_amount(self):
        return len(self.get_clusters_assets())

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'protocol': self.protocol,
            'auth_method': self.auth_method,
            'auto_push': self.auto_push,
        }

    class Meta:
        ordering = ['name']

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue



