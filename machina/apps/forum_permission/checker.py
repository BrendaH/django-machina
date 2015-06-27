# -*- coding: utf-8 -*-

# Standard library imports
from __future__ import unicode_literals

# Third party imports
from django.contrib.auth import get_user_model
from django.db.models import Q

# Local application / specific library imports
from machina.conf import settings as machina_settings
from machina.core.db.models import get_model

ForumPermission = get_model('forum_permission', 'ForumPermission')
GroupForumPermission = get_model('forum_permission', 'GroupForumPermission')
UserForumPermission = get_model('forum_permission', 'UserForumPermission')


class ForumPermissionChecker(object):
    def __init__(self, user):
        self.user = user
        self._forum_perms_cache = {}

    def has_perm(self, perm, forum):
        """
        Checks if the considered user has given permission for the passed forum.
        """
        if not self.user.is_anonymous() and not self.user.is_active:
            return False
        elif self.user and self.user.is_superuser:
            return True
        return perm in self.get_perms(forum)

    def get_perms(self, forum):
        """
        Returns the list of codenames of all permissions for the given forum.
        """
        if not self.user.is_anonymous() and not self.user.is_active:
            return []
        user_model = get_user_model()
        user_groups_related_name = user_model.groups.field.related_query_name()

        if forum.id not in self._forum_perms_cache:
            if self.user and self.user.is_superuser:
                perms = list(ForumPermission.objects.values_list('codename', flat=True))
            elif self.user:
                default_auth_forum_perms = machina_settings.DEFAULT_AUTHENTICATED_USER_FORUM_PERMISSIONS

                user_kwargs_filter = {'anonymous_user': True} if self.user.is_anonymous() \
                    else {'user': self.user}

                user_perms = UserForumPermission.objects.select_related().filter(**user_kwargs_filter) \
                    .filter(Q(forum__isnull=True) | Q(forum=forum))

                globally_granted_user_perms = list(filter(lambda p: p.has_perm and p.forum is None, user_perms))
                globally_granted_user_perms = [p.permission.codename for p in globally_granted_user_perms]

                per_forum_granted_user_perms = list(filter(lambda p: p.has_perm and p.forum is not None, user_perms))
                per_forum_granted_user_perms = [p.permission.codename for p in per_forum_granted_user_perms]

                per_forum_nongranted_user_perms = list(filter(lambda p: not p.has_perm and p.forum is not None, user_perms))
                per_forum_nongranted_user_perms = [p.permission.codename for p in per_forum_nongranted_user_perms]

                if self.user.is_authenticated() and not globally_granted_user_perms:
                    globally_granted_user_perms = default_auth_forum_perms

                granted_user_perms = [c for c in globally_granted_user_perms if
                                      c not in per_forum_nongranted_user_perms] + per_forum_granted_user_perms
                granted_user_perms = set(granted_user_perms)

                perms = granted_user_perms

                if not self.user.is_anonymous():
                    group_perms = GroupForumPermission.objects.select_related() \
                        .filter(**{'group__{}'.format(user_groups_related_name): self.user}) \
                        .filter(Q(forum__isnull=True) | Q(forum=forum))

                    globally_granted_group_perms = list(filter(lambda p: p.has_perm and p.forum is None, group_perms))
                    globally_granted_group_perms = [p.permission.codename for p in globally_granted_group_perms]

                    per_forum_granted_group_perms = list(filter(lambda p: p.has_perm and p.forum is not None, group_perms))
                    per_forum_granted_group_perms = [p.permission.codename for p in per_forum_granted_group_perms]

                    per_forum_nongranted_group_perms = list(filter(lambda p: not p.has_perm and p.forum is not None, group_perms))
                    per_forum_nongranted_group_perms = [p.permission.codename for p in per_forum_nongranted_group_perms]

                    granted_group_perms = [c for c in globally_granted_group_perms if
                                           c not in per_forum_nongranted_group_perms] + per_forum_granted_group_perms
                    granted_group_perms = filter(lambda x: x not in per_forum_nongranted_user_perms, granted_group_perms)
                    granted_group_perms = set(granted_group_perms)

                    perms |= granted_group_perms

            self._forum_perms_cache[forum.id] = perms

        return self._forum_perms_cache[forum.id]
