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
import simplejson
import logging
import traceback

from decimal import Decimal
from urllib import urlopen, urlencode

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged


class UserProfile(models.Model):
    """
    Extends the default User model with additional fields.

    """
    user = models.OneToOneField(User)

    # Facebook user id.
    facebook_id = models.BigIntegerField(null=True, blank=True)

class Purchase(models.Model):
    """
    Represents a purchase of an item by a user.

    """
    user = models.ForeignKey(User)

    item_code = models.CharField(max_length=32, null=False, blank=False)
    purchased_at = models.DateTimeField(auto_now_add=True)


def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates Cardstories user profile after creation of default User.

    """
    if created:
        UserProfile.objects.create(user=instance)

def grant_user_bought_cards(ipn_obj):
    """
    This is a paypal IPN handler.
    Whenever an IPN request comes in, it validates it and grants the
    player who made the purchase the cards the he bought.
    """

    logger = logging.getLogger('cardstories.paypal')
    valid = True

    # Make sure the money goes to us!
    if ipn_obj.business != settings.PAYPAL_RECEIVER_EMAIL:
        logger.error("Wrong 'business' param in IPN request: %r" % ipn_obj.business)
        valid = False

    # Make sure the transaction was completed:
    if ipn_obj.payment_status != 'Completed':
        logger.error("Wrong 'payment_status' param in IPN request: %r" % ipn_obj.payment_status)
        valid = False

    # Make sure the amount is correct:
    if ipn_obj.mc_gross != Decimal(settings.CS_EXTRA_CARD_PACK_PRICE):
        logger.error("Wrong 'mc_gross' param in IPN request: %r" % ipn_obj.mc_gross)
        valid = False

    # Make sure the currency is correct:
    if ipn_obj.mc_currency != settings.CS_EXTRA_CARD_PACK_CURRENCY:
        logger.error("Wrong 'mc_currency' param in IPN request: %r" % ipn_obj.mc_currency)
        valid = False

    # If everything seems correct, grant player the cards.
    if valid:
        # Wow, that was a tough test, but it looks like we have a winner!
        # Grant player the cards:
        player_id = simplejson.loads(ipn_obj.custom)['player_id']

        params = {'action': 'grant_cards_to_player',
                  'player_id': player_id,
                  'card_ids': settings.CS_EXTRA_CARD_PACK_CARD_IDS}

        url = 'http://%s/resource?%s' % (settings.CARDSTORIES_HOST,
                                         urlencode(params, True))
        data = urlopen(url).read()
        logger.info("The webservice responded with: %r" % data)
        response = simplejson.loads(data)

        if response.get('status') == 'success':
            Purchase.objects.create(user_id=player_id, item_code=settings.CS_EXTRA_CARD_PACK_ITEM_ID)
            logger.info("Successfuly granted bought cards to player: %r" % player_id)
            return True
        else:
            logger.error("Failed granting bought cards to player: %r; response: %r" % (player_id, response))
            return False
    else:
        return False

def paypal_payment_was_successful_handler(sender, **kwargs):
    """
    Handles paypal IPN requests.
    Calls grant_user_bought_cards, wrapped in some logging.

    """
    logger = logging.getLogger('cardstories.paypal')
    logger.info("Handling transaction from: %r" % sender.payer_email)
    try:
        return grant_user_bought_cards(sender)
    except:
        logger.error("Error handling transaction from %r" % sender.payer_email)
        logger.error('-'*60 + '\n' + traceback.format_exc() + '\n' + '-'*60)
        return False

def paypal_payment_was_flagged_handler(sender, **kwargs):
    logger = logging.getLogger('cardstories.paypal')
    logger.error("Paypal Payment Failed! %r; %r" % (sender.flag_code, sender.flag_info))


# Registers creation of user profile on post_save signal.
post_save.connect(create_user_profile, sender=User)
# Registers Paypal's IPN signals.
payment_was_successful.connect(paypal_payment_was_successful_handler)
payment_was_flagged.connect(paypal_payment_was_flagged_handler)
