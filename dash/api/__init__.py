from __future__ import unicode_literals

import json
import logging
import requests
import time

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_text
from django.utils.text import slugify
from redis_cache import get_redis_connection
from six.moves import urllib


logger = logging.getLogger(__name__)

COUNTRY = 0

BOUNDARY_START_LEVEL = getattr(settings, 'BOUNDARY_START_LEVEL', 1)

BOUNDARY_END_LEVEL = getattr(settings, 'BOUNDARY_END_LEVEL', 3)
# we cache boundary data for a month at a time
BOUNDARY_CACHE_TIME = getattr(settings, 'API_BOUNDARY_CACHE_TIME', 60 * 60 * 24 * 30)

# one hour for group cache
GROUP_CACHE_TIME = getattr(settings, 'API_GROUP_CACHE_TIME', 60 * 60)

# fifteen minutes for result cache
RESULT_CACHE_TIME = getattr(settings, 'API_RESULT_CACHE_TIME', 60 * 15)

# fifteen minutes for flows cache
FLOWS_CACHE_TIME = getattr(settings, 'API_FLOWS_CACHE_TIME', 60 * 15)

# one hour to cache group results and breakdowns
CONTACT_RESULT_CACHE_TIME = getattr(settings, 'API_CONTACT_RESULT_CACHE_TIME', 60 * 60)

# five minutes to cache contacts and breakdowns
CONTACT_CACHE_TIME = getattr(settings, 'API_CONTACTS_CACHE_TIME', 60 * 5)


class API(object):

    def __init__(self, org):
        self.org = org

    def get_group(self, name):
        """
        Returns the attributes for a group
        """
        key = 'group:%d:%s' % (self.org.id, slugify(name))
        return self._get_from_cache(key, GROUP_CACHE_TIME, lambda: self._fetch_group(name))

    def get_contacts(self, group=None):
        """
        Returns the contacts within a particular group
        """
        key = 'contacts:%d:%s' % (self.org.id, slugify(group))
        return self._get_from_cache(key, CONTACT_CACHE_TIME, lambda: self._fetch_contacts(group))

    def get_country_geojson(self):
        """
        Returns the geojson for a particular country
        """
        key = 'geojson:%d' % self.org.id
        return self._get_from_cache(key, BOUNDARY_CACHE_TIME, self._fetch_country_geojson)

    def get_geojson_by_parent_id(self, parent_id):
        """
        Returns the geojson for a particular state
        """
        key = 'geojson:%d:%s' % (self.org.id, parent_id)
        return self._get_from_cache(
            key, BOUNDARY_CACHE_TIME,
            lambda: self._fetch_geojson_by_parent_id(parent_id))

    def get_ruleset_results(self, ruleset_id, segment=None):
        """
        Returns the results summary for a flow ruleset.
        """
        key = 'rs:%s:%d' % (self.org.id, ruleset_id)
        if segment:
            location = segment.get('location', None)
            if location == 'State':
                segment['location'] = self.org.get_config('state_label')
            elif location == 'District':
                segment['location'] = self.org.get_config('district_label')

            key += ":" + slugify(force_text(json.dumps(segment)))

        return self._get_from_cache(
            key, RESULT_CACHE_TIME,
            lambda: self._fetch_ruleset_results(ruleset_id, segment))

    def get_contact_field_results(self, contact_field_label, segment=None):
        """
        Returns the results summary for a contact field.
        """
        key = 'cf:%d:%s' % (self.org.id, slugify(contact_field_label))
        if segment:
            location = segment.get('location', None)
            if location == 'State':
                segment['location'] = self.org.get_config('state_label')
            elif location == 'District':
                segment['location'] = self.org.get_config('district_label')

            key += ":" + slugify(force_text(json.dumps(segment)))

        return self._get_from_cache(
            key, CONTACT_RESULT_CACHE_TIME,
            lambda: self._fetch_contact_field_results(contact_field_label, segment))

    def get_flow(self, flow_id):
        """
        Returns the attributes on a flow.
        """
        start = time.time()

        flow = None
        flows = self.get_flows("flow=%d" % flow_id)
        if flows:
            flow = flows[0]

        logger.debug("- got flow %d in %f" % (flow_id, time.time() - start))

        return flow

    def get_flow_messages(self, flow, page=0, direction=None):
        """
        Returns the most recent messages for a given flow.
        """
        try:
            url = '%s/api/v1/messages.json' % settings.SITE_API_HOST
            params = dict(flow=flow)
            if direction:
                params['direction'] = direction

            response = requests.get(url,
                                    params=params,
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            result = response.json()
            return result['results']

        except Exception as e:
            raise e

    def get_flows(self, filter=None):
        key = 'flows:%d' % self.org.id
        if filter:
            key += ":" + filter

        return self._get_from_cache(key, FLOWS_CACHE_TIME, lambda: self._fetch_flows(filter))

    def _get_from_cache(self, key, timeout, fetch_method):
        """
        Takes care of performing the following logic:
            1) check whether we have a recent version of the cached value, if
               so returns it
            2) if not, tries to acquire a lock to calculate it, if lock exists
               returns 'fallback' value
            3) if lock is available calls 'fetch_method' to calculate the new
               value

        The above keeps us from having a stampeding herd of clients hammering
        the API for an expensive calculating at the cost of us serving a stale
        value once in a while.
        """
        # 1) try to get it from our cache
        cached_value = cache.get(key)

        # if we found it, yay, hand it back to the client
        if cached_value is not None:
            return cached_value

        r = get_redis_connection()

        lock_key = 'lock:%s' % key
        fallback_key = 'fallback:%s' % key

        # 2) didn't find it, somebody is already calculating it, return the fallback
        if r.exists(lock_key):
            # do we have a fallback value?
            fallback_value = cache.get(fallback_key)

            # use our fallback, that's good enough
            if fallback_value is not None:
                return fallback_value

        # 3) acquire our lock and calculate our value
        with r.lock(lock_key, 240):
            # check for a cached value again, it's possible we were waiting in line
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # no such luck, let's go calculate it
            # fetch_methods are expected to raise exception if we aren't
            # getting something valid looking
            try:
                calculated = fetch_method()
            except:
                # log our error
                import traceback
                traceback.print_exc()

                # can we fall back?
                fallback_value = cache.get(fallback_key)
                if fallback_value is not None:
                    return fallback_value

                # oh well, return None, we tried
                else:
                    return None

            # populate our value as well as our fallback
            cache.set(key, calculated, timeout)

            # fallback never expires
            cache.set(fallback_key, calculated, timeout=None)

            # return our calculated value
            return calculated

    def _fetch_group(self, name):
        start = time.time()
        response = requests.get('%s/api/v1/groups.json' % settings.SITE_API_HOST,
                                params={'name': name},
                                headers={'Content-type': 'application/json',
                                         'Accept': 'application/json',
                                         'Authorization': 'Token %s' % self.org.api_token})

        response.raise_for_status()

        result = response.json()
        group = result['results'][0]

        logger.debug("- got group %s in %f" % (name, time.time() - start))

        return group

    def _fetch_contacts(self, group=None):
        next = '%s/api/v1/contacts.json' % settings.SITE_API_HOST
        contacts = []

        while next:
            response = requests.get(next,
                                    params={'group': group},
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            response.raise_for_status()
            result = response.json()
            for contact in result['results']:
                contacts.append(contact)

            next = result['next']

        return contacts

    def _fetch_country_geojson(self):
        boundaries = self._build_boundaries()
        return boundaries['geojson:%d'] % self.org.id

    def _fetch_geojson_by_parent_id(self, parent_id):
        boundaries = self._build_boundaries()
        return boundaries['geojson:%d:%s' % (self.org.id, parent_id)]

    def _build_boundaries(self):
        start = time.time()

        next = '%s/api/v1/boundaries.json' % settings.SITE_API_HOST
        boundaries = []

        while next:
            response = requests.get(next,
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})
            response.raise_for_status()
            response_json = response.json()

            for boundary in response_json['results']:
                boundaries.append(boundary)

            if 'next' in response_json:
                next = response_json['next']
            else:
                next = None

        # we now build our cached versions of level 1 (all states) and level 2
        # (all districts for each state) geojson
        start_level = []
        other_levels_by_parent = dict()
        for boundary in boundaries:
            if boundary['level'] == BOUNDARY_START_LEVEL:
                start_level.append(boundary)
            elif boundary['level'] <= BOUNDARY_END_LEVEL and boundary['parent']:
                osm_id = boundary['parent']
                if osm_id not in other_levels_by_parent:
                    other_levels_by_parent[osm_id] = []

                districts = other_levels_by_parent[osm_id]
                districts.append(boundary)

        # mini function to convert a list of boundary objects to geojson
        def to_geojson(boundary_list):
            features = [dict(type='Feature', geometry=b['geometry'],
                             properties=dict(name=b['name'], id=b['boundary'],
                             level=b['level']))
                        for b in boundary_list]
            return dict(type='FeatureCollection', features=features)

        cached = dict()

        # save our cached geojson to redis
        cache.set('geojson:%d' % self.org.id, to_geojson(start_level), BOUNDARY_CACHE_TIME)
        cache.set('fallback:geojson:%d' % self.org.id, to_geojson(start_level), timeout=None)

        cached['geojson:%d' % self.org.id] = to_geojson(start_level)

        for parent_id in other_levels_by_parent.keys():
            cache.set('geojson:%d:%s' % (self.org.id, parent_id),
                      to_geojson(other_levels_by_parent[parent_id]), BOUNDARY_CACHE_TIME)
            cache.set('fallback:geojson:%d:%s' % (self.org.id, parent_id),
                      to_geojson(other_levels_by_parent[parent_id]), timeout=None)

            cached['geojson:%d:%s' % (self.org.id, parent_id)] = to_geojson(
                other_levels_by_parent[parent_id])

            logger.debug("- built boundaries in %f" % (time.time() - start))

        return cached

    def _fetch_ruleset_results(self, ruleset_id, segment=None):
        start = time.time()

        url = '%s/api/v1/results.json?ruleset=%d&segment=%s' % (
            settings.SITE_API_HOST, ruleset_id,
            urllib.parse.quote(force_text(json.dumps(segment)).encode('utf8')))

        logger.debug(url)

        response = requests.get(url,
                                headers={'Content-type': 'application/json',
                                         'Accept': 'application/json',
                                         'Authorization': 'Token %s' % self.org.api_token})

        response.raise_for_status()
        response_json = response.json()

        results = response_json['results']

        logger.debug("- got ruleset results for %d in %f" % (ruleset_id, time.time() - start))

        return results

    def _fetch_contact_field_results(self, contact_field_label, segment=None):
        start = time.time()

        url = '%s/api/v1/results.json?contact_field=%s&segment=%s' % (
            settings.SITE_API_HOST,
            contact_field_label,
            urllib.parse.quote(force_text(json.dumps(segment)).encode('utf8')))
        logger.debug(url)

        response = requests.get(url,
                                headers={'Content-type': 'application/json',
                                         'Accept': 'application/json',
                                         'Authorization': 'Token %s' % self.org.api_token})

        response.raise_for_status()
        response_json = response.json()
        results = response_json['results']

        logger.debug("- got contact field results for %s in %f" % (
            contact_field_label, time.time() - start))

        return results

    def _fetch_flows(self, filter=None):
        start = time.time()

        next = '%s/api/v1/flows.json' % settings.SITE_API_HOST
        if filter:
            next += "?" + filter

        flows = []
        while next:
            response = requests.get(next,
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            response.raise_for_status()
            result = response.json()

            # we only include flows that have one or more rules
            for flow in result['results']:
                if len(flow['rulesets']) > 0:
                    flows.append(flow)

            if 'next' in result:
                next = result['next']
            else:
                next = None

        if flows:
            logger.debug("- got flows in %f" % (time.time() - start))

        return flows
