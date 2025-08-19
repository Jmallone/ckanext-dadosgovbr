# -*- coding: utf-8 -*-
import ckan.plugins.toolkit as toolkit
from ckan.lib.helpers import full_current_url

def get_schema_name(dataset_name=None):
    ''' Return schema name '''
    if(dataset_name == None):
        schema_name = str(full_current_url()).replace(toolkit.g.site_url, '').split('/')[1].split('?')[0]
        if(schema_name[-1:]=='s'):
            schema_name=schema_name[:-1]
        # print(schema_name)
        return schema_name
    return 'dataset'

def get_schema_title(schema_name=None, plural=False):
    ''' Return schema title '''
    schema_titles = {}
    schema_titles['aplicativo']         = "aplicativo"
    schema_titles['aplicativo_plural']  = "aplicativos"
    schema_titles['concurso']           = "concurso"
    schema_titles['concurso_plural']    = "concursos"
    schema_titles['inventario']         = "item de inventário"
    schema_titles['inventario_plural']  = "itens de inventário"
    schema_titles['dataset']            = "conjunto de dados"
    schema_titles['dataset_plural']     = "conjuntos de dados"
    if(schema_name==None):
        schema_name=get_schema_name()
    if(schema_name in schema_titles):
        if(plural):
            return schema_titles[schema_name+'_plural']
        else:
            return schema_titles[schema_name]
    return 'resultado(s)'
