#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Author: Adolfo R. Brandes <arbrandes@gmail.com>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save


class UserProfile(models.Model):
    """
    Extends the default User model with additional fields.

    """
    user = models.OneToOneField(User)

    # Facebook user id.
    facebook_id = models.BigIntegerField(null=True, blank=True)

    # Player score
    score = models.BigIntegerField(null=True, blank=True)

    # Number of times a player leveled up.
    levelups = models.IntegerField(null=True, blank=True)


class UserCard(models.Model):
    """
    Card a user can earn when leveling up.

    """

    # The user the card belongs to.
    user = models.ForeignKey(User)

    # The card earned by the user.
    card = models.IntegerField()

    class Meta:
        # A user cannot have the same card twice.
        unique_together = (("user", "card"),)


def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates Cardstories user profile after creation of default User.

    """
    if created:
        UserProfile.objects.create(user=instance)


# Registers creation of user profile on post_save signal.
post_save.connect(create_user_profile, sender=User)
