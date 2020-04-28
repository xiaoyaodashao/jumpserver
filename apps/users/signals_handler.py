# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from django_auth_ldap.backend import populate_user
from django.conf import settings
from django_cas_ng.signals import cas_user_authenticated

from jms_oidc_rp.signals import openid_user_create_or_update

from common.utils import get_logger
from .signals import post_user_create
from .models import User


logger = get_logger(__file__)


@receiver(post_user_create)
def on_user_create(sender, user=None, **kwargs):
    logger.debug("Receive user `{}` create signal".format(user.name))
    from .utils import send_user_created_mail
    logger.info("   - Sending welcome mail ...".format(user.name))
    if user.can_send_created_mail():
        send_user_created_mail(user)


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_change(sender, instance=None, action='', **kwargs):
    """
    资产节点发生变化时，刷新节点
    """
    if action.startswith('post'):
        logger.debug("User group member change signal recv: {}".format(instance))
        from perms.utils import AssetPermissionUtil
        AssetPermissionUtil.expire_all_user_tree_cache()


@receiver(cas_user_authenticated)
def on_cas_user_authenticated(sender, user, created, **kwargs):
    if created:
        user.source = user.SOURCE_CAS
        user.save()


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.username not in ['admin']:
        exists = User.objects.filter(username=user.username).exists()
        if not exists:
            user.source = user.SOURCE_LDAP
            user.save()


@receiver(openid_user_create_or_update)
def on_openid_user_create_or_update(sender, request, user, created, name, username, email):
    if created:
        user.source = User.SOURCE_OPENID
        user.save()
        return

    if not created and settings.AUTH_OPENID_ALWAYS_UPDATE_USER:
        user.name = name
        user.username = username
        user.email = email
        user.save()
