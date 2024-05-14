#!/usr/bin/env python3
import asyncio
from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from time import sleep
from nicegui import Client, app, ui, events, run
import pandas as pd
import os, re, json, random, time, sys, shutil
from pathlib import Path
import platform
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


# local functools import
from utils.common import Common
from utils.config import Config
from utils.login import Login
from utils.local_file_picker import local_file_picker

# code path
root_path = os.path.dirname(os.path.abspath(__file__))
# config path
config_path = os.path.join(root_path, "config.json")
# base config init
config = Config(config_path)


# read config
log_config = config.get("log")
validator = Login(log_file=log_config.get('user_log'))
admin_users = config.get("admin_users")

# logger config init
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# user logger
login_logger = logging.getLogger('user_login')
login_logger.setLevel(logging.INFO)
login_log_handler = logging.FileHandler(filename=log_config.get('user_log'), mode='a', encoding='utf8')
login_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
login_log_handler.setFormatter(login_formatter)
login_logger.addHandler(login_log_handler)

# error log handler
error_log_handler = logging.FileHandler(filename=log_config.get('error_log'), mode='a', encoding='utf8')
error_log_handler.setLevel(logging.ERROR)
error_log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')
error_log_handler.setFormatter(error_log_formatter)
root_logger.addHandler(error_log_handler)

# 运行日志（可选，根据需要调整日志级别）
runtime_log_handler = logging.FileHandler(filename=log_config.get('runtime_log'), mode='a', encoding='utf8')
runtime_log_handler.setLevel(logging.DEBUG)
runtime_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
runtime_log_handler.setFormatter(runtime_formatter)
root_logger.addHandler(runtime_log_handler)

# user login func
def log_user_login(user, login_status):
    log_message = f"{user} - {login_status}"
    login_logger.info(log_message)

# default route
unrestricted_page_routes = {'/login'}

# 封装的nicegui fastapi http 服务
class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)


# add middleware
app.add_middleware(AuthMiddleware)
app.add_static_files(local_directory="imgs", url_path="/imgs")
        

# login page
@ui.page('/login')
def login() -> Optional[RedirectResponse]:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        # init auth config
        auth_mode = config.get('auth_mode')
        if auth_mode == "local":
            local_auth = eval(config.get('local_users'))
        elif auth_mode == "ldap":
            ldap_auth = Common.ldap_auth(username.value, password.value)
        elif auth_mode == "ldap3":
            ldap3_auth = Common.ldap3_auth(username.value, password.value)
        
        # login auth       
        if username.value == "" or password.value == "":
            ui.notify('Username and password cannot be empty', color='negative', position='top')
        # login limit check
        elif not validator.check_login_status(username=username.value):
            ui.notify('Too many login attempts. Please refresh your browser and try again in ten minutes!', type='ongoing', color='warning', position='top', )
            ui.run_javascript("document.getElementById('c10').disabled = true")
        elif (auth_mode == "ldap3" and ldap3_auth) or (auth_mode == "ldap" and ldap_auth):
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
            log_user_login(user=username.value, login_status="login succeed")
        elif auth_mode == "local" and local_auth.get(f'{username.value}') == password.value:
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to(app.storage.user.get('referrer_path', '/')) 
            log_user_login(user=username.value, login_status="login succeed")
        else:
            ui.notify(f'Could not authenticate you from Ldapmain because "Invalid credentials for {username.value}"', color='negative', position='top')
            log_user_login(user=username.value, login_status="login failed")
            
    # login status check
    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')
    
    # login type
    if "ldap" in config.get('auth_mode'):
        auth_type = "LDAP"
    else:
        auth_type = "Standard"
    
    ui.query(".nicegui-content").classes("bg-[url('/imgs/bg.jpg')] bg-cover").style('height: 100vh')
    with ui.card().classes("backdrop-blur-sm bg-white/30 p-10 w-[20%] gap-4 absolute-center"):
        # login_icon = ui.icon('account_circle', color='primary').style("float:center; ")
        ui.label("Sign in").classes("text-h4 ").style("align-self:center; text-align:center")
        username = ui.input('username').on('keydown.enter', try_login).style(
            "width:100%;height:auto;align-self:center; text-align:center")
        password = ui.input('password', password=True, password_toggle_button=True).on('keydown.enter', try_login).style(
            "width:100%;height:auto;align-self:center; text-align:center")
        ui.button('Sign in', on_click=try_login).style(
            "width:100%;height:auto;align-self:center;text-align:center;font-size:1.1rem")
        ui.label(f'Verification Method：{auth_type}').classes('text-subtitle2 text-center').style("color: white; opacity: 0.8;")
    
    ui.label("Copyright © 2020 - 2024 ITShareStudio").classes('absolute-bottom text-subtitle2 text-center').style('color: white; opacity: 0.8;')

    return None


# home page
@ui.page('/')
async def main_page(client: Client) -> None:
    download_path = config.get("download_path")
    username = app.storage.user["username"]
    download_path = download_path + '/' + username
        
    async def pick_file() -> None:
        # pop up the file picker and notify the user of the selected file
        result = await local_file_picker("{}".format(download_path), multiple=True)
        
        # determine file path and download file
        if result and len(result) > 0:
            filename_path = re.sub("/data/", "", result[0])
            filename = filename_path.split("/")[-1]
            if os.path.isfile(result[0]):
                ui.notify(f'You chose {filename_path}')
                ui.download(result[0], filename, "application/octet-stream")
                logging.info(msg="{} download file: {}".format(username, result))
        
    with ui.header().style("background-color: #3874c8").classes("items-center justify-between"):
        ui.label("X-EPIC Web Transfer Client").classes("text-2xl")
        ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')), icon='logout').props(
            'outline round color=white').classes("right")

    with ui.left_drawer(fixed=True, bottom_corner=True).style("background-color: #d7e3f4"):
        ui.chat_message(f'Hello {app.storage.user["username"]}!',name='Robot',stamp='now', avatar='https://robohash.org/ui')
        ui.chat_message(f'Welcome to Web Transfer Client. You can download the necessary files.',name='Robot',stamp='now', avatar='https://robohash.org/ui')
        ui.button("Download", on_click=pick_file).style("width: 100%")
        with ui.button(on_click=lambda: ui.notify('Redirecting...')).style("width: 100%"):
            ui.link('Feedback', 'https://github.com/levywang/ftp-web-client/discussions').style("width: 90%; color: white; text-decoration: none")
        if username in admin_users:
            ui.button("Admin", on_click=lambda: (ui.navigate.to('/admin'))).style("width: 100%;")
        ui.button("Logout", on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))).style("width: 100%;")

    with ui.element('div'):
        ui.query(".nicegui-content").style("height:100%; background-image: url('/imgs/bg.jpg'); background-size: cover;  background-position: center;")
        ui.label("Prompt: Click the 'DOWNLOAD' button to download your files.").style('color: white')
        ui.run_javascript("document.getElementById('c3').style.height = document.getElementById('c2').style.minHeight")
    
    await client.connected()
    await pick_file()

@ui.page('/admin')
async def admin_page(client: Client) -> None:
    """
    Check and enforce admin access for a user.

    Args:
    - client: A client connection instance.

    Returns:
    - None: The function doesn't return any value.
    """
    
    # Get the current user's username
    username = app.storage.user['username']
    # If the user isn't an admin, deny access
    if username not in admin_users:
        # Notify the user and display unauthorized message
        ui.query(".nicegui-content").classes("bg-[url('/imgs/bg.jpg')] bg-cover backdrop-opacity-10").style('height: 100vh')
        ui.notify(f'{username} is not an administrator user!', color='negative', position='top')
        with ui.row().classes('h-screen w-full items-center justify-center'):
            ui.chip('Access denied!', icon='block', color='red', text_color='white').set_enabled(False)
        return None

    # storage init value
    app.storage.user['level'] = 'DEBUG'
    app.storage.user['rows'] = '100'
    app.storage.user['logpath'] = log_config.get('user_log')
    
    async def alert_log(level, rows, keyword=None) -> None:
        """
        Asynchronous function to read the log file based on the specified log level and 
        push the last few lines of the log to the page.

        Parameters:
        - level: The log level, determining which type of log file to read (USER, DEBUG, ERROR).
        - rows: The number of log rows to display, an integer.
        - keyword: An optional parameter for filtering logs. If provided, only lines containing this keyword will be displayed.

        Returns:
        - None
        """
        # Set the log file path based on the log level
        if level == 'USER':
            app.storage.user['logpath'] = log_config.get('user_log')
        elif level == 'DEBUG':
            app.storage.user['logpath'] = log_config.get('runtime_log')
        elif level == 'ERROR':
            app.storage.user['logpath'] = log_config.get('error_log')

        filepath = app.storage.user['logpath']

        # Read the last few lines from the log file
        rows = int(rows)
        with open(filepath, 'r') as file:
            lines = file.readlines()[-rows:]

        # Filter the log based on the presence of the keyword
        if keyword:
            # If a keyword is provided, filter out log lines not containing it
            keyword = keyword.lower()
            content = '\n'.join(line for line in lines if keyword in line.lower())
        else:
            content = '\n'.join(lines)

        # Clear the existing log content on the page
        await ui.run_javascript(f'document.getElementById("c69").innerHTML = ""')

        # Push the filtered log content to the page
        log.push(content)

    #  download log file      
    async def download_log_file(level) -> None:
        if level == 'USER':
            filepath = log_config.get('user_log')
        elif level == 'DEBUG':
            filepath = log_config.get('runtime_log')
        elif level == 'ERROR':
            filepath = log_config.get('error_log')

        filename = filepath.split('/')[-1]
        if os.path.isfile(filepath):
            ui.notify(f'You chose download file: {filename}', type='positive')
            ui.download(filepath, filename, "application/octet-stream")
            logging.info(f'Download file: {filepath}')
        else:
            ui.notify(f'File not found: {filename}', type='warning')
            logging.error(f'File not found: {filename}')

    # dark mode switch
    dark = ui.dark_mode(True)
    def change_light_status():
        if dark.value:
            button_light.set_text("Dark Mode")
        else:
            button_light.set_text("Light Mode")
        dark.toggle()
    def save_config():
        """
        Saves the configuration file. Updates the global variables `config` and `config_path`, 
        then writes the updated configuration data into the file.
        If an exception occurs while reading or writing the configuration file, error logs are recorded 
        and the user is notified.

        Returns:
            - True: Configuration data successfully written to the file.
            - False: An error occurred while writing the configuration file.
        """

        global config, config_path

        # Attempt to read the configuration file
        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logging.error(f"Unable to read the configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to read the configuration file! {e}")
            return False

        # Write the configuration to the file
        try:
            # Update configuration items
            # Administrator users
            config.update(["admin_users"], input_admin_users.value)
            # Authentication mode
            config.update(["auth_mode"], select_auth_mode.value)
            # Download path configuration
            config.update(["download_path"], input_download_path.value)
            # LDAP configuration
            config.update(["local_users"], input_local_users.value)
            config.update(["ldap", "server"], input_ldap_server.value)
            config.update(["ldap", "password"], input_ldap_password.value)
            config.update(["ldap", "search_base"], input_ldap_search_base.value)
            config.update(["ldap", "dn"], input_ldap_dn.value)
            # LDAP3 configuration
            config.update(["ldap3", "server"], input_ldap3_server.value)
            config.update(["ldap3", "port"], int(input_ldap3_port.value))
            config.update(["ldap3", "domain"], input_ldap3_domain.value)
            # Logging configuration
            config.update(["log", "user_log"], input_user_log_path.value)
            config.update(["log", "runtime_log"], input_runtime_log_path.value)
            config.update(["log", "error_log"], input_error_log_path.value)
            logging.info("Configuration data successfully written to the file!")
            ui.notify(position="top", type="positive", message="Configuration data successfully written to the file!")

            return True
        except Exception as e:
            logging.error(f"Unable to write to the configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to write to the configuration file!\n{e}")
            return False
    
    def export_config():
        global config, config_path
        try:
            ui.download(config_path, "config.json", "application/json")
            ui.notify(position="top", type="positive", message="Configuration data has been exported successfully!")
        except Exception as e:
            logging.error(f"Unable to export configuration file!\n{e}")
            ui.notify(position="top", type="negative", message=f"Unable to export configuration file!\n{e}")


    async def bypass_login_restrictions(users) -> None:
        for user in users:
            if user == 'username':
                ui.notify(position="top", type="negative", message=f"user list is empty")
            else:
                validator.remove_failed_logins_from_file(username=user)
                ui.notify(position="top", type="positive", message=f"user: {user} login restrictions have been removed!")

     # clear specify log file
    async def clear_log_file(level) -> None:
        if level == 'USER':
            filepath = log_config.get('user_log')
        elif level == 'DEBUG':
            filepath = log_config.get('runtime_log')
        elif level == 'ERROR':
            filepath = log_config.get('error_log')

        if os.path.isfile(filepath):
            with open(filepath, 'w') as file:
                file.write('')
            ui.notify(position="top", type="positive", message=f"{level} log has been cleared!")
            logging.info(f"{level} log has been cleared!")
        else:
            ui.notify(position="top", type="warning", message=f"{level} log does not exist!")

    # clear .nicegui dir cache files
    async def clear_cache() -> None:
        filepath = root_path + '/.nicegui/'
        try:
            if os.path.exists(filepath):
                shutil.rmtree(filepath)
            ui.notify(position="top", type="positive", message=f"Cache has been cleared! {filepath}")
            logging.info(f"Cache has been cleared!")
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"Unable to clear cache!\n{e}")
            logging.error(f"Unable to clear cache!\n{e}")
            
    
    # Manage page paging
    ui.query(".nicegui-content").classes("bg-[url('/imgs/bg.jpg')] bg-cover backdrop-opacity-10").style('height: 100vh')
    with ui.splitter(value=10).classes('w-full h-full bg-slate-500/[0.06] backdrop-opacity-10') as splitter:
        with splitter.before:
            with ui.tabs().props('vertical').classes('w-full') as tabs:
                config_tab = ui.tab('Config', icon='settings').style("color: white")
                admin_tab = ui.tab('Admin', icon='admin_panel_settings').style("color: white")
                log_tab = ui.tab('Logs', icon='assignment').style("color: white")
                about_tab = ui.tab('About', icon='assignment').style("color: white")
        with splitter.after:
            with ui.tab_panels(tabs, value=config_tab).props('vertical').classes('w-full h-full backdrop-opacity-10 backdrop-invert bg-white/5'):
                with ui.tab_panel(config_tab):
                    ui.label("Basic Configuration")
                    with ui.row():
                        select_auth_mode = ui.select(
                            label='auth_mode', 
                            options={
                                'local': 'LOCAL', 
                                'ldap': 'LDAP', 
                                'ldap3': 'LDAP3'
                            }, 
                            value=config.get("auth_mode")
                        ).style("width:200px;")
                        input_download_path = ui.input(label='download path', placeholder='default bind directory', value=config.get("download_path")).style("width:200px;")
                    
                    ui.label("Local Auth Configuration")
                    with ui.row():
                        input_local_users = ui.input(label='local users', placeholder='default value: {\'admin\': \'123456\'}', value=str(config.get("local_users"))).classes('w-64')
                        input_admin_users = ui.input(label='admin user list', placeholder='default value: [\'admin\']', value=str(config.get("admin_users"))).classes('w-64')

                    ui.label("LDAP3 Auth Configuration")
                    with ui.row():
                        input_ldap3_server = ui.input(label='ldap3 server address', value=config.get("ldap3").get("server")).style("width:200px;")
                        input_ldap3_port = ui.input(label='ldap3 server port', value=config.get("ldap3").get("port")).style("width:100px;")
                        input_ldap3_domain = ui.input(label='ldap3 domain', value=config.get("ldap3").get("domain")).style("width:200px;")

                    ui.label("LDAP Auth Configuration")
                    with ui.row():
                        input_ldap_server = ui.input(label='ldap server address', value=config.get("ldap").get("server")).style("width:200px;")
                        input_ldap_dn = ui.input(label='ldap bind cn', value=config.get("ldap").get("dn")).style("width:300px;")
                        input_ldap_password = ui.input(label='ldap bind password', value=config.get("ldap").get("password")).style("width:200px;")
                        input_ldap_search_base = ui.input(label='ldap search base', value=config.get("ldap").get("search_base")).style("width:300px;")
                      
                    ui.label("Log Configuration")
                    with ui.row():
                        input_user_log_path = ui.input(label='user log path', value=config.get("log").get("user_log")).style("width:200px;")
                        input_runtime_log_path = ui.input(label='runtime log path', value=config.get("log").get("runtime_log")).style("width:200px;")
                        input_error_log_path = ui.input(label='error log path', value=config.get("log").get("error_log")).style("width:200px;")
                    
                    with ui.grid(columns=6).style("position: fixed; bottom: 10px; text-align: center;"):
                        button_save = ui.button('Save', on_click=lambda: save_config())
                        button_run = ui.button('Export', on_click=lambda: export_config())
                        button_light = ui.button('Light Mode', on_click=lambda: change_light_status())
                        button_logout = ui.button("Logout", on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))).style("width: 100%;")

                with ui.tab_panel(admin_tab).classes('backdrop-opacity-10'):
                    ui.label("User activity")
                    with ui.row():
                        today = datetime.now().date()
                        daily_login_stats, user_login_status = validator.get_login_counts()
                        succeed_list = [value['succeed'] for value in daily_login_stats.values()]
                        failed_list = [value['failed'] for value in daily_login_stats.values()]
                        ui.label(f'today total login count: {daily_login_stats[today]["succeed"] + daily_login_stats[today]["failed"]}')
                        ui.label(f'today total login succeed count: {daily_login_stats[today]["succeed"]}')
                        ui.label(f'today total login failed count: {daily_login_stats[today]["failed"]}')
                    ui.echart({
                        'xAxis': {'type': 'category', 'data': list(daily_login_stats.keys())},
                        'yAxis': {'type': 'value', },
                        'legend': {'textStyle': {'color': 'gray'}},
                        'series': [
                            {'type': 'line', 'name': 'succeed', 'data': succeed_list},
                            {'type': 'line', 'name': 'failed', 'data': failed_list}],
                        }, on_point_click=ui.notify)

                    ui.label("User Login Control")
                    with ui.row():
                        login_failed_users = validator.get_recent_failed_users()
                        select_login_failed_users = ui.select(options=login_failed_users, label='user list', with_input=True, multiple=True, clearable=True, value='username', on_change=lambda e: ui.notify(e.value))
                        ui.button("Unlock", on_click=lambda: bypass_login_restrictions(select_login_failed_users.value)).bind_visibility(select_login_failed_users, 'value')

                    ui.label("Log Management")
                    with ui.row():
                        select_log_level = ui.select(['USER', 'DEBUG', 'ERROR'], label="log level", value='USER', on_change=lambda e: app.storage.user.update(level=e.value)).classes('w-36')
                        ui.button("Clear", on_click=lambda: clear_log_file(select_log_level.value))

                    ui.label("System Management")
                    with ui.row():
                        ui.button("Clear Cache", on_click=lambda: clear_cache())
                    
                with ui.tab_panel(log_tab).classes('backdrop-opacity-10'):
                    with ui.grid(columns=12).classes('w-full h-12'):
                        rows_select = ui.select(['50', '100', '200', '300'], label="Rows", value='50', on_change=lambda e: app.storage.user.update(rows=e.value))
                        level_select = ui.select(['USER', 'DEBUG', 'ERROR'], label="Level", value='DEBUG', on_change=lambda e: app.storage.user.update(level=e.value))
                        filter = ui.input(label='Filter', placeholder='Keyword', autocomplete=['user', 'download', 'error', 'debug'])
                        ui.button('View', on_click=lambda: alert_log(level=app.storage.user['level'], rows=app.storage.user['rows'], keyword=filter.value),icon='visibility').props('no-caps')
                        ui.button('Download', on_click=lambda: download_log_file(level=level_select.value), icon='download').bind_visibility(level_select, 'value').props('no-caps').classes('text-[12px]')
                        ui.button('Clear', on_click=lambda: ui.run_javascript(f'document.getElementById("c69").innerHTML = ""'), icon='delete').props('no-caps')
                    
                    log = ui.log().classes('w-full h-full')
                with ui.tab_panel(about_tab).classes('backdrop-opacity-10'):
                    with ui.timeline(side='right'):
                        ui.timeline_entry('The first version, providing basic login and file download functions.',
                                        title='Release of 1.0.0',
                                        subtitle='May 14, 2024',
                                        icon='rocket')
                    
                    with ui.row().style("position: fixed; bottom: 10px; text-align: center;"):
                        ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
                        with ui.link(target='https://github.com/levywang/ftp_web_client').classes('absolute bottom-20'):
                            ui.icon('eva-github', color='primary').classes('text-5xl')
                        ui.label('Author:').style("text-align: left")
                        ui.link('levywang', 'https://github.com/levywang/')
                        ui.label('Powered by').style("text-align: left")
                        ui.link('NiceGUI', 'https://github.com/zauberzeug/nicegui')                        
                        ui.label('Copyright © 2020 - 2024 ITShareStudio. All rights reserved.').style("text-align: left; width: 100%")

ui.run(favicon='imgs/favicon.ico', storage_secret='ftp_web_client', title='Web Transfer Client')