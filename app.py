import streamlit as st
from streamlit_keplergl import keplergl_static
import pandas as pd
import json
from keplergl import KeplerGl
import requests
import json
from datetime import datetime
# Título de la app
# st.set_page_config(layout="wide")
st.title("Rutas y puntos de detención frecuentes")



# Carga el archivo GeoJSON
# geojson_file = st.file_uploader("Sube un archivo GeoJSON", type="geojson")
responseData = None

def format_minutes(value):
    hours = value // 60
    minutes = value % 60
    return f"{int(hours)}h {int(minutes)}m" if hours else f"{int(minutes)}m"
def toGeoJsonRoute(data):
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    for item in data:
        route = item.get("route", [])
        coordinates = [(lon, lat) for lon, lat in route]

        # Crea el objeto Feature de tipo LineString
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {
                "id": item.get("reference"),
                "frequency": item.get("frequency"),
                "transportUnit": [
                    unit[list(unit.keys())[0]]["plate"] for unit in item.get("transportUnit", [])
                ],
                "types" : [
                    unit[list(unit.keys())[0]]["type"] for unit in item.get("transportUnit", [])
                ],
                "averageTravelTimeInMin": item.get("averageTravelTimeInMin"),
                "lastUpdated": item.get("lastUpdated"),
                "color_category": item.get("reference"),
                "lastUpdated": item.get("lastUpdated"),
            }
        }

        geojson["features"].append(feature)
        # with open("rutas_frecuentes.geojson", "w", encoding="utf-8") as f:
        #     json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    return geojson

def toGeoJsonStops(data):
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    for item in data:
        lon, lat = item.get("points", [0, 0])
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "id": item.get("reference"),
                "frequency": item.get("frequency"),
                "transportUnit": [
                    unit[list(unit.keys())[0]]["plate"] for unit in item.get("transportUnits", [])
                ],
                "types": [
                    unit[list(unit.keys())[0]]["type"] for unit in item.get("transportUnits", [])
                ],
                "averageStoppedInMin": item.get("averageStoppedInMin"),
                "coverageRadius": item.get("coverageRadius"),
                "color_category": item.get("reference"),
                "lastUpdated": item.get("lastUpdated"),
            }
        }
        geojson["features"].append(feature)
    return geojson


endpoint_url = "https://fmsstages-filestasks-1b138qf473xbw.s3.amazonaws.com/FrequentRoutesQA.json"
response = requests.get(endpoint_url)

averageStoppedInMin = 0

if response.status_code == 200:
    responseData = response.json() 
    lastUpdated = responseData["lastUpdated"]
    date = datetime.fromisoformat(lastUpdated.replace("Z", ""))
    formatted_date = date.strftime("%d/%m/%Y %H:%M")
    
    st.markdown(f"**Última actualización:** {formatted_date} UTC")
  
    vista = st.radio("Seleccionar vista:", ["Rutas frecuentes", "Puntos frecuentes"])
    
    if vista == "Rutas frecuentes":
        geojson = toGeoJsonRoute(responseData["sortedFrequentRoutes"])
        total_routes = len(geojson["features"])
        frecuencias = [f['properties'].get('frequency', 0) for f in geojson["features"]]
        duraciones = [f['properties'].get('averageTravelTimeInMin', 0) for f in geojson["features"]]

        # Calcular estadísticas
        total_frecuencias = sum(frecuencias)
        duracion_promedio = round(sum(duraciones) / len(duraciones), 2) if duraciones else 0

        # Mostrar tarjetas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Rutas Frecuentes", total_routes)
        col2.metric("Suma de Frecuencias", total_frecuencias)
        col3.metric("Duración Promedio de Rutas", format_minutes(duracion_promedio))
         # print(json.dumps(geojson, indent=2))
        
    else:
        geojson = toGeoJsonStops(responseData["sortedFrequentStopped"])
        total_points = len(geojson["features"])
        frecuencias = [f['properties'].get('frequency', 0) for f in geojson["features"]]
        duraciones = [f['properties'].get('averageStoppedInMin', 0) for f in geojson["features"]]


        # Calcular estadísticas
        total_frecuencias = sum(frecuencias)
        duracion_promedio = round(sum(duraciones) / len(duraciones), 2) if duraciones else 0

        # Mostrar tarjetas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Rutas Frecuentes", total_points)
        col2.metric("Suma de Frecuencias", total_frecuencias)
        col3.metric("Duración Promedio en Paradas (min)", duracion_promedio)

        averageStoppedInMin = list({f['properties'].get('averageStoppedInMin', 'Sin frecuencia') for f in geojson["features"]})

    frecuency = list({f['properties'].get('frequency', 'Sin frecuencia') for f in geojson["features"]})
    plates = list({
        plate
        for f in geojson["features"]
        for plate in f["properties"].get("transportUnit", [])
    })
    types = list({
        type
        for f in geojson["features"]
        for type in f["properties"].get("types", [])
    })

    filterByFrequecy = st.multiselect("Filtrar por frecuencia:", frecuency, default=[])
    filterByPlate = st.multiselect("Filtrar por placa:", plates, default=[])
    filterByType = st.multiselect("Filtrar por tipo de transporte:", types, default=[])
    if averageStoppedInMin != 0:
        averageStoppedInMin = st.slider("Filtrar por duración en min:", 0, 100, 0)

    # Filtrar las features
    features_filtradas = [
        f for f in geojson['features']
        if (
            (not filterByFrequecy or f['properties'].get('frequency', 'Sin frecuencia') in filterByFrequecy)
            and (not filterByPlate or any(plate in filterByPlate for plate in f['properties'].get('transportUnit', [])))
            and (not filterByType or any(type_ in filterByType for type_ in f['properties'].get('types', [])))
            and (not averageStoppedInMin or f['properties'].get('averageStoppedInMin', 'Sin frecuencia') <= averageStoppedInMin)
            
        )
    ]

    geojson_filtrado = {
        "type": "FeatureCollection",
        "features": features_filtradas
    }


    layer_type = "geojson" if vista == "Rutas frecuentes" else "point"
    dataId = "data_1" if vista == "Rutas frecuentes" else "data_2"


    #format
    if vista == "Rutas frecuentes":
       for feature in geojson["features"]:
            avg_min = feature["properties"].get("averageTravelTimeInMin", 0)
            feature["properties"]["Tiempo promedio de viaje"] = format_minutes(avg_min)
        
    else:
        for feature in geojson["features"]:
            avg_min = feature["properties"].get("averageStoppedInMin", 0)
            feature["properties"]["Tiempo promedio en paradas"] = format_minutes(avg_min)
            feature["properties"]["Radio de cobertura promedio"] = feature["properties"]["coverageRadius"]
    
    #General
    for feature in geojson["features"]:
            feature["properties"]["Frecuencia"] = feature["properties"]["frequency"]
            feature["properties"]["Placa"] = ", ".join(feature["properties"]["transportUnit"]) 
            feature["properties"]["Tipo"] = ", ".join(feature["properties"]["types"])
            feature["properties"]["Ultima actualización"] = feature["properties"]["lastUpdated"]

    toShow = [
        {"name": "id", "format": None},
        {"name": "Frecuencia", "format": None},
        {"name": "Placa", "format": None},
        {"name": "Tipo", "format": None},
        {"name": "Tiempo promedio de viaje", "format": None},
        {"name": "Ultima actualización", "format": "DD/MM/YYYY HH:mm"},
    ] if vista == "Rutas frecuentes" else [
        {"name": "id", "format": None},
        {"name": "Frecuencia", "format": None},
        {"name": "Placa", "format": None},
        {"name": "Tipo", "format": None},
        {"name": "Tiempo promedio en paradas", "format": None},
        {"name": "Radio de cobertura promedio", "format": None},
        {"name": "Ultima actualización", "format": "DD/MM/YYYY HH:mm"},
    ]

    config = {
        "version": "v1",
        "config": {
            "visState": {
                "layers": [
                    {
                        "id": "iplvtps",
                        "type": "geojson",
                        "config": {
                            "dataId": dataId,
                            "columnMode": layer_type,
                            "label": "rutas_frecuentes",
                            "color": [
                                248,
                                149,
                                112
                            ],
                            "highlightColor": [
                                252,
                                242,
                                26,
                                255
                            ],
                            "columns": {
                                "geojson": "_geojson"
                            },
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 2.1,
                                "strokeColor": None,
                                "colorRange": {
                                    "name": "Global Warming",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#4C0035",
                                        "#880030",
                                        "#B72F15",
                                        "#D6610A",
                                        "#EF9100",
                                        "#FFC300"
                                    ]
                                },
                                "strokeColorRange": {
                                    "colors": [
                                        "#4C0035",
                                        "#880030",
                                        "#B72F15",
                                        "#D6610A",
                                        "#EF9100",
                                        "#FFC300"
                                    ],
                                    "name": "Global Warming",
                                    "type": "sequential",
                                    "category": "Uber"
                                },
                                "radius": 10,
                                "sizeRange": [
                                    0,
                                    10
                                ],
                                "radiusRange": [
                                    0,
                                    50
                                ],
                                "heightRange": [
                                    0,
                                    500
                                ],
                                "elevationScale": 5,
                                "stroked": True,
                                "filled": False,
                                "enable3d": False,
                                "wireframe": False,
                                "fixedHeight": False
                            },
                            "hidden": False,
                        },
                        "visualChannels": {
                            "colorField": None,
                            "colorScale": "quantile",
                            "strokeColorField": {
                                "name": "id",
                                "type": "string"
                            },
                            "strokeColorScale": "ordinal",
                            "sizeField": None,
                            "sizeScale": "linear",
                            "heightField": None,
                            "heightScale": "linear",
                            "radiusField": None,
                            "radiusScale": "linear"
                        }
                    }
                ],
                "interactionConfig": {
                    "tooltip": {
                        "enabled": True,
                        "fieldsToShow": {
                            dataId: toShow
                        },
                        "compareMode": False,
                        "compareType": "absolute",
                    }
                }
            },
            "mapState": {
                "latitude": 14.6349,
                "longitude": -90.5069,
                "zoom": 7
            },
            "mapStyle": {
                "styleType": "positron",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": True,
                    "road": True,
                    "border": False,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False
                },
                "threeDBuildingColor": [
                    232.7874787737094,
                    232.7874787737094,
                    230.92517894351974
                ],
                "backgroundColor": [
                    0,
                    0,
                    0
                ],
                "mapStyles": {}
            },
        }
    }
    from keplergl import KeplerGl
    map = KeplerGl()
    map.add_data(data=geojson_filtrado, name=dataId)
    map.config = config
    keplergl_static(map,500,2000)
    
    
else:
    st.error("No se pudo obtener los datos del endpoint.")
