# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan import model
from flask import request, response, redirect
import requests

# Wordpress integration
import ckanext.dadosgovbr.helpers.wordpress as wp

# ============================================================
# Aplicativos
# ============================================================
class AplicativosController(p.toolkit.BaseController):
    def index (ctrl):
        # Query
        from ckan.logic import get_action
        context = {'model': model, 'session': model.Session,
                'user': toolkit.g.user or toolkit.g.author}

        # Get "aplicativos"
        data_dict = {'fq': 'type:aplicativo'}
        toolkit.g.aplicativos = get_action('package_search')(context, data_dict)['results']

        # Get page content from Wordpress
        wp_page_slug = 'scheming_aplicativos'
        toolkit.g.wp_page = type('Nothing', (object,), {})  
        toolkit.g.wp_page.content = type('Nothing', (object,), {})  
        toolkit.g.wp_page.content.rendered = "Conteudo da pagina nao encontrado..."
        try:
            toolkit.g.wp_page = wp.page(wp_page_slug)
        except:
            pass

        # DEBUG
        # from pprint import pprint
        # pprint(toolkit.g.aplicativos)


        # Get search params from URL
        if request.method == 'GET' and 's' in request.args:
            toolkit.g.s_result    = request.args['s']
        else:
            toolkit.g.s_result    = ""


        return toolkit.render('scheming/aplicativo/search_bkp.html')


    
    def single (ctrl, title):
        from ckan.logic import get_action
        context = {'model': model, 'session': model.Session,
                'user': toolkit.g.user or toolkit.g.author}

        # Get app
        data_dict = {'id': title, 'include_extras': 'True'}
        app = get_action('package_show')(context, data_dict)
        toolkit.g.app_dict = app

        # DEBUG
        from pprint import pprint
        pprint(app)

        toolkit.g.app_title = title
        return toolkit.render("scheming/aplicativo_modal.html")
