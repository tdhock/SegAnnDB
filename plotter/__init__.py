from pyramid.config import Configurator
from pyramid.request import Request
import db

# sudo easy_install pyramid_persona
# https://github.com/madjar/pyramid_persona/
# add 2 lines to development.ini
# persona.secret = sdajk3287781232rhjkas wasd 89u23eniu123hr89 3
# persona.audiences = localhost:8080

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    Format of entries is -
    <'route_name', 'route_path/url'>
    """
    config = Configurator(settings=settings)
    config.include("seganndb_login")
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    #config.add_route('delete_profiles', '/delete_profiles/')
    config.add_route('delete_profile', '/delete_profile/{name}/')
    config.add_route('upload', 'upload')
    config.add_route('initial', '/initial/{profiles}/{chromosomes}/')
    config.add_route('profile', '/profile/{name}/')
    config.add_route('old_chrom', '/profile/{name}/{chr}/')
    config.add_route("new_chrom", "/profile_new/{name}/{chr}/")
    config.add_route('delete_region',
                     '/delete_region/{name}/{chr}/{trackType}/{id}/')
    config.add_route('add_region',
              '/add_region/{name}/{chr}/{trackType}/{annotation}/{min}/{max}/')
    config.add_route("export","/export/{user}/{name}/{what}/{format}/")
    config.add_route('trackhub_export', '/trackhub_init/')
    config.add_route('trackhub_details', '/trackhub_details/{short_name}/')
    config.add_route('trackhub_file', '/trackhub/{short_name}/*file')
    config.add_route('trackhub_list', '/trackhub_list/')
    name_regex = db.HEADER_PATTERNS["name"]
    # config.add_route("secret","/secret/{name:%s}{suffix}"%name_regex)
    config.add_route("secret","/secret/{profile_name}/{name:%s}{suffix}"%name_regex)
    config.add_route("secret_new","/secret/{profile_name}/{chr_num}/{name:%s}{suffix}"%name_regex)
    config.add_route("all_profiles","/all_profiles/")
    config.add_route("view_profiles","/view_profiles/")
    config.add_route("csv_profiles","/csv_profiles/")
    config.add_route("links","/links/{name}/")
    config.add_route("about","/about/")
    config.add_route("random","/random/")
    config.scan()
    return config.make_wsgi_app()
