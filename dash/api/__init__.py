from __future__ import unicode_literals
import json
import urllib

from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
import requests
import time


# level constants
COUNTRY = 0
STATE = 1
DISTRICT = 2

# we cache boundary data for a month at a time
BOUNDARY_CACHE_TIME = getattr(settings, 'API_BOUNDARY_CACHE_TIME', 60 * 60 * 24 * 30)

# one hour for group cache
GROUP_CACHE_TIME = getattr(settings, 'API_GROUP_CACHE_TIME', 60 * 60)

# fifteen minutes for result cache
RESULT_CACHE_TIME = getattr(settings, 'API_RESULT_CACHE_TIME', 60 * 15)

# one hour to cache group results and breakdowns
CONTACT_RESULT_CACHE_TIME = getattr(settings, 'API_CONTACT_RESULT_CACHE_TIME', 60 * 60)


class API(object):

    def __init__(self, org):
        self.org = org

    def get_group(self, name):
        start = time.time()

        cache_key = 'group:%d:%s' % (self.org.id, slugify(name))
        group = cache.get(cache_key)

        if not group:
            response = requests.get('%s/api/v1/groups.json' % settings.API_ENDPOINT,
                                    params={'name': name},
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            result = response.json()
            if response.status_code == 200 and 'results' in result and len(result['results']) > 0:
                group = result['results'][0]
                cache.set(cache_key, group, GROUP_CACHE_TIME)

                if settings.DEBUG: # pragma: no cover
                    print "- got group %s in %f" % (name, time.time() - start)

            else:
                cache.delete(cache_key)
                if settings.DEBUG: # pragma: no cover
                    print "- *** FAILED *** to get group %s" % name

        return group


    def get_country_geojson(self):
        start = time.time()

        cache_key = 'geojson:%d' % self.org.id
        states = cache.get(cache_key)

        if not states:
            cached = self.build_boundaries()
            states = cached.get(cache_key, None)

        if settings.DEBUG: # pragma: no cover
            print "- got country in %f" % (time.time() - start)

        return states

    def get_state_geojson(self, state_id):
        start = time.time()

        cache_key = 'geojson:%d:%s' % (self.org.id, state_id)
        districts = cache.get(cache_key)

        if not districts:
            cached = self.build_boundaries()
            districts = cached.get(cache_key, None)

        if settings.DEBUG: # pragma: no cover
            print "- got states in %f" % (time.time() - start)

        return districts

    def build_boundaries(self):
        start = time.time()

        next = '%s/api/v1/boundaries.json' % settings.API_ENDPOINT
        boundaries = []

        while next:
            response = requests.get(next,
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            response_json = response.json()

            if response.status_code == 200 and 'results' in response_json:
                for boundary in response_json['results']:
                    boundaries.append(boundary)

            if 'next' in response_json:
                next = response_json['next']
            else:
                next = None

        # we now build our cached versions of level 1 (all states) and level 2 (all districts for each state) geojson
        states = []
        districts_by_state = dict()
        for boundary in boundaries:
            if boundary['level'] == STATE:
                states.append(boundary)
            elif boundary['level'] == DISTRICT:
                osm_id = boundary['parent']
                if not osm_id in districts_by_state:
                    districts_by_state[osm_id] = []

                districts = districts_by_state[osm_id]
                districts.append(boundary)

        # mini function to convert a list of boundary objects to geojson
        def to_geojson(boundary_list):
            features = [dict(type='Feature', geometry=b['geometry'],
                             properties=dict(name=b['name'], id=b['boundary'], level=b['level'])) for b in boundary_list]
            return dict(type='FeatureCollection', features=features)

        cached = dict()

        # save our cached geojson to redis
        cache.set('geojson:%d' % self.org.id, to_geojson(states), BOUNDARY_CACHE_TIME)
        cached['geojson:%d' % self.org.id] = to_geojson(states)

        for state_id in districts_by_state.keys():
            cache.set('geojson:%d:%s' % (self.org.id, state_id), to_geojson(districts_by_state[state_id]), BOUNDARY_CACHE_TIME)
            cached['geojson:%d:%s' % (self.org.id, state_id)] = to_geojson(districts_by_state[state_id])

        if settings.DEBUG: # pragma: no cover
            print "- built boundaries in %f" % (time.time() - start)

        return cached

    def get_ruleset_results(self, ruleset_id, segment=None):
        start = time.time()

        cache_key = 'rs:%s:%d' % (self.org.id, ruleset_id)

        if segment:
            # if our segment is on location, remap the location from the static 'State' and 'District' to the actual labels
            location = segment.get('location', None)
            if location == 'State':
                segment['location'] = self.org.get_config('state_label')
            elif location == 'District':
                segment['location'] = self.org.get_config('district_label')

            cache_key += ":" + slugify(unicode(json.dumps(segment)))

        results = cache.get(cache_key)

        if not results:
            url = '%s/api/v1/results.json?ruleset=%d&segment=%s' % (settings.API_ENDPOINT, ruleset_id,
                                                                    urllib.quote(unicode(json.dumps(segment)).encode('utf8')))
            response = requests.get(url,
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            response_json = response.json()

            if response.status_code == 200 and 'results' in response_json:
                results = response_json['results']
                cache.set(cache_key, results, RESULT_CACHE_TIME)

                if settings.DEBUG: # pragma: no cover
                    print "- got ruleset results for %d in %f" % (ruleset_id, time.time() - start)
            else:
                cache.delete(cache_key)
                if settings.DEBUG: # pragma: no cover
                    print "- *** FAILED *** to get ruleset results for %d" % ruleset_id

        return results

    def get_contact_field_results(self, contact_field_label, segment=None):
        start = time.time()

        cache_key = 'cf:%d:%s' % (self.org.id, slugify(contact_field_label))

        if segment:
            # if our segment is on location, remap the location from the static 'State' and 'District' to the actual labels
            location = segment.get('location', None)
            if location == 'State':
                segment['location'] = self.org.get_config('state_label')
            elif location == 'District':
                segment['location'] = self.org.get_config('district_label')

            cache_key += ":" + slugify(unicode(json.dumps(segment)))

        results = cache.get(cache_key)

        if not results:
            response = requests.get('%s/api/v1/results.json?contact_field=%s&segment=%s' % (settings.API_ENDPOINT, contact_field_label, urllib.quote(unicode(json.dumps(segment)).encode('utf8'))),
                                    headers={'Content-type': 'application/json',
                                             'Accept': 'application/json',
                                             'Authorization': 'Token %s' % self.org.api_token})

            response_json = response.json()

            if response.status_code == 200 and 'results' in response_json:
                results = response_json['results']
                cache.set(cache_key, results, CONTACT_RESULT_CACHE_TIME)

                if settings.DEBUG: # pragma: no cover
                    print "- got contact field results for %s in %f" % (contact_field_label, time.time() - start)

            else:
                cache.delete(cache_key)
                if settings.DEBUG: # pragma: no cover
                    print "- *** FAILED *** to get contact field results for %s" % contact_field_label

        return results

    def get_flow(self, flow_id):
        start = time.time()

        flow = None

        flows = self.get_flows("flow=%d" % flow_id)
        if flows:
            flow = flows[0]

        if settings.DEBUG: # pragma: no cover
            print "- got flow %d in %f" % (flow_id, time.time() - start)

        return flow

    def get_flows(self, filter=None):
        start = time.time()

        cache_key = 'flows:%d' % self.org.id
        next = '%s/api/v1/flows.json' % settings.API_ENDPOINT

        # munge our cache key and filter if necessary
        if filter:
            cache_key += ":" + filter
            next += "?" + filter

        flows = cache.get(cache_key)

        if not flows:
            flows = []

            while next:
                response = requests.get(next,
                                        headers={'Content-type': 'application/json',
                                                 'Accept': 'application/json',
                                                 'Authorization': 'Token %s' % self.org.api_token})

                result = response.json()

                if response.status_code == 200 and 'results' in result:

                    # we only include flows that have one or more rules
                    for flow in result['results']:
                        if len(flow['rulesets']) > 0:
                            flows.append(flow)

                if 'next' in result:
                    next = result['next']
                else:
                    next = None

            if flows:
                # save to our cache for fifteen minutes
                cache.set(cache_key, flows, RESULT_CACHE_TIME)

            else:
                next = None
                cache.delete(cache_key)

        if settings.DEBUG and flows: # pragma: no cover
            print "- got flows in %f" % (time.time() - start)

        return flows
