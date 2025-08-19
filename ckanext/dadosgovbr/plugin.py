# -*- coding: utf-8 -*-


import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from collections import OrderedDict
from flask import redirect, request
import json

# Custom helper
from ckanext.dadosgovbr import helpers


class DadosgovbrPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    ''' Plugin Dados Abertos

        Classe principal.
        - Define recriação do schema do Solr
        - Define diretórios para imagens, CSS e JS
        - Define mapeamento para novas rotas
        - Define novos helpers
    '''
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)



    # Recriação do schema (Solr)
    # =======================================================
    def scheming_get_types(self):
        return ['concurso', 'aplicativo', 'inventario']

    def read(self, entity):
        # HACK: Show private package or resource (block for not logged in users)
        if request.endpoint == 'package.read':
            if entity.private and not toolkit.g.user:
                toolkit.abort(403, 'Acesso negado!')

        # HACK: Edit package or resource (block for not logged in users)
        if request.endpoint in ['package.edit', 'resource.edit']:
            if not toolkit.g.user:
                toolkit.abort(403, 'Acesso negado!') 
        
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_search(self, search_params):
        # Redirect for search page
        schemas = self.scheming_get_types()
        url_current = toolkit.h.full_current_url()
        if(url_current.replace(toolkit.g.site_url+'/','') in schemas):
            return redirect(url_current.replace(toolkit.g.site_url,'')+'s')
        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, data_dict):
        # All multiValue fields from ckanext-scheming
        multiValue = ['dados_abertos_base', 'atualizacoes_base', 'informacoes_publicas_base']

        for i, value in enumerate(multiValue):
            # If package has "multiValue"
            if('extras_'+value in data_dict):
                # Add to Solr schema
                data_dict[multiValue[i]] = []

                # If package has multi value for multiValue field
                try:
                    for item in json.loads(data_dict['extras_'+value]):
                        data_dict[multiValue[i]].append(item)
                    #print(data_dict[multiValue[i]])
                
                # If package has just one value for multiValue field
                except:
                    data_dict[multiValue[i]].append(data_dict['extras_'+value])
                    #print(data_dict['extras_'+value])
        return data_dict

    def before_view(self, pkg_dict):
        # Redirect to correct URL based on schema name
        actions_accepted = ['read','edit','new']
        if (request.endpoint in ['package.read', 'package.edit', 'package.new']):
            schema_expected = pkg_dict['type']
            schema_current  = str(toolkit.h.full_current_url()).replace(toolkit.g.site_url, '').split('/')[1]
            if (schema_current != schema_expected):
                url_current = toolkit.h.full_current_url()
                url_current = str(url_current).replace(toolkit.g.site_url+'/'+schema_current, toolkit.g.site_url+'/'+schema_expected)
                # print('redir_to',url_current)
                # print(schema_expected)
                # print(schema_current)
                return redirect(url_current.replace(toolkit.g.site_url,''))
        return pkg_dict

    def after_create(self, context, data_dict):
        return data_dict

    def after_update(self, context, data_dict):
        return data_dict

    def after_delete(self, context, data_dict):
        return data_dict

    def after_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles


    # Diretórios para templates e arquivos estáticos
    # =======================================================
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        #toolkit.add_resource('fanstatic', 'dadosgovbr')

    
    
    # Nota: Mapeamento de rotas removido - não é mais suportado no CKAN moderno
    # As rotas devem ser configuradas via Blueprint ou outro mecanismo




    # Registro dos helpers
    # =======================================================
    def get_helpers(self):
        '''Register all functions

        '''
        
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
            # Homepage
            'dadosgovbr_most_recent_datasets': helpers.tools.most_recent_datasets,

            # Wordpress
            'dadosgovbr_wordpress_posts': helpers.wordpress.posts,
            'dadosgovbr_format_timestamp': helpers.wordpress.format_timestamp,

            # Scheming
            'dadosgovbr_get_schema_name': helpers.scheming.get_schema_name,
            'dadosgovbr_get_schema_title': helpers.scheming.get_schema_title,

            # Generict tools
            'dadosgovbr_trim_string': helpers.tools.trim_string,
            'dadosgovbr_trim_letter': helpers.tools.trim_letter,
            'dadosgovbr_resource_count': helpers.tools.resource_count,
            'dadosgovbr_get_featured_group': helpers.tools.get_featured_group,
            'dadosgovbr_get_organization_extra': helpers.tools.get_organization_extra,
            'dadosgovbr_get_package': helpers.tools.get_package,
            'dadosgovbr_cache_create': helpers.tools.cache_create,
            'dadosgovbr_cache_load': helpers.tools.cache_load,
            'dadosgovbr_group_id_or_name_exists': helpers.tools.group_id_or_name_exists,

            # e-Ouv
            'dadosgovbr_eouv_is_avaliable': helpers.tools.eouv_is_avaliable,
            'dadosgovbr_get_contador_eouv': helpers.tools.helper_get_contador_eouv
        }
        
