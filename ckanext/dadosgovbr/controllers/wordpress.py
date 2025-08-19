# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from flask import request, response, redirect
import requests

# Wordpress integration
import ckanext.dadosgovbr.helpers.wordpress as wp


class NoticiasController(p.toolkit.BaseController):

    def redirect (ctrl, slug):
        return redirect('/noticia/'+slug)

    def show (ctrl, slug):
        toolkit.g.wp_post = wp.post(slug)
        return toolkit.render('wordpress/post_single.html')

    def list (ctrl):
        if ('page' in request.args):
            toolkit.g.wp_page_number = int(request.args['page'])
        else:
            toolkit.g.wp_page_number = int(1)

        toolkit.g.title = "Notícias"
        toolkit.g.wp_posts = wp.posts(10, toolkit.g.wp_page_number)
        return toolkit.render('wordpress/posts.html')

    def feed (ctrl):
        # Get content from feed URL
        url     = "http://wp.dados.gov.br/wp/feed"
        feed    = requests.get(url)
        content = feed.content

        # Update URL to mask Wordpress path
        #content = content.replace("dados.gov.br/wp", "dados.gov.br/noticias")

        # Set header for XML content
        response.headers['Content-Type'] = 'text/xml; charset=utf-8'

        return content


class PaginasController(p.toolkit.BaseController):
    def index (ctrl, slug):
        toolkit.g.wp_page = wp.page(slug)
        return toolkit.render('wordpress/page_single.html')

    def redirect (ctrl, slug):
        return redirect('/pagina/'+slug)

