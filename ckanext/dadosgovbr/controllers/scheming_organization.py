# -*- coding: utf-8 -*-

import logging
import datetime
from urllib.parse import urlencode

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import OrderedDict, config, _, g
from flask import request

log = logging.getLogger(__name__)

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin
lookup_group_controller = ckan.lib.plugins.lookup_group_plugin

from ckan.controllers.organization import OrganizationController

class TestController(OrganizationController):
    def index (ctrl):
        return toolkit.render("test.html")

    def read_dataset(self, id, limit=20):
        
        # Variáveis para a view identificar qual guia deve ser ativada e definir o tipo de resultado
        # nos resultados. 
        toolkit.g.dataset = True
        toolkit.g.aplicativo = False
        toolkit.g.concurso = False

        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = { 'id': id, 'type': group_type}

        # unicode format (decoded from utf8)
        toolkit.g.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = True
            toolkit.g.group_dict = self._action('group_show')(context, data_dict)
            toolkit.g.group = context['group']
        except (NotFound, NotAuthorized):
            toolkit.abort(404, _('Group not found'))

        self._read_dataset(id, limit, group_type)
        
        return toolkit.render('organization/view_scheming_organization.html')

        #return toolkit.render(self._read_template(toolkit.g.group_dict['type']),
        #              extra_vars={'group_type': group_type})

    def _read_dataset(self, id, limit, group_type):
        ''' This is common code used by both read and bulk_process'''
        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = toolkit.g.q = request.params.get('q', '')
        # Search within group
        if toolkit.g.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % toolkit.g.group_dict.get('id')
        else:
            q += ' groups:"%s"' % toolkit.g.group_dict.get('name')

        toolkit.g.description_formatted = \
            h.render_markdown(toolkit.g.group_dict.get('description'))

        context['return_query'] = True

        page = h.get_page_number(request.params)

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        sort_by = request.params.get('sort', None)

        def search_url(params):
            controller = lookup_group_controller(group_type)
            action = 'bulk_process' if toolkit.g.action == 'bulk_process' else 'read'
            url = h.url_for(controller=controller, action=action, id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, str)
                       else str(v)) for k, v in params]
            return url + '?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=toolkit.g.group_dict.get('name')),
                                   new_params=by)

        toolkit.g.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            controller = lookup_group_controller(group_type)
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller=controller, action='read',
                                      extras=dict(id=toolkit.g.group_dict.get('name')))

        toolkit.g.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            toolkit.g.fields = []
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

            default_facet_titles = {'organization': _('Organizations'),
                                    'groups': _('Groups'),
                                    'tags': _('Tags'),
                                    'res_format': _('Formats'),
                                    'license_id': _('Licenses')}

            package_type_facets = 'organization groups tags res_format license_id'
            for facet in config.get('search.facets', package_type_facets.split()):
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            self._update_facet_titles(facets, group_type)

            toolkit.g.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': 'type:dataset',
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

            toolkit.g.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            toolkit.g.group_dict['package_count'] = query['count']

            toolkit.g.search_facets = query['search_facets']
            toolkit.g.search_facets_limits = {}
            for facet in toolkit.g.search_facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                            config.get('search.facets.default', 10)))
                toolkit.g.search_facets_limits[facet] = limit
            toolkit.g.page.items = query['results']

            toolkit.g.sort_by_selected = sort_by

        except search.SearchError as se:
            log.error('Group search error: %r', se.args)
            toolkit.g.query_error = True
            toolkit.g.page = h.Page(collection=[])

        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)

    def read_aplicativo(self, id, limit=20):

        # Variáveis para a view identificar qual guia deve ser ativada e definir o tipo de resultado
        # nos resultados. 
        toolkit.g.dataset = False
        toolkit.g.aplicativo = True
        toolkit.g.concurso = False

        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = { 'id': id, 'type': group_type}

        # unicode format (decoded from utf8)
        toolkit.g.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = True
            toolkit.g.group_dict = self._action('group_show')(context, data_dict)
            toolkit.g.group = context['group']
        except (NotFound, NotAuthorized):
            toolkit.abort(404, _('Group not found'))

        self._read_aplicativo(id, limit, group_type)
        
        return toolkit.render('organization/view_scheming_organization.html')

        #return toolkit.render(self._read_template(toolkit.g.group_dict['type']),
        #              extra_vars={'group_type': group_type})

    def _read_aplicativo(self, id, limit, group_type):
        ''' This is common code used by both read and bulk_process'''
        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = toolkit.g.q = request.params.get('q', '')
        # Search within group
        if toolkit.g.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % toolkit.g.group_dict.get('id')
        else:
            q += ' groups:"%s"' % toolkit.g.group_dict.get('name')

        toolkit.g.description_formatted = \
            h.render_markdown(toolkit.g.group_dict.get('description'))

        context['return_query'] = True

        page = h.get_page_number(request.params)

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        sort_by = request.params.get('sort', None)

        def search_url(params):
            controller = lookup_group_controller(group_type)
            action = 'bulk_process' if toolkit.g.action == 'bulk_process' else 'read'
            url = h.url_for(controller=controller, action=action, id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, str)
                       else str(v)) for k, v in params]
            return url + '?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=toolkit.g.group_dict.get('name')),
                                   new_params=by)

        toolkit.g.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            controller = lookup_group_controller(group_type)
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller=controller, action='read',
                                      extras=dict(id=toolkit.g.group_dict.get('name')))

        toolkit.g.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            toolkit.g.fields = []
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

            default_facet_titles = {'organization': _('Organizations'),
                                    'groups': _('Groups'),
                                    'tags': _('Tags'),
                                    'res_format': _('Formats'),
                                    'license_id': _('Licenses')}

            package_type_facets = 'organization groups tags res_format license_id'
            for facet in config.get('search.facets', package_type_facets.split()):
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            self._update_facet_titles(facets, group_type)

            toolkit.g.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': 'type:aplicativo',
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

            toolkit.g.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            toolkit.g.group_dict['package_count'] = query['count']

            toolkit.g.search_facets = query['search_facets']
            toolkit.g.search_facets_limits = {}
            for facet in toolkit.g.search_facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                            config.get('search.facets.default', 10)))
                toolkit.g.search_facets_limits[facet] = limit
            toolkit.g.page.items = query['results']

            toolkit.g.sort_by_selected = sort_by

        except search.SearchError as se:
            log.error('Group search error: %r', se.args)
            toolkit.g.query_error = True
            toolkit.g.page = h.Page(collection=[])

        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)

    def read_concurso(self, id, limit=20):
        
        # Variáveis para a view identificar qual guia deve ser ativada e definir o tipo de resultado
        # nos resultados. 
        toolkit.g.dataset = False
        toolkit.g.aplicativo = False
        toolkit.g.concurso = True

        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = { 'id': id, 'type': group_type}

        # unicode format (decoded from utf8)
        toolkit.g.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = True
            toolkit.g.group_dict = self._action('group_show')(context, data_dict)
            toolkit.g.group = context['group']
        except (NotFound, NotAuthorized):
            toolkit.abort(404, _('Group not found'))

        self._read_concurso(id, limit, group_type)
        
        return toolkit.render('organization/view_scheming_organization.html')

        #return toolkit.render(self._read_template(toolkit.g.group_dict['type']),
        #              extra_vars={'group_type': group_type})

    def _read_concurso(self, id, limit, group_type):
        ''' This is common code used by both read and bulk_process'''
        context = {'model': model, 'session': model.Session,
                   'user': toolkit.g.user,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = toolkit.g.q = request.params.get('q', '')
        # Search within group
        if toolkit.g.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % toolkit.g.group_dict.get('id')
        else:
            q += ' groups:"%s"' % toolkit.g.group_dict.get('name')

        toolkit.g.description_formatted = \
            h.render_markdown(toolkit.g.group_dict.get('description'))

        context['return_query'] = True

        page = h.get_page_number(request.params)

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        sort_by = request.params.get('sort', None)

        def search_url(params):
            controller = lookup_group_controller(group_type)
            action = 'bulk_process' if toolkit.g.action == 'bulk_process' else 'read'
            url = h.url_for(controller=controller, action=action, id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, str)
                       else str(v)) for k, v in params]
            return url + '?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=toolkit.g.group_dict.get('name')),
                                   new_params=by)

        toolkit.g.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            controller = lookup_group_controller(group_type)
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller=controller, action='read',
                                      extras=dict(id=toolkit.g.group_dict.get('name')))

        toolkit.g.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            toolkit.g.fields = []
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

            default_facet_titles = {'organization': _('Organizations'),
                                    'groups': _('Groups'),
                                    'tags': _('Tags'),
                                    'res_format': _('Formats'),
                                    'license_id': _('Licenses')}

            package_type_facets = 'organization groups tags res_format license_id'
            for facet in config.get('search.facets', package_type_facets.split()):
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            self._update_facet_titles(facets, group_type)

            toolkit.g.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': 'type:concurso',
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

            toolkit.g.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            toolkit.g.group_dict['package_count'] = query['count']

            toolkit.g.search_facets = query['search_facets']
            toolkit.g.search_facets_limits = {}
            for facet in toolkit.g.search_facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                            config.get('search.facets.default', 10)))
                toolkit.g.search_facets_limits[facet] = limit
            toolkit.g.page.items = query['results']

            toolkit.g.sort_by_selected = sort_by

        except search.SearchError as se:
            log.error('Group search error: %r', se.args)
            toolkit.g.query_error = True
            toolkit.g.page = h.Page(collection=[])

        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)