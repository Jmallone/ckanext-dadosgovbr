# coding=utf-8

import logging
from urllib.parse import urlencode
import datetime
import mimetypes
import cgi
import json
from collections import OrderedDict


from ckan.common import config
from paste.deploy.converters import asbool
import paste.fileapp

import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.i18n as i18n
import ckan.lib.maintain as maintain
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.helpers as h
import ckan.model as model
import ckan.lib.datapreview as datapreview
import ckan.lib.plugins
import ckan.lib.uploader as uploader
import ckan.plugins as p
import ckan.lib.render
import ckan.plugins.toolkit as toolkit

from flask import request, response
#from home import CACHE_PARAMETERS

from ckan.controllers.package import PackageController

log = logging.getLogger(__name__)

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin

def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, str) else str(v))
            for k, v in params]

def url_with_params(url, params):
    params = _encode_params(params)
    return url + '?' + urlencode(params)

def search_url(params, package_type=None):
    if not package_type or package_type == 'dataset':
        url = h.url_for(controller='package', action='search')
    else:
        url = h.url_for('{0}_search'.format(package_type))
    return url_with_params(url, params)


class SchemingPagesController(PackageController):
    
    def search(self):
        from ckan.lib.search import SearchError, SearchQueryError

        # Get package type name
        package_type = self._guess_package_type()[:-1]
        toolkit.g.package_type = package_type


        # Get page content from Wordpress
        # =========================================
        import ckanext.dadosgovbr.helpers.wordpress as wp
        wp_page_slug = 'scheming_'+package_type+'s'
        toolkit.g.wp_page = type('Nothing', (object,), {})  
        toolkit.g.wp_page.content = type('Nothing', (object,), {})  
        toolkit.g.wp_page.content.rendered = "Conteudo da pagina nao encontrado..."
        try:
            toolkit.g.wp_page = wp.page(wp_page_slug)
        except:
            pass

        # DEBUG
        # from pprint import pprint 
        # pprint(toolkit.g.concursos)

        # Package type facets (filters)
        # =========================================
        package_type_facets = 'organization groups tags res_format license_id'
        if(package_type == 'inventario'):
            package_type_facets = 'organization situacao_base informacoes_sigilosas_base informacoes_publicas_base atualizacoes_base dados_abertos_base'

        if(package_type == 'concurso'):
            package_type_facets = 'organization datasets_used'

        if(package_type == 'aplicativo'):
            package_type_facets = 'organization groups tags res_format license_id'
        

        try:
            context = {'model': model, 'user': toolkit.g.user,
                       'auth_user_obj': toolkit.g.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            toolkit.abort(403, toolkit._('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = toolkit.g.q = request.params.get('q', '')
        toolkit.g.query_error = False
        page = h.get_page_number(request.params)

        limit = int(config.get('ckan.datasets_per_page', 20))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        toolkit.g.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='package', action='search')

        toolkit.g.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.
            Each entry in the list is a 2-tuple: (fieldname, sort_order)
            eg - [('metadata_modified', 'desc'), ('name', 'asc')]
            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))

            return search_url(params, package_type)

        toolkit.g.sort_by = _sort_by
        toolkit.g.sort_by_fields = []
        if sort_by:
            toolkit.g.sort_by_fields = [field.split()[0]
                                       for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, package_type)

        toolkit.g.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            toolkit.g.fields = []
            # toolkit.g.fields_grouped will contain a dict of params containing
            # a list of values, eg {'tag': ['tag1', 'tag2']}
            toolkit.g.fields_grouped = {}
            search_extras = {}
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        toolkit.g.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                        if param not in toolkit.g.fields_grouped:
                            toolkit.g.fields_grouped[param] = [value]
                        else:
                            toolkit.g.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            facets = OrderedDict()

            default_facet_titles = {'organization': toolkit._('Organizations'),
                                    'groups': toolkit._('Groups'),
                                    'tags': toolkit._('Tags'),
                                    'res_format': toolkit._('Formats'),
                                    'license_id': toolkit._('Licenses')}

            package_type_facets = 'organization groups tags res_format license_id'
            for facet in config.get('search.facets', package_type_facets.split()):
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            self._update_facet_titles(facets, package_type)

            toolkit.g.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': 'type:'+package_type,
                'include_private': True,
                'facet.field': facets.keys(),
                'rows': limit,
                'sort': sort_by,
                'start': (page - 1) * limit,
                'extras': search_extras
            }

            print(data_dict)

            context_ = dict((k, v) for (k, v) in context.items()
                            if k != 'schema')
            query = get_action('package_search')(context_, data_dict)

            toolkit.g.sort_by_selected = query['sort']
            toolkit.g.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            toolkit.g.search_facets = query['search_facets']
            toolkit.g.page.items = query['results']

            toolkit.g.query_error = False

        except SearchQueryError as se:
            # User's search parameters are invalid, in such a way that is not
            # achievable with the web interface, so return a proper error to
            # discourage this.
            toolkit.abort(400, toolkit._('Invalid search query: {error_message}')
                    .format(error_message=str(se)))
        except SearchError as se:
            # May be bad input from the user, but may also be more serious like
            # bad code causing a SOLR syntax error, or a problem connecting to
            # SOLR.
            log.error('Search error: %r', se.args)
            toolkit.g.query_error = True
            toolkit.g.search_facets = {}
            toolkit.g.page = h.Page(collection=[])
            toolkit.g.search_facets_limits = {}
            for facet in toolkit.g.search_facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                            config.get('search.facets.default', 10)))
                toolkit.g.search_facets_limits[facet] = limit

        self._setup_template_variables(context, {},
                                       package_type=package_type)

        return toolkit.render('scheming/'+package_type+'/search.html',
                              extra_vars={'dataset_type': package_type})

    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user, 'for_view': True,
                   'auth_user_obj': toolkit.g.userobj}
        data_dict = {'id': id}

        try:
            toolkit.g.pkg_dict = get_action('package_show')(context, data_dict)
            toolkit.g.pkg = context['package']
        except (NotFound, NotAuthorized):
            toolkit.abort(404, toolkit._('Dataset not found'))

        package_type = toolkit.g.pkg_dict['type'] or 'dataset'

        return toolkit.render('scheming/'+package_type+'/read.html')
