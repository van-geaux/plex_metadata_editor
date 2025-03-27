
#!/usr/bin/env python3
from dotenv import load_dotenv

# import json
import os
import requests
import xml.etree.ElementTree as ET

from nicegui import ui, app
from router import Router

load_dotenv()

def load_settings():
    if os.getenv("PLEX_URL") and os.getenv("PLEX_TOKEN"):
        return {
            "host": os.getenv("PLEX_URL", "").replace('\'','').replace('\"',''),
            "apikey": os.getenv("PLEX_TOKEN", "").replace('\'','').replace('\"','')
        }
    
    else:
        load_dotenv()
        return {
            "host": os.getenv("PLEX_URL", "").replace('\'','').replace('\"',''),
            "apikey": os.getenv("PLEX_TOKEN", "").replace('\'','').replace('\"','')
        }

def save_settings(host, apikey):
    with open(".env", "w") as f:
        f.write(f"PLEX_URL={host}\nPLEX_API_KEY={apikey}\n")
    
cached_data = {}
settings = load_settings()
    
def fetch_data():
    global cached_data
    if settings["host"]:
        headers = {"X-Plex-Token": settings["apikey"]} if settings["apikey"] else {}

        identity_url = f"{settings['host']}/identity"
        try:
            response = requests.get(identity_url, headers=headers)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                cached_data['identity'] = {k: v for k, v in root.attrib.items()}
        except requests.RequestException as e:
            cached_data = {}

        libraries_url =  f"{settings['host']}/library/sections"
        try:
            response = requests.get(libraries_url, headers=headers)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                root = root.findall('Directory')
                cached_data['libraries'] = [elem.attrib for elem in root]
        except requests.RequestException as e:
            cached_data = {}

        butler_url =  f"{settings['host']}/butler"
        try:
            response = requests.get(butler_url, headers=headers)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                root = root.findall('ButlerTask')
                cached_data['butler'] = [elem.attrib for elem in root]
        except requests.RequestException as e:
            cached_data = {}

@ui.page('/')
@ui.page('/{_:path}')
def main():
    router = Router()

    fetch_data()

    @router.add('/')
    def info_page():
        with ui.column().style("margin-left: 220px;"):
            ui.label("Plex Server Information").style("font-size: 24px; font-weight: bold;")
            api_version = ui.label(f"API Version: {cached_data.get('identity').get('apiVersion', 'N/A')}")
            claim_status = ui.label(f"Claimed: {cached_data.get('identity').get('claimed', 'N/A')}")
            machine_id = ui.label(f"Machine Identifier: {cached_data.get('identity').get('machineIdentifier', 'N/A')}")
            version = ui.label(f"Version: {cached_data.get('identity').get('version', 'N/A')}")
            
            def refresh():
                fetch_data()
                api_version.set_text(f"API Version: {cached_data.get('identity').get('apiVersion', 'N/A')}")
                claim_status.set_text(f"Claimed: {cached_data.get('identity').get('claimed', 'N/A')}")
                machine_id.set_text(f"Machine Identifier: {cached_data.get('identity').get('machineIdentifier', 'N/A')}")
                version.set_text(f"Version: {cached_data.get('identity').get('version', 'N/A')}")

            ui.button("Refresh", on_click=refresh)

            ui.separator()

            ui.label("Library Selection").style("font-size: 24px; font-weight: bold;")

            with ui.row().style("flex-wrap: wrap; gap: 10px; justify-content: start;"):
                for library in cached_data.get('libraries', []):
                    with ui.card().style("width: 250px;"):
                        with ui.column():
                            ui.label(f"{library.get('title')}").style("font-size: 18px; font-weight: bold;")
                            # ui.label(f"🔑 Key: {library.get('key')}")
                            ui.label(f"📂 Type: {library.get('type')}")
                            ui.label(f"🤖 Agent: {library.get('agent')}")
                            ui.label(f"🔍 Scanner: {library.get('scanner')}")
                            ui.button("EDIT", on_click=lambda libkey=library.get('key'), lib_title=library.get('title'): set_selected_key_and_navigate(libkey, lib_title)).style("margin-top: auto; width: 120px; text-align: center;")

    def set_selected_key_and_navigate(lib_key, lib_title):
        app.storage.client['selected_library_key'] = lib_key
        app.storage.client['selected_library_name'] = lib_title
        router.open(library_page)

    @router.add('/library')
    def library_page():
        lib_key = app.storage.client.get('selected_library_key')
        lib_title = app.storage.client.get('selected_library_name')
        lib_type = next((d for d in cached_data.get('libraries') if d.get('key') == lib_key )).get('type')
        headers = {"X-Plex-Token": settings["apikey"]} if settings["apikey"] else {}
        library_url = f"{settings['host']}/library/sections/{lib_key}/all"

        def fetch_data():
            try:
                response = requests.get(library_url, headers=headers)
                response.raise_for_status()
                root = ET.fromstring(response.content)

                if lib_type == 'movie':
                    video_items = root.findall('Video')
                elif lib_type == 'show':
                    video_items = root.findall('Directory')
                
                data = []
                for video in video_items:
                    item_data = video.attrib.copy()
                    for child in video:
                        item_data[child.tag] = child.attrib
                    data.append(item_data)
                
                return data
            except Exception as e:
                print(f"Error fetching data: {e}")
                return []
            
        data = fetch_data()

        with ui.column().style("margin-left: 220px;"):
            ui.label(f"📚 {lib_title}").style("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
            ui.label("Warning!!!!!!!!!")
            ui.label("Whatever you edit here is currently not logged.")
            ui.label("This page use PUT API to send whatever you change to your Plex Server, proceed if you understand the risks.")
            ui.label("Double click the field you want to edit, fill it, then hit enter to send the updated data to your server.")

            if data:
                # first_item = data[0]
                columns = [
                    {'headerName': 'Key', 'field': 'ratingKey', "sortable": True, 'editable': False},
                    {'headerName': 'Title', 'field': 'title', "sortable": True, 'editable': True, 'filter': 'agTextColumnFilter', 'floatingFilter': True},
                    {'headerName': 'Original Title', 'field': 'originalTitle', "sortable": True, 'editable': True, 'filter': 'agTextColumnFilter', 'floatingFilter': True},
                    {'headerName': 'Studio', 'field': 'studio', "sortable": True, 'editable': True, 'filter': 'agTextColumnFilter', 'floatingFilter': True},
                    {'headerName': 'MPAA', 'field': 'contentRating', "sortable": True, 'editable': True, 'filter': 'agTextColumnFilter', 'floatingFilter': True},
                    {'headerName': 'Critic Rating', 'field': 'rating', "sortable": True, 'editable': True, 'filter': 'agNumberColumnFilter', 'floatingFilter': True, "valueGetter": "Number(data.rating && !isNaN(Number(data.rating))) ? Number(data.rating) : null"},
                    {'headerName': 'Audience Rating', 'field': 'audienceRating', "sortable": True, 'editable': True, 'filter': 'agNumberColumnFilter', 'floatingFilter': True, "valueGetter": "Number(data.audienceRating && !isNaN(Number(data.audienceRating))) ? Number(data.audienceRating) : null"},
                    {'headerName': 'User Rating', 'field': 'userRating', "sortable": True, 'editable': True, 'filter': 'agNumberColumnFilter', 'floatingFilter': True, "valueGetter": "Number(data.userRating && !isNaN(Number(data.userRating))) ? Number(data.userRating) : null"},
                    {'headerName': 'Year', 'field': 'year', "sortable": True, 'editable': True, 'filter': 'agNumberColumnFilter', 'floatingFilter': True},
                    {'headerName': 'Tagline', 'field': 'tagline', "sortable": True, 'editable': True},
                    {'headerName': 'Summary', 'field': 'summary', "sortable": True, 'editable': True},
                    {'headerName': 'Orginally Available At', 'field': 'originallyAvailableAt', "sortable": True, 'editable': True},
                    # {"name": key, "label": key.capitalize(), "field": key, "sortable": True, "filterable": True, 'editable': True} 
                    # for key in first_item.keys() 
                    # if isinstance(first_item[key], (str, int, float)) and key in (
                    #     'ratingKey', 'title', 'studio', 'contentRating', 'rating', 'audienceRating',
                    #     'userRating', 'year', 'summary', 'originallyAvailableAt'
                    #     )
                    ]
                
                def handle_cell_value_change(e):
                    updated_row = e.args["data"]
                    row_id = updated_row["ratingKey"]

                    original_row = next((row for row in data if row["ratingKey"] == row_id), None)
                    
                    if original_row:
                        changed_column = next((key for key in updated_row if updated_row[key] != original_row[key]), None)
                        
                        if changed_column:
                            updated_value = updated_row[changed_column]

                            if changed_column not in ("ratingKey",):
                                put_url = f"{settings['host']}/library/metadata/{row_id}?{changed_column}={updated_value}"
                                put_response = requests.put(put_url, headers=headers)

                            if put_response.status_code == 200:
                                ui.notify(f"Updated key {row_id}'s {changed_column} to: {updated_value}")
                            else:
                                ui.notify(f"Failed to update key {row_id}'s {changed_column} due to {put_response.text}")
                            
                            for row in data:
                                if row["ratingKey"] == row_id:
                                    row.update(updated_row)
                                    break

                aggrid = ui.aggrid({
                    'columnDefs': columns,
                    'rowData': data,
                    'rowSelection': 'multiple',
                    'stopEditingWhenCellsLoseFocus': True,
                    'domLayout': 'autoHeight',
                }).on('cellValueChanged', handle_cell_value_change)

            else:
                ui.label("No data found for this library").style("color: red;")

    @router.add('/butler')
    def butler_page():
        headers = {"X-Plex-Token": settings["apikey"]} if settings["apikey"] else {}
        with ui.column().style("margin-left: 220px;"):
            ui.label("Butler Tasks").style("font-size: 24px; font-weight: bold;")
            ui.label("The RUN button will attempt to start a single Butler task that is enabled in the settings.")
            ui.label("Butler tasks normally run automatically during a time window configured on the server’s Settings page but can be manually started using this endpoint.")
            ui.label("Tasks will run with the following criteria:")
            ui.label("    1. Any tasks not scheduled to run on the current day will be skipped.")
            ui.label("    2. If a task is configured to run at a random time during the configured window and you are outside that window, the task will start immediately.")
            ui.label("    3. If a task is configured to run at a random time during the configured window and you are within that window, the task will be scheduled at a random time within the window.")
            ui.label("    4. If you are outside the configured window, the task will start immediately.")

            def run_butler(butler_name):
                post_url = f"{settings['host']}/butler/{butler_name}"
                post_response = requests.post(post_url, headers=headers)

                if post_response.status_code == 200:
                    ui.notify(f"Task {butler_name} successfully sent to")
                else:
                    ui.notify(f"Failed to send butler task {butler_name} due to {post_response.text}")

            with ui.row().style("flex-wrap: wrap; gap: 10px; justify-content: start;"):
                for butler in cached_data.get('butler', []):
                    with ui.card().style("width: 250px;"):
                        with ui.column():
                            ui.label(f"{butler.get('name')}").style("font-size: 18px; font-weight: bold;")
                            ui.label(f"🤖 Enabled: {butler.get('enabled')}")
                            ui.label(f"⌛ Interval: {butler.get('interval')}")
                            ui.label(f"🕔 Random Schedule: {butler.get('scheduleRandomized')}")
                            ui.button("RUN", on_click=lambda: run_butler(butler.get('name'))).style("margin-top: auto; width: 120px; text-align: center;")

                            
    @router.add('/options')
    def options_page():
        with ui.row():
            with ui.column().style("margin-left: 220px;"):
                ui.label("Settings").style("font-size: 24px; font-weight: bold;")
                host_input = ui.input("Host", value=settings["host"])
                apikey_input = ui.input("API Key", value=settings["apikey"])
                
                def save():
                    settings["host"] = host_input.value
                    settings["apikey"] = apikey_input.value
                    save_settings(settings["host"], settings["apikey"])
                    ui.notify("Settings saved!")

                ui.button("Save", on_click=save)

    with ui.column().style("position: fixed; left: 0; top: 0; bottom: 0; width: 200px; padding: 20px; background: #f5f5f5;"):
        ui.label("Navigation").style("font-weight: bold; font-size: 18px;")
        ui.button("Main", on_click=lambda: router.open(info_page))
        ui.button("Butler", on_click=lambda: router.open(butler_page))
        ui.button("Options", on_click=lambda: router.open(options_page))

    router.frame().classes('w-full p-4 bg-gray-100')

ui.run()